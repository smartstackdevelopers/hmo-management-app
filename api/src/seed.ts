import 'dotenv/config';
import bcrypt from 'bcryptjs';
import { prisma } from './lib/prisma';

async function main() {
  console.log('Seeding Room Ready database with demo rooms...');

  const passwordHash = await bcrypt.hash('Password123', 12);

  const admin = await prisma.user.upsert({
    where: { email: 'admin@roomready.co.uk' },
    update: {},
    create: {
      email: 'admin@roomready.co.uk',
      passwordHash,
      firstName: 'Platform',
      lastName: 'Admin',
      role: 'admin',
      verified: true,
    },
  });

  const landlord = await prisma.user.upsert({
    where: { email: 'landlord@roomready.co.uk' },
    update: {},
    create: {
      email: 'landlord@roomready.co.uk',
      passwordHash,
      firstName: 'James',
      lastName: 'Mitchell',
      role: 'landlord',
      phone: '+447700900123',
      verified: true,
    },
  });

  const manager = await prisma.user.upsert({
    where: { email: 'manager@roomready.co.uk' },
    update: {},
    create: {
      email: 'manager@roomready.co.uk',
      passwordHash,
      firstName: 'Sarah',
      lastName: 'Chen',
      role: 'property_manager',
      phone: '+447700900456',
      verified: true,
    },
  });

  const tenant = await prisma.user.upsert({
    where: { email: 'tenant@roomready.co.uk' },
    update: {},
    create: {
      email: 'tenant@roomready.co.uk',
      passwordHash,
      firstName: 'Emma',
      lastName: 'Thompson',
      role: 'tenant',
      phone: '+447700900789',
      verified: true,
    },
  });

  const contractor = await prisma.user.upsert({
    where: { email: 'contractor@roomready.co.uk' },
    update: {},
    create: {
      email: 'contractor@roomready.co.uk',
      passwordHash,
      firstName: 'David',
      lastName: 'Walsh',
      role: 'contractor',
      phone: '+447700900321',
      verified: true,
    },
  });

  // Extra demo tenants for applications variety (optional)
  const tenant2 = await prisma.user.upsert({
    where: { email: 'alex.tenant@roomready.co.uk' },
    update: {},
    create: {
      email: 'alex.tenant@roomready.co.uk',
      passwordHash,
      firstName: 'Alex',
      lastName: 'Patel',
      role: 'tenant',
      phone: '+447700900111',
      verified: true,
    },
  });

  const properties = [
    {
      id: 'seed-property-1',
      name: '42 Edgbaston Road HMO',
      addressLine1: '42 Edgbaston Road',
      city: 'Birmingham',
      county: 'West Midlands',
      postcode: 'B15 2TT',
      hmoLicenceNumber: 'HMO-BCC-2024-0042',
      maxOccupants: 6,
      description: 'Well-maintained 6-bed HMO in Edgbaston, close to University of Birmingham.',
      emergencyContact: 'James Mitchell: 07700 900123',
      houseRules:
        'Bin collection: Tuesday (general waste), Friday (recycling). No smoking indoors. Quiet hours 11pm-7am.',
    },
    {
      id: 'seed-property-2',
      name: '18 Harborne Park House',
      addressLine1: '18 Harborne Park Road',
      city: 'Birmingham',
      county: 'West Midlands',
      postcode: 'B17 0BS',
      hmoLicenceNumber: 'HMO-BCC-2024-0118',
      maxOccupants: 5,
      description: 'Quiet professional HMO near Harborne High Street with off-street parking nearby.',
      emergencyContact: 'James Mitchell: 07700 900123',
      houseRules: 'Shared kitchen rota. No overnight guests without notice. Quiet hours 10:30pm–7am.',
    },
    {
      id: 'seed-property-3',
      name: '7 Selly Oak Gardens',
      addressLine1: '7 Dawlish Road',
      city: 'Birmingham',
      county: 'West Midlands',
      postcode: 'B29 7AD',
      hmoLicenceNumber: 'HMO-BCC-2023-0087',
      maxOccupants: 7,
      description: 'Student-friendly HMO in Selly Oak with fast Wi‑Fi and a large shared lounge.',
      emergencyContact: 'Sarah Chen: 07700 900456',
      houseRules: 'Clean shared areas after cooking. Recycling every Wednesday.',
    },
    {
      id: 'seed-property-4',
      name: '3 Digbeth Lofts HMO',
      addressLine1: '3 Allison Street',
      city: 'Birmingham',
      county: 'West Midlands',
      postcode: 'B5 5TH',
      hmoLicenceNumber: 'HMO-BCC-2025-0003',
      maxOccupants: 4,
      description: 'Modern city-centre rooms near Digbeth dining and New Street Station.',
      emergencyContact: 'James Mitchell: 07700 900123',
      houseRules: 'No parties. Keep corridors clear. Report repairs in the app.',
    },
  ] as const;

  for (const p of properties) {
    await prisma.property.upsert({
      where: { id: p.id },
      update: {
        name: p.name,
        addressLine1: p.addressLine1,
        city: p.city,
        county: p.county,
        postcode: p.postcode,
        hmoLicenceNumber: p.hmoLicenceNumber,
        maxOccupants: p.maxOccupants,
        description: p.description,
        emergencyContact: p.emergencyContact,
        houseRules: p.houseRules,
        managerId: manager.id,
      },
      create: {
        id: p.id,
        ownerId: landlord.id,
        managerId: manager.id,
        name: p.name,
        addressLine1: p.addressLine1,
        city: p.city,
        county: p.county,
        postcode: p.postcode,
        hmoLicenceNumber: p.hmoLicenceNumber,
        maxOccupants: p.maxOccupants,
        description: p.description,
        emergencyContact: p.emergencyContact,
        houseRules: p.houseRules,
      },
    });
  }

  type RoomSeed = {
    id: string;
    propertyId: string;
    name: string;
    floor: string;
    rentPcm: number;
    deposit: number;
    sizeSqm: number;
    furnished: boolean;
    ensuite: boolean;
    status: 'available' | 'occupied' | 'maintenance';
    description?: string;
  };

  const roomsSeed: RoomSeed[] = [
    // Edgbaston
    {
      id: 'seed-room-1',
      propertyId: 'seed-property-1',
      name: 'Room 1 - Ground',
      floor: 'Ground',
      rentPcm: 550,
      deposit: 600,
      sizeSqm: 12,
      furnished: true,
      ensuite: false,
      status: 'occupied',
    },
    {
      id: 'seed-room-2',
      propertyId: 'seed-property-1',
      name: 'Room 2 - Ground',
      floor: 'Ground',
      rentPcm: 575,
      deposit: 625,
      sizeSqm: 13,
      furnished: true,
      ensuite: false,
      status: 'occupied',
    },
    {
      id: 'seed-room-3',
      propertyId: 'seed-property-1',
      name: 'Room 3 - First Floor',
      floor: 'First',
      rentPcm: 625,
      deposit: 650,
      sizeSqm: 14,
      furnished: true,
      ensuite: true,
      status: 'occupied',
    },
    {
      id: 'seed-room-4',
      propertyId: 'seed-property-1',
      name: 'Room 4 - First Floor',
      floor: 'First',
      rentPcm: 650,
      deposit: 700,
      sizeSqm: 15,
      furnished: true,
      ensuite: true,
      status: 'available',
      description: 'Bright double with ensuite and desk space.',
    },
    {
      id: 'seed-room-5',
      propertyId: 'seed-property-1',
      name: 'Room 5 - Second Floor',
      floor: 'Second',
      rentPcm: 595,
      deposit: 650,
      sizeSqm: 13.5,
      furnished: true,
      ensuite: false,
      status: 'available',
      description: 'Quiet top-floor room with garden views.',
    },
    // Harborne
    {
      id: 'seed-room-6',
      propertyId: 'seed-property-2',
      name: 'Front Double',
      floor: 'Ground',
      rentPcm: 700,
      deposit: 750,
      sizeSqm: 16,
      furnished: true,
      ensuite: true,
      status: 'available',
      description: 'Large ensuite front room for professionals.',
    },
    {
      id: 'seed-room-7',
      propertyId: 'seed-property-2',
      name: 'Rear Twin',
      floor: 'Ground',
      rentPcm: 580,
      deposit: 600,
      sizeSqm: 12,
      furnished: true,
      ensuite: false,
      status: 'available',
      description: 'Cosy twin overlooking the rear garden.',
    },
    {
      id: 'seed-room-8',
      propertyId: 'seed-property-2',
      name: 'Master Ensuite',
      floor: 'First',
      rentPcm: 775,
      deposit: 800,
      sizeSqm: 18,
      furnished: true,
      ensuite: true,
      status: 'available',
      description: 'House master suite with fitted wardrobe.',
    },
    // Selly Oak
    {
      id: 'seed-room-9',
      propertyId: 'seed-property-3',
      name: 'Room A',
      floor: 'Ground',
      rentPcm: 495,
      deposit: 550,
      sizeSqm: 11,
      furnished: true,
      ensuite: false,
      status: 'available',
      description: 'Affordable student room, bills included option.',
    },
    {
      id: 'seed-room-10',
      propertyId: 'seed-property-3',
      name: 'Room B Ensuite',
      floor: 'First',
      rentPcm: 560,
      deposit: 600,
      sizeSqm: 12.5,
      furnished: true,
      ensuite: true,
      status: 'available',
      description: 'Ensuite room near campus and cafés.',
    },
    {
      id: 'seed-room-11',
      propertyId: 'seed-property-3',
      name: 'Room C',
      floor: 'First',
      rentPcm: 520,
      deposit: 550,
      sizeSqm: 12,
      furnished: true,
      ensuite: false,
      status: 'available',
      description: 'Light-filled double with study desk.',
    },
    // Digbeth
    {
      id: 'seed-room-12',
      propertyId: 'seed-property-4',
      name: 'Loft Studio Room',
      floor: 'Second',
      rentPcm: 825,
      deposit: 900,
      sizeSqm: 20,
      furnished: true,
      ensuite: true,
      status: 'available',
      description: 'City loft-style ensuite, ideal for professionals.',
    },
    {
      id: 'seed-room-13',
      propertyId: 'seed-property-4',
      name: 'Canal View Room',
      floor: 'First',
      rentPcm: 720,
      deposit: 750,
      sizeSqm: 14,
      furnished: true,
      ensuite: true,
      status: 'available',
      description: 'Modern ensuite overlooking the canal basin.',
    },
  ];

  for (const room of roomsSeed) {
    await prisma.room.upsert({
      where: { id: room.id },
      update: {
        name: room.name,
        floor: room.floor,
        rentPcm: room.rentPcm,
        deposit: room.deposit,
        sizeSqm: room.sizeSqm,
        furnished: room.furnished,
        ensuite: room.ensuite,
        status: room.status,
        description: room.description,
      },
      create: room,
    });
  }

  const daysFromNow = (days: number) => new Date(Date.now() + days * 24 * 60 * 60 * 1000);

  const photoSets: string[][] = [
    [
      'https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=1200&q=80',
      'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=1200&q=80',
      'https://images.unsplash.com/photo-1560184897-ae75f418493e?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=1200&q=80',
      'https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=1200&q=80',
      'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=1200&q=80',
      'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=1200&q=80',
      'https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1200&q=80',
      'https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=1200&q=80',
      'https://images.unsplash.com/photo-1484154218962-a197022b5858?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200&q=80',
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1200&q=80',
      'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=1200&q=80',
      'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdbc?w=1200&q=80',
      'https://images.unsplash.com/photo-1600607687644-c7171b42498f?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1554995207-c18c203602cb?w=1200&q=80',
      'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1200&q=80',
      'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80',
      'https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=1200&q=80',
      'https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1600121848594-d8644e57abab?w=1200&q=80',
      'https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=1200&q=80',
      'https://images.unsplash.com/photo-1600573472591-ee6981cf4214?w=1200&q=80',
    ],
    [
      'https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=1200&q=80',
      'https://images.unsplash.com/photo-1618220179428-22790b461013?w=1200&q=80',
      'https://images.unsplash.com/photo-1616137466211-f939a420be44?w=1200&q=80',
    ],
  ];

  const listingsSeed = [
    {
      id: 'seed-listing-1',
      roomId: 'seed-room-4',
      title: 'Bright ensuite in Edgbaston HMO',
      description:
        'Spacious first-floor ensuite with desk space. Bills can be included. 10-minute walk to University of Birmingham and Queen Elizabeth Hospital.',
      billsIncluded: true,
      availableFrom: daysFromNow(7),
      photos: photoSets[0],
    },
    {
      id: 'seed-listing-2',
      roomId: 'seed-room-5',
      title: 'Quiet top-floor room · Edgbaston',
      description:
        'Peaceful second-floor double with garden views. Shared kitchen and lounge. Ideal for postgrads or young professionals.',
      billsIncluded: true,
      availableFrom: daysFromNow(14),
      photos: photoSets[1],
    },
    {
      id: 'seed-listing-3',
      roomId: 'seed-room-6',
      title: 'Large ensuite · Harborne professionals',
      description:
        'Front double with private bathroom near Harborne High Street. Off-street parking nearby. Fully furnished.',
      billsIncluded: false,
      availableFrom: daysFromNow(3),
      photos: photoSets[2],
    },
    {
      id: 'seed-listing-4',
      roomId: 'seed-room-7',
      title: 'Cosy garden-view twin · Harborne',
      description: 'Affordable twin room overlooking the garden. Great value for Harborne. Shared bathroom.',
      billsIncluded: true,
      availableFrom: daysFromNow(10),
      photos: photoSets[3],
    },
    {
      id: 'seed-listing-5',
      roomId: 'seed-room-8',
      title: 'Master ensuite suite · Harborne Park',
      description: 'Largest room in the house with fitted wardrobe and ensuite. Perfect for a professional tenant.',
      billsIncluded: false,
      availableFrom: daysFromNow(21),
      photos: photoSets[4],
    },
    {
      id: 'seed-listing-6',
      roomId: 'seed-room-9',
      title: 'Student room near campus · Selly Oak',
      description: 'Budget-friendly double close to University of Birmingham. Fast Wi‑Fi and large shared lounge.',
      billsIncluded: true,
      availableFrom: daysFromNow(0),
      photos: photoSets[5],
    },
    {
      id: 'seed-listing-7',
      roomId: 'seed-room-10',
      title: 'Ensuite near Uni · Selly Oak',
      description: 'Private ensuite room on Dawlish Road. Short walk to campus, cafés and the train station.',
      billsIncluded: true,
      availableFrom: daysFromNow(5),
      photos: photoSets[6],
    },
    {
      id: 'seed-listing-8',
      roomId: 'seed-room-11',
      title: 'Light double with desk · Selly Oak',
      description: 'Furnished double with study desk. Shared kitchen and bathroom. Bills included.',
      billsIncluded: true,
      availableFrom: daysFromNow(12),
      photos: photoSets[7],
    },
    {
      id: 'seed-listing-9',
      roomId: 'seed-room-12',
      title: 'City loft ensuite · Digbeth',
      description: 'Modern loft-style ensuite minutes from New Street Station and Digbeth dining.',
      billsIncluded: false,
      availableFrom: daysFromNow(2),
      photos: photoSets[8],
    },
    {
      id: 'seed-listing-10',
      roomId: 'seed-room-13',
      title: 'Canal-view ensuite · Digbeth Lofts',
      description: 'Stylish ensuite with canal views. Ideal for professionals working in the city centre.',
      billsIncluded: false,
      availableFrom: daysFromNow(9),
      photos: photoSets[9],
    },
  ];

  for (const listing of listingsSeed) {
    const photosJson = JSON.stringify(listing.photos);
    await prisma.listing.upsert({
      where: { id: listing.id },
      update: {
        title: listing.title,
        description: listing.description,
        status: 'active',
        billsIncluded: listing.billsIncluded,
        availableFrom: listing.availableFrom,
        photos: photosJson,
      },
      create: {
        id: listing.id,
        roomId: listing.roomId,
        title: listing.title,
        description: listing.description,
        status: 'active',
        billsIncluded: listing.billsIncluded,
        availableFrom: listing.availableFrom,
        photos: photosJson,
      },
    });
  }

  // Demo tenant home: Emma at 42 Edgbaston Road, Room 1 (keep listings on rooms 4–5 free)
  await prisma.tenancy.updateMany({
    where: { tenantId: tenant.id, status: 'active', NOT: { id: 'seed-tenancy-1' } },
    data: { status: 'ended', endDate: new Date() },
  });
  await prisma.room.update({
    where: { id: 'seed-room-1' },
    data: { status: 'occupied' },
  });
  await prisma.room.update({
    where: { id: 'seed-room-4' },
    data: { status: 'available' },
  });
  await prisma.tenancy.upsert({
    where: { id: 'seed-tenancy-1' },
    update: {
      roomId: 'seed-room-1',
      tenantId: tenant.id,
      startDate: new Date('2025-09-01'),
      endDate: null,
      rentPcm: 550,
      deposit: 600,
      status: 'active',
    },
    create: {
      id: 'seed-tenancy-1',
      roomId: 'seed-room-1',
      tenantId: tenant.id,
      startDate: new Date('2025-09-01'),
      rentPcm: 550,
      deposit: 600,
      status: 'active',
    },
  });

  // Documents seeded below (readable HTML demos in /uploads/demo)

  // Demo pending application from second tenant
  const existingApp = await prisma.application.findFirst({
    where: { id: 'seed-application-1' },
  });
  if (!existingApp) {
    await prisma.application.create({
      data: {
        id: 'seed-application-1',
        listingId: 'seed-listing-3',
        tenantId: tenant2.id,
        message: 'I work nearby in Harborne and can move in from next week. Happy to provide references.',
        moveInDate: daysFromNow(10),
        status: 'pending',
      },
    });
  }

  const maintenance = await prisma.maintenanceRequest.upsert({
    where: { id: 'seed-maintenance-1' },
    update: {
      title: 'Leaking tap in shared kitchen',
      description:
        'The cold tap on the shared kitchen sink drips constantly. Bowl left underneath overnight fills up. Started about 2 days ago.',
      category: 'Plumbing',
      priority: 'medium',
      status: 'assigned',
      contractorId: contractor.id,
      roomId: 'seed-room-2',
    },
    create: {
      id: 'seed-maintenance-1',
      propertyId: 'seed-property-1',
      roomId: 'seed-room-2',
      reporterId: tenant.id,
      contractorId: contractor.id,
      title: 'Leaking tap in shared kitchen',
      description:
        'The cold tap on the shared kitchen sink drips constantly. Bowl left underneath overnight fills up. Started about 2 days ago.',
      category: 'Plumbing',
      priority: 'medium',
      status: 'assigned',
    },
  });

  await prisma.maintenanceRequest.upsert({
    where: { id: 'seed-maintenance-2' },
    update: {
      title: 'Radiator not heating',
      description:
        'Bedroom radiator (Room 1) stays cold when the heating is on. Other radiators in the house are warm. Affects evenings.',
      category: 'Heating & Boiler',
      priority: 'high',
      status: 'open',
      roomId: 'seed-room-1',
    },
    create: {
      id: 'seed-maintenance-2',
      propertyId: 'seed-property-1',
      roomId: 'seed-room-1',
      reporterId: tenant.id,
      title: 'Radiator not heating',
      description:
        'Bedroom radiator (Room 1) stays cold when the heating is on. Other radiators in the house are warm. Affects evenings.',
      category: 'Heating & Boiler',
      priority: 'high',
      status: 'open',
    },
  });

  const existingUpdate = await prisma.maintenanceUpdate.findFirst({
    where: { id: 'seed-maintenance-update-1' },
  });
  if (!existingUpdate) {
    await prisma.maintenanceUpdate.create({
      data: {
        id: 'seed-maintenance-update-1',
        requestId: maintenance.id,
        authorId: landlord.id,
        note: 'Assigned David Walsh (plumbing). He will visit within 48 hours — please leave access to the shared kitchen.',
        photoUrls: '[]',
      },
    });
  }

  const propertyMeta: Record<string, { name: string; licence: string }> = {
    'seed-property-1': { name: '42 Edgbaston Road HMO', licence: 'HMO-BCC-2024-0042' },
    'seed-property-2': { name: '18 Harborne Park House', licence: 'HMO-BCC-2024-0118' },
    'seed-property-3': { name: '7 Selly Oak Gardens', licence: 'HMO-BCC-2023-0087' },
    'seed-property-4': { name: '3 Digbeth Lofts HMO', licence: 'HMO-BCC-2025-0003' },
  };

  type DocSeed = {
    id: string;
    propertyId: string;
    type:
      | 'hmo_licence'
      | 'epc'
      | 'gas_safety'
      | 'electrical_safety'
      | 'insurance'
      | 'tenancy_agreement'
      | 'inventory'
      | 'other';
    name: string;
    fileUrl: string;
    expiryDate?: Date;
    notes?: string;
  };

  const documentsSeed: DocSeed[] = [
    // Edgbaston — full readable pack for Emma (tenant demo)
    {
      id: 'seed-doc-edg-hmo',
      propertyId: 'seed-property-1',
      type: 'hmo_licence',
      name: 'HMO Licence — 42 Edgbaston Road',
      fileUrl: '/uploads/demo/edgbaston-hmo-licence.html',
      expiryDate: new Date('2027-03-15'),
      notes: 'Birmingham City Council mandatory HMO licence',
    },
    {
      id: 'seed-doc-edg-gas',
      propertyId: 'seed-property-1',
      type: 'gas_safety',
      name: 'Gas Safety (CP12) — 42 Edgbaston Road',
      fileUrl: '/uploads/demo/edgbaston-gas-safety.html',
      expiryDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000),
      notes: 'Due soon — renew before expiry',
    },
    {
      id: 'seed-doc-edg-epc',
      propertyId: 'seed-property-1',
      type: 'epc',
      name: 'EPC — 42 Edgbaston Road',
      fileUrl: '/uploads/demo/edgbaston-epc.html',
      expiryDate: new Date('2030-06-01'),
    },
    {
      id: 'seed-doc-edg-eicr',
      propertyId: 'seed-property-1',
      type: 'electrical_safety',
      name: 'Electrical Safety (EICR) — 42 Edgbaston Road',
      fileUrl:
        '/uploads/demo/generic-certificate.html?name=Electrical%20Safety%20(EICR)&property=42%20Edgbaston%20Road',
      expiryDate: new Date('2029-09-01'),
    },
    {
      id: 'seed-doc-edg-insurance',
      propertyId: 'seed-property-1',
      type: 'insurance',
      name: 'Buildings & landlord insurance — 42 Edgbaston Road',
      fileUrl:
        '/uploads/demo/generic-certificate.html?name=Buildings%20%26%20Landlord%20Insurance&property=42%20Edgbaston%20Road',
      expiryDate: new Date('2027-04-01'),
    },
    {
      id: 'seed-doc-edg-ast',
      propertyId: 'seed-property-1',
      type: 'tenancy_agreement',
      name: 'Assured Shorthold Tenancy — Emma Thompson',
      fileUrl: '/uploads/demo/edgbaston-ast.html',
      expiryDate: new Date('2026-08-31'),
      notes: 'Room 1 · £550 pcm',
    },
    {
      id: 'seed-doc-edg-rules',
      propertyId: 'seed-property-1',
      type: 'other',
      name: 'House rules — 42 Edgbaston Road',
      fileUrl: '/uploads/demo/edgbaston-house-rules.html',
    },
    {
      id: 'seed-doc-edg-inventory',
      propertyId: 'seed-property-1',
      type: 'inventory',
      name: 'Check-in inventory — Room 1',
      fileUrl: '/uploads/demo/edgbaston-inventory.html',
      notes: 'Signed at move-in',
    },
    {
      id: 'seed-doc-edg-welcome',
      propertyId: 'seed-property-1',
      type: 'other',
      name: 'Welcome guide — Wi‑Fi, heating & bins',
      fileUrl: '/uploads/demo/edgbaston-welcome.html',
    },
    {
      id: 'seed-doc-edg-fire',
      propertyId: 'seed-property-1',
      type: 'other',
      name: 'Fire risk assessment — 42 Edgbaston Road',
      fileUrl:
        '/uploads/demo/generic-certificate.html?name=Fire%20Risk%20Assessment&property=42%20Edgbaston%20Road',
      expiryDate: new Date('2026-12-01'),
      notes: 'Annual review',
    },
  ];

  for (const propertyId of ['seed-property-2', 'seed-property-3', 'seed-property-4'] as const) {
    const meta = propertyMeta[propertyId];
    const qName = encodeURIComponent(meta.name);
    documentsSeed.push(
      {
        id: `seed-doc-${propertyId}-hmo`,
        propertyId,
        type: 'hmo_licence',
        name: `HMO Licence — ${meta.name}`,
        fileUrl: `/uploads/demo/generic-certificate.html?name=${encodeURIComponent('HMO Licence')}&property=${qName}`,
        expiryDate: new Date('2027-03-15'),
      },
      {
        id: `seed-doc-${propertyId}-gas`,
        propertyId,
        type: 'gas_safety',
        name: `Gas Safety (CP12) — ${meta.name}`,
        fileUrl: `/uploads/demo/generic-certificate.html?name=${encodeURIComponent('Gas Safety (CP12)')}&property=${qName}`,
        expiryDate: new Date('2027-01-01'),
      },
      {
        id: `seed-doc-${propertyId}-epc`,
        propertyId,
        type: 'epc',
        name: `EPC — ${meta.name}`,
        fileUrl: `/uploads/demo/generic-certificate.html?name=${encodeURIComponent('Energy Performance Certificate')}&property=${qName}`,
        expiryDate: new Date('2030-06-01'),
      }
    );
  }

  for (const doc of documentsSeed) {
    await prisma.document.upsert({
      where: { id: doc.id },
      update: {
        name: doc.name,
        type: doc.type,
        fileUrl: doc.fileUrl,
        expiryDate: doc.expiryDate ?? null,
        notes: doc.notes,
        propertyId: doc.propertyId,
      },
      create: {
        id: doc.id,
        propertyId: doc.propertyId,
        uploadedBy: landlord.id,
        type: doc.type,
        name: doc.name,
        fileUrl: doc.fileUrl,
        expiryDate: doc.expiryDate,
        notes: doc.notes,
      },
    });
  }

  // Remove legacy placeholder docs that pointed at missing PDFs
  await prisma.document.deleteMany({
    where: {
      OR: [
        { fileUrl: { startsWith: '/uploads/sample-' } },
        {
          fileUrl: {
            in: [
              '/uploads/sample-hmo-licence.pdf',
              '/uploads/sample-gas-cert.pdf',
              '/uploads/sample-epc.pdf',
              '/uploads/sample-ast.pdf',
              '/uploads/sample-eicr.pdf',
              '/uploads/sample-insurance.pdf',
              '/uploads/sample-fire-risk.pdf',
            ],
          },
        },
      ],
    },
  });

  const conversation = await prisma.conversation.upsert({
    where: { id: 'seed-conversation-1' },
    update: {},
    create: {
      id: 'seed-conversation-1',
      propertyId: 'seed-property-1',
      subject: '42 Edgbaston Road - General',
    },
  });

  for (const p of [
    { conversationId: conversation.id, userId: landlord.id },
    { conversationId: conversation.id, userId: tenant.id },
  ]) {
    const exists = await prisma.conversationParticipant.findUnique({
      where: { conversationId_userId: { conversationId: p.conversationId, userId: p.userId } },
    });
    if (!exists) await prisma.conversationParticipant.create({ data: p });
  }

  for (const msg of [
    {
      conversationId: conversation.id,
      senderId: landlord.id,
      body: 'Hi Emma, welcome to 42 Edgbaston Road. Please review the house rules in your tenancy documents.',
    },
    {
      conversationId: conversation.id,
      senderId: tenant.id,
      body: 'Thank you! I have read them. Could you confirm the bin collection day?',
    },
  ]) {
    const exists = await prisma.message.findFirst({
      where: { conversationId: msg.conversationId, body: msg.body },
    });
    if (!exists) await prisma.message.create({ data: msg });
  }

  await prisma.inspection.upsert({
    where: { id: 'seed-inspection-1' },
    update: {},
    create: {
      id: 'seed-inspection-1',
      propertyId: 'seed-property-1',
      inspectorId: manager.id,
      scheduledAt: daysFromNow(5),
      status: 'scheduled',
      notes: 'Quarterly compliance inspection',
    },
  });

  const notifCount = await prisma.notification.count({
    where: { userId: landlord.id, title: 'Gas Safety Certificate expiring' },
  });
  if (notifCount === 0) {
    await prisma.notification.createMany({
      data: [
        {
          userId: landlord.id,
          type: 'compliance',
          title: 'Gas Safety Certificate expiring',
          body: 'CP12 for 42 Edgbaston Road expires in 14 days',
          data: JSON.stringify({ propertyId: 'seed-property-1' }),
        },
        {
          userId: landlord.id,
          type: 'application',
          title: 'New room application',
          body: 'Alex Patel applied for Large ensuite · Harborne professionals',
          data: JSON.stringify({ listingId: 'seed-listing-3' }),
        },
        {
          userId: tenant.id,
          type: 'maintenance',
          title: 'Repair update',
          body: 'Your repair request has been assigned to a contractor',
          data: JSON.stringify({ maintenanceId: maintenance.id }),
        },
      ],
    });
  }

  void admin;

  const listingCount = await prisma.listing.count({ where: { status: 'active' } });
  const propertyCount = await prisma.property.count();
  const roomCount = await prisma.room.count();

  console.log('Seed complete.');
  console.log(`  ${propertyCount} properties · ${roomCount} rooms · ${listingCount} live listings`);
  console.log('Demo accounts (password: Password123):');
  console.log('  landlord@roomready.co.uk');
  console.log('  tenant@roomready.co.uk');
  console.log('  manager@roomready.co.uk');
  console.log('  contractor@roomready.co.uk');
  console.log('  admin@roomready.co.uk');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
