/**
 * Birmingham City Council HMO compliance reference standards.
 * Aligned with Housing Act 2004, HMO Management Regulations 2006,
 * and Birmingham City Council mandatory HMO licensing requirements.
 *
 * @see https://www.birmingham.gov.uk/hmo
 */

export const BIRMINGHAM_COUNCIL = {
  name: 'Birmingham City Council',
  shortName: 'BCC',
  city: 'Birmingham',
  region: 'West Midlands',
  housingTeam: 'Private Sector Housing',
  licensingPhone: '0121 303 6007',
  licensingEmail: 'hmo.licensing@birmingham.gov.uk',
  housingStandardsUrl: 'https://www.birmingham.gov.uk/hmo',
  reportRepairUrl: 'https://www.birmingham.gov.uk/info/20016/housing',
  licensingThreshold: {
    minOccupants: 5,
    minHouseholds: 2,
    description: 'Mandatory licence required for 5+ occupants forming 2+ households',
  },
} as const;

/** Statutory minimum bedroom floor areas (square metres) — England HMO standards */
export const HMO_ROOM_STANDARDS = {
  singleOccupancy: 6.51,
  doubleOccupancy: 10.22,
  description: 'Minimum floor area per Birmingham City Council HMO amenity standards',
} as const;

/** Documents expected for Birmingham HMO licence compliance */
export const BIRMINGHAM_REQUIRED_DOCUMENTS = [
  { id: 'hmo_licence', label: 'HMO Licence', statutory: true, renewalYears: 5 },
  { id: 'gas_safety', label: 'Gas Safety Certificate (CP12)', statutory: true, renewalYears: 1 },
  { id: 'electrical_safety', label: 'Electrical Installation Condition Report (EICR)', statutory: true, renewalYears: 5 },
  { id: 'epc', label: 'Energy Performance Certificate (EPC)', statutory: true, renewalYears: 10 },
  { id: 'fire_risk_assessment', label: 'Fire Risk Assessment', statutory: true, renewalYears: 1 },
  { id: 'insurance', label: 'Buildings & Landlord Insurance', statutory: true, renewalYears: 1 },
  { id: 'legionella_assessment', label: 'Legionella Risk Assessment', statutory: false, renewalYears: 2 },
  { id: 'inventory', label: 'Property Inventory', statutory: false, renewalYears: 0 },
] as const;

export const BIRMINGHAM_HMO_STANDARDS = [
  {
    id: 'licence',
    title: 'HMO Licence',
    description: 'Valid Birmingham City Council HMO licence displayed at the property',
    regulation: 'Housing Act 2004 Part 2',
  },
  {
    id: 'room_sizes',
    title: 'Room Size Standards',
    description: 'Bedrooms meet minimum 6.51m² (single) or 10.22m² (double) floor area',
    regulation: 'Housing Act 2004 Schedule 4',
  },
  {
    id: 'gas_safety',
    title: 'Gas Safety',
    description: 'Annual gas safety check by Gas Safe registered engineer',
    regulation: 'Gas Safety (Installation and Use) Regulations 1998',
  },
  {
    id: 'electrical',
    title: 'Electrical Safety',
    description: 'EICR completed at least every 5 years',
    regulation: 'Electrical Safety Standards in the Private Rented Sector (England) Regulations 2020',
  },
  {
    id: 'fire_safety',
    title: 'Fire Safety',
    description: 'Smoke alarms, fire doors, escape routes and fire risk assessment in place',
    regulation: 'HMO Management Regulations 2006 / Fire Safety Order 2005',
  },
  {
    id: 'waste',
    title: 'Waste & Refuse',
    description: 'Adequate internal and external waste storage with Birmingham Council collection',
    regulation: 'HMO Management Regulations 2006 Reg. 9',
  },
  {
    id: 'manager',
    title: 'Manager Details',
    description: 'Responsible person contact details displayed for tenants',
    regulation: 'HMO Management Regulations 2006 Reg. 6',
  },
  {
    id: 'tenancy',
    title: 'Tenancy Information',
    description: 'Written tenancy agreement and How to Rent guide provided',
    regulation: 'Tenant Fees Act 2019 / Deregulation Act 2015',
  },
] as const;

export const TENANT_RIGHTS_BIRMINGHAM = [
  'Your landlord must hold a valid HMO licence where required',
  'Gas safety certificate must be provided within 28 days of request',
  'Electrical installation must be safe with valid EICR',
  'Repairs to structure, heating, water and sanitation must be completed promptly',
  'Deposit must be protected in a government-approved scheme',
  'Report serious hazards to Birmingham City Council Private Sector Housing',
] as const;

export function isBirminghamPostcode(postcode: string): boolean {
  const prefix = postcode.trim().toUpperCase().split(' ')[0] ?? '';
  return prefix.startsWith('B') && /^B\d/.test(prefix);
}
