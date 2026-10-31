export interface MaintenanceTriageResult {
  priority: 'low' | 'medium' | 'high' | 'emergency';
  summary: string;
  riskFlags: string[];
}

const EMERGENCY_KEYWORDS = [
  'gas leak',
  'smell gas',
  'fire',
  'smoke',
  'sparks',
  'electrocute',
  'flood',
  'burst pipe',
  'no heating',
  'no hot water',
  'carbon monoxide',
];

const HIGH_PRIORITY_KEYWORDS = [
  'mould',
  'mold',
  'damp',
  'leak',
  'toilet blocked',
  'security',
  'lock broken',
  'broken window',
  'roof leak',
];

export function runMaintenanceAICopilot(input: {
  title: string;
  description: string;
  category?: string;
}): MaintenanceTriageResult {
  const text = `${input.title} ${input.description}`.toLowerCase();
  const riskFlags: string[] = [];
  let priority: MaintenanceTriageResult['priority'] = 'medium';

  for (const keyword of EMERGENCY_KEYWORDS) {
    if (text.includes(keyword)) {
      riskFlags.push(`Emergency indicator: "${keyword}"`);
      priority = 'emergency';
    }
  }

  if (priority !== 'emergency') {
    for (const keyword of HIGH_PRIORITY_KEYWORDS) {
      if (text.includes(keyword)) {
        riskFlags.push(`High-risk condition: "${keyword}"`);
        priority = 'high';
      }
    }
  }

  if (input.category?.toLowerCase().includes('fire') && priority !== 'emergency') {
    riskFlags.push('Fire safety category selected');
    priority = 'high';
  }

  if (!input.description.trim() || input.description.trim().length < 20) {
    riskFlags.push('Low detail report — add symptom, location, and urgency');
  }

  const summary =
    priority === 'emergency'
      ? 'Immediate action recommended. Treat as urgent safety risk and dispatch immediately.'
      : priority === 'high'
        ? 'High-risk issue detected. Prioritize within 24 hours and document mitigation.'
        : priority === 'medium'
          ? 'Standard priority. Plan attendance and monitor for escalation.'
          : 'Low urgency. Bundle with planned maintenance where appropriate.';

  return { priority, summary, riskFlags };
}

