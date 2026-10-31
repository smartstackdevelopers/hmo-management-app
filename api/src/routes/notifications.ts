import { Router } from 'express';
import { prisma } from '../lib/prisma';
import { authMiddleware } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

router.get('/', async (req, res) => {
  const { userId } = req.user!;
  const unreadOnly = req.query.unread === 'true';

  const notifications = await prisma.notification.findMany({
    where: {
      userId,
      ...(unreadOnly ? { read: false } : {}),
    },
    orderBy: { createdAt: 'desc' },
    take: 50,
  });

  res.json({
    notifications: notifications.map((n) => {
      const data = JSON.parse(n.data);
      return {
        ...n,
        data,
        severity:
          data?.riskLevel ??
          (n.type === 'document_expiry' ? 'high' : n.type === 'compliance' ? 'medium' : 'info'),
      };
    }),
    unreadCount: await prisma.notification.count({ where: { userId, read: false } }),
  });
});

router.patch('/:id/read', async (req, res) => {
  const { userId } = req.user!;
  const notification = await prisma.notification.findFirst({
    where: { id: req.params.id, userId },
  });
  if (!notification) return res.status(404).json({ error: 'Notification not found' });

  const updated = await prisma.notification.update({
    where: { id: req.params.id },
    data: { read: true },
  });
  res.json({ notification: updated });
});

router.post('/read-all', async (req, res) => {
  const { userId } = req.user!;
  await prisma.notification.updateMany({
    where: { userId, read: false },
    data: { read: true },
  });
  res.json({ success: true });
});

router.post('/compliance-scan', async (req, res) => {
  const { userId, role } = req.user!;
  if (!['landlord', 'property_manager', 'admin'].includes(role)) {
    return res.status(403).json({ error: 'Access denied' });
  }

  const docs = await prisma.document.findMany({
    where: {
      expiryDate: {
        lte: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000),
        gte: new Date(),
      },
      ...(role === 'landlord'
        ? { property: { ownerId: userId } }
        : role === 'property_manager'
          ? { property: { managerId: userId } }
          : {}),
    },
    include: { property: { select: { id: true, name: true } } },
  });

  let created = 0;
  for (const d of docs) {
    if (!d.expiryDate) continue;
    const daysLeft = Math.max(0, Math.ceil((d.expiryDate.getTime() - Date.now()) / (24 * 60 * 60 * 1000)));
    if (![90, 60, 30, 7].includes(daysLeft)) continue;
    const riskLevel = daysLeft <= 7 ? 'critical' : daysLeft <= 30 ? 'high' : 'medium';
    const title = `Compliance alert: ${d.name} expires in ${daysLeft} day${daysLeft === 1 ? '' : 's'}`;
    const existing = await prisma.notification.findFirst({
      where: {
        userId,
        type: 'compliance',
        title,
      },
    });
    if (existing) continue;
    await prisma.notification.create({
      data: {
        userId,
        type: 'compliance',
        title,
        body: `${d.property?.name ?? 'Property'} requires renewal planning.`,
        data: JSON.stringify({
          propertyId: d.propertyId,
          documentId: d.id,
          riskLevel,
          daysLeft,
        }),
      },
    });
    created += 1;
  }

  res.json({ created });
});

export default router;
