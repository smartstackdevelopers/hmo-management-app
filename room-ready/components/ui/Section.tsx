import { Pressable, StyleSheet, Text, View } from 'react-native';

import { theme } from '@/constants/theme';

interface SectionProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
  children: React.ReactNode;
}

export function Section({ title, subtitle, actionLabel, onAction, children }: SectionProps) {
  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <View style={styles.copy}>
          <Text style={styles.title}>{title}</Text>
          {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
        </View>
        {actionLabel && onAction && (
          <Pressable onPress={onAction} hitSlop={8}>
            <Text style={styles.action}>{actionLabel}</Text>
          </Pressable>
        )}
      </View>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.lg },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
  },
  copy: { flex: 1 },
  title: { fontSize: 17, fontWeight: '600', color: theme.colors.text },
  subtitle: { fontSize: 13, color: theme.colors.textMuted, marginTop: 2 },
  action: { fontSize: 14, fontWeight: '600', color: theme.colors.secondary },
});
