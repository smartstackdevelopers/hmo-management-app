import { Ionicons } from '@expo/vector-icons';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export function LoadingScreen({ message = 'Loading...' }: { message?: string }) {
  return (
    <View style={styles.center}>
      <RoomReadyLogo size="sm" centered />
      <ActivityIndicator size="large" color={theme.colors.secondary} style={styles.spinner} />
      <Text style={styles.muted}>{message}</Text>
    </View>
  );
}

export function EmptyState({
  title,
  message,
  icon = 'folder-open-outline',
  actionLabel,
  onAction,
}: {
  title: string;
  message?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <View style={styles.center}>
      <Card style={styles.card} elevated>
        <View style={styles.iconCircle}>
          <Ionicons name={icon} size={28} color={theme.colors.secondary} />
        </View>
        <Text style={styles.title}>{title}</Text>
        {message && <Text style={styles.message}>{message}</Text>}
        {actionLabel && onAction && (
          <Button title={actionLabel} onPress={onAction} style={styles.action} size="md" variant="secondary" />
        )}
      </Card>
    </View>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <View style={styles.center}>
      <Card style={styles.card} elevated>
        <View style={[styles.iconCircle, styles.errorCircle]}>
          <Ionicons name="cloud-offline-outline" size={28} color={theme.colors.error} />
        </View>
        <Text style={styles.title}>Something went wrong</Text>
        <Text style={styles.message}>{message}</Text>
        {onRetry && (
          <Button title="Try again" onPress={onRetry} variant="outline" style={styles.action} />
        )}
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.background,
  },
  card: {
    width: '100%',
    maxWidth: 340,
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
    paddingHorizontal: theme.spacing.lg,
  },
  spinner: { marginTop: theme.spacing.lg },
  muted: {
    color: theme.colors.textSecondary,
    marginTop: 12,
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
  },
  iconCircle: {
    width: 68,
    height: 68,
    borderRadius: theme.radius.xl,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: '#CCFBF1',
  },
  errorCircle: {
    backgroundColor: theme.colors.errorLight,
    borderColor: '#FECACA',
  },
  title: {
    fontSize: 18,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    textAlign: 'center',
    letterSpacing: -0.3,
  },
  message: {
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 22,
    fontSize: 14,
  },
  action: { marginTop: theme.spacing.lg, minWidth: 160 },
});
