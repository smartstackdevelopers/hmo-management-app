import { theme } from './theme';

export default {
  light: {
    text: theme.colors.text,
    background: theme.colors.background,
    tint: theme.colors.secondary,
    tabIconDefault: theme.colors.textMuted,
    tabIconSelected: theme.colors.secondary,
    card: theme.colors.surface,
    border: theme.colors.border,
    primary: theme.colors.primary,
    accent: theme.colors.accent,
  },
  dark: {
    text: '#F1F5F9',
    background: '#0A1628',
    tint: theme.colors.secondaryLight,
    tabIconDefault: '#64748B',
    tabIconSelected: theme.colors.secondaryLight,
    card: '#132337',
    border: '#1E3A52',
    primary: theme.colors.primaryLight,
    accent: theme.colors.accentLight,
  },
};
