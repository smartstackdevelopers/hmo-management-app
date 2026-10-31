import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';
import { canAccessMaintenance, canReportMaintenance } from '../lib/access';

const router = Router();
router.use(authMiddleware);

const requestSchema = z.object({
  propertyId: z.string(),
  roomId: z.string().optional(),
  title: z.string().min(1),
  description: z.string().min(1),
  category: z.string().min(1),
  priority: z.enum(['low', 'medium', 'high', 'emergency']).optional(),
  photoUrls: z.array(z.string()).optional(),
});

const updateSchema = z.object({
  status: z
    .enum(['open', 'assigned', 'in_progress', 'awaiting_parts', 'completed', 'closed', 'cancelled'])
    .optional(),
  contractorId: z.string().optional(),
  note: z.string().optional(),
  photoUrls: z.array(z.string()).optional(),
});

router.get('/', async (req, res) => {
  const { userId, role } = req.user!;

  let where = {};
  if (role === 'tenant') {
    where = { reporterId: userId };
  } else if (role === 'contractor') {
    where = { contractorId: userId };
  } else if (role === 'landlord') {
    where = { property: { ownerId: userId } };
  } else if (role === 'property_manager') {
    where = { property: { managerId: userId } };
  } else if (role === 'admin') {
    // Admin sees all maintenance requests
  } else {
    return res.status(403).json({ error: 'Access denied' });
  }

  const requests = await prisma.maintenanceRequest.findMany({
    where,
    include: {
      property: { select: { id: true, name: true, addressLine1: true, postcode: true } },
      room: { select: { id: true, name: true } },
      reporter: { select: { id: true, firstName: true, lastName: true } },
      contractor: { select: { id: true, firstName: true, lastName: true, phone: true } },
      updates: {
        include: { author: { select: { id: true, firstName: true, lastName: true } } },
        orderBy: { createdAt: 'asc' },
      },
    },
    orderBy: { createdAt: 'desc' },
  });

  res.json({
    requests: requests.map((r) => ({
      ...r,
      photoUrls: JSON.parse(r.photoUrls),
      updates: r.updates.map((u) => ({ ...u, photoUrls: JSON.parse(u.photoUrls) })),
    })),
  });
});

router.get('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const request = await prisma.maintenanceRequest.findUnique({
    where: { id: req.params.id },
    include: {
      property: true,
      room: true,
      reporter: { select: { id: true, firstName: true, lastName: true, email: true } },
      contractor: { select: { id: true, firstName: true, lastName: true, phone: true } },
      updates: {
        include: { author: { select: { id: true, firstName: true, lastName: true } } },
        orderBy: { createdAt: 'asc' },
      },
    },
  });
  if (!request) return res.status(404).json({ error: 'Request not found' });

  const allowed = await canAccessMaintenance(userId, role, request);
  if (!allowed) return res.status(403).json({ error: 'Access denied' });

  res.json({
    request: {
      ...request,
      photoUrls: JSON.parse(request.photoUrls),
      updates: request.updates.map((u) => ({ ...u, photoUrls: JSON.parse(u.photoUrls) })),
    },
  });
});

router.post('/', async (req, res) => {
  const { userId, role } = req.user!;
  if (!['tenant', 'landlord', 'property_manager', 'admin'].includes(role)) {
    return res.status(403).json({ error: 'Insufficient permissions' });
  }

  try {
    const data = requestSchema.parse(req.body);
    const allowed = await canReportMaintenance(userId, role, data.propertyId);
    if (!allowed) return res.status(403).json({ error: 'You cannot report repairs for this property' });

    const request = await prisma.maintenanceRequest.create({
      data: {
        propertyId: data.propertyId,
        roomId: data.roomId,
        reporterId: userId,
        title: data.title,
        description: data.description,
        category: data.category,
        priority: data.priority ?? 'medium',
        photoUrls: JSON.stringify(data.photoUrls ?? []),
      },
      include: {
        property: true,
        room: true,
        reporter: { select: { id: true, firstName: true, lastName: true } },
      },
    });

    const property = await prisma.property.findUnique({ where: { id: data.propertyId } });
    if (property) {
      await prisma.notification.create({
        data: {
          userId: property.ownerId,
          type: 'maintenance',
          title: 'New repair request',
          body: data.title,
          data: JSON.stringify({ maintenanceId: request.id }),
        },
      });
    }

    res.status(201).json({ request: { ...request, photoUrls: JSON.parse(request.photoUrls) } });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to create request' });
  }
});

router.patch('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const existing = await prisma.maintenanceRequest.findUnique({
    where: { id: req.params.id },
    include: { property: true },
  });
  if (!existing) return res.status(404).json({ error: 'Request not found' });

  try {
    const data = updateSchema.parse(req.body);
    const isOwner = existing.property.ownerId === userId || existing.property.managerId === userId;
    const isContractor = existing.contractorId === userId;
    const isReporter = existing.reporterId === userId;

    if (data.contractorId && !['landlord', 'property_manager', 'admin'].includes(role)) {
      return res.status(403).json({ error: 'Only managers can assign contractors' });
    }
    if (data.status && role === 'contractor' && !isContractor) {
      return res.status(403).json({ error: 'Access denied' });
    }
    if (data.status && role === 'tenant' && !isReporter) {
      return res.status(403).json({ error: 'Access denied' });
    }
    if (!isOwner && !isContractor && !isReporter && role !== 'admin') {
      return res.status(403).json({ error: 'Access denied' });
    }

    const updateData: Record<string, unknown> = {};
    if (data.status) {
      updateData.status = data.status;
      if (data.status === 'assigned' && data.contractorId) {
        updateData.contractorId = data.contractorId;
      }
      if (data.status === 'closed' || data.status === 'completed') {
        updateData.completedAt = new Date();
      }
    }
    if (data.contractorId && !data.status) {
      updateData.contractorId = data.contractorId;
      updateData.status = 'assigned';
    }

    const request = await prisma.maintenanceRequest.update({
      where: { id: req.params.id },
      data: updateData,
      include: {
        property: true,
        contractor: { select: { id: true, firstName: true, lastName: true } },
        updates: true,
      },
    });

    if (data.note) {
      await prisma.maintenanceUpdate.create({
        data: {
          requestId: req.params.id,
          authorId: userId,
          note: data.note,
          photoUrls: JSON.stringify(data.photoUrls ?? []),
        },
      });
    }

    if (data.contractorId) {
      await prisma.notification.create({
        data: {
          userId: data.contractorId,
          type: 'maintenance',
          title: 'New job assigned',
          body: existing.title,
          data: JSON.stringify({ maintenanceId: existing.id }),
        },
      });
    }

    res.json({ request: { ...request, photoUrls: JSON.parse(request.photoUrls) } });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to update request' });
  }
});

export default router;
