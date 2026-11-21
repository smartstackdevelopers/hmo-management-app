import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';

export default function AccessibilityScreen() {
  const { prefs, update, fontScale, t } = useI18n();
  const larger = prefs.textScale !== 'default';
  const contrast = prefs.highContrast;

  return (
    <ScrollView style={[styles.page, contrast && styles.contrast]} contentContainerStyle={styles.content}>
      <Text style={[styles.title, { fontSize: 28 * fontScale }, contrast && styles.contrastText]} accessibilityRole="header">
        {t('profile.accessibility')}
      </Text>
      <Text style={[styles.lead, contrast && styles.contrastText]}>{t('settings.lead')}</Text>

      <Text style={[styles.label, contrast && styles.contrastText]}>{t('settings.language')}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('settings.language')}
        onPress={() => update({ language: prefs.language === 'ur' ? 'en' : 'ur' })}
        style={[styles.select, contrast && styles.contrastChoice]}
      >
        <Text style={[styles.rowLabel, contrast && styles.contrastText]}>
          {prefs.language === 'ur' ? t('settings.urdu') : t('settings.english')}
        </Text>
        <Ionicons name="chevron-down" size={18} color={contrast ? '#000000' : theme.colors.textSecondary} />
      </Pressable>

      <Toggle
        label={t('settings.textSize')}
        value={larger}
        contrast={contrast}
        onChange={(on) => update({ textScale: on ? 'large' : 'default' })}
      />
      <Toggle
        label={t('settings.contrast')}
        value={contrast}
        contrast={contrast}
        onChange={(on) => update({ highContrast: on })}
      />
    </ScrollView>
  );
}

function Toggle({
  label,
  value,
  onChange,
  contrast,
}: {
  label: string;
  value: boolean;
  onChange: (value: boolean) => void;
  contrast: boolean;
}) {
  return (
    <View style={[styles.row, contrast && styles.contrastChoice]}>
      <Text style={[styles.rowLabel, contrast && styles.contrastText]}>{label}</Text>
      <Switch
        accessibilityLabel={label}
        accessibilityRole="switch"
        value={value}
        onValueChange={onChange}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  content: { padding: theme.spacing.md, paddingBottom: 40 },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: 8 },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20, marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: 8 },
  select: {
    minHeight: 52,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.lg,
    backgroundColor: theme.colors.surface,
    paddingHorizontal: 14,
    marginBottom: theme.spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  contrastChoice: { borderColor: '#000000' },
  row: {
    minHeight: 56,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.lg,
    backgroundColor: theme.colors.surface,
    paddingHorizontal: 14,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  rowLabel: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, flex: 1, marginRight: 12 },
});
