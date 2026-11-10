import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Alert, Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { ListScreen } from '@/components/ui/ListScreen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { fetchDocumentContent, listDocuments, uploadOwnDocument } from '@/lib/hmore/services/documents';
import type { ManagedDocument } from '@/lib/hmore/types';
import { pickDocument } from '@/lib/uploads';

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
  const { t, fontScale } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ['hmore', 'documents'], queryFn: listDocuments });
  const [opening, setOpening] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<{ uri: string; name: string; mimeType: string } | null>(null);
  const [uploaded, setUploaded] = useState(false);

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error(t('documents.chooseFile'));
      return uploadOwnDocument(file, title.trim());
    },
    onSuccess: async () => {
      setUploaded(true);
      setTitle('');
      setFile(null);
      await client.invalidateQueries({ queryKey: ['hmore', 'documents'] });
    },
    onError: () => setUploaded(false),
  });

  if (query.isLoading) return <LoadingScreen message={t('documents.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error, t('documents.loadError'))} onRetry={query.refetch} />;

  const documents = query.data?.items ?? [];

  async function chooseFile() {
    const picked = await pickDocument();
    if (!picked) return;
    setUploaded(false);
    setFile({
      uri: picked.uri,
      name: picked.name,
      mimeType: picked.mimeType ?? 'application/pdf',
    });
    if (!title.trim()) setTitle(picked.name.replace(/\.[^.]+$/, ''));
  }

  return (
    <ListScreen
      data={documents}
      keyExtractor={(item) => item.id}
      refreshing={query.isRefetching}
      onRefresh={query.refetch}
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={[styles.lead, { fontSize: 14 * fontScale }]}>{t('documents.lead')}</Text>
          <Input
            label={t('documents.titleLabel')}
            value={title}
            onChangeText={(value) => {
              setUploaded(false);
              setTitle(value);
            }}
            accessibilityLabel={t('documents.titleLabel')}
          />
          <Button
            title={t('documents.chooseFile')}
            accessibilityLabel={t('documents.chooseFile')}
            variant="outline"
            onPress={chooseFile}
            fullWidth
          />
          {file ? (
            <View style={styles.fileRow}>
              <Text style={styles.meta}>
                {t('documents.selected')}: {file.name}
              </Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={t('documents.removeFile')}
                onPress={() => setFile(null)}
              >
                <Text style={styles.remove}>{t('documents.removeFile')}</Text>
              </Pressable>
            </View>
          ) : null}
          {upload.error ? <Text style={styles.error}>{hmoreErrorMessage(upload.error)}</Text> : null}
          {uploaded ? <Text style={styles.saved}>{t('documents.uploaded')}</Text> : null}
          <Button
            title={t('documents.upload')}
            accessibilityLabel={t('documents.upload')}
            onPress={() => upload.mutate()}
            loading={upload.isPending}
            disabled={!file || !title.trim()}
            fullWidth
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>
      }
      ListEmptyComponent={<Text style={styles.empty}>{t('documents.empty')}</Text>}
      renderItem={({ item }) => (
        <Card
          style={styles.card}
          onPress={async () => {
            setError('');
            setOpening(item.id);
            try {
              await openDocument(item);
            } catch (err) {
              setError(hmoreErrorMessage(err, t('documents.openError')));
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
  saved: { color: theme.colors.success, fontFamily: FONT_MEDIUM, marginTop: 8, marginBottom: 8 },
  error: { color: theme.colors.error, marginTop: 8, fontFamily: FONT_MEDIUM },
  remove: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginTop: 4 },
  fileRow: { marginBottom: theme.spacing.sm },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, textAlign: 'center', marginTop: 24 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, alignItems: 'center' },
  title: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text, flex: 1 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, color: theme.colors.textSecondary, marginTop: 8 },
});
