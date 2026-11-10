import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listCommunityServices } from '@/lib/hmore/services/community';

const CATEGORIES = [
  { id: '', labelKey: 'community.all' },
  { id: 'food_bank', labelKey: 'community.foodBank' },
  { id: 'kitchen', labelKey: 'community.kitchen' },
  { id: 'clothing_bank', labelKey: 'community.clothingBank' },
  { id: 'local_service', labelKey: 'community.localService' },
] as const;

export default function CommunityScreen() {
  const { t, fontScale, prefs } = useI18n();
  const [draft, setDraft] = useState('');
  const [q, setQ] = useState('');
  const [category, setCategory] = useState('');
  const query = useQuery({
    queryKey: ['hmore', 'community-services', q, category],
    queryFn: () => listCommunityServices({ q: q || undefined, category: category || undefined }),
  });

  if (query.isLoading) return <LoadingScreen message={t('community.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const items = query.data ?? [];
  const contrast = prefs.highContrast;

  return (
    <Screen style={contrast ? styles.contrast : undefined}>
      <Text style={[styles.title, { fontSize: 24 * fontScale }, contrast && styles.contrastText]}>{t('community.title')}</Text>
      <Input
        label={t('community.search')}
        value={draft}
        onChangeText={setDraft}
        accessibilityLabel={t('community.search')}
      />
      <Button
        title={t('community.searchAction')}
        accessibilityLabel={t('community.searchAction')}
        onPress={() => setQ(draft.trim())}
      />
      <View style={styles.filters}>
        {CATEGORIES.map((item) => {
          const selected = category === item.id;
          return (
            <Pressable
              key={item.labelKey}
              accessibilityRole="button"
              accessibilityLabel={t(item.labelKey)}
              accessibilityState={{ selected }}
              onPress={() => setCategory(item.id)}
              style={[styles.chip, selected && styles.chipOn]}
            >
              <Text style={[styles.chipText, selected && styles.chipTextOn]}>{t(item.labelKey)}</Text>
            </Pressable>
          );
        })}
      </View>
      {items.length === 0 ? (
        <Text style={[styles.empty, { fontSize: 16 * fontScale }]}>{t('community.empty')}</Text>
      ) : (
        items.map((item) => (
          <Card key={item.id} style={styles.card}>
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.meta}>{t(CATEGORIES.find((entry) => entry.id === item.category)?.labelKey ?? 'community.localService')}</Text>
            {item.description ? <Text style={styles.body}>{item.description}</Text> : null}
            {item.address_line ? <Text style={styles.body}>{item.address_line}</Text> : null}
            {item.opening_hours ? (
              <Text style={styles.meta}>
                {t('community.hours')}: {item.opening_hours}
              </Text>
            ) : null}
            {item.eligibility ? (
              <Text style={styles.meta}>
                {t('community.eligibility')}: {item.eligibility}
              </Text>
            ) : null}
            {item.contact ? (
              <Text style={styles.meta}>
                {t('community.contact')}: {item.contact}
              </Text>
            ) : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.md },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: theme.spacing.md },
  chip: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.full,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: theme.colors.surface,
  },
  chipOn: { backgroundColor: theme.colors.secondary, borderColor: theme.colors.secondary },
  chipText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, fontSize: 13 },
  chipTextOn: { color: theme.colors.textInverse },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginTop: theme.spacing.md },
  card: { marginBottom: theme.spacing.sm },
  name: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, color: theme.colors.textSecondary, marginTop: 6, lineHeight: 20 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
});
