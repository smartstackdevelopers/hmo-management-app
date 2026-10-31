import { prisma } from './prisma';

export async function getAccessiblePropertyIds(userId: string, role: string): Promise<string[]> {
  if (role === 'admin') {
    const all = await prisma.property.findMany({ select: { id: true } });
    return all.map((p) => p.id);
  }
  if (role === 'property_manager') {
    const managed = await prisma.property.findMany({
      where: { managerId: userId },
      select: { id: true },
    });
    return managed.map((p) => p.id);
  }
  if (role === 'landlord') {
    const owned = await prisma.property.findMany({
      where: { ownerId: userId },
      select: { id: true },
    });
    return owned.map((p) => p.id);
  }
  if (role === 'tenant') {
    const tenancies = await prisma.tenancy.findMany({
      where: { tenantId: userId, status: 'active' },
      include: { room: { select: { propertyId: true } } },
    });
    return [...new Set(tenancies.map((t) => t.room.propertyId))];
  }
  if (role === 'contractor') {
    const jobs = await prisma.maintenanceRequest.findMany({
      where: { contractorId: userId },
      select: { propertyId: true },
    });
    return [...new Set(jobs.map((j) => j.propertyId))];
  }
  return [];
}

export async function canAccessProperty(userId: string, role: string, propertyId: string): Promise<boolean> {
  if (role === 'admin') return true;
  const ids = await getAccessiblePropertyIds(userId, role);
  return ids.includes(propertyId);
}

export async function canManageProperty(
  userId: string,
  role: string,
  property: { ownerId: string; managerId: string | null }
): Promise<boolean> {
  if (role === 'admin') return true;
  if (role === 'landlord') return property.ownerId === userId;
  if (role === 'property_manager') return property.managerId === userId;
  return false;
}

export async function canAccessMaintenance(
  userId: string,
  role: string,
  request: { reporterId: string; contractorId: string | null; property: { ownerId: string; managerId: string | null } }
): Promise<boolean> {
  if (role === 'admin') return true;
  if (role === 'tenant') return request.reporterId === userId;
  if (role === 'contractor') return request.contractorId === userId;
  if (role === 'landlord') return request.property.ownerId === userId;
  if (role === 'property_manager') return request.property.managerId === userId;
  return false;
}

export async function canReportMaintenance(
  userId: string,
  role: string,
  propertyId: string
): Promise<boolean> {
  const property = await prisma.property.findUnique({ where: { id: propertyId } });
  if (!property) return false;
  if (role === 'admin') return true;
  if (role === 'landlord') return property.ownerId === userId;
  if (role === 'property_manager') return property.managerId === userId;
  if (role === 'tenant') {
    const tenancy = await prisma.tenancy.findFirst({
      where: { tenantId: userId, status: 'active', room: { propertyId } },
    });
    return !!tenancy;
  }
  return false;
}

export async function getDocumentListFilter(userId: string, role: string): Promise<Record<string, unknown>> {
  if (role === 'admin') return {};
  if (role === 'tenant') {
    const propertyIds = await getAccessiblePropertyIds(userId, role);
    return { OR: [{ propertyId: { in: propertyIds } }, { uploadedBy: userId }] };
  }
  if (role === 'landlord') {
    const propertyIds = await getAccessiblePropertyIds(userId, role);
    return { propertyId: { in: propertyIds } };
  }
  if (role === 'property_manager') {
    const propertyIds = await getAccessiblePropertyIds(userId, role);
    return { propertyId: { in: propertyIds } };
  }
  if (role === 'contractor') {
    const propertyIds = await getAccessiblePropertyIds(userId, role);
    return { propertyId: { in: propertyIds } };
  }
  return { id: { in: [] } };
}
