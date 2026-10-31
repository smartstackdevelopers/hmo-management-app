import { StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ListScreen } from '@/components/ui/ListScreen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { AdminUser } from '@/lib/api';
import { useAdminUsers, useVerifyUser } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { ROLE_LABELS } from '@/types';

export default function UsersScreen() {
  const guard = useRoleGuard(TAB_ROLES.users);
  if (guard) return guard;

  const { data, isLoading, error, refetch, isRefetching } = useAdminUsers();
  const verify = useVerifyUser();

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load users" />;

  const users = data?.users ?? [];

  return (
    <ListScreen
      data={users}
      keyExtractor={(item) => item.id}
      refreshing={isRefetching}
      onRefresh={refetch}
      contentContainerStyle={users.length === 0 ? styles.emptyList : undefined}
      ListEmptyComponent={<EmptyState title="No users" />}
      renderItem={({ item }) => (
        <UserCard user={item} onVerify={() => verify.mutate({ id: item.id, verified: true })} />
      )}
    />
  );
}

function UserCard({ user, onVerify }: { user: AdminUser; onVerify: () => void }) {
  return (
    <Card style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.name} numberOfLines={1}>
          {user.firstName} {user.lastName}
        </Text>
        <Badge label={ROLE_LABELS[user.role as keyof typeof ROLE_LABELS] ?? user.role} variant="info" />
      </View>
      <Text style={styles.email} numberOfLines={1}>{user.email}</Text>
      <View style={styles.tags}>
        <Badge label={user.verified ? 'Verified' : 'Unverified'} variant={user.verified ? 'success' : 'warning'} />
        <Badge label={user.active ? 'Active' : 'Suspended'} variant={user.active ? 'default' : 'error'} />
      </View>
      {!user.verified && (
        <Button title="Verify User" size="sm" onPress={onVerify} style={styles.verifyBtn} />
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  emptyList: { flexGrow: 1 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  name: { fontWeight: '600', fontSize: 16, color: theme.colors.text, flex: 1, minWidth: 0 },
  email: { color: theme.colors.textSecondary, marginTop: 4 },
  tags: { flexDirection: 'row', gap: 8, marginTop: 8, flexWrap: 'wrap' },
  verifyBtn: { marginTop: 12, alignSelf: 'flex-start' },
});
