import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DOCUMENT_TYPES } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useUploadDocument } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { pickDocument } from '@/lib/uploads';

export default function UploadDocumentScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.propertyUploadDocument);
  if (guard) return guard;

  const { propertyId } = useLocalSearchParams<{ propertyId: string }>();
  const upload = useUploadDocument();
  const [docType, setDocType] = useState<string>(DOCUMENT_TYPES[0].id);
  const [name, setName] = useState('');
  const [expiryDate, setExpiryDate] = useState('');

  async function handlePickAndUpload() {
    const file = await pickDocument();
    if (!file) return;
    const formData = new FormData();
    formData.append('file', { uri: file.uri, name: file.name, type: file.mimeType ?? 'application/pdf' } as unknown as Blob);
    formData.append('type', docType);
    formData.append('name', name || file.name);
    if (propertyId) formData.append('propertyId', propertyId);
    if (expiryDate) {
      const [day, month, year] = expiryDate.split('/').map(Number);
      if (day && month && year) {
        formData.append('expiryDate', new Date(year, month - 1, day).toISOString());
      }
    }
    try {
      await upload.mutateAsync(formData);
      Alert.alert('Uploaded', 'Document saved successfully', [{ text: 'OK', onPress: () => router.back() }]);
    } catch (err) {
      Alert.alert('Upload failed', err instanceof Error ? err.message : 'Could not upload');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.hint}>Upload compliance certificates and property documents.</Text>

      <Text style={styles.label}>Document type</Text>
      {DOCUMENT_TYPES.filter((d) => d.id !== 'contractor_invoice').map((d) => (
        <Pressable key={d.id} onPress={() => setDocType(d.id)} style={[styles.option, docType === d.id && styles.optionSelected]}>
          <Text style={styles.optionText}>{d.label}</Text>
        </Pressable>
      ))}

      <Input label="Display name" value={name} onChangeText={setName} placeholder="HMO Licence 2025" />
      <Input label="Expiry date (DD/MM/YYYY)" value={expiryDate} onChangeText={setExpiryDate} placeholder="15/03/2027" />
      <Button title="Choose File & Upload" onPress={handlePickAndUpload} loading={upload.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  hint: { color: theme.colors.textSecondary, marginBottom: theme.spacing.lg, lineHeight: 20 },
  label: { ...theme.typography.label, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.md },
  option: { padding: 12, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border, marginBottom: 8 },
  optionSelected: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.infoLight },
  optionText: { color: theme.colors.text },
});
