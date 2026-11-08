import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import {
  Alert,
  Image,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { HmoreRepairDetail } from '@/components/tenant/HmoreRepairDetail';
import { RepairStatusTrack } from '@/components/maintenance/RepairStatusTrack';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useContractors, useMaintenanceDetail, useUpdateMaintenance } from '@/hooks/useApi';
import { getFileUrl } from '@/lib/config';
import {
  PRIORITY_VARIANT,
  STATUS_VARIANT,
  categoryIcon,
  nextStepHint,
  relativeTime,
  statusLabel,
} from '@/lib/maintenance';

function PhotoThumb({ url }: { url: string }) {
  const fullUrl = getFileUrl(url);
  return (
    <Pressable onPress={() => Linking.openURL(fullUrl)}>
      <Image source={{ uri: fullUrl }} style={styles.photo} />
    </Pressable>
  );
}

function LegacyMaintenanceDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useMaintenanceDetail(id);
  const update = useUpdateMaintenance();
  const { data: contractorsData } = useContractors();
  const [note, setNote] = useState('');
  const [selectedContractor, setSelectedContractor] = useState<string | null>(null);

  if (isLoading) return <LoadingScreen message="Loading repair..." />;
  if (error || !data) return <ErrorState message="Repair request not found" onRetry={refetch} />;

  const request = data.request;
  const role = user?.role ?? '';
  const isManager = ['landlord', 'property_manager', 'admin'].includes(role);
  const isContractor = role === 'contractor' && request.contractor?.id === user?.id;
  const isTenant = role === 'tenant';
  const contractors = contractorsData?.contractors ?? [];
  const hint = nextStepHint(request.status, role);
  const icon = categoryIcon(request.category);

  async function handleStatus(status: string, contractorId?: string) {
    try {
      await update.mutateAsync({ id: request.id, status, contractorId, note: note || undefined });
      setNote('');
      refetch();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Update failed');
    }
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />
      }
    >
      <Card style={styles.hero}>
        <View style={styles.heroTop}>
          <View style={styles.iconTile}>
            <Ionicons name={icon} size={22} color={theme.colors.secondary} />
          </View>
          <View style={styles.heroCopy}>
            <Text style={styles.title}>{request.title}</Text>
            <Text style={styles.meta}>
              {request.property?.name}
              {request.room ? ` · ${request.room.name}` : ''}
            </Text>
          </View>
        </View>

        <View style={styles.badgeRow}>
          <Badge
            label={statusLabel(request.status)}
            variant={STATUS_VARIANT[request.status] ?? 'default'}
            format={false}
          />
          <Badge
            label={request.priority === 'emergency' ? 'Emergency' : request.priority}
            variant={PRIORITY_VARIANT[request.priority] ?? 'default'}
          />
          <Badge label={request.category} variant="default" format={false} />
        </View>

        <View style={styles.trackWrap}>
          <RepairStatusTrack status={request.status} />
        </View>

        {hint && (
          <View style={styles.hint}>
            <Ionicons name="information-circle-outline" size={18} color={theme.colors.secondary} />
            <Text style={styles.hintText}>{hint}</Text>
          </View>
        )}
      </Card>

      <Card style={styles.section}>
        <Text style={styles.sectionTitle}>What happened</Text>
        <Text style={styles.body}>{request.description}</Text>
        <Text style={styles.date}>
          Reported {formatUKDate(request.createdAt)} · {relativeTime(request.createdAt)}
          {request.reporter
            ? ` by ${request.reporter.firstName} ${request.reporter.lastName}`
            : ''}
        </Text>
      </Card>

      {request.photoUrls?.length > 0 && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Photos</Text>
          <Text style={styles.photoHint}>Tap to view full size</Text>
          <View style={styles.photos}>
            {request.photoUrls.map((url) => (
              <PhotoThumb key={url} url={url} />
            ))}
          </View>
        </Card>
      )}

      {request.contractor && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Contractor</Text>
          <View style={styles.contractorRow}>
            <View style={styles.contractorAvatar}>
              <Text style={styles.contractorInitials}>
                {request.contractor.firstName[0]}
                {request.contractor.lastName[0]}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.contractorName}>
                {request.contractor.firstName} {request.contractor.lastName}
              </Text>
              {request.contractor.phone ? (
                <Pressable onPress={() => Linking.openURL(`tel:${request.contractor!.phone!.replace(/\s/g, '')}`)}>
                  <Text style={styles.link}>{request.contractor.phone}</Text>
                </Pressable>
              ) : (
                <Text style={styles.muted}>Assigned to this job</Text>
              )}
            </View>
            {request.contractor.phone && (
              <Pressable
                style={styles.callBtn}
                onPress={() => Linking.openURL(`tel:${request.contractor!.phone!.replace(/\s/g, '')}`)}
              >
                <Ionicons name="call" size={18} color={theme.colors.textInverse} />
              </Pressable>
            )}
          </View>
        </Card>
      )}

      <Text style={styles.heading}>Activity</Text>
      {request.updates?.length ? (
        request.updates.map((u, index) => (
          <View key={u.id} style={styles.timelineItem}>
            <View style={styles.timelineRail}>
              <View style={styles.timelineDot} />
              {index < (request.updates?.length ?? 0) - 1 && <View style={styles.timelineLine} />}
            </View>
            <Card style={styles.update}>
              <View style={styles.updateHead}>
                <Text style={styles.updateAuthor}>
                  {u.author?.firstName} {u.author?.lastName}
                </Text>
                <Text style={styles.updateDate}>{relativeTime(u.createdAt)}</Text>
              </View>
              <Text style={styles.updateNote}>{u.note}</Text>
              {u.photoUrls?.length > 0 && (
                <View style={styles.photos}>
                  {u.photoUrls.map((url) => (
                    <PhotoThumb key={url} url={url} />
                  ))}
                </View>
              )}
            </Card>
          </View>
        ))
      ) : (
        <EmptyState
          title="No updates yet"
          message={
            isTenant
              ? 'When your landlord or contractor adds a note, it will show here.'
              : 'Status changes and notes will appear here.'
          }
          icon="chatbubbles-outline"
        />
      )}

      {(isManager || isContractor) && request.status !== 'closed' && request.status !== 'cancelled' && (
        <Card style={styles.actions}>
          <Text style={styles.sectionTitle}>Manage job</Text>
          <Input label="Add note (optional)" value={note} onChangeText={setNote} multiline />

          {isManager && request.status === 'open' && contractors.length === 0 && (
            <Text style={styles.noContractors}>
              No contractors on the platform yet. Add a note to track progress manually, or ask your admin to invite contractors.
            </Text>
          )}

          {isManager && request.status === 'open' && contractors.length > 0 && (
            <>
              <Text style={styles.pickerLabel}>Assign contractor</Text>
              {contractors.map((c) => (
                <Pressable
                  key={c.id}
                  onPress={() => setSelectedContractor(c.id)}
                  style={[styles.contractorOption, selectedContractor === c.id && styles.contractorSelected]}
                >
                  <Text style={styles.optionName}>
                    {c.firstName} {c.lastName}
                  </Text>
                  <Text style={styles.optionEmail}>{c.email}</Text>
                </Pressable>
              ))}
              <Button
                title="Assign contractor"
                onPress={() => selectedContractor && handleStatus('assigned', selectedContractor)}
                loading={update.isPending}
                disabled={!selectedContractor}
                fullWidth
              />
            </>
          )}

          {isContractor && request.status === 'assigned' && (
            <Button title="Start work" variant="secondary" onPress={() => handleStatus('in_progress')} loading={update.isPending} fullWidth />
          )}
          {isContractor && (request.status === 'in_progress' || request.status === 'awaiting_parts') && (
            <Button title="Mark complete" variant="accent" onPress={() => handleStatus('completed')} loading={update.isPending} fullWidth />
          )}
          {isManager && request.status === 'completed' && (
            <Button title="Close job" onPress={() => handleStatus('closed')} loading={update.isPending} fullWidth />
          )}
        </Card>
      )}

      {isTenant && (
        <Button
          title="Message about this repair"
          variant="outline"
          onPress={() => router.push('/(app)/(tabs)/messages')}
          fullWidth
          style={styles.messageBtn}
        />
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  hero: { marginBottom: theme.spacing.md },
  heroTop: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  iconTile: {
    width: 48,
    height: 48,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroCopy: { flex: 1, minWidth: 0 },
  title: {
    fontSize: 20,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.3,
    lineHeight: 26,
  },
  meta: {
    color: theme.colors.textSecondary,
    marginTop: 4,
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
  },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 12 },
  trackWrap: { marginTop: theme.spacing.md },
  hint: {
    flexDirection: 'row',
    gap: 8,
    marginTop: theme.spacing.md,
    padding: 12,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'flex-start',
  },
  hintText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 19,
    color: theme.colors.secondaryDark,
    fontFamily: FONT_MEDIUM,
  },
  section: { marginBottom: theme.spacing.md },
  sectionTitle: {
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '700',
    marginBottom: 8,
    color: theme.colors.text,
    fontSize: 15,
  },
  body: { color: theme.colors.textSecondary, lineHeight: 22, fontSize: 15, fontFamily: FONT_MEDIUM },
  link: { color: theme.colors.secondary, fontFamily: FONT_SEMIBOLD, fontWeight: '600', marginTop: 2 },
  muted: { color: theme.colors.textMuted, fontSize: 13, marginTop: 2, fontFamily: FONT_MEDIUM },
  date: { color: theme.colors.textMuted, fontSize: 13, marginTop: 10, fontFamily: FONT_MEDIUM },
  photoHint: { fontSize: 12, color: theme.colors.textMuted, marginBottom: 8, fontFamily: FONT_MEDIUM },
  photos: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  photo: { width: 88, height: 88, borderRadius: theme.radius.md, backgroundColor: theme.colors.surfaceMuted },
  contractorRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  contractorAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  contractorInitials: {
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.secondaryDark,
  },
  contractorName: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text, fontSize: 15 },
  callBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heading: {
    fontSize: 17,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    marginBottom: theme.spacing.sm,
    color: theme.colors.text,
  },
  timelineItem: { flexDirection: 'row', gap: 10, marginBottom: theme.spacing.sm },
  timelineRail: { width: 14, alignItems: 'center' },
  timelineDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: theme.colors.secondary,
    marginTop: 16,
  },
  timelineLine: {
    flex: 1,
    width: 2,
    backgroundColor: theme.colors.border,
    marginTop: 4,
    minHeight: 24,
  },
  update: { flex: 1, marginBottom: 0 },
  updateHead: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, marginBottom: 4 },
  updateAuthor: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  updateNote: { color: theme.colors.textSecondary, marginTop: 2, lineHeight: 20, fontFamily: FONT_MEDIUM },
  updateDate: { color: theme.colors.textMuted, fontSize: 12, fontFamily: FONT_MEDIUM },
  actions: { marginTop: theme.spacing.md, gap: theme.spacing.sm },
  noContractors: {
    color: theme.colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    backgroundColor: theme.colors.warningLight,
    padding: 12,
    borderRadius: theme.radius.md,
    fontFamily: FONT_MEDIUM,
  },
  pickerLabel: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 8,
  },
  contractorOption: {
    padding: 12,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 8,
  },
  contractorSelected: {
    borderColor: theme.colors.secondary,
    backgroundColor: theme.colors.accentLight,
  },
  optionName: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  optionEmail: { fontSize: 13, color: theme.colors.textMuted, marginTop: 2, fontFamily: FONT_MEDIUM },
  messageBtn: { marginTop: theme.spacing.md },
});

export default function MaintenanceDetailScreen() {
  const { hmore } = useAuth();
  if (hmore) return <HmoreRepairDetail />;
  return <LegacyMaintenanceDetailScreen />;
}
