import { useMemo, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ListScreen } from '@/components/ui/ListScreen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { SIMPLE } from '@/constants/simpleCopy';
import { DOCUMENT_TYPES, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { roleHasAccess, ROUTE_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useDeleteDocument, useDocuments, useEvidencePack } from '@/hooks/useApi';
import { openDocumentFile } from '@/lib/openDocument';
import { pickDocument, uploadFile } from '@/lib/uploads';
import { DocumentItem } from '@/lib/api';

const TENANCY_TYPES = new Set(['tenancy_agreement', 'inventory', 'other']);

function isUrgent(doc: DocumentItem): boolean {
  if (doc.expiryDate && new Date(doc.expiryDate) < new Date()) return true;
  if (typeof doc.daysLeft === 'number' && doc.daysLeft <= 30) return true;
  return doc.riskLevel === 'critical' || doc.riskLevel === 'high';
}

function typeLabel(type: string): string {
  return DOCUMENT_TYPES.find((t) => t.id === type)?.label ?? type.replace(/_/g, ' ');
}

function typeIcon(type: string): keyof typeof Ionicons.glyphMap {
  switch (type) {
    case 'tenancy_agreement':
      return 'document-text-outline';
    case 'inventory':
      return 'clipboard-outline';
    case 'hmo_licence':
      return 'shield-checkmark-outline';
    case 'gas_safety':
      return 'flame-outline';
    case 'epc':
      return 'leaf-outline';
    case 'electrical_safety':
      return 'flash-outline';
    default:
      return 'folder-outline';
  }
}

export default function DocumentsScreen() {
  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useDocuments();
  const deleteDoc = useDeleteDocument();
  const evidencePack = useEvidencePack();
  const canUpload = roleHasAccess(user?.role, ROUTE_ROLES.documentsUpload);
  const canExportPack = ['landlord', 'property_manager', 'admin'].includes(user?.role ?? '');
  const isTenant = user?.role === 'tenant';
  const [uploading, setUploading] = useState(false);

  const documents = data?.documents ?? [];

  const { urgent, tenancyDocs, certificates } = useMemo(() => {
    const urgentDocs = documents.filter(isUrgent);
    const urgentIds = new Set(urgentDocs.map((d) => d.id));
    const rest = documents.filter((d) => !urgentIds.has(d.id));
    return {
      urgent: urgentDocs,
      tenancyDocs: rest.filter((d) => TENANCY_TYPES.has(d.type)),
      certificates: rest.filter((d) => !TENANCY_TYPES.has(d.type)),
    };
  }, [documents]);

  if (isLoading) return <LoadingScreen message="Loading files..." />;
  if (error) return <ErrorState message="Could not load your files" onRetry={refetch} />;

  async function handleUpload() {
    const file = await pickDocument();
    if (!file) return;
    setUploading(true);
    try {
      await uploadFile(file.uri, file.name, file.mimeType ?? 'application/pdf', {
        type: 'other',
        name: file.name,
      });
      refetch();
      Alert.alert('Done', 'Your file was uploaded.');
    } catch (err) {
      Alert.alert('Upload failed', err instanceof Error ? err.message : 'Please try again.');
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(doc: DocumentItem) {
    Alert.alert('Remove file?', doc.name, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteDoc.mutateAsync(doc.id);
            refetch();
          } catch (err) {
            Alert.alert('Error', err instanceof Error ? err.message : 'Could not remove file');
          }
        },
      },
    ]);
  }

  async function handleExportPack() {
    const properties = documents
      .map((d) => d.property)
      .filter((p): p is { id: string; name: string } => !!p?.id);
    if (properties.length === 0) {
      Alert.alert('No property found', 'Add a property first, then upload certificates.');
      return;
    }
    try {
      await evidencePack.mutateAsync(properties[0].id);
      Alert.alert('Pack ready', `Summary created for ${properties[0].name}.`);
    } catch (err) {
      Alert.alert('Download failed', err instanceof Error ? err.message : 'Please try again.');
    }
  }

  const listData = [...tenancyDocs, ...certificates];

  return (
    <ListScreen
      data={listData}
      keyExtractor={(item) => item.id}
      refreshing={isRefetching}
      onRefresh={refetch}
      contentContainerStyle={documents.length === 0 ? styles.emptyList : undefined}
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.title}>{isTenant ? 'Your documents' : 'Portfolio documents'}</Text>
          <Text style={styles.subtitle}>
            {isTenant
              ? 'Read your tenancy agreement, house rules and property certificates.'
              : 'Read HMO licences, safety certificates and tenancy papers across your properties.'}
          </Text>

          {documents.length > 0 && (
            <View style={styles.summary}>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{documents.length}</Text>
                <Text style={styles.summaryLabel}>Files</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryValue, urgent.length > 0 && styles.summaryWarn]}>
                  {urgent.length}
                </Text>
                <Text style={styles.summaryLabel}>Need attention</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{tenancyDocs.length}</Text>
                <Text style={styles.summaryLabel}>Tenancy</Text>
              </View>
            </View>
          )}

          <View style={styles.actions}>
            {canUpload && (
              <Button title={SIMPLE.documents.upload} onPress={handleUpload} loading={uploading} style={styles.actionBtn} />
            )}
            {canExportPack && documents.length > 0 && (
              <Button
                title={SIMPLE.documents.export}
                variant="outline"
                onPress={handleExportPack}
                loading={evidencePack.isPending}
                style={styles.actionBtn}
              />
            )}
          </View>

          {urgent.length > 0 && (
            <>
              <Text style={styles.sectionLabel}>{SIMPLE.documents.actionNeeded}</Text>
              {urgent.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  canDelete={canUpload}
                  onOpen={() => openDocumentFile(doc.fileUrl)}
                  onDelete={() => handleDelete(doc)}
                />
              ))}
            </>
          )}

          {tenancyDocs.length > 0 && (
            <Text style={styles.sectionLabel}>
              {isTenant ? 'Your tenancy papers' : 'Tenancy & house info'}
            </Text>
          )}
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title="No files yet"
          message={
            isTenant
              ? 'When your landlord shares agreements and certificates, they will appear here.'
              : SIMPLE.documents.empty
          }
          icon="folder-open-outline"
          actionLabel={canUpload ? SIMPLE.documents.upload : undefined}
          onAction={canUpload && !uploading ? handleUpload : undefined}
        />
      }
      renderItem={({ item, index }) => (
        <>
          {index === tenancyDocs.length && certificates.length > 0 && tenancyDocs.length > 0 ? (
            <Text style={styles.sectionLabelInline}>Property certificates</Text>
          ) : null}
          {index === 0 && tenancyDocs.length === 0 && certificates.length > 0 ? (
            <Text style={styles.sectionLabelInline}>Property certificates</Text>
          ) : null}
          <DocumentCard
            doc={item}
            canDelete={canUpload}
            onOpen={() => openDocumentFile(item.fileUrl)}
            onDelete={() => handleDelete(item)}
          />
        </>
      )}
    />
  );
}

function DocumentCard({
  doc,
  canDelete,
  onOpen,
  onDelete,
}: {
  doc: DocumentItem;
  canDelete: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const expired = !!(doc.expiryDate && new Date(doc.expiryDate) < new Date());
  const dueSoon =
    !expired &&
    !!doc.expiryDate &&
    (typeof doc.daysLeft === 'number'
      ? doc.daysLeft <= 30
      : new Date(doc.expiryDate).getTime() - Date.now() < 30 * 24 * 60 * 60 * 1000);

  return (
    <Card style={[styles.card, expired && styles.expired, dueSoon && !expired && styles.dueSoon]} onPress={onOpen}>
      <View style={styles.cardTop}>
        <View style={styles.fileIcon}>
          <Ionicons name={typeIcon(doc.type)} size={20} color={theme.colors.secondary} />
        </View>
        <View style={styles.cardCopy}>
          <Text style={styles.name}>{doc.name}</Text>
          <Text style={styles.type}>{typeLabel(doc.type)}</Text>
          {doc.property && <Text style={styles.property}>{doc.property.name}</Text>}
          {doc.notes ? <Text style={styles.notes}>{doc.notes}</Text> : null}
        </View>
        {expired ? (
          <Badge label="Expired" variant="error" />
        ) : dueSoon ? (
          <Badge label="Due soon" variant="warning" />
        ) : (
          <Badge label="Readable" variant="success" format={false} />
        )}
      </View>
      {doc.expiryDate && (
        <Text style={[styles.expiry, expired && styles.expiryBad, dueSoon && !expired && styles.expiryWarn]}>
          {expired ? 'Expired' : 'Expires'} {formatUKDate(doc.expiryDate)}
        </Text>
      )}
      <View style={styles.readRow}>
        <Ionicons name="book-outline" size={14} color={theme.colors.secondary} />
        <Text style={styles.open}>Tap to read</Text>
      </View>
      {canDelete && (
        <Pressable onPress={onDelete} hitSlop={8}>
          <Text style={styles.deleteText}>Remove</Text>
        </Pressable>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  emptyList: { flexGrow: 1 },
  header: { marginBottom: theme.spacing.sm },
  title: {
    fontSize: 26,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.4,
  },
  subtitle: {
    color: theme.colors.textSecondary,
    fontSize: 14,
    marginTop: 4,
    marginBottom: theme.spacing.md,
    fontFamily: FONT_MEDIUM,
    lineHeight: 20,
  },
  summary: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  summaryItem: {
    flex: 1,
    backgroundColor: theme.colors.surfaceMuted,
    borderRadius: theme.radius.lg,
    paddingVertical: 12,
    alignItems: 'center',
  },
  summaryValue: {
    fontSize: 20,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
  },
  summaryWarn: { color: theme.colors.warning },
  summaryLabel: {
    fontSize: 11,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textMuted,
    marginTop: 2,
  },
  actions: { flexDirection: 'column', gap: theme.spacing.sm, marginBottom: theme.spacing.md, width: '100%' },
  actionBtn: { width: '100%' },
  sectionLabel: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
  sectionLabelInline: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  card: { marginBottom: theme.spacing.sm },
  expired: { borderColor: theme.colors.error, backgroundColor: theme.colors.errorLight },
  dueSoon: { borderColor: theme.colors.warning, backgroundColor: theme.colors.warningLight },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  fileIcon: {
    width: 42,
    height: 42,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardCopy: { flex: 1, minWidth: 0 },
  name: {
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    fontSize: 15,
    color: theme.colors.text,
    letterSpacing: -0.2,
  },
  type: { color: theme.colors.textMuted, fontSize: 13, marginTop: 2, fontFamily: FONT_MEDIUM },
  property: {
    color: theme.colors.secondary,
    fontSize: 12,
    marginTop: 4,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
  },
  notes: { color: theme.colors.textSecondary, fontSize: 12, marginTop: 4, fontFamily: FONT_MEDIUM },
  expiry: {
    color: theme.colors.textMuted,
    fontSize: 12,
    marginTop: 10,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
  },
  expiryBad: { color: theme.colors.error },
  expiryWarn: { color: theme.colors.warning },
  readRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  open: { color: theme.colors.secondary, fontSize: 13, fontFamily: FONT_SEMIBOLD, fontWeight: '700' },
  deleteText: { color: theme.colors.error, fontSize: 12, fontFamily: FONT_SEMIBOLD, fontWeight: '600', marginTop: 8 },
});
