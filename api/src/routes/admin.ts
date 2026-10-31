import { Router } from 'express';
import { prisma } from '../lib/prisma';
import { authMiddleware, requireRoles } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);
router.use(requireRoles('admin'));

router.get('/users', async (req, res) => {
  const users = await prisma.user.findMany({
    select: {
      id: true,
      email: true,
      firstName: true,
      lastName: true,
      role: true,
      verified: true,
      active: true,
      phone: true,
      createdAt: true,
      _count: {
        select: {
          ownedProperties: true,
          tenancies: true,
        },
      },
    },
    orderBy: { createdAt: 'desc' },
  });
  res.json({ users });
});

router.patch('/users/:id', async (req, res) => {
  const { verified, active } = req.body;
  const user = await prisma.user.update({
    where: { id: req.params.id },
    data: {
      ...(verified !== undefined ? { verified } : {}),
      ...(active !== undefined ? { active } : {}),
    },
    select: {
      id: true,
      email: true,
      firstName: true,
      lastName: true,
      role: true,
      verified: true,
      active: true,
    },
  });
  res.json({ user });
});

router.get('/analytics', async (_req, res) => {
  const [users, properties, listings, maintenance, applications] = await Promise.all([
    prisma.user.count(),
    prisma.property.count(),
    prisma.listing.count({ where: { status: 'active' } }),
    prisma.maintenanceRequest.count({ where: { status: { notIn: ['closed', 'cancelled'] } } }),
    prisma.application.count({ where: { status: 'pending' } }),
  ]);

  const usersByRole = await prisma.user.groupBy({
    by: ['role'],
    _count: { role: true },
  });

  res.json({
    analytics: {
      totalUsers: users,
      totalProperties: properties,
      activeListings: listings,
      openMaintenance: maintenance,
      pendingApplications: applications,
      usersByRole: Object.fromEntries(usersByRole.map((r) => [r.role, r._count.role])),
    },
  });
});

router.get('/contractors', async (_req, res) => {
  const contractors = await prisma.user.findMany({
    where: { role: 'contractor', active: true },
    select: { id: true, firstName: true, lastName: true, email: true, phone: true, verified: true },
  });
  res.json({ contractors });
});

export default router;
