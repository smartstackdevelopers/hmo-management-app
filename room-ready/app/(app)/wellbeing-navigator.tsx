import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Linking, Pressable, StyleSheet, Text } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getNavigator, listNavigatorCategories } from '@/lib/hmore/services/wellbeing';

export default function WellbeingNavigatorScreen() {
  const { t, fontScale } = useI18n();
  const [selected, setSelected] = useState<string | null>(null);
  const cats = useQuery({ queryKey: ['hmore', 'wellbeing-nav-cats'], queryFn: listNavigatorCategories });
  const detail = useQuery({
    queryKey: ['hmore', 'wellbeing-nav', selected],
    queryFn: () => getNavigator(String(selected)),
    enabled: Boolean(selected),
  });

  if (cats.isLoading) return <LoadingScreen message={t('wellbeing.loading')} />;
  if (cats.error) return <ErrorState message={hmoreErrorMessage(cats.error)} onRetry={cats.refetch} />;

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('wellbeing.navigator')}</Text>
      <Text style={styles.disclaimer}>{cats.data?.disclaimer}</Text>
      {(cats.data?.items ?? []).map((item) => (
        <Pressable key={String(item.id)} onPress={() => setSelected(String(item.id))}>
          <Card style={[styles.card, selected === item.id && styles.selected]}>
            <Text style={styles.name}>{String(item.title)}</Text>
            <Text style={styles.meta}>{String(item.description)}</Text>
          </Card>
        </Pressable>
      ))}
      {detail.data ? (
        <Card style={styles.card}>
          {detail.data.crisis_guidance ? (
            <Text style={styles.crisis}>{String(detail.data.crisis_guidance)}</Text>
          ) : null}
          {Array.isArray(detail.data.national_links)
            ? detail.data.national_links.map((link: Record<string, unknown>) => (
                <Pressable
                  key={String(link.id)}
                  onPress={() => (link.url ? Linking.openURL(String(link.url)) : undefined)}
                >
                  <Text style={styles.name}>{String(link.title)}</Text>
                  <Text style={styles.meta}>
                    {String(link.contact ?? '')} · {String(link.description ?? '')}
                  </Text>
                </Pressable>
              ))
            : null}
          {Array.isArray(detail.data.directory_entries) && detail.data.directory_entries.length === 0 ? (
            <Text style={styles.meta}>{t('wellbeing.noDirectory')}</Text>
          ) : null}
          {Array.isArray(detail.data.directory_entries)
            ? detail.data.directory_entries.map((entry: Record<string, unknown>) => (
                <Text key={String(entry.id)} style={styles.meta}>
                  • {String(entry.name)}
                </Text>
              ))
            : null}
        </Card>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 12, marginBottom: theme.spacing.md },
  card: { marginBottom: theme.spacing.sm, gap: 6 },
  selected: { borderColor: theme.colors.text, borderWidth: 1 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  crisis: { fontFamily: FONT_BOLD, color: theme.colors.danger, marginBottom: 8 },
});
