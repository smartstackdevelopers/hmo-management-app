import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { PushPreferenceToggle } from '@/components/PushPreferenceToggle';
import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { LANGUAGE_OPTIONS, TextScale } from '@/lib/hmore/accessibility';

const SCALES: { id: TextScale; labelKey: 'settings.default' | 'settings.large' | 'settings.extraLarge' }[] = [
  { id: 'default', labelKey: 'settings.default' },
  { id: 'large', labelKey: 'settings.large' },
  { id: 'xlarge', labelKey: 'settings.extraLarge' },
];

export function AccessibilitySettings() {
  const { prefs, update, fontScale, t } = useI18n();

  return (
    <ScrollView style={[styles.page, prefs.highContrast && styles.contrast]} contentContainerStyle={styles.content}>
      <Text style={[styles.lead, { fontSize: 15 * fontScale }, prefs.highContrast && styles.contrastText]}>{t('settings.lead')}</Text>

      <Text style={[styles.heading, prefs.highContrast && styles.contrastText]}>{t('settings.textSize')}</Text>
      <View style={styles.wrap}>
        {SCALES.map((scale) => (
          <Pressable
            key={scale.id}
            accessibilityRole="button"
            accessibilityLabel={t(scale.labelKey)}
            accessibilityState={{ selected: prefs.textScale === scale.id }}
            onPress={() => update({ textScale: scale.id })}
            style={[styles.choice, prefs.textScale === scale.id && styles.choiceOn, prefs.highContrast && styles.contrastChoice]}
          >
            <Text style={[styles.choiceText, { fontSize: 14 * fontScale }]}>{t(scale.labelKey)}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={[styles.heading, prefs.highContrast && styles.contrastText]}>{t('settings.contrast')}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={prefs.highContrast ? t('settings.contrastOn') : t('settings.contrastOff')}
        onPress={() => update({ highContrast: !prefs.highContrast })}
        style={[styles.choice, prefs.highContrast && styles.choiceOn]}
      >
        <Text style={styles.choiceText}>{prefs.highContrast ? t('settings.contrastOn') : t('settings.contrastOff')}</Text>
      </Pressable>

      <Text style={[styles.heading, prefs.highContrast && styles.contrastText]}>{t('settings.language')}</Text>
      <Card style={prefs.highContrast ? styles.contrastCard : undefined}>
        {LANGUAGE_OPTIONS.map((item) => (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityLabel={item.id === 'ur' ? t('settings.urdu') : t('settings.english')}
            accessibilityState={{ selected: prefs.language === item.id }}
            onPress={() => update({ language: item.id })}
            style={styles.lang}
          >
            <Text style={[styles.choiceText, prefs.language === item.id && styles.selected]}>
              {item.id === 'ur' ? t('settings.urdu') : t('settings.english')}
            </Text>
          </Pressable>
        ))}
      </Card>
      <PushPreferenceToggle />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastChoice: { borderColor: '#000000' },
  contrastCard: { borderWidth: 2, borderColor: '#000000' },
  content: { padding: theme.spacing.md, paddingBottom: 40 },
  lead: { fontFamily: FONT_MEDIUM, lineHeight: 22, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  heading: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text, marginTop: theme.spacing.md, marginBottom: 8 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  choice: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: theme.colors.surface,
    marginBottom: 8,
  },
  choiceOn: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.accentLight },
  choiceText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, fontSize: 14 },
  lang: { paddingVertical: 10 },
  selected: { color: theme.colors.secondaryDark },
});
