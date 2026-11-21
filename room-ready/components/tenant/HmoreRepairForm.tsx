import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Image, Pressable, StyleSheet, Switch, Text, View } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Chip } from '@/components/ui/Chip';
import { Button } from '@/components/ui/Button';
import { useOfflineDrafts } from '@/hooks/useStaffDrafts';
import { retainAttachment } from '@/lib/hmore/offline/attachments';
import { readConnectivity } from '@/lib/hmore/offline/network';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useConnectivity } from '@/components/tenant/safeFetch';
import { TenantLoadError, TenantOffline } from '@/components/tenant/TenantStates';
import { Screen } from '@/components/ui/Screen';
import { LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
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

const MAX_PHOTOS = 5;

export function HmoreRepairForm() {
  useHideTabHeader();
  const { t, fontScale, prefs } = useI18n();
  const net = useConnectivity();
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

  const offline = net.data === 'offline';
  if (
    (profileQuery.isLoading && profileQuery.data === undefined) ||
    (housingQuery.isLoading && housingQuery.data === undefined)
  ) {
    if (offline && profileQuery.data === undefined && housingQuery.data === undefined) return <TenantOffline />;
    return <LoadingScreen message={t('repairs.preparing')} />;
  }
  if ((profileQuery.error && profileQuery.data === undefined) || (housingQuery.error && housingQuery.data === undefined)) {
    if (offline) return <TenantOffline />;
    return (
      <TenantLoadError
        title={t('repairs.couldNot')}
        onRetry={() => {
          profileQuery.refetch();
          housingQuery.refetch();
          net.refetch();
        }}
      />
    );
  }

  async function choosePhoto() {
    if (photos.length >= MAX_PHOTOS) return;
    const image = await pickImage();
    if (!image) return;
    setPhotos((current) => {
      if (current.length >= MAX_PHOTOS) return current;
      return [
        ...current,
        {
          uri: image.uri,
          name: image.fileName || 'repair.jpg',
          mimeType: image.mimeType || 'image/jpeg',
        },
      ];
    });
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
    <Screen style={contrast ? styles.contrast : undefined} keyboardShouldPersistTaps="handled">
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('housing.back')}
        onPress={() => (router.canGoBack() ? router.back() : router.replace('/(app)/(tabs)/maintenance'))}
        style={styles.back}
      >
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>{t('housing.back')}</Text>
      </Pressable>
      <Text style={[styles.pageTitle, { fontSize: 28 * fontScale }]} accessibilityRole="header">
        {t('repairs.report')}
      </Text>
      <Text style={[styles.note, { fontSize: 14 * fontScale }]}>{t('repairs.danger')}</Text>
      {!propertyId ? (
        <Card>
          <Text style={[styles.note, { fontSize: 14 * fontScale }]}>{t('repairs.needAssignment')}</Text>
        </Card>
      ) : (
        <View style={styles.assigned}>
          <Text style={styles.label}>{t('repairs.property')}</Text>
          <Text style={styles.choiceText}>{housingQuery.data?.property?.name}</Text>
          {address ? <Text style={styles.assignedAddress}>{address}</Text> : null}
        </View>
      )}
      <View style={styles.fields}>
        <Text style={styles.label}>{t('repairs.where')}</Text>
        <View style={styles.wrap}>
          {categories.map((item) => (
            <Chip
              key={item.code}
              label={item.title}
              selected={category === item.code}
              onPress={() => setCategory(item.code)}
              style={styles.choiceChip}
            />
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
          label={t('repairs.what')}
          value={description}
          onChangeText={setDescription}
          multiline
          placeholder={t('repairs.descriptionPlaceholder')}
          accessibilityLabel={t('repairs.what')}
        />
        <Text style={styles.label}>{t('repairs.photos')}</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('repairs.addPhotos')}
          accessibilityState={{ disabled: photos.length >= MAX_PHOTOS }}
          onPress={choosePhoto}
          disabled={photos.length >= MAX_PHOTOS}
          style={[styles.photoAdd, photos.length >= MAX_PHOTOS && styles.photoAddOff]}
        >
          <Text style={styles.photoAddTitle}>+ {t('repairs.addPhotos')}</Text>
          <Text style={styles.photoAddHint}>{t('repairs.photoHint')}</Text>
        </Pressable>
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
        <View style={styles.risk}>
          <Text style={[styles.riskLabel, { fontSize: 15 * fontScale }]}>{t('repairs.risk')}</Text>
          <Switch
            accessibilityLabel={t('repairs.risk')}
            value={priority === 'urgent'}
            onValueChange={(on) => setPriority(on ? 'urgent' : 'normal')}
            trackColor={{ false: theme.colors.border, true: theme.colors.accentSoft }}
            thumbColor={priority === 'urgent' ? theme.colors.secondaryDark : theme.colors.surface}
          />
        </View>
        <Text style={styles.label}>{t('repairs.priority')}</Text>
        <View style={styles.wrap}>
          {priorities.map((item) => (
            <Chip
              key={item.id}
              label={item.label}
              selected={priority === item.id}
              onPress={() => setPriority(item.id)}
              style={styles.choiceChip}
            />
          ))}
        </View>
      </View>
      {notice ? <Text style={styles.note}>{notice}</Text> : null}
      {create.error ? <Text style={styles.error}>{hmoreErrorMessage(create.error)}</Text> : null}
      <Button
        title={t('repairs.continue')}
        accessibilityLabel={t('repairs.continue')}
        onPress={submit}
        loading={create.isPending}
        disabled={!propertyId}
        fullWidth
        size="lg"
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  back: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 2,
    marginBottom: 4,
    paddingRight: 8,
  },
  backText: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.secondaryDark },
  pageTitle: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.5, marginBottom: theme.spacing.sm },
  note: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  assigned: { marginBottom: theme.spacing.sm },
  assignedAddress: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
  fields: { marginTop: theme.spacing.sm, marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_SEMIBOLD, fontSize: 13, color: theme.colors.text, marginBottom: 8, marginTop: 8 },
  choiceChip: { minHeight: 44, paddingHorizontal: 14, justifyContent: 'center' },
  photoAdd: {
    minHeight: 96,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: theme.colors.accentSoft,
    backgroundColor: theme.colors.accentLight,
    borderRadius: theme.radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
    marginBottom: theme.spacing.sm,
  },
  photoAddOff: { opacity: 0.45 },
  photoAddTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.secondaryDark },
  photoAddHint: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 4 },
  risk: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    marginTop: 8,
    marginBottom: 8,
  },
  riskLabel: { flex: 1, fontFamily: FONT_SEMIBOLD, color: theme.colors.text },
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
