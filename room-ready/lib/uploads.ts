import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';

import { api } from '@/lib/api';
import { DocumentItem } from '@/lib/api';

export async function pickDocument() {
  const result = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true });
  if (result.canceled || !result.assets?.[0]) return null;
  return result.assets[0];
}

export async function pickImage() {
  const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permission.granted) return null;
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    quality: 0.8,
  });
  if (result.canceled || !result.assets?.[0]) return null;
  return result.assets[0];
}

export async function uploadFile(
  uri: string,
  name: string,
  mimeType: string,
  fields: Record<string, string>
): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', { uri, name, type: mimeType } as unknown as Blob);
  Object.entries(fields).forEach(([key, value]) => formData.append(key, value));
  const { document } = await api.upload<{ document: DocumentItem }>('/documents', formData);
  return document;
}
