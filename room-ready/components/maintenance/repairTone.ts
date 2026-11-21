import { Ionicons } from '@expo/vector-icons';

import type { Tone } from '@/components/ui/Chip';

const STATUS_TONE: Record<string, Tone> = {
  open: 'amber',
  new: 'amber',
  reported: 'amber',
  submitted: 'amber',
  acknowledged: 'blue',
  assigned: 'blue',
  scheduled: 'indigo',
  in_progress: 'blue',
  awaiting_parts: 'amber',
  awaiting_approval: 'indigo',
  on_hold: 'gray',
  completed: 'green',
  closed: 'green',
  resolved: 'green',
  cancelled: 'gray',
  rejected: 'red',
};

export function repairStatusTone(status: string): Tone {
  return STATUS_TONE[status] ?? 'gray';
}

export function repairStatusText(status: string): string {
  const text = status.replace(/_/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function repairPriorityTone(priority: string): Tone {
  if (priority === 'urgent' || priority === 'emergency') return 'red';
  if (priority === 'high') return 'amber';
  return 'gray';
}

export function repairCategoryIcon(category: string | null | undefined): keyof typeof Ionicons.glyphMap {
  const key = (category ?? '').toLowerCase();
  if (key.includes('plumb') || key.includes('water') || key.includes('leak')) return 'water-outline';
  if (key.includes('elect')) return 'flash-outline';
  if (key.includes('heat') || key.includes('boiler')) return 'thermometer-outline';
  if (key.includes('door') || key.includes('window') || key.includes('lock')) return 'key-outline';
  if (key.includes('damp') || key.includes('mould') || key.includes('mold')) return 'cloudy-outline';
  if (key.includes('pest')) return 'bug-outline';
  if (key.includes('fire') || key.includes('smoke') || key.includes('alarm')) return 'alert-circle-outline';
  if (key.includes('applian') || key.includes('kitchen')) return 'restaurant-outline';
  return 'construct-outline';
}
