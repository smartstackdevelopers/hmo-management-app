/**
 * Room Ready — professional property management UI.
 * Cool slate surfaces, deep teal accent, calm hierarchy.
 */
export const theme = {
  colors: {
    primary: '#0B1220',
    primaryLight: '#1E293B',
    primaryMuted: '#64748B',
    secondary: '#0D9488',
    secondaryLight: '#2DD4BF',
    secondaryDark: '#0F766E',
    accent: '#0D9488',
    accentLight: '#F0FDFA',

    background: '#F4F7F9',
    backgroundAlt: '#F4F7F9',
    surface: '#FFFFFF',
    surfaceSecondary: '#F8FAFC',
    surfaceMuted: '#EEF2F6',
    surfaceElevated: '#FFFFFF',
    glass: '#FFFFFF',
    glassBorder: '#E2E8F0',

    text: '#0B1220',
    textSecondary: '#475569',
    textMuted: '#94A3B8',
    textInverse: '#FFFFFF',

    border: '#E2E8F0',
    borderLight: '#F1F5F9',

    success: '#059669',
    successLight: '#ECFDF5',
    warning: '#D97706',
    warningLight: '#FFFBEB',
    error: '#DC2626',
    errorLight: '#FEF2F2',
    info: '#0284C7',
    infoLight: '#F0F9FF',

    tabBar: '#FFFFFF',
    tabBarBorder: '#E2E8F0',
    tabBarActive: '#0D9488',
    tabBarInactive: '#94A3B8',
    overlay: 'rgba(11, 18, 32, 0.48)',

    gradientStart: '#FFFFFF',
    gradientMid: '#F8FAFC',
    gradientEnd: '#F1F5F9',
    gradientAccent: '#0D9488',
  },

  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 },

  layout: {
    phoneMaxWidth: 420,
    tabBarBase: 52,
    tabBarClearance: 68,
    fabSize: 54,
    fabBottom: 92,
  },

  radius: { sm: 10, md: 14, lg: 18, xl: 22, xxl: 28, full: 9999 },

  typography: {
    hero: { fontSize: 32, fontWeight: '700' as const, lineHeight: 38, letterSpacing: -0.8 },
    h1: { fontSize: 26, fontWeight: '700' as const, lineHeight: 32, letterSpacing: -0.5 },
    h2: { fontSize: 20, fontWeight: '700' as const, lineHeight: 26, letterSpacing: -0.3 },
    h3: { fontSize: 17, fontWeight: '600' as const, lineHeight: 22, letterSpacing: -0.2 },
    body: { fontSize: 16, fontWeight: '400' as const, lineHeight: 24 },
    bodySmall: { fontSize: 14, fontWeight: '400' as const, lineHeight: 20 },
    caption: { fontSize: 12, fontWeight: '500' as const, lineHeight: 16 },
    label: { fontSize: 12, fontWeight: '600' as const, lineHeight: 16, letterSpacing: 0.2 },
    overline: { fontSize: 11, fontWeight: '600' as const, lineHeight: 14, letterSpacing: 0.6 },
  },

  shadows: {
    sm: { shadowColor: '#0B1220', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 1 },
    md: { shadowColor: '#0B1220', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.07, shadowRadius: 12, elevation: 3 },
    lg: { shadowColor: '#0B1220', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.1, shadowRadius: 24, elevation: 6 },
    glow: { shadowColor: '#0D9488', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.22, shadowRadius: 10, elevation: 3 },
  },
} as const;

export type Theme = typeof theme;
