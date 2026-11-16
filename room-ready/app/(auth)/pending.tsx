import { Link, router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { theme } from '@/constants/theme';

export default function PendingApprovalScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.flex, { paddingTop: insets.top + 32, paddingBottom: insets.bottom + 24 }]}>
      <RoomReadyLogo size="sm" />
      <Text style={styles.title}>Registration pending</Text>
      <Card style={styles.card}>
        <Text style={styles.body}>
          Your account was created and is waiting for Super Admin (or Organisation Admin) approval.
        </Text>
        <Text style={styles.body}>
          You cannot open the app until an admin approves your requested role on the web dashboard.
        </Text>
        <Text style={styles.hint}>
          Admin path: Dashboard → Registration approvals
          {'\n'}
          http://localhost:3000/dashboard/approvals/registrations
        </Text>
      </Card>
      <Button title="Go to sign in" onPress={() => router.replace('/(auth)/login')} fullWidth size="lg" />
      <Link href="/(auth)/welcome" asChild>
        <Pressable style={styles.secondary}>
          <Text style={styles.link}>Back to welcome</Text>
        </Pressable>
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: theme.colors.background,
    paddingHorizontal: theme.spacing.lg,
  },
  title: {
    ...theme.typography.h2,
    color: theme.colors.text,
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  card: { marginBottom: theme.spacing.lg },
  body: {
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.sm,
  },
  hint: {
    fontSize: 12,
    lineHeight: 18,
    color: theme.colors.textMuted,
    marginTop: theme.spacing.sm,
  },
  secondary: { alignItems: 'center', marginTop: theme.spacing.lg },
  link: { color: theme.colors.secondary, fontWeight: '600', fontSize: 15 },
});
