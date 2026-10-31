import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';

const router = Router();

const listingSchema = z.object({
  roomId: z.string(),
  title: z.string().min(1),
  description: z.string().optional(),
  photos: z.array(z.string().url()).optional(),
  status: z.enum(['draft', 'active', 'paused', 'let']).optional(),
  availableFrom: z.string().datetime().optional(),
  billsIncluded: z.boolean().optional(),
});

router.get('/', authMiddleware, async (req, res) => {
  const { userId, role } = req.user!;
  const status = req.query.status as string | undefined;

  if (req.query.mine && !['landlord', 'property_manager', 'admin'].includes(role)) {
    return res.status(403).json({ error: 'Access denied' });
  }

  if (role === 'tenant' || !req.query.mine) {
    const listings = await prisma.listing.findMany({
      where: {
        status: status ? (status as 'active') : 'active',
      },
      include: {
        room: {
          include: {
            property: {
              select: { id: true, name: true, city: true, postcode: true, addressLine1: true },
            },
          },
        },
        _count: { select: { applications: true } },
      },
      orderBy: { createdAt: 'desc' },
    });
    return res.json({ listings });
  }

  const listings = await prisma.listing.findMany({
    where: {
      ...(status ? { status: status as 'active' } : {}),
      room: {
        property:
          role === 'landlord'
            ? { ownerId: userId }
            : role === 'property_manager'
              ? { managerId: userId }
              : {},
      },
    },
    include: {
      room: { include: { property: true } },
      applications: { include: { tenant: { select: { id: true, firstName: true, lastName: true, email: true } } } },
    },
    orderBy: { createdAt: 'desc' },
  });
  res.json({ listings });
});

router.post('/', authMiddleware, async (req, res) => {
  const { userId, role } = req.user!;
  if (!['landlord', 'property_manager', 'admin'].includes(role)) {
    return res.status(403).json({ error: 'Insufficient permissions' });
  }

  try {
    const data = listingSchema.parse(req.body);
    const room = await prisma.room.findUnique({
      where: { id: data.roomId },
      include: { property: true, listing: true },
    });
    if (!room) return res.status(404).json({ error: 'Room not found' });
    if (room.listing) return res.status(409).json({ error: 'Room already has a listing' });

    const canManage =
      role === 'admin' ||
      room.property.ownerId === userId ||
      room.property.managerId === userId;
    if (!canManage) return res.status(403).json({ error: 'Access denied' });

    const listing = await prisma.listing.create({
      data: {
        roomId: data.roomId,
        title: data.title,
        description: data.description,
        photos: data.photos ? JSON.stringify(data.photos) : undefined,
        status: data.status ?? 'draft',
        availableFrom: data.availableFrom ? new Date(data.availableFrom) : undefined,
        billsIncluded: data.billsIncluded ?? false,
      },
      include: { room: { include: { property: true } } },
    });
    res.status(201).json({ listing });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to create listing' });
  }
});

router.get('/:id', authMiddleware, async (req, res) => {
  const { userId, role } = req.user!;
  const listingId = String(req.params.id);
  const listing = await prisma.listing.findUnique({
    where: { id: listingId },
    include: {
      room: {
        include: {
          property: {
            select: {
              id: true,
              name: true,
              city: true,
              postcode: true,
              addressLine1: true,
              description: true,
              ownerId: true,
              managerId: true,
            },
          },
        },
      },
      applications: {
        include: { tenant: { select: { id: true, firstName: true, lastName: true, email: true } } },
      },
    },
  });
  if (!listing) return res.status(404).json({ error: 'Listing not found' });

  const property = listing.room.property;
  const canSeeApplications =
    role === 'admin' ||
    property.ownerId === userId ||
    property.managerId === userId;

  res.json({
    listing: {
      ...listing,
      applications: canSeeApplications ? listing.applications : [],
    },
  });
});

router.patch('/:id', authMiddleware, async (req, res) => {
  const listingId = String(req.params.id);
  const listing = await prisma.listing.findUnique({
    where: { id: listingId },
    include: { room: { include: { property: true } } },
  });
  if (!listing) return res.status(404).json({ error: 'Listing not found' });

  const { userId, role } = req.user!;
  const canManage =
    role === 'admin' ||
    listing.room.property.ownerId === userId ||
    listing.room.property.managerId === userId;
  if (!canManage) return res.status(403).json({ error: 'Access denied' });

  try {
    const data = listingSchema.partial().omit({ roomId: true }).parse(req.body);
    const { photos, availableFrom, ...rest } = data;
    const updated = await prisma.listing.update({
      where: { id: listingId },
      data: {
        ...rest,
        ...(photos !== undefined ? { photos: JSON.stringify(photos) } : {}),
        availableFrom: availableFrom ? new Date(availableFrom) : undefined,
      },
      include: { room: { include: { property: true } } },
    });
    res.json({ listing: updated });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to update listing' });
  }
});

export default router;
