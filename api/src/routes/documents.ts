import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { z } from 'zod';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';
import { canAccessProperty, canManageProperty, getDocumentListFilter } from '../lib/access';

const router = Router();
router.use(authMiddleware);

const uploadDir = process.env.UPLOAD_DIR ?? './uploads';
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, uploadDir),
  filename: (_req, file, cb) => {
    const unique = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
    cb(null, `${unique}${path.extname(file.originalname)}`);
  },
});

const upload = multer({ storage, limits: { fileSize: 10 * 1024 * 1024 } });

const documentSchema = z.object({
  propertyId: z.string().optional(),
  type: z.enum([
    'hmo_licence', 'epc', 'gas_safety', 'electrical_safety', 'insurance',
    'tenancy_agreement', 'inventory', 'inspection_report', 'contractor_invoice', 'other',
  ]),
  name: z.string().min(1),
  expiryDate: z.string().datetime().optional(),
  notes: z.string().optional(),
});

router.get('/', async (req, res) => {
  const { userId, role } = req.user!;
  const propertyId = req.query.propertyId as string | undefined;

  if (propertyId) {
    const allowed = await canAccessProperty(userId, role, propertyId);
    if (!allowed) return res.status(403).json({ error: 'Access denied' });
  }

  const where = propertyId
    ? { propertyId }
    : await getDocumentListFilter(userId, role);

  const documents = await prisma.document.findMany({
    where,
    include: {
      property: { select: { id: true, name: true } },
      uploader: { select: { id: true, firstName: true, lastName: true } },
    },
    orderBy: { expiryDate: 'asc' },
  });

  const enriched = documents.map((d) => {
    const daysLeft = d.expiryDate
      ? Math.ceil((d.expiryDate.getTime() - Date.now()) / (24 * 60 * 60 * 1000))
      : null;
    const riskLevel =
      daysLeft === null
        ? 'info'
        : daysLeft < 0
          ? 'critical'
          : daysLeft <= 7
            ? 'critical'
            : daysLeft <= 30
              ? 'high'
              : 'medium';
    return { ...d, daysLeft, riskLevel };
  });

  res.json({ documents: enriched });
});

router.get('/evidence-pack', async (req, res) => {
  const { userId, role } = req.user!;
  const propertyId = req.query.propertyId as string | undefined;
  if (!propertyId) return res.status(400).json({ error: 'propertyId is required' });

  const allowed = await canAccessProperty(userId, role, propertyId);
  if (!allowed) return res.status(403).json({ error: 'Access denied' });

  const property = await prisma.property.findUnique({
    where: { id: propertyId },
    include: {
      documents: true,
      rooms: true,
      maintenance: {
        orderBy: { createdAt: 'desc' },
        take: 25,
      },
      inspections: {
        orderBy: { scheduledAt: 'desc' },
        take: 12,
      },
    },
  });
  if (!property) return res.status(404).json({ error: 'Property not found' });

  const requiredTypes = ['hmo_licence', 'epc', 'gas_safety', 'electrical_safety', 'insurance'];
  const now = new Date();
  const complianceChecklist = requiredTypes.map((type) => {
    const doc = property.documents.find((d) => d.type === type);
    const valid = !!doc && (!doc.expiryDate || doc.expiryDate > now);
    return {
      type,
      present: !!doc,
      valid,
      expiryDate: doc?.expiryDate ?? null,
      fileUrl: doc?.fileUrl ?? null,
    };
  });

  const openRepairs = property.maintenance.filter((m) => !['closed', 'cancelled'].includes(m.status));
  const completedRepairs30d = property.maintenance.filter(
    (m) => m.completedAt && m.completedAt > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
  );

  res.json({
    evidencePack: {
      generatedAt: new Date().toISOString(),
      property: {
        id: property.id,
        name: property.name,
        addressLine1: property.addressLine1,
        city: property.city,
        postcode: property.postcode,
        hmoLicenceNumber: property.hmoLicenceNumber,
      },
      complianceChecklist,
      summary: {
        roomCount: property.rooms.length,
        documentsCount: property.documents.length,
        openRepairs: openRepairs.length,
        completedRepairs30d: completedRepairs30d.length,
        inspectionsLast12: property.inspections.length,
      },
      latestDocuments: property.documents
        .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
        .slice(0, 20)
        .map((d) => ({
          id: d.id,
          type: d.type,
          name: d.name,
          fileUrl: d.fileUrl,
          expiryDate: d.expiryDate,
          createdAt: d.createdAt,
        })),
      maintenanceLog: property.maintenance.slice(0, 25).map((m) => ({
        id: m.id,
        title: m.title,
        priority: m.priority,
        status: m.status,
        createdAt: m.createdAt,
        completedAt: m.completedAt,
      })),
    },
  });
});

router.post('/', upload.single('file'), async (req, res) => {
  const { userId, role } = req.user!;
  if (!req.file) {
    return res.status(400).json({ error: 'File is required' });
  }

  try {
    const data = documentSchema.parse(req.body);
    const fileUrl = `/uploads/${req.file.filename}`;

    if (data.propertyId) {
      const property = await prisma.property.findUnique({ where: { id: data.propertyId } });
      if (!property) return res.status(404).json({ error: 'Property not found' });

      if (['landlord', 'property_manager', 'admin'].includes(role)) {
        const canManage = await canManageProperty(userId, role, property);
        if (!canManage) return res.status(403).json({ error: 'Access denied' });
      } else if (role === 'tenant') {
        const tenancy = await prisma.tenancy.findFirst({
          where: { tenantId: userId, status: 'active', room: { propertyId: data.propertyId } },
        });
        if (!tenancy) return res.status(403).json({ error: 'Access denied' });
        const tenantTypes = ['tenancy_agreement', 'inventory', 'other'];
        if (!tenantTypes.includes(data.type)) {
          return res.status(403).json({ error: 'Tenants can only upload tenancy-related documents' });
        }
      } else if (role === 'contractor') {
        const job = await prisma.maintenanceRequest.findFirst({
          where: { contractorId: userId, propertyId: data.propertyId },
        });
        if (!job || data.type !== 'contractor_invoice') {
          return res.status(403).json({ error: 'Contractors can only upload invoices for assigned jobs' });
        }
      } else {
        return res.status(403).json({ error: 'Access denied' });
      }
    } else if (!['tenant', 'contractor'].includes(role)) {
      // Landlords/PMs must attach compliance docs to a property
      if (['hmo_licence', 'epc', 'gas_safety', 'electrical_safety', 'insurance', 'inspection_report'].includes(data.type)) {
        return res.status(400).json({ error: 'Property is required for compliance documents' });
      }
    }

    const document = await prisma.document.create({
      data: {
        propertyId: data.propertyId,
        uploadedBy: userId,
        type: data.type,
        name: data.name,
        fileUrl,
        expiryDate: data.expiryDate ? new Date(data.expiryDate) : undefined,
        notes: data.notes,
      },
      include: { property: { select: { id: true, name: true } } },
    });

    res.status(201).json({ document });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to upload document' });
  }
});

router.delete('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const document = await prisma.document.findUnique({
    where: { id: req.params.id },
    include: { property: true },
  });
  if (!document) return res.status(404).json({ error: 'Document not found' });

  const canDelete =
    role === 'admin' ||
    document.uploadedBy === userId ||
    document.property?.ownerId === userId ||
    document.property?.managerId === userId;
  if (!canDelete) return res.status(403).json({ error: 'Access denied' });

  await prisma.document.delete({ where: { id: req.params.id } });
  res.json({ success: true });
});

export default router;
