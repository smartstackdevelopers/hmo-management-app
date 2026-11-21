/**
 * HMore — Blue & White design system (docs/audit/HMORE_UI_UX_DESIGN_SPEC_COMPLETE_BLUE.pdf §3).
 * White surfaces, royal blue accent, navy brand, calm hierarchy.
 */
export const theme = {
  colors: {
    primary: '#0B1220',
    primaryLight: '#1E293B',
    primaryMuted: '#64748B',
    secondary: '#2563EB',
    secondaryLight: '#60A5FA',
    secondaryDark: '#1D4ED8',
    accent: '#2563EB',
    accentLight: '#EFF6FF',
    accentSoft: '#DBEAFE',
    brand: '#172554',

    background: '#F3F7FD',
    backgroundAlt: '#F3F7FD',
    surface: '#FFFFFF',
    surfaceSecondary: '#F8FBFF',
    surfaceMuted: '#EEF3FA',
    surfaceElevated: '#FFFFFF',
    glass: '#FFFFFF',
    glassBorder: '#DFE6F1',

    text: '#0B1220',
    textSecondary: '#475569',
    textMuted: '#94A3B8',
    textInverse: '#FFFFFF',

    border: '#DFE6F1',
    borderLight: '#F1F5FB',

    success: '#059669',
    successLight: '#ECFDF5',
    warning: '#D97706',
    warningLight: '#FFFBEB',
    error: '#DC2626',
    errorLight: '#FEF2F2',
    /** Alias used by wellbeing/job-matching screens */
    danger: '#DC2626',
    dangerLight: '#FEF2F2',
    info: '#4F46E5',
    infoLight: '#EEF2FF',

    tabBar: '#FFFFFF',
    tabBarBorder: '#DFE6F1',
    tabBarActive: '#1D4ED8',
    tabBarInactive: '#94A3B8',
    overlay: 'rgba(11, 18, 32, 0.48)',

    gradientStart: '#FFFFFF',
    gradientMid: '#F8FBFF',
    gradientEnd: '#EEF3FA',
    gradientAccent: '#2563EB',
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
    glow: { shadowColor: '#2563EB', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.22, shadowRadius: 10, elevation: 3 },
  },
} as const;

export type Theme = typeof theme;
