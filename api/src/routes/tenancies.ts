import { Router } from 'express';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

router.get('/', async (req, res) => {
  const { userId, role } = req.user!;

  if (role === 'tenant') {
    const tenancies = await prisma.tenancy.findMany({
      where: { tenantId: userId },
      include: {
        room: { include: { property: true } },
        application: true,
      },
      orderBy: { createdAt: 'desc' },
    });
    return res.json({ tenancies });
  }

  const tenancies = await prisma.tenancy.findMany({
    where: {
      room: {
        property: role === 'admin' ? undefined : {
          OR: [{ ownerId: userId }, { managerId: userId }],
        },
      },
    },
    include: {
      tenant: { select: { id: true, firstName: true, lastName: true, email: true, phone: true } },
      room: { include: { property: true } },
    },
    orderBy: { createdAt: 'desc' },
  });
  res.json({ tenancies });
});

router.get('/:id', async (req, res) => {
  const tenancy = await prisma.tenancy.findUnique({
    where: { id: req.params.id },
    include: {
      tenant: true,
      room: { include: { property: { include: { documents: true } } } },
      application: true,
    },
  });
  if (!tenancy) return res.status(404).json({ error: 'Tenancy not found' });

  const { userId, role } = req.user!;
  const property = tenancy.room.property;
  const canView =
    role === 'admin' ||
    tenancy.tenantId === userId ||
    property.ownerId === userId ||
    property.managerId === userId;
  if (!canView) return res.status(403).json({ error: 'Access denied' });

  res.json({ tenancy });
});

export default router;
