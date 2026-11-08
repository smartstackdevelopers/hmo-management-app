import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import type { Phase5PendingResult } from '@/lib/hmore/types';

export function Phase5Notice({ result }: { result: Phase5PendingResult }) {
  const icon = result.feature === 'jobs' ? 'briefcase-outline' : 'location-outline';
  const title = result.feature === 'jobs' ? 'Jobs and training' : 'Local services';
  return (
    <View style={styles.page}>
      <Card>
        <View style={styles.iconWrap}>
          <Ionicons name={icon} size={28} color={theme.colors.secondary} />
        </View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.body}>{result.message}</Text>
        <Text style={styles.meta}>Status: {result.status}</Text>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background, padding: theme.spacing.md },
  iconWrap: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
  },
  title: { fontFamily: FONT_BOLD, fontSize: 22, color: theme.colors.text, marginBottom: theme.spacing.sm },
  body: { fontFamily: FONT_MEDIUM, fontSize: 15, lineHeight: 22, color: theme.colors.textSecondary },
  meta: { marginTop: theme.spacing.md, fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted },
});
