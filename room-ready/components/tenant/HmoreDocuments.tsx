import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Alert, Platform, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { ListScreen } from '@/components/ui/ListScreen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { fetchDocumentContent, listDocuments } from '@/lib/hmore/services/documents';
import type { ManagedDocument } from '@/lib/hmore/types';

async function openDocument(doc: ManagedDocument) {
  const { bytes, contentType } = await fetchDocumentContent(doc.id);
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    const blob = new Blob([bytes], { type: contentType });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    return;
  }
  const kb = Math.max(1, Math.round(bytes.byteLength / 1024));
  Alert.alert(doc.title, `Retrieved securely (${contentType}, ${kb} KB). This build does not include a native file viewer.`);
}

export function HmoreDocuments() {
  const query = useQuery({ queryKey: ['hmore', 'documents'], queryFn: listDocuments });
  const [opening, setOpening] = useState<string | null>(null);
  const [error, setError] = useState('');

  if (query.isLoading) return <LoadingScreen message="Loading files..." />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load your files')} onRetry={query.refetch} />;

  const documents = query.data?.items ?? [];

  return (
    <ListScreen
      data={documents}
      keyExtractor={(item) => item.id}
      refreshing={query.isRefetching}
      onRefresh={query.refetch}
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.lead}>Files your organisation has shared with you. You can open ones you are allowed to read.</Text>
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>
      }
      ListEmptyComponent={<Text style={styles.empty}>No files yet.</Text>}
      renderItem={({ item }) => (
        <Card
          style={styles.card}
          onPress={async () => {
            setError('');
            setOpening(item.id);
            try {
              await openDocument(item);
            } catch (err) {
              setError(hmoreErrorMessage(err, 'Could not open this file'));
            } finally {
              setOpening(null);
            }
          }}
        >
          <View style={styles.row}>
            <Text style={styles.title}>{item.title}</Text>
            <Badge label={opening === item.id ? 'Opening' : item.status} format={false} />
          </View>
          <Text style={styles.meta}>
            {item.category_code || 'Document'}
            {item.expiry_date ? ` · Expires ${formatUKDate(item.expiry_date)}` : ''}
            {item.created_at ? ` · Added ${formatUKDate(item.created_at)}` : ''}
          </Text>
          {item.description ? <Text style={styles.body}>{item.description}</Text> : null}
        </Card>
      )}
    />
  );
}

const styles = StyleSheet.create({
  header: { marginBottom: theme.spacing.md },
  lead: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary },
  error: { color: theme.colors.error, marginTop: 8, fontFamily: FONT_MEDIUM },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, textAlign: 'center', marginTop: 24 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, alignItems: 'center' },
  title: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text, flex: 1 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, color: theme.colors.textSecondary, marginTop: 8 },
});
