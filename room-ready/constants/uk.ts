export const UK_CONFIG = {
  country: 'United Kingdom',
  countryCode: 'GB',
  currency: 'GBP',
  currencySymbol: '£',
  locale: 'en-GB',
  phonePrefix: '+44',
  dateFormat: 'DD/MM/YYYY',
  postcodePattern: /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i,
} as const;

export const DOCUMENT_TYPES = [
  { id: 'hmo_licence', label: 'HMO Licence', reminderDays: [90, 60, 30, 14, 7] },
  { id: 'epc', label: 'EPC Certificate', reminderDays: [90, 60, 30] },
  { id: 'gas_safety', label: 'Gas Safety (CP12)', reminderDays: [60, 30, 14, 7] },
  { id: 'electrical_safety', label: 'Electrical Safety (EICR)', reminderDays: [90, 60, 30, 14] },
  { id: 'fire_risk_assessment', label: 'Fire Risk Assessment', reminderDays: [60, 30, 14] },
  { id: 'legionella_assessment', label: 'Legionella Risk Assessment', reminderDays: [60, 30] },
  { id: 'insurance', label: 'Buildings Insurance', reminderDays: [60, 30, 14] },
  { id: 'tenancy_agreement', label: 'Tenancy Agreement', reminderDays: [60, 30, 14] },
  { id: 'inventory', label: 'Inventory Report', reminderDays: [30] },
  { id: 'inspection_report', label: 'Inspection Report', reminderDays: [30] },
  { id: 'contractor_invoice', label: 'Contractor Invoice', reminderDays: [] },
] as const;

export const MAINTENANCE_CATEGORIES = [
  'Plumbing',
  'Electrical',
  'Heating & Boiler',
  'Damp & Mould',
  'Structural',
  'Appliances',
  'Locks & Security',
  'Pest Control',
  'Other',
] as const;

export function formatGBP(amount: number): string {
  return new Intl.NumberFormat(UK_CONFIG.locale, {
    style: 'currency',
    currency: UK_CONFIG.currency,
  }).format(amount);
}

export function formatUKDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat(UK_CONFIG.locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(d);
}
