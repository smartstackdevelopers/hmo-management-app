import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { FactGrid, FilterChips, InitialsTile, SearchField, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { DOCUMENT_TYPES, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { roleHasAccess, ROUTE_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { useDocuments } from '@/hooks/useApi';
import { DocumentItem } from '@/lib/api';
import { HmoreApiError, hmoreErrorMessage } from '@/lib/hmore/client';
import { fetchDocumentContent, listDocuments } from '@/lib/hmore/services/documents';
import type { ManagedDocument, Page } from '@/lib/hmore/types';
import { openDocumentFile } from '@/lib/openDocument';

type FileFilter = 'all' | 'tenancy' | 'certificate' | 'id';

type FileBucket = 'tenancy' | 'certificate' | 'id' | 'other';

type FileRow = {
  id: string;
  title: string;
  meta: string;
  bucket: FileBucket;
  chip: string;
  tone: Tone;
  facts: { label: string; value: string }[];
  onPress: () => void;
};

const FILTERS: { id: FileFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'tenancy', label: 'Tenancy' },
  { id: 'certificate', label: 'Certificates' },
  { id: 'id', label: 'ID' },
];

function fileBucket(type: string, title: string): FileBucket {
  const blob = `${type} ${title}`.toLowerCase();
  if (/(passport|identity|proof of id|\bid\b|driving)/.test(blob)) return 'id';
  if (/(tenancy|agreement|inventory)/.test(blob)) return 'tenancy';
  if (/(cert|gas|epc|eicr|electrical|fire|licen[cs]e|hmo|legionella|insurance)/.test(blob)) return 'certificate';
  return 'other';
}

function statusChip(expiry: string | null | undefined, tracking?: string | null, daysLeft?: number | null): { label: string; tone: Tone } {
  if (tracking === 'expired') return { label: 'Expired', tone: 'red' };
  if (tracking === 'expiring_soon') return { label: 'Due soon', tone: 'amber' };
  if (typeof daysLeft === 'number' && daysLeft <= 30) return { label: daysLeft < 0 ? 'Expired' : 'Due soon', tone: daysLeft < 0 ? 'red' : 'amber' };
  if (expiry) {
    const time = new Date(expiry).getTime();
    if (!Number.isNaN(time)) {
      if (time < Date.now()) return { label: 'Expired', tone: 'red' };
      if (time - Date.now() < 30 * 24 * 60 * 60 * 1000) return { label: 'Due soon', tone: 'amber' };
      return { label: 'Valid', tone: 'green' };
    }
  }
  if (tracking === 'valid' || tracking === 'renewed') return { label: 'Valid', tone: 'green' };
  return { label: 'On file', tone: 'gray' };
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

function fromLegacy(doc: DocumentItem): FileRow {
  const typeLabel = DOCUMENT_TYPES.find((item) => item.id === doc.type)?.label ?? doc.type.replace(/_/g, ' ');
  const chip = statusChip(doc.expiryDate, null, doc.daysLeft);
  const meta = [typeLabel, doc.property?.name, doc.expiryDate ? formatUKDate(doc.expiryDate) : null].filter(Boolean).join(' · ');
  const facts = [
    { label: 'Type', value: typeLabel },
    doc.property?.name ? { label: 'Property', value: doc.property.name } : null,
    doc.expiryDate ? { label: 'Expires', value: formatUKDate(doc.expiryDate) } : null,
    doc.notes ? { label: 'Notes', value: doc.notes } : null,
  ].filter((item): item is { label: string; value: string } => item != null);
  return {
    id: doc.id,
    title: doc.name,
    meta,
    bucket: fileBucket(doc.type, doc.name),
    chip: chip.label,
    tone: chip.tone,
    facts,
    onPress: () => openDocumentFile(doc.fileUrl),
  };
}

function fromManaged(doc: ManagedDocument): FileRow {
  const chip = statusChip(doc.expiry_date, doc.expiry_tracking);
  const meta = [doc.reference_number, doc.expiry_date ? formatUKDate(doc.expiry_date) : doc.created_at ? formatUKDate(doc.created_at) : null]
    .filter(Boolean)
    .join(' · ');
  const facts = [
    doc.reference_number ? { label: 'Reference', value: doc.reference_number } : null,
    doc.category_code ? { label: 'Type', value: titleCase(doc.category_code) } : null,
    { label: 'Status', value: titleCase(doc.status) },
    doc.expiry_date ? { label: 'Expires', value: formatUKDate(doc.expiry_date) } : null,
    doc.created_at ? { label: 'Added', value: formatUKDate(doc.created_at) } : null,
  ].filter((item): item is { label: string; value: string } => item != null);
  return {
    id: doc.id,
    title: doc.title,
    meta: meta || doc.status.replace(/_/g, ' '),
    bucket: fileBucket(doc.category_code ?? '', doc.title),
    chip: chip.label,
    tone: chip.tone,
    facts,
    onPress: () => {
      void openManaged(doc);
    },
  };
}

export default function DocumentsScreen() {
  useHideTabHeader();
  const { t } = useI18n();
  const { user, hmore } = useAuth();
  const legacy = useDocuments();
  const managed = useQuery({
    queryKey: ['hmore', 'documents', 'files'],
    queryFn: loadManaged,
    enabled: !!hmore,
  });
  const [filter, setFilter] = useState<FileFilter>('all');
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const canUpload = !!hmore || roleHasAccess(user?.role, ROUTE_ROLES.documentsUpload);

  const rows = useMemo(
    () => (hmore ? (managed.data?.items ?? []).map(fromManaged) : (legacy.data?.documents ?? []).map(fromLegacy)),
    [hmore, managed.data, legacy.data],
  );
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (filter !== 'all' && row.bucket !== filter) return false;
      if (!needle) return true;
      return `${row.title} ${row.meta}`.toLowerCase().includes(needle);
    });
  }, [rows, filter, query]);

  const selected = rows.find((row) => row.id === selectedId) ?? null;
  const loading = hmore ? managed.isLoading : legacy.isLoading;
  const loadError = hmore ? managed.error : legacy.error;
  if (loading) return <LoadingScreen message={t('documents.loading')} />;
  if (loadError) {
    return (
      <ErrorState
        message={hmoreErrorMessage(loadError, t('documents.loadError'))}
        onRetry={() => (hmore ? managed.refetch() : legacy.refetch())}
      />
    );
  }

  function upload() {
    router.push('/(app)/property/upload-document');
  }

  if (selected) {
    return (
      <ScrollView style={styles.screen} contentContainerStyle={styles.detail} keyboardShouldPersistTaps="handled">
        <Pressable onPress={() => setSelectedId(null)} style={[styles.back, styles.detailBack]} accessibilityRole="button" accessibilityLabel="Back">
          <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
          <Text style={styles.backText}>Back</Text>
        </Pressable>
        <View style={styles.banner}>
          <View style={styles.fileMark}>
            <Ionicons name="document-text" size={32} color={theme.colors.textInverse} />
          </View>
        </View>
        <Text style={styles.detailTitle}>{selected.title}</Text>
        {selected.meta ? <Text style={styles.detailMeta}>{selected.meta}</Text> : null}
        <View style={styles.chips}>
          <Chip label={selected.chip} tone={selected.tone} />
        </View>
        {selected.facts.length > 0 ? <FactGrid items={selected.facts} /> : null}
        <Button title="Open file" onPress={selected.onPress} fullWidth size="lg" />
      </ScrollView>
    );
  }

  return (
    <View style={styles.screen}>
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <ListScreen
        data={filtered}
        keyExtractor={(item) => item.id}
        refreshing={hmore ? managed.isRefetching : legacy.isRefetching}
        onRefresh={() => (hmore ? managed.refetch() : legacy.refetch())}
        padded={false}
        contentContainerStyle={[styles.list, filtered.length === 0 && styles.emptyList]}
        ListHeaderComponent={
          <View>
            <ScreenHeader
              title={t('nav.files')}
              subtitle={t('documents.lead')}
              action={canUpload ? <Button title={t('documents.upload')} size="sm" icon="add" onPress={upload} /> : undefined}
            />
            <SearchField value={query} onChangeText={setQuery} placeholder="Search files" />
            {rows.length > 0 ? <FilterChips options={FILTERS} value={filter} onChange={(id) => setFilter(id as FileFilter)} /> : null}
          </View>
        }
        ListEmptyComponent={
          <EmptyState
            title={rows.length === 0 ? t('documents.empty') : 'Nothing in this filter'}
            message={rows.length === 0 ? undefined : 'Try another filter or search.'}
            icon="folder-open-outline"
            actionLabel={canUpload && rows.length === 0 ? t('documents.upload') : undefined}
            onAction={canUpload && rows.length === 0 ? upload : undefined}
          />
        }
        renderItem={({ item }) => (
          <Card style={styles.card} onPress={() => setSelectedId(item.id)}>
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
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.colors.background, paddingTop: theme.spacing.sm },
  back: { flexDirection: 'row', alignItems: 'center', marginLeft: theme.spacing.md, marginBottom: theme.spacing.xs },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  list: { paddingHorizontal: theme.spacing.md },
  emptyList: { flexGrow: 1 },
  detail: { paddingHorizontal: theme.spacing.md, paddingBottom: 48 },
  detailBack: { marginLeft: 0 },
  banner: {
    height: 132,
    borderRadius: theme.radius.xl,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
  },
  fileMark: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: theme.colors.secondaryDark,
    alignItems: 'center',
    justifyContent: 'center',
  },
  detailTitle: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4 },
  detailMeta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 6, fontSize: 14 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
});
