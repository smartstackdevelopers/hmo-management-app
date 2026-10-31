import { Router } from 'express';
import { prisma } from '../lib/prisma';
import { authMiddleware, requireRoles } from '../middleware/auth';

const router = Router();
router.use(authMiddleware);

router.get('/contractors', requireRoles('landlord', 'property_manager', 'admin'), async (_req, res) => {
  const contractors = await prisma.user.findMany({
    where: { role: 'contractor', active: true },
    select: { id: true, firstName: true, lastName: true, email: true, phone: true, verified: true },
  });
  res.json({ contractors });
});

router.get('/contacts', async (req, res) => {
  const { userId, role } = req.user!;
  const select = { id: true, firstName: true, lastName: true, email: true, role: true };

  if (role === 'landlord') {
    const properties = await prisma.property.findMany({
      where: { ownerId: userId },
      include: {
        manager: { select },
        rooms: {
          include: {
            tenancies: {
              where: { status: 'active' },
              include: { tenant: { select } },
            },
          },
        },
      },
    });
    const contacts = new Map<string, (typeof select & { id: string })>();
    for (const p of properties) {
      if (p.manager) contacts.set(p.manager.id, p.manager);
      for (const room of p.rooms) {
        for (const t of room.tenancies) {
          if (t.tenant) contacts.set(t.tenant.id, t.tenant);
        }
      }
    }
    const contractorList = await prisma.user.findMany({
      where: { role: 'contractor', active: true },
      select,
    });
    contractorList.forEach((c) => contacts.set(c.id, c));
    return res.json({ contacts: [...contacts.values()] });
  }

  if (role === 'tenant') {
    const tenancies = await prisma.tenancy.findMany({
      where: { tenantId: userId, status: 'active' },
      include: {
        room: {
          include: {
            property: {
              include: {
                owner: { select },
                manager: { select },
              },
            },
          },
        },
      },
    });
    const contacts = new Map<string, (typeof select & { id: string })>();
    for (const t of tenancies) {
      const prop = t.room.property;
      contacts.set(prop.owner.id, prop.owner);
      if (prop.manager) contacts.set(prop.manager.id, prop.manager);
    }
    return res.json({ contacts: [...contacts.values()] });
  }

  if (role === 'property_manager') {
    const properties = await prisma.property.findMany({
      where: { managerId: userId },
      include: {
        owner: { select },
        rooms: {
          include: {
            tenancies: {
              where: { status: 'active' },
              include: { tenant: { select } },
            },
          },
        },
      },
    });
    const contacts = new Map<string, (typeof select & { id: string })>();
    for (const p of properties) {
      contacts.set(p.owner.id, p.owner);
      for (const room of p.rooms) {
        for (const t of room.tenancies) {
          if (t.tenant) contacts.set(t.tenant.id, t.tenant);
        }
      }
    }
    return res.json({ contacts: [...contacts.values()] });
  }

  if (role === 'contractor') {
    const jobs = await prisma.maintenanceRequest.findMany({
      where: { contractorId: userId },
      include: {
        property: {
          include: {
            owner: { select },
            manager: { select },
          },
        },
        reporter: { select },
      },
      distinct: ['propertyId'],
    });
    const contacts = new Map<string, (typeof select & { id: string })>();
    for (const job of jobs) {
      contacts.set(job.property.owner.id, job.property.owner);
      if (job.property.manager) contacts.set(job.property.manager.id, job.property.manager);
      if (job.reporter) contacts.set(job.reporter.id, job.reporter);
    }
    return res.json({ contacts: [...contacts.values()] });
  }

  res.json({ contacts: [] });
});

export default router;
