import { useMemo, useState } from 'react';
import { RefreshControl, Text } from 'react-native';

import { FilterChips, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { StatusRow, staffLabel, statusTone } from '@/components/staff/ui';
import { Screen, ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { AdminUser } from '@/lib/api';
import { useAdminUsers } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { ROLE_LABELS } from '@/types';
import type { UserRole } from '@/types';

type Filter = 'all' | 'pending' | 'staff' | 'tenants';

function roleLabel(role: string): string {
  if (role in ROLE_LABELS) return ROLE_LABELS[role as UserRole];
  return staffLabel(role);
}

function isTenant(role: string): boolean {
  return role === 'tenant';
}

export default function UsersScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(TAB_ROLES.users);
  const { data, isLoading, error, refetch, isRefetching } = useAdminUsers();
  const [queryText, setQueryText] = useState('');
  const [filter, setFilter] = useState<Filter>('all');

  const users = data?.users ?? [];
  const visible = useMemo(() => {
    const needle = queryText.trim().toLowerCase();
    return users.filter((user) => {
      if (filter === 'pending' && user.verified) return false;
      if (filter === 'staff' && isTenant(user.role)) return false;
      if (filter === 'tenants' && !isTenant(user.role)) return false;
      if (!needle) return true;
      return `${user.firstName} ${user.lastName} ${user.email} ${user.role}`.toLowerCase().includes(needle);
    });
  }, [users, filter, queryText]);

  if (guard) return guard;
  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load users" />;

  return (
    <Screen refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}>
      <ScreenHeader title="Users" subtitle={`${users.length} users`} />
      <SearchField value={queryText} onChangeText={setQueryText} placeholder="Search name or email" />
      <FilterChips
        value={filter}
        onChange={(id) => setFilter(id as Filter)}
        options={[
          { id: 'all', label: 'All' },
          { id: 'pending', label: 'Pending' },
          { id: 'staff', label: 'Staff' },
          { id: 'tenants', label: 'Tenants' },
        ]}
      />
      {visible.length === 0 ? (
        users.length === 0 ? <EmptyState title="No users" /> : <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary }}>No users match this search.</Text>
      ) : (
        visible.map((user) => <UserRow key={user.id} user={user} />)
      )}
    </Screen>
  );
}

function UserRow({ user }: { user: AdminUser }) {
  const name = `${user.firstName} ${user.lastName}`.trim() || user.email;
  const chip = !user.active ? 'Suspended' : !user.verified ? 'Pending' : 'Active';
  return (
    <StatusRow
      name={name}
      title={name}
      subtitle={`${roleLabel(user.role)} · ${user.email}`}
      chip={chip}
      tone={statusTone(chip)}
    />
  );
}
