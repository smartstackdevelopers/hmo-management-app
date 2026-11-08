import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { createMaintenance, listMaintenance, listMaintenanceCategories, uploadMaintenancePhoto } from '@/lib/hmore/services/maintenance';
import { listHousingApplications } from '@/lib/hmore/services/housingApplications';
import { getOwnTenant } from '@/lib/hmore/services/tenants';
import { pickImage } from '@/lib/uploads';

const FALLBACK_CATEGORIES = [
  { code: 'general', title: 'General repairs' },
  { code: 'plumbing', title: 'Plumbing' },
  { code: 'electrical', title: 'Electrical' },
  { code: 'heating', title: 'Heating' },
  { code: 'water_leak', title: 'Water leaks' },
  { code: 'other', title: 'Other' },
];

const PRIORITIES = [
  { id: 'low' as const, label: 'Low' },
  { id: 'normal' as const, label: 'Normal' },
  { id: 'high' as const, label: 'High' },
  { id: 'urgent' as const, label: 'Urgent' },
];

export function HmoreRepairForm() {
  const { hmore } = useAuth();
  const client = useQueryClient();
  const userId = hmore?.auth.id ?? '';
  const tenantQuery = useQuery({
    queryKey: ['hmore', 'tenant', userId],
    queryFn: () => getOwnTenant(userId),
    enabled: !!userId,
  });
  const appsQuery = useQuery({ queryKey: ['hmore', 'housing-applications'], queryFn: listHousingApplications });
  const repairsQuery = useQuery({
    queryKey: ['hmore', 'maintenance'],
    queryFn: () => listMaintenance({ page: 1, page_size: 50 }),
  });
  const categoriesQuery = useQuery({
    queryKey: ['hmore', 'maintenance-categories'],
    queryFn: listMaintenanceCategories,
  });

  const propertyIds = useMemo(() => {
    const ids = new Set<string>();
    for (const app of appsQuery.data?.items ?? []) {
      if (app.preferred_property_id) ids.add(app.preferred_property_id);
    }
    for (const repair of repairsQuery.data?.items ?? []) {
      if (repair.property_id) ids.add(repair.property_id);
    }
    return [...ids];
  }, [appsQuery.data, repairsQuery.data]);

  const categories = categoriesQuery.data?.length ? categoriesQuery.data : FALLBACK_CATEGORIES;
  const [propertyId, setPropertyId] = useState('');
  const [category, setCategory] = useState('general');
  const [priority, setPriority] = useState<(typeof PRIORITIES)[number]['id']>('normal');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [photo, setPhoto] = useState<{ uri: string; name: string; mimeType: string } | null>(null);

  const selectedProperty = propertyId || propertyIds[0] || '';

  const create = useMutation({
    mutationFn: async () => {
      if (!tenantQuery.data) throw new Error('Your login is not linked to a housing record yet.');
      if (!selectedProperty) throw new Error('No property is linked yet, so a repair cannot be filed.');
      const created = await createMaintenance({
        title: title.trim(),
        description: description.trim(),
        category_code: category,
        priority,
        property_id: selectedProperty,
        tenant_id: tenantQuery.data.id,
      });
      if (photo) {
        await uploadMaintenancePhoto(created.id, photo, title.trim());
      }
      return created;
    },
    onSuccess: async (created) => {
      await client.invalidateQueries({ queryKey: ['hmore', 'maintenance'] });
      router.replace(`/(app)/maintenance/${created.id}`);
    },
  });

  if (tenantQuery.isLoading || appsQuery.isLoading || repairsQuery.isLoading) {
    return <LoadingScreen message="Preparing the repair form..." />;
  }
  if (tenantQuery.error || appsQuery.error || repairsQuery.error) {
    return <ErrorState message={hmoreErrorMessage(tenantQuery.error ?? appsQuery.error ?? repairsQuery.error)} />;
  }

  async function choosePhoto() {
    const image = await pickImage();
    if (!image) return;
    setPhoto({
      uri: image.uri,
      name: image.fileName || 'repair.jpg',
      mimeType: image.mimeType || 'image/jpeg',
    });
  }

  function submit() {
    if (!title.trim() || !description.trim()) {
      Alert.alert('Add a title and description', 'Tell us what needs repairing.');
      return;
    }
    create.mutate();
  }

  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.note}>
        If someone is in immediate danger, call 999. Urgent is the highest priority you can set — staff review emergency priority.
      </Text>
      {!selectedProperty ? (
        <Card>
          <Text style={styles.note}>
            No property is on your housing applications or existing repairs. You can view repairs, and your organisation needs to link a property before a new report can be sent.
          </Text>
        </Card>
      ) : (
        <Card>
          <Text style={styles.label}>Property</Text>
          {propertyIds.map((id) => (
            <Pressable key={id} onPress={() => setPropertyId(id)} style={[styles.choice, selectedProperty === id && styles.choiceOn]}>
              <Text style={styles.choiceText}>{id}</Text>
            </Pressable>
          ))}
        </Card>
      )}
      <Card style={styles.gap}>
        <Text style={styles.label}>Category</Text>
        <View style={styles.wrap}>
          {categories.map((item) => (
            <Pressable key={item.code} onPress={() => setCategory(item.code)} style={[styles.choice, category === item.code && styles.choiceOn]}>
              <Text style={styles.choiceText}>{item.title}</Text>
            </Pressable>
          ))}
        </View>
        <Text style={styles.label}>Priority</Text>
        <View style={styles.wrap}>
          {PRIORITIES.map((item) => (
            <Pressable key={item.id} onPress={() => setPriority(item.id)} style={[styles.choice, priority === item.id && styles.choiceOn]}>
              <Text style={styles.choiceText}>{item.label}</Text>
            </Pressable>
          ))}
        </View>
        <Input label="Title" value={title} onChangeText={setTitle} placeholder="For example, leaking tap" />
        <Input label="What happened" value={description} onChangeText={setDescription} multiline placeholder="Where it is and what you noticed" />
        <Button title={photo ? 'Photo added' : 'Add a photo'} variant="outline" onPress={choosePhoto} fullWidth />
      </Card>
      {create.error ? <Text style={styles.error}>{hmoreErrorMessage(create.error)}</Text> : null}
      <Button title="Send repair" onPress={submit} loading={create.isPending} disabled={!selectedProperty} fullWidth />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
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
  error: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: theme.spacing.sm },
});
