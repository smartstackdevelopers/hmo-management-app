import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { useOfflineDrafts } from '@/hooks/useStaffDrafts';
import { retainAttachment } from '@/lib/hmore/offline/attachments';
import { readConnectivity } from '@/lib/hmore/offline/network';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { assignedPropertyId, formatAssignedAddress, getOwnHousing } from '@/lib/hmore/services/housing';
import { listMaintenanceCategories } from '@/lib/hmore/services/maintenance';
import { getOwnProfile } from '@/lib/hmore/services/tenants';
import { pickImage } from '@/lib/uploads';

const FALLBACK_CATEGORIES = [
  { code: 'general', title: 'General repairs' },
  { code: 'plumbing', title: 'Plumbing' },
  { code: 'electrical', title: 'Electrical' },
  { code: 'heating', title: 'Heating' },
  { code: 'water_leak', title: 'Water leaks' },
  { code: 'other', title: 'Other' },
];

type Photo = { uri: string; name: string; mimeType: string };

export function HmoreRepairForm() {
  const { t, fontScale, prefs } = useI18n();
  const client = useQueryClient();
  const drafts = useOfflineDrafts();
  const [notice, setNotice] = useState('');
  const profileQuery = useQuery({
    queryKey: ['hmore', 'tenant-me'],
    queryFn: getOwnProfile,
  });
  const housingQuery = useQuery({
    queryKey: ['hmore', 'tenant-housing'],
    queryFn: getOwnHousing,
  });
  const categoriesQuery = useQuery({
    queryKey: ['hmore', 'maintenance-categories'],
    queryFn: listMaintenanceCategories,
  });

  const categories = categoriesQuery.data?.length ? categoriesQuery.data : FALLBACK_CATEGORIES;
  const priorities = [
    { id: 'low' as const, label: t('repairs.low') },
    { id: 'normal' as const, label: t('repairs.normal') },
    { id: 'high' as const, label: t('repairs.high') },
    { id: 'urgent' as const, label: t('repairs.urgent') },
  ];
  const [category, setCategory] = useState('general');
  const [priority, setPriority] = useState<(typeof priorities)[number]['id']>('normal');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [photos, setPhotos] = useState<Photo[]>([]);

  const propertyId = assignedPropertyId(housingQuery.data);
  const address = formatAssignedAddress(housingQuery.data);
  const roomId = housingQuery.data?.room?.id ?? null;

  const create = useMutation({
    mutationFn: async () => {
      if (!profileQuery.data) throw new Error(t('repairs.unlinked'));
      if (!propertyId) throw new Error(t('repairs.needAssignment'));
      const stored = [];
      for (const photo of photos) {
        const uri = drafts.owner
          ? await retainAttachment(drafts.owner, photo.uri, profileQuery.data.id, undefined, photo.name)
          : photo.uri;
        stored.push({ ...photo, uri });
      }
      const draft = await drafts.save({
        type: 'repair_create',
        payload: {
          title: title.trim(),
          description: description.trim(),
          category_code: category,
          priority,
          property_id: propertyId,
          room_id: roomId,
          tenant_id: profileQuery.data.id,
          local_files: stored,
        },
        localAttachmentUris: stored.map((photo) => photo.uri),
      });
      if ((await readConnectivity()) !== 'online') return { offline: true as const, id: '' };
      const report = await drafts.sync();
      const result = report.results.find((item) => item.id === draft.id);
      if (!result?.saved || !result.serverResourceId) {
        throw new Error(result?.error || t('repairs.savedOffline'));
      }
      return { offline: false as const, id: result.serverResourceId };
    },
    onSuccess: async (created) => {
      if (created.offline) {
        setNotice(t('repairs.savedOffline'));
        return;
      }
      setNotice('');
      await client.invalidateQueries({ queryKey: ['hmore', 'maintenance'] });
      router.replace(`/(app)/maintenance/${created.id}`);
    },
  });

  if (profileQuery.isLoading || housingQuery.isLoading) {
    return <LoadingScreen message={t('repairs.preparing')} />;
  }
  if (profileQuery.error || housingQuery.error) {
    return <ErrorState message={hmoreErrorMessage(profileQuery.error ?? housingQuery.error)} />;
  }

  async function choosePhoto() {
    const image = await pickImage();
    if (!image) return;
    setPhotos((current) => [
      ...current,
      {
        uri: image.uri,
        name: image.fileName || 'repair.jpg',
        mimeType: image.mimeType || 'image/jpeg',
      },
    ]);
  }

  function removePhoto(index: number) {
    setPhotos((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  function submit() {
    if (!title.trim() || !description.trim()) {
      Alert.alert(t('repairs.missing'), t('repairs.missingBody'));
      return;
    }
    create.mutate();
  }

  const contrast = prefs.highContrast;

  return (
    <ScrollView
      style={[styles.page, contrast && styles.contrast]}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={[styles.note, { fontSize: 14 * fontScale }]}>{t('repairs.danger')}</Text>
      {!propertyId ? (
        <Card>
          <Text style={[styles.note, { fontSize: 14 * fontScale }]}>{t('repairs.needAssignment')}</Text>
        </Card>
      ) : (
        <Card>
          <Text style={styles.label}>{t('repairs.property')}</Text>
          <Text style={styles.choiceText}>{housingQuery.data?.property?.name}</Text>
          {address ? <Text style={styles.note}>{address}</Text> : null}
        </Card>
      )}
      <Card style={styles.gap}>
        <Text style={styles.label}>{t('repairs.category')}</Text>
        <View style={styles.wrap}>
          {categories.map((item) => (
            <Pressable
              key={item.code}
              accessibilityRole="button"
              accessibilityLabel={item.title}
              accessibilityState={{ selected: category === item.code }}
              onPress={() => setCategory(item.code)}
              style={[styles.choice, category === item.code && styles.choiceOn]}
            >
              <Text style={styles.choiceText}>{item.title}</Text>
            </Pressable>
          ))}
        </View>
        <Text style={styles.label}>{t('repairs.priority')}</Text>
        <View style={styles.wrap}>
          {priorities.map((item) => (
            <Pressable
              key={item.id}
              accessibilityRole="button"
              accessibilityLabel={item.label}
              accessibilityState={{ selected: priority === item.id }}
              onPress={() => setPriority(item.id)}
              style={[styles.choice, priority === item.id && styles.choiceOn]}
            >
              <Text style={styles.choiceText}>{item.label}</Text>
            </Pressable>
          ))}
        </View>
        <Input
          label={t('repairs.title')}
          value={title}
          onChangeText={setTitle}
          placeholder={t('repairs.titlePlaceholder')}
          accessibilityLabel={t('repairs.title')}
        />
        <Input
          label={t('repairs.description')}
          value={description}
          onChangeText={setDescription}
          multiline
          placeholder={t('repairs.descriptionPlaceholder')}
          accessibilityLabel={t('repairs.description')}
        />
        <Button
          title={t('repairs.addPhoto')}
          accessibilityLabel={t('repairs.addPhoto')}
          variant="outline"
          onPress={choosePhoto}
          fullWidth
        />
        {photos.map((photo, index) => (
          <View key={`${photo.uri}-${index}`} style={styles.photoRow}>
            <Image source={{ uri: photo.uri }} style={styles.preview} accessibilityLabel={t('repairs.photoAdded')} />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('repairs.removePhoto')}
              onPress={() => removePhoto(index)}
              style={styles.remove}
            >
              <Text style={styles.removeText}>{t('repairs.removePhoto')}</Text>
            </Pressable>
          </View>
        ))}
      </Card>
      {notice ? <Text style={styles.note}>{notice}</Text> : null}
      {create.error ? <Text style={styles.error}>{hmoreErrorMessage(create.error)}</Text> : null}
      <Button
        title={t('repairs.send')}
        accessibilityLabel={t('repairs.send')}
        onPress={submit}
        loading={create.isPending}
        disabled={!propertyId}
        fullWidth
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
  contrast: { backgroundColor: '#FFFFFF' },
  content: { padding: theme.spacing.md, paddingBottom: 40 },
  note: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  gap: { marginTop: theme.spacing.md, marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_SEMIBOLD, fontSize: 13, color: theme.colors.text, marginBottom: 8, marginTop: 8 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  choice: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 8,
  },
  choiceOn: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.accentLight },
  choiceText: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.text },
  photoRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 12 },
  preview: { width: 72, height: 72, borderRadius: theme.radius.md, backgroundColor: theme.colors.surfaceMuted },
  remove: { paddingVertical: 8 },
  removeText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.error, fontSize: 14 },
  error: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: theme.spacing.sm },
});
