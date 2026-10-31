import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';
import { canManageProperty, getAccessiblePropertyIds } from '../lib/access';

const router = Router();
router.use(authMiddleware);

const propertySchema = z.object({
  name: z.string().min(1),
  addressLine1: z.string().min(1),
  addressLine2: z.string().optional(),
  city: z.string().min(1),
  county: z.string().optional(),
  postcode: z.string().min(1),
  hmoLicenceNumber: z.string().optional(),
  maxOccupants: z.number().int().min(0).optional(),
  description: z.string().optional(),
  emergencyContact: z.string().optional(),
  houseRules: z.string().optional(),
  managerId: z.string().optional(),
});

router.get('/', async (req, res) => {
  const { userId, role } = req.user!;
  const ids = await getAccessiblePropertyIds(userId, role);

  const properties = await prisma.property.findMany({
    where: role === 'admin' ? undefined : { id: { in: ids } },
    include: {
      owner: { select: { id: true, firstName: true, lastName: true, email: true } },
      manager: { select: { id: true, firstName: true, lastName: true, email: true } },
      rooms: { include: { listing: true, tenancies: { where: { status: 'active' } } } },
      _count: { select: { maintenance: { where: { status: { notIn: ['closed', 'cancelled'] } } } } },
    },
    orderBy: { createdAt: 'desc' },
  });

  res.json({ properties });
});

router.get('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const ids = await getAccessiblePropertyIds(userId, role);
  if (role !== 'admin' && !ids.includes(req.params.id)) {
    return res.status(403).json({ error: 'Access denied' });
  }

  const property = await prisma.property.findUnique({
    where: { id: req.params.id },
    include: {
      owner: { select: { id: true, firstName: true, lastName: true, email: true } },
      manager: { select: { id: true, firstName: true, lastName: true, email: true } },
      rooms: { include: { listing: true, tenancies: { where: { status: 'active' }, include: { tenant: true } } } },
      documents: { orderBy: { expiryDate: 'asc' } },
    },
  });

  if (!property) return res.status(404).json({ error: 'Property not found' });
  res.json({ property });
});

router.post('/', async (req, res) => {
  const { userId, role } = req.user!;
  if (!['landlord', 'admin'].includes(role)) {
    return res.status(403).json({ error: 'Only landlords can create properties' });
  }

  try {
    const data = propertySchema.parse(req.body);
    const property = await prisma.property.create({
      data: {
        ...data,
        ownerId: role === 'admin' && req.body.ownerId ? req.body.ownerId : userId,
      },
      include: { rooms: true },
    });
    res.status(201).json({ property });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to create property' });
  }
});

router.patch('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const property = await prisma.property.findUnique({ where: { id: req.params.id } });
  if (!property) return res.status(404).json({ error: 'Property not found' });

  const canEdit =
    role === 'admin' ||
    property.ownerId === userId ||
    property.managerId === userId;
  if (!canEdit) return res.status(403).json({ error: 'Access denied' });

  try {
    const data = propertySchema.partial().parse(req.body);
    const updated = await prisma.property.update({
      where: { id: req.params.id },
      data,
      include: { rooms: { include: { listing: true } } },
    });
    res.json({ property: updated });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to update property' });
  }
});

router.delete('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const property = await prisma.property.findUnique({ where: { id: req.params.id } });
  if (!property) return res.status(404).json({ error: 'Property not found' });
  if (role !== 'admin' && property.ownerId !== userId) {
    return res.status(403).json({ error: 'Access denied' });
  }

  await prisma.property.delete({ where: { id: req.params.id } });
  res.json({ success: true });
});

// Rooms
const roomSchema = z.object({
  name: z.string().min(1),
  floor: z.string().optional(),
  rentPcm: z.number().int().min(0),
  deposit: z.number().int().min(0).optional(),
  sizeSqm: z.number().optional(),
  furnished: z.boolean().optional(),
  ensuite: z.boolean().optional(),
  status: z.enum(['available', 'occupied', 'maintenance', 'unavailable']).optional(),
  description: z.string().optional(),
});

router.post('/:propertyId/rooms', async (req, res) => {
  const { userId, role } = req.user!;
  const property = await prisma.property.findUnique({ where: { id: req.params.propertyId } });
  if (!property) return res.status(404).json({ error: 'Property not found' });
  if (role !== 'admin' && property.ownerId !== userId && property.managerId !== userId) {
    return res.status(403).json({ error: 'Access denied' });
  }

  try {
    const data = roomSchema.parse(req.body);
    const room = await prisma.room.create({
      data: { ...data, propertyId: req.params.propertyId },
    });
    res.status(201).json({ room });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to create room' });
  }
});

router.patch('/rooms/:roomId', async (req, res) => {
  const room = await prisma.room.findUnique({
    where: { id: req.params.roomId },
    include: { property: true },
  });
  if (!room) return res.status(404).json({ error: 'Room not found' });

  const { userId, role } = req.user!;
  const canEdit =
    role === 'admin' ||
    room.property.ownerId === userId ||
    room.property.managerId === userId;
  if (!canEdit) return res.status(403).json({ error: 'Access denied' });

  try {
    const data = roomSchema.partial().parse(req.body);
    const updated = await prisma.room.update({
      where: { id: req.params.roomId },
      data,
      include: { listing: true },
    });
    res.json({ room: updated });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to update room' });
  }
});

router.delete('/rooms/:roomId', async (req, res) => {
  const room = await prisma.room.findUnique({
    where: { id: req.params.roomId },
    include: { property: true },
  });
  if (!room) return res.status(404).json({ error: 'Room not found' });

  const { userId, role } = req.user!;
  if (role !== 'admin' && room.property.ownerId !== userId) {
    return res.status(403).json({ error: 'Access denied' });
  }

  await prisma.room.delete({ where: { id: req.params.roomId } });
  res.json({ success: true });
});

export default router;
