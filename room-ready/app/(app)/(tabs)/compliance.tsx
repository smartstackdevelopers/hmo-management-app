import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, Platform, StyleSheet, Text, View } from 'react-native';

import { FilterChips, InitialsTile, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { DOCUMENT_TYPES, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useDocuments } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { DocumentItem } from '@/lib/api';
import { HmoreApiError } from '@/lib/hmore/client';
import { fetchDocumentContent, listDocuments } from '@/lib/hmore/services/documents';
import type { ManagedDocument, Page } from '@/lib/hmore/types';
import { openDocumentFile } from '@/lib/openDocument';

type CertFilter = 'due' | 'expired' | 'valid';

type CertRow = {
  id: string;
  title: string;
  meta: string;
  bucket: CertFilter;
  chip: string;
  tone: Tone;
  onPress: () => void;
};

const FILTERS: { id: CertFilter; label: string }[] = [
  { id: 'due', label: 'Due soon' },
  { id: 'expired', label: 'Expired' },
  { id: 'valid', label: 'Valid' },
];

function isCertificate(type: string, title: string): boolean {
  const blob = `${type} ${title}`.toLowerCase();
  return /(cert|gas|epc|eicr|electrical|fire|licen[cs]e|hmo|legionella|insurance|cp12)/.test(blob);
}

function expiryBucket(expiry: string | null | undefined, tracking: string | null | undefined, daysLeft?: number | null): CertFilter {
  if (tracking === 'expired') return 'expired';
  if (tracking === 'expiring_soon') return 'due';
  if (typeof daysLeft === 'number' && daysLeft <= 30) return daysLeft < 0 ? 'expired' : 'due';
  if (expiry) {
    const time = new Date(expiry).getTime();
    if (!Number.isNaN(time)) {
      if (time < Date.now()) return 'expired';
      if (time - Date.now() < 30 * 24 * 60 * 60 * 1000) return 'due';
      return 'valid';
    }
  }
  if (tracking === 'valid' || tracking === 'renewed') return 'valid';
  return 'valid';
}

function daysUntil(iso?: string | null): number | null {
  if (!iso) return null;
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return null;
  return Math.ceil((time - Date.now()) / (24 * 60 * 60 * 1000));
}

function chipFor(bucket: CertFilter, dated: boolean, daysLeft?: number | null): { label: string; tone: Tone } {
  if (bucket === 'expired') return { label: 'Expired', tone: 'red' };
  if (bucket === 'due') {
    if (typeof daysLeft === 'number' && daysLeft >= 0) {
      return { label: daysLeft === 1 ? '1 day' : `${daysLeft} days`, tone: 'amber' };
    }
    return { label: 'Due soon', tone: 'amber' };
  }
  if (!dated) return { label: 'On file', tone: 'gray' };
  return { label: 'Valid', tone: 'green' };
}

function expiryPhrase(expiry: string | null | undefined, bucket: CertFilter): string | null {
  if (!expiry) return null;
  const date = formatUKDate(expiry);
  if (bucket === 'expired') return `Expired ${date}`;
  if (bucket === 'due') return `Expires ${date}`;
  return `Valid to ${date}`;
}

async function loadManaged(): Promise<Page<ManagedDocument>> {
  try {
    return await listDocuments();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 400 || error.status === 403 || error.status === 404)) {
      return { items: [], page: 1, page_size: 50, total: 0 };
    }
    throw error;
  }
}

async function openManaged(doc: ManagedDocument) {
  try {
    const { bytes, contentType } = await fetchDocumentContent(doc.id);
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      const blob = new Blob([bytes], { type: contentType });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
    const kb = Math.max(1, Math.round(bytes.byteLength / 1024));
    Alert.alert(doc.title, `Retrieved securely (${contentType}, ${kb} KB). This build does not include a native file viewer.`);
  } catch (error) {
    Alert.alert('Could not open file', error instanceof Error ? error.message : 'Please try again.');
  }
}

function legacyRow(doc: DocumentItem): CertRow | null {
  const typeLabel = DOCUMENT_TYPES.find((item) => item.id === doc.type)?.label ?? doc.type.replace(/_/g, ' ');
  if (!isCertificate(doc.type, `${doc.name} ${typeLabel}`)) return null;
  const bucket = expiryBucket(doc.expiryDate, null, doc.daysLeft);
  const chip = chipFor(bucket, Boolean(doc.expiryDate), doc.daysLeft ?? daysUntil(doc.expiryDate));
  const phrase = expiryPhrase(doc.expiryDate, bucket);
  return {
    id: doc.id,
    title: doc.property?.name ? `${doc.name || typeLabel} · ${doc.property.name}` : doc.name || typeLabel,
    meta: phrase || typeLabel,
    bucket,
    chip: chip.label,
    tone: chip.tone,
    onPress: () => openDocumentFile(doc.fileUrl),
  };
}

function managedRow(doc: ManagedDocument): CertRow | null {
  const kind = doc.category_code ?? '';
  const tracked = doc.expiry_tracking === 'expired' || doc.expiry_tracking === 'expiring_soon' || doc.expiry_tracking === 'valid' || doc.expiry_tracking === 'renewed';
  if (!isCertificate(kind, doc.title) && !tracked) return null;
  const bucket = expiryBucket(doc.expiry_date, doc.expiry_tracking);
  const days = daysUntil(doc.expiry_date);
  const chip = chipFor(bucket, Boolean(doc.expiry_date), days);
  const phrase = expiryPhrase(doc.expiry_date, bucket);
  const meta = [phrase, doc.reference_number].filter(Boolean).join(' · ');
  return {
    id: doc.id,
    title: doc.title,
    meta: meta || doc.status.replace(/_/g, ' '),
    bucket,
    chip: chip.label,
    tone: chip.tone,
    onPress: () => {
      void openManaged(doc);
    },
  };
}

export default function ComplianceScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(TAB_ROLES.compliance);
  if (guard) return guard;

  const { user, hmore } = useAuth();
  const legacy = useDocuments();
  const managed = useQuery({
    queryKey: ['hmore', 'documents', 'compliance'],
    queryFn: loadManaged,
    enabled: !!hmore,
  });
  const canUpload = ['landlord', 'property_manager', 'admin'].includes(user?.role ?? '');
  const [filter, setFilter] = useState<CertFilter>('due');
  const [query, setQuery] = useState('');

  const rows = useMemo(() => {
    const source = hmore ? (managed.data?.items ?? []).map(managedRow) : (legacy.data?.documents ?? []).map(legacyRow);
    return source.filter((row): row is CertRow => row != null);
  }, [hmore, managed.data, legacy.data]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (row.bucket !== filter) return false;
      if (!needle) return true;
      return `${row.title} ${row.meta}`.toLowerCase().includes(needle);
    });
  }, [rows, filter, query]);

  const loading = hmore ? managed.isLoading : legacy.isLoading;
  const loadError = hmore ? managed.error : legacy.error;
  if (loading) return <LoadingScreen message="Loading..." />;
  if (loadError) {
    return <ErrorState message="Could not load certificates" onRetry={() => (hmore ? managed.refetch() : legacy.refetch())} />;
  }

  function upload() {
    router.push('/(app)/property/upload-document');
  }

  return (
    <ListScreen
      data={filtered}
      keyExtractor={(item) => item.id}
      refreshing={hmore ? managed.isRefetching : legacy.isRefetching}
      onRefresh={() => (hmore ? managed.refetch() : legacy.refetch())}
      contentContainerStyle={filtered.length === 0 ? styles.emptyList : undefined}
      ListHeaderComponent={
        <View>
          <ScreenHeader
            title="Compliance"
            subtitle="Certificates across all properties"
            action={canUpload ? <Button title="Upload" icon="add" size="sm" onPress={upload} /> : undefined}
          />
          <SearchField value={query} onChangeText={setQuery} placeholder="Search certificates" />
          {rows.length > 0 ? <FilterChips options={FILTERS} value={filter} onChange={(id) => setFilter(id as CertFilter)} /> : null}
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title={rows.length === 0 ? 'No certificates yet' : 'Nothing in this filter'}
          message={
            rows.length === 0
              ? 'Gas, electrical, fire and licence files show up here after they are uploaded.'
              : 'Try another filter or search.'
          }
          icon="shield-checkmark-outline"
          actionLabel={canUpload && rows.length === 0 ? 'Upload certificate' : undefined}
          onAction={canUpload && rows.length === 0 ? upload : undefined}
        />
      }
      renderItem={({ item }) => (
        <Card style={styles.card} onPress={item.onPress}>
          <View style={styles.row}>
            <InitialsTile name={item.title} size={42} />
            <View style={styles.copy}>
              <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
              <Text style={styles.meta} numberOfLines={1}>{item.meta}</Text>
            </View>
            <Chip label={item.chip} tone={item.tone} />
            <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
          </View>
        </Card>
      )}
    />
  );
}

const styles = StyleSheet.create({
  emptyList: { flexGrow: 1 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
});
