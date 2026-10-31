import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

const applicationSchema = z.object({
  listingId: z.string(),
  message: z.string().optional(),
  moveInDate: z.string().datetime().optional(),
});

router.get('/', async (req, res) => {
  const { userId, role } = req.user!;

  if (role === 'tenant') {
    const applications = await prisma.application.findMany({
      where: { tenantId: userId },
      include: {
        listing: { include: { room: { include: { property: true } } } },
        tenancy: true,
      },
      orderBy: { createdAt: 'desc' },
    });
    return res.json({ applications });
  }

  const applications = await prisma.application.findMany({
    where: {
      listing: {
        room: {
          property: role === 'admin' ? undefined : {
            OR: [{ ownerId: userId }, { managerId: userId }],
          },
        },
      },
    },
    include: {
      tenant: { select: { id: true, firstName: true, lastName: true, email: true, phone: true } },
      listing: { include: { room: { include: { property: true } } } },
    },
    orderBy: { createdAt: 'desc' },
  });
  res.json({ applications });
});

router.post('/', async (req, res) => {
  const { userId, role } = req.user!;
  if (role !== 'tenant') {
    return res.status(403).json({ error: 'Only tenants can apply for rooms' });
  }

  try {
    const data = applicationSchema.parse(req.body);
    const listing = await prisma.listing.findUnique({
      where: { id: data.listingId },
      include: { room: true },
    });
    if (!listing || listing.status !== 'active') {
      return res.status(400).json({ error: 'Listing is not available' });
    }

    const existing = await prisma.application.findFirst({
      where: { listingId: data.listingId, tenantId: userId, status: 'pending' },
    });
    if (existing) {
      return res.status(409).json({ error: 'You already have a pending application' });
    }

    const application = await prisma.application.create({
      data: {
        listingId: data.listingId,
        tenantId: userId,
        message: data.message,
        moveInDate: data.moveInDate ? new Date(data.moveInDate) : undefined,
      },
      include: { listing: { include: { room: { include: { property: true } } } } },
    });

    const property = await prisma.property.findUnique({
      where: { id: listing.room.propertyId },
    });
    if (property) {
      await prisma.notification.create({
        data: {
          userId: property.ownerId,
          type: 'application',
          title: 'New room application',
          body: `A tenant has applied for ${listing.title}`,
          data: JSON.stringify({ applicationId: application.id }),
        },
      });
    }

    res.status(201).json({ application });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: err.issues[0]?.message });
    }
    res.status(500).json({ error: 'Failed to submit application' });
  }
});

router.patch('/:id', async (req, res) => {
  const { userId, role } = req.user!;
  const application = await prisma.application.findUnique({
    where: { id: req.params.id },
    include: { listing: { include: { room: { include: { property: true } } } }, tenant: true },
  });
  if (!application) return res.status(404).json({ error: 'Application not found' });

  const property = application.listing.room.property;
  const canReview =
    role === 'admin' ||
    property.ownerId === userId ||
    property.managerId === userId;
  if (!canReview) return res.status(403).json({ error: 'Access denied' });

  const status = req.body.status as 'approved' | 'rejected';
  if (!['approved', 'rejected'].includes(status)) {
    return res.status(400).json({ error: 'Status must be approved or rejected' });
  }

  const updated = await prisma.application.update({
    where: { id: req.params.id },
    data: { status, reviewedAt: new Date() },
  });

  if (status === 'approved') {
    const room = application.listing.room;
    await prisma.tenancy.create({
      data: {
        roomId: room.id,
        tenantId: application.tenantId,
        applicationId: application.id,
        startDate: application.moveInDate ?? new Date(),
        rentPcm: room.rentPcm,
        deposit: room.deposit,
        status: 'active',
      },
    });
    await prisma.room.update({ where: { id: room.id }, data: { status: 'occupied' } });
    await prisma.listing.update({
      where: { id: application.listingId },
      data: { status: 'let' },
    });
  }

  await prisma.notification.create({
    data: {
      userId: application.tenantId,
      type: 'application',
      title: status === 'approved' ? 'Application approved' : 'Application declined',
      body: `Your application for ${application.listing.title} has been ${status}`,
      data: JSON.stringify({ applicationId: application.id }),
    },
  });

  res.json({ application: updated });
});

export default router;
