import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DOCUMENT_TYPES } from '@/constants/uk';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { useUploadDocument } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { uploadOwnDocument } from '@/lib/hmore/services/documents';
import { pickDocument } from '@/lib/uploads';

type Picked = { uri: string; name: string; mimeType: string };

export default function UploadDocumentScreen() {
  useHideTabHeader();
  const { hmore } = useAuth();
  const { t } = useI18n();
  const guard = useRoleGuard(ROUTE_ROLES.propertyUploadDocument);
  if (guard && !hmore) return guard;

  const { propertyId } = useLocalSearchParams<{ propertyId?: string }>();
  const upload = useUploadDocument();
  const [docType, setDocType] = useState<string>(DOCUMENT_TYPES[0].id);
  const [name, setName] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [file, setFile] = useState<Picked | null>(null);
  const [busy, setBusy] = useState(false);

  async function chooseFile() {
    const picked = await pickDocument();
    if (!picked) return;
    setFile({ uri: picked.uri, name: picked.name, mimeType: picked.mimeType ?? 'application/pdf' });
    if (!name.trim()) setName(picked.name.replace(/\.[^.]+$/, ''));
  }

  async function handleUpload() {
    if (!file) {
      Alert.alert('Choose a file', t('documents.chooseFile'));
      return;
    }
    setBusy(true);
    try {
      if (hmore) {
        await uploadOwnDocument(file, name.trim() || file.name);
      } else {
        const formData = new FormData();
        formData.append('file', { uri: file.uri, name: file.name, type: file.mimeType } as unknown as Blob);
        formData.append('type', docType);
        formData.append('name', name.trim() || file.name);
        if (propertyId) formData.append('propertyId', propertyId);
        if (expiryDate.trim()) {
          const [day, month, year] = expiryDate.split('/').map(Number);
          if (day && month && year) formData.append('expiryDate', new Date(year, month - 1, day).toISOString());
        }
        await upload.mutateAsync(formData);
      }
      Alert.alert(t('documents.uploaded'), '', [{ text: 'OK', onPress: () => router.back() }]);
    } catch (err) {
      Alert.alert('Upload failed', err instanceof Error ? err.message : 'Could not upload');
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <Text style={styles.title}>Upload document</Text>

      {hmore ? null : (
        <>
          <Text style={styles.label}>Document type</Text>
          {DOCUMENT_TYPES.filter((item) => item.id !== 'contractor_invoice').map((item) => (
            <Pressable
              key={item.id}
              onPress={() => setDocType(item.id)}
              style={[styles.option, docType === item.id && styles.optionSelected]}
            >
              <Text style={styles.optionText}>{item.label}</Text>
            </Pressable>
          ))}
        </>
      )}

      <Input label={t('documents.titleLabel')} value={name} onChangeText={setName} placeholder="File title" />
      {hmore ? null : <Input label="Expiry date" value={expiryDate} onChangeText={setExpiryDate} placeholder="DD/MM/YYYY" />}

      <Text style={styles.label}>File</Text>
      <Pressable onPress={chooseFile} style={styles.file} accessibilityRole="button" accessibilityLabel={t('documents.chooseFile')}>
        <Ionicons name="add" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.fileText}>{file ? file.name : t('documents.chooseFile')}</Text>
      </Pressable>

      <Button title={t('documents.upload')} onPress={handleUpload} loading={busy || upload.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  title: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.lg },
  label: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.sm },
  option: { padding: 12, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border, marginBottom: 8 },
  optionSelected: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.accentLight },
  optionText: { color: theme.colors.text, fontFamily: FONT_MEDIUM },
  file: {
    minHeight: 72,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 8,
    marginBottom: theme.spacing.lg,
    padding: theme.spacing.md,
  },
  fileText: { fontFamily: FONT_MEDIUM, color: theme.colors.secondaryDark, fontSize: 14 },
});
