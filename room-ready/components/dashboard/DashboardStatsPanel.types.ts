import { Ionicons } from '@expo/vector-icons';

export interface DashboardStat {
  label: string;
  value: string;
  icon?: keyof typeof Ionicons.glyphMap;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';
}
