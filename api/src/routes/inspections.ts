import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';
import { canManageProperty } from '../lib/access';

const router = Router();
router.use(authMiddleware);

const inspectionSchema = z.object({
  propertyId: z.string(),
  scheduledAt: z.string().datetime(),
  notes: z.string().optional(),
});

router.get('/', async (req, res) => {
  const { userId, role } = req.user!;

  let where: Record<string, unknown> = { id: { in: [] } };
  if (role === 'property_manager') {
    where = { inspectorId: userId };
  } else if (role === 'landlord') {
    where = { property: { ownerId: userId } };
  } else if (role === 'admin') {
    where = {};
  }

  const inspections = await prisma.inspection.findMany({
    where,
    include: {
      property: { select: { id: true, name: true, addressLine1: true, postcode: true } },
      inspector: { select: { id: true, firstName: true, lastName: true } },
    },
    orderBy: { scheduledAt: 'asc' },
  });

  res.json({
    inspections: inspections.map((i) => ({
      ...i,
      findings: JSON.parse(i.findings),
    })),
  });
});

router.post('/', async (req, res) => {
  const { userId, role } = req.user!;
  if (!['property_manager', 'admin'].includes(role)) {
    return res.status(403).json({ error: 'Insufficient permissions' });
  }

  try {
    const data = inspectionSchema.parse(req.body);
    const property = await prisma.property.findUnique({ where: { id: data.propertyId } });
    if (!property) return res.status(404).json({ error: 'Property not found' });

    if (role === 'property_manager') {
      const canManage = await canManageProperty(userId, role, property);
      if (!canManage) return res.status(403).json({ error: 'You can only inspect properties you manage' });
    }

    const inspection = await prisma.inspection.create({
      data: {
        propertyId: data.propertyId,
        inspectorId: userId,
        scheduledAt: new Date(data.scheduledAt),
        notes: data.notes,
      },
      include: {
        property: { select: { id: true, name: true } },
      },
    });
    res.status(201).json({ inspection: { ...inspection, findings: [] } });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to schedule inspection' });
  }
});

router.patch('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const inspection = await prisma.inspection.findUnique({
    where: { id: req.params.id },
    include: { property: true },
  });
  if (!inspection) return res.status(404).json({ error: 'Inspection not found' });

  const canEdit =
    role === 'admin' ||
    inspection.inspectorId === userId ||
    inspection.property.ownerId === userId;
  if (!canEdit) return res.status(403).json({ error: 'Access denied' });

  const updateData: Record<string, unknown> = {};
  if (req.body.status) updateData.status = req.body.status;
  if (req.body.notes) updateData.notes = req.body.notes;
  if (req.body.findings) updateData.findings = JSON.stringify(req.body.findings);
  if (req.body.status === 'completed') updateData.completedAt = new Date();

  const updated = await prisma.inspection.update({
    where: { id: req.params.id },
    data: updateData,
    include: { property: true, inspector: { select: { id: true, firstName: true, lastName: true } } },
  });

  res.json({ inspection: { ...updated, findings: JSON.parse(updated.findings) } });
});

export default router;
