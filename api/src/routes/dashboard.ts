import { Router } from 'express';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

router.get('/', async (req, res) => {
  const { userId, role } = req.user!;

  const stats: Record<string, number | string> = {};

  if (role === 'landlord') {
    const properties = await prisma.property.count({ where: { ownerId: userId } });
    const rooms = await prisma.room.count({
      where: { property: { ownerId: userId } },
    });
    const occupied = await prisma.room.count({
      where: { property: { ownerId: userId }, status: 'occupied' },
    });
    const openMaintenance = await prisma.maintenanceRequest.count({
      where: {
        property: { ownerId: userId },
        status: { notIn: ['closed', 'cancelled'] },
      },
    });
    const expiringDocs = await prisma.document.count({
      where: {
        property: { ownerId: userId },
        expiryDate: { lte: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) },
      },
    });
    const expiring90 = await prisma.document.count({
      where: {
        property: { ownerId: userId },
        expiryDate: { lte: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000) },
      },
    });
    const pendingApps = await prisma.application.count({
      where: {
        status: 'pending',
        listing: { room: { property: { ownerId: userId } } },
      },
    });

    stats.properties = properties;
    stats.rooms = rooms;
    stats.occupiedRooms = occupied;
    stats.openMaintenance = openMaintenance;
    stats.expiringDocs = expiringDocs;
    stats.expiringDocs90 = expiring90;
    stats.pendingApplications = pendingApps;
  } else if (role === 'tenant') {
    const tenancy = await prisma.tenancy.findFirst({
      where: { tenantId: userId, status: 'active' },
      include: { room: true },
    });
    const openRepairs = await prisma.maintenanceRequest.count({
      where: { reporterId: userId, status: { notIn: ['closed', 'cancelled'] } },
    });
    const unreadMessages = await prisma.notification.count({
      where: { userId, type: 'message', read: false },
    });

    stats.rentPcm = tenancy?.rentPcm ?? 0;
    stats.openRepairs = openRepairs;
    stats.unreadMessages = unreadMessages;
    stats.hasTenancy = tenancy ? 1 : 0;
  } else if (role === 'property_manager') {
    stats.managedProperties = await prisma.property.count({ where: { managerId: userId } });
    stats.inspectionsDue = await prisma.inspection.count({
      where: {
        inspectorId: userId,
        status: 'scheduled',
        scheduledAt: { lte: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) },
      },
    });
    stats.openMaintenance = await prisma.maintenanceRequest.count({
      where: {
        property: { managerId: userId },
        status: { notIn: ['closed', 'cancelled'] },
      },
    });
    stats.pendingApplications = await prisma.application.count({
      where: {
        status: 'pending',
        listing: { room: { property: { managerId: userId } } },
      },
    });
  } else if (role === 'contractor') {
    stats.activeJobs = await prisma.maintenanceRequest.count({
      where: {
        contractorId: userId,
        status: { in: ['assigned', 'in_progress', 'awaiting_parts'] },
      },
    });
    stats.scheduledToday = await prisma.maintenanceRequest.count({
      where: {
        contractorId: userId,
        status: { in: ['assigned', 'in_progress'] },
        updatedAt: { gte: new Date(new Date().setHours(0, 0, 0, 0)) },
      },
    });
    stats.completedMonth = await prisma.maintenanceRequest.count({
      where: {
        contractorId: userId,
        status: { in: ['completed', 'closed'] },
        completedAt: { gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) },
      },
    });
    stats.awaitingApproval = await prisma.maintenanceRequest.count({
      where: { contractorId: userId, status: 'completed' },
    });
  } else if (role === 'admin') {
    stats.totalUsers = await prisma.user.count();
    stats.activeListings = await prisma.listing.count({ where: { status: 'active' } });
    stats.pendingVerification = await prisma.user.count({ where: { verified: false } });
    stats.openMaintenance = await prisma.maintenanceRequest.count({
      where: { status: { notIn: ['closed', 'cancelled'] } },
    });
  }

  const notifications = await prisma.notification.findMany({
    where: { userId },
    orderBy: { createdAt: 'desc' },
    take: 5,
  });

  const expiringDocuments =
    role === 'landlord' || role === 'property_manager'
      ? await prisma.document.findMany({
          where: {
            expiryDate: {
              lte: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000),
              gte: new Date(),
            },
            ...(role === 'landlord'
              ? { property: { ownerId: userId } }
              : { property: { managerId: userId } }),
          },
          include: { property: { select: { id: true, name: true } } },
          take: 10,
        })
      : [];

  res.json({
    stats,
    notifications: notifications.map((n) => ({ ...n, data: JSON.parse(n.data) })),
    expiringDocuments: expiringDocuments.map((d) => {
      const daysLeft = d.expiryDate
        ? Math.max(0, Math.ceil((d.expiryDate.getTime() - Date.now()) / (24 * 60 * 60 * 1000)))
        : null;
      const riskLevel =
        daysLeft === null
          ? 'info'
          : daysLeft <= 7
            ? 'critical'
            : daysLeft <= 30
              ? 'high'
              : 'medium';
      return { ...d, daysLeft, riskLevel };
    }),
  });
});

export default router;
