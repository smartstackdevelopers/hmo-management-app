import {
  BIRMINGHAM_REQUIRED_DOCUMENTS,
  BIRMINGHAM_HMO_STANDARDS,
  HMO_ROOM_STANDARDS,
} from '@/constants/birmingham';
import { DocumentItem, PropertyItem, RoomItem } from '@/lib/api';

export type ComplianceStatus = 'compliant' | 'warning' | 'non_compliant' | 'unknown';

export interface ComplianceCheck {
  id: string;
  title: string;
  description: string;
  regulation: string;
  status: ComplianceStatus;
  detail?: string;
}

export interface PropertyComplianceReport {
  score: number;
  status: ComplianceStatus;
  checks: ComplianceCheck[];
  roomIssues: { roomId: string; roomName: string; issue: string }[];
}

export interface ComplianceCopilotAction {
  id: string;
  severity: 'critical' | 'high' | 'medium';
  title: string;
  reason: string;
  regulation: string;
}

function docTypePresent(documents: DocumentItem[] | undefined, type: string): DocumentItem | undefined {
  return documents?.find((d) => d.type === type || d.type.replace(/_/g, '') === type.replace(/_/g, ''));
}

function isDocValid(doc?: DocumentItem): boolean {
  if (!doc) return false;
  if (!doc.expiryDate) return true;
  return new Date(doc.expiryDate) > new Date();
}

function isDocExpiringSoon(doc?: DocumentItem, days = 30): boolean {
  if (!doc?.expiryDate) return false;
  const expiry = new Date(doc.expiryDate);
  const threshold = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  return expiry <= threshold && expiry > new Date();
}

export function assessRoomCompliance(room: RoomItem): string | null {
  if (!room.sizeSqm) return 'Room floor area not recorded — required for BCC HMO standards';
  const isDouble = room.sizeSqm >= HMO_ROOM_STANDARDS.doubleOccupancy * 0.95;
  const minRequired = isDouble ? HMO_ROOM_STANDARDS.doubleOccupancy : HMO_ROOM_STANDARDS.singleOccupancy;
  if (room.sizeSqm < minRequired) {
    return `Floor area ${room.sizeSqm}m² below minimum ${minRequired}m²`;
  }
  return null;
}

export function assessPropertyCompliance(property: PropertyItem): PropertyComplianceReport {
  const documents = property.documents ?? [];
  const rooms = property.rooms ?? [];
  const roomIssues = rooms
    .map((room) => {
      const issue = assessRoomCompliance(room);
      return issue ? { roomId: room.id, roomName: room.name, issue } : null;
    })
    .filter(Boolean) as { roomId: string; roomName: string; issue: string }[];

  const checks: ComplianceCheck[] = BIRMINGHAM_HMO_STANDARDS.map((standard) => {
    switch (standard.id) {
      case 'licence': {
        const hasLicence = !!property.hmoLicenceNumber;
        const doc = docTypePresent(documents, 'hmo_licence');
        const valid = hasLicence && isDocValid(doc);
        const expiring = isDocExpiringSoon(doc);
        return {
          ...standard,
          status: valid ? (expiring ? 'warning' : 'compliant') : hasLicence ? 'warning' : 'non_compliant',
          detail: property.hmoLicenceNumber
            ? `Licence ref: ${property.hmoLicenceNumber}`
            : 'HMO licence number required for Birmingham mandatory licensing',
        };
      }
      case 'room_sizes': {
        const issues = roomIssues.length;
        const unmeasured = rooms.filter((r) => !r.sizeSqm).length;
        return {
          ...standard,
          status: issues > 0 ? 'non_compliant' : unmeasured > 0 ? 'warning' : 'compliant',
          detail:
            issues > 0
              ? `${issues} room(s) below minimum size`
              : unmeasured > 0
                ? `${unmeasured} room(s) missing floor area data`
                : 'All recorded rooms meet minimum standards',
        };
      }
      case 'gas_safety': {
        const doc = docTypePresent(documents, 'gas_safety');
        return {
          ...standard,
          status: isDocValid(doc) ? (isDocExpiringSoon(doc, 60) ? 'warning' : 'compliant') : 'non_compliant',
          detail: doc ? (isDocValid(doc) ? 'CP12 certificate on file' : 'Gas certificate expired') : 'Annual CP12 required',
        };
      }
      case 'electrical': {
        const doc = docTypePresent(documents, 'electrical_safety');
        return {
          ...standard,
          status: isDocValid(doc) ? (isDocExpiringSoon(doc) ? 'warning' : 'compliant') : 'non_compliant',
          detail: doc ? (isDocValid(doc) ? 'EICR on file' : 'EICR expired') : 'EICR required (max 5 years)',
        };
      }
      case 'fire_safety': {
        const doc = documents.find((d) => d.type === 'fire_risk_assessment' || d.name.toLowerCase().includes('fire'));
        return {
          ...standard,
          status: isDocValid(doc) ? 'compliant' : 'warning',
          detail: doc ? 'Fire risk assessment on file' : 'Fire risk assessment recommended',
        };
      }
      case 'waste':
        return {
          ...standard,
          status: property.houseRules?.toLowerCase().includes('bin') ? 'compliant' : 'warning',
          detail: 'Ensure waste arrangements documented in house rules',
        };
      case 'manager':
        return {
          ...standard,
          status: property.emergencyContact ? 'compliant' : 'non_compliant',
          detail: property.emergencyContact ?? 'Manager/emergency contact must be displayed',
        };
      case 'tenancy':
        return {
          ...standard,
          status: rooms.some((r) => r.tenancies?.length) ? 'compliant' : 'unknown',
          detail: 'Tenancy agreements required for all occupied rooms',
        };
      default: {
        const s = standard as (typeof BIRMINGHAM_HMO_STANDARDS)[number];
        return { ...s, status: 'unknown' as ComplianceStatus };
      }
    }
  });

  const weights = { compliant: 1, warning: 0.6, unknown: 0.4, non_compliant: 0 };
  const score = Math.round(
    (checks.reduce((sum, c) => sum + weights[c.status], 0) / checks.length) * 100
  );

  const status: ComplianceStatus =
    score >= 85 ? 'compliant' : score >= 60 ? 'warning' : 'non_compliant';

  return { score, status, checks, roomIssues };
}

export function getComplianceCopilotActions(
  property: PropertyItem,
  report: PropertyComplianceReport
): ComplianceCopilotAction[] {
  const actions: ComplianceCopilotAction[] = [];
  const getCheck = (id: string) => report.checks.find((c) => c.id === id);

  const licence = getCheck('licence');
  if (licence && licence.status !== 'compliant') {
    actions.push({
      id: `${property.id}-licence`,
      severity: 'critical',
      title: 'Resolve HMO licence gap',
      reason: licence.detail ?? 'Licence evidence or number is missing/expiring.',
      regulation: licence.regulation,
    });
  }

  const gas = getCheck('gas_safety');
  if (gas && gas.status !== 'compliant') {
    actions.push({
      id: `${property.id}-gas`,
      severity: gas.status === 'non_compliant' ? 'critical' : 'high',
      title: 'Update gas safety certificate (CP12)',
      reason: gas.detail ?? 'Annual gas safety evidence is required.',
      regulation: gas.regulation,
    });
  }

  const electrical = getCheck('electrical');
  if (electrical && electrical.status !== 'compliant') {
    actions.push({
      id: `${property.id}-electrical`,
      severity: electrical.status === 'non_compliant' ? 'critical' : 'high',
      title: 'Renew electrical safety certification',
      reason: electrical.detail ?? 'Electrical safety evidence is missing or expired.',
      regulation: electrical.regulation,
    });
  }

  if (report.roomIssues.length > 0) {
    actions.push({
      id: `${property.id}-rooms`,
      severity: 'high',
      title: 'Fix room size compliance issues',
      reason: `${report.roomIssues.length} room(s) fail minimum HMO dimensions.`,
      regulation: 'Housing Act 2004 / BCC Room Standards',
    });
  }

  const manager = getCheck('manager');
  if (manager && manager.status !== 'compliant') {
    actions.push({
      id: `${property.id}-manager`,
      severity: 'medium',
      title: 'Publish responsible person details',
      reason: manager.detail ?? 'Emergency contact details must be displayed.',
      regulation: manager.regulation,
    });
  }

  const fire = getCheck('fire_safety');
  if (fire && fire.status !== 'compliant') {
    actions.push({
      id: `${property.id}-fire`,
      severity: 'medium',
      title: 'Upload fire risk assessment evidence',
      reason: fire.detail ?? 'Fire safety evidence should be available for inspections.',
      regulation: fire.regulation,
    });
  }

  const severityRank = { critical: 0, high: 1, medium: 2 } as const;
  return actions.sort((a, b) => severityRank[a.severity] - severityRank[b.severity]);
}

export function getComplianceLabel(status: ComplianceStatus): string {
  const labels: Record<ComplianceStatus, string> = {
    compliant: 'Compliant',
    warning: 'Action Required',
    non_compliant: 'Non-Compliant',
    unknown: 'Review Needed',
  };
  return labels[status];
}

export function getComplianceVariant(
  status: ComplianceStatus
): 'success' | 'warning' | 'error' | 'default' | 'info' {
  const map: Record<ComplianceStatus, 'success' | 'warning' | 'error' | 'default'> = {
    compliant: 'success',
    warning: 'warning',
    non_compliant: 'error',
    unknown: 'default',
  };
  return map[status];
}

export { BIRMINGHAM_REQUIRED_DOCUMENTS };
