import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { HmoreRepairForm } from '@/components/tenant/HmoreRepairForm';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState, LoadingScreen } from '@/components/ui/States';
import { Input } from '@/components/ui/Input';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { MAINTENANCE_CATEGORIES } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateMaintenance, useProperties, useTenancies } from '@/hooks/useApi';
import { useAuth } from '@/contexts/AuthContext';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { runMaintenanceAICopilot } from '@/lib/ai';
import { getFileUrl } from '@/lib/config';
import { categoryIcon, PRIORITY_LABEL } from '@/lib/maintenance';
import { pickImage, uploadFile } from '@/lib/uploads';

const PRIORITIES = [
  { id: 'low' as const, hint: 'Cosmetic / not urgent' },
  { id: 'medium' as const, hint: 'Needs fixing soon' },
  { id: 'high' as const, hint: 'Affects daily living' },
  { id: 'emergency' as const, hint: 'Safety / no heat / flood' },
];

function LegacyNewMaintenanceScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.maintenanceNew);
  if (guard) return guard;

  const { user } = useAuth();
  const create = useCreateMaintenance();
  const { data: propertiesData, isLoading: loadingProps } = useProperties();
  const { data: tenanciesData, isLoading: loadingTenancy } = useTenancies();

  const [propertyId, setPropertyId] = useState('');
  const [roomId, setRoomId] = useState<string | undefined>();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<string>(MAINTENANCE_CATEGORIES[0]);
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'emergency'>('medium');
  const [photoUrls, setPhotoUrls] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [triage, setTriage] = useState<ReturnType<typeof runMaintenanceAICopilot> | null>(null);

  const properties = propertiesData?.properties ?? [];
  const tenancy =
    tenanciesData?.tenancies?.find((t) => t.status === 'active') ?? tenanciesData?.tenancies?.[0];
  const isTenant = user?.role === 'tenant';
  const defaultPropertyId = isTenant ? tenancy?.room?.property?.id : properties[0]?.id;
  const selectedPropertyId = propertyId || defaultPropertyId || '';
  const selectedProperty = properties.find((p) => p.id === selectedPropertyId);

  const homeLabel = useMemo(() => {
    if (!isTenant || !tenancy?.room?.property) return null;
    const p = tenancy.room.property;
    return `${p.name} · ${tenancy.room.name}`;
  }, [isTenant, tenancy]);

  if (loadingProps || loadingTenancy) return <LoadingScreen />;

  if (isTenant && !tenancy) {
    return (
      <EmptyState
        title="No active tenancy"
        message="You need an active tenancy to report a repair."
        actionLabel="View My home"
        onAction={() => router.push('/(app)/(tabs)/tenancy')}
      />
    );
  }

  if (!isTenant && properties.length === 0) {
    return (
      <EmptyState
        title="No properties yet"
        message="Add a property before reporting a repair."
        icon="business-outline"
        actionLabel="Add Property"
        onAction={() => router.push('/(app)/property/new')}
      />
    );
  }

  async function handleAddPhoto() {
    const image = await pickImage();
    if (!image || !selectedPropertyId) return;
    setUploading(true);
    try {
      const doc = await uploadFile(image.uri, `repair-${Date.now()}.jpg`, 'image/jpeg', {
        type: 'other',
        name: `Repair photo ${photoUrls.length + 1}`,
        propertyId: selectedPropertyId,
      });
      setPhotoUrls((prev) => [...prev, doc.fileUrl]);
    } catch (err) {
      Alert.alert('Upload failed', err instanceof Error ? err.message : 'Could not upload photo');
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmit() {
    if (!selectedPropertyId || !title.trim() || !description.trim()) {
      Alert.alert('Missing details', 'Add a title and description so we can help fix it.');
      return;
    }
    try {
      await create.mutateAsync({
        propertyId: selectedPropertyId,
        roomId: roomId ?? (isTenant ? tenancy?.room?.id : undefined),
        title: title.trim(),
        description: description.trim(),
        category,
        priority,
        photoUrls,
      });
      router.replace('/(app)/(tabs)/maintenance');
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Failed to submit request');
    }
  }

  function handleRunTriage() {
    if (!title.trim() && !description.trim()) {
      Alert.alert('Add details first', 'Write a short title or description, then run triage.');
      return;
    }
    const result = runMaintenanceAICopilot({ title, description, category });
    setPriority(result.priority);
    setTriage(result);
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      {homeLabel && (
        <Card style={styles.homeBanner}>
          <View style={styles.homeIcon}>
            <Ionicons name="home" size={18} color={theme.colors.secondary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.homeEyebrow}>Reporting for</Text>
            <Text style={styles.homeTitle}>{homeLabel}</Text>
          </View>
        </Card>
      )}

      {!isTenant && properties.length > 0 && (
        <>
          <Text style={styles.label}>Property</Text>
          {properties.map((p) => (
            <Pressable
              key={p.id}
              onPress={() => {
                setPropertyId(p.id);
                setRoomId(undefined);
              }}
              style={[styles.option, selectedPropertyId === p.id && styles.optionSelected]}
            >
              <Text style={styles.optionText}>{p.name}</Text>
              <Text style={styles.optionSub}>{p.addressLine1}</Text>
            </Pressable>
          ))}
        </>
      )}

      {!isTenant && selectedProperty?.rooms && selectedProperty.rooms.length > 0 && (
        <>
          <Text style={styles.label}>Room (optional)</Text>
          <View style={styles.chips}>
            {selectedProperty.rooms.map((r) => (
              <Pressable
                key={r.id}
                onPress={() => setRoomId(roomId === r.id ? undefined : r.id)}
                style={[styles.chip, roomId === r.id && styles.chipSelected]}
              >
                <Text style={[styles.chipText, roomId === r.id && styles.chipTextSelected]}>{r.name}</Text>
              </Pressable>
            ))}
          </View>
        </>
      )}

      <Text style={styles.label}>What type of issue?</Text>
      <View style={styles.categoryGrid}>
        {MAINTENANCE_CATEGORIES.map((c) => {
          const selected = category === c;
          return (
            <Pressable
              key={c}
              onPress={() => setCategory(c)}
              style={[styles.categoryCard, selected && styles.categoryCardSelected]}
            >
              <Ionicons
                name={categoryIcon(c)}
                size={20}
                color={selected ? theme.colors.secondary : theme.colors.textMuted}
              />
              <Text style={[styles.categoryLabel, selected && styles.categoryLabelSelected]} numberOfLines={2}>
                {c}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Input
        label="Short title *"
        value={title}
        onChangeText={setTitle}
        placeholder="e.g. Radiator not heating"
      />
      <Input
        label="Describe the problem *"
        value={description}
        onChangeText={setDescription}
        multiline
        numberOfLines={4}
        placeholder="Where is it? When did it start? Any safety risk?"
      />

      <Button title="Suggest priority with AI" variant="outline" onPress={handleRunTriage} fullWidth style={styles.aiBtn} />
      {triage && (
        <Card style={styles.aiCard}>
          <Text style={styles.aiTitle}>Suggested triage</Text>
          <Text style={styles.aiSummary}>{triage.summary}</Text>
          <Text style={styles.aiPriority}>Priority → {PRIORITY_LABEL[triage.priority] ?? triage.priority}</Text>
          {triage.riskFlags.map((flag) => (
            <Text key={flag} style={styles.aiFlag}>• {flag}</Text>
          ))}
        </Card>
      )}

      <Text style={styles.label}>Photos</Text>
      <Text style={styles.help}>A clear photo helps contractors fix it faster.</Text>
      <View style={styles.photos}>
        {photoUrls.map((url) => (
          <Image key={url} source={{ uri: getFileUrl(url) }} style={styles.photo} />
        ))}
        <Pressable
          style={styles.addPhoto}
          onPress={handleAddPhoto}
          disabled={uploading || !selectedPropertyId}
        >
          {uploading ? (
            <ActivityIndicator size="small" color={theme.colors.secondary} />
          ) : (
            <>
              <Ionicons name="camera-outline" size={22} color={theme.colors.secondary} />
              <Text style={styles.addPhotoText}>Add</Text>
            </>
          )}
        </Pressable>
      </View>

      <Text style={styles.label}>How urgent?</Text>
      <View style={styles.priorityList}>
        {PRIORITIES.map((p) => {
          const selected = priority === p.id;
          return (
            <Pressable
              key={p.id}
              onPress={() => setPriority(p.id)}
              style={[styles.priorityRow, selected && styles.prioritySelected, p.id === 'emergency' && selected && styles.priorityEmergency]}
            >
              <View style={[styles.radio, selected && styles.radioSelected]} />
              <View style={{ flex: 1 }}>
                <Text style={[styles.priorityTitle, selected && styles.priorityTitleSelected]}>
                  {PRIORITY_LABEL[p.id]}
                </Text>
                <Text style={styles.priorityHint}>{p.hint}</Text>
              </View>
            </Pressable>
          );
        })}
      </View>

      <Button
        title="Submit repair"
        onPress={handleSubmit}
        loading={create.isPending}
        fullWidth
        size="lg"
      />
      <Text style={styles.footerNote}>
        Your landlord is notified straight away. You can track progress under Repairs.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  homeBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: theme.spacing.md,
    backgroundColor: theme.colors.accentLight,
    borderColor: theme.colors.border,
  },
  homeIcon: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  homeEyebrow: {
    fontSize: 11,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.secondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  homeTitle: {
    fontSize: 15,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginTop: 2,
  },
  label: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  help: {
    fontSize: 13,
    color: theme.colors.textMuted,
    fontFamily: FONT_MEDIUM,
    marginTop: -4,
    marginBottom: theme.spacing.sm,
  },
  option: {
    padding: 14,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 8,
    backgroundColor: theme.colors.surface,
  },
  optionSelected: {
    borderColor: theme.colors.secondary,
    backgroundColor: theme.colors.accentLight,
  },
  optionText: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  optionSub: { fontSize: 13, color: theme.colors.textMuted, marginTop: 2, fontFamily: FONT_MEDIUM },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: theme.spacing.sm,
  },
  categoryCard: {
    width: '31%',
    minWidth: 96,
    flexGrow: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    gap: 6,
  },
  categoryCardSelected: {
    borderColor: theme.colors.secondary,
    backgroundColor: theme.colors.accentLight,
  },
  categoryLabel: {
    fontSize: 11,
    textAlign: 'center',
    color: theme.colors.textSecondary,
    fontFamily: FONT_MEDIUM,
    lineHeight: 14,
  },
  categoryLabelSelected: {
    color: theme.colors.secondaryDark,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
  },
  photos: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.sm },
  photo: { width: 76, height: 76, borderRadius: theme.radius.md },
  addPhoto: {
    width: 76,
    height: 76,
    borderRadius: theme.radius.md,
    borderWidth: 1.5,
    borderColor: theme.colors.border,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
    backgroundColor: theme.colors.surface,
  },
  addPhotoText: { fontSize: 12, color: theme.colors.secondary, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
  aiBtn: { marginTop: 4 },
  aiCard: {
    backgroundColor: theme.colors.accentLight,
    borderColor: theme.colors.border,
    marginTop: theme.spacing.sm,
    marginBottom: theme.spacing.sm,
  },
  aiTitle: { color: theme.colors.secondaryDark, fontFamily: FONT_BOLD, fontWeight: '700', marginBottom: 6 },
  aiSummary: { color: theme.colors.text, lineHeight: 20, marginBottom: 8, fontFamily: FONT_MEDIUM },
  aiPriority: {
    color: theme.colors.text,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    marginBottom: 6,
  },
  aiFlag: { color: theme.colors.textSecondary, fontSize: 13, lineHeight: 19, fontFamily: FONT_MEDIUM },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.sm },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: theme.radius.full,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
  },
  chipSelected: { backgroundColor: theme.colors.secondary, borderColor: theme.colors.secondary },
  chipText: { fontSize: 13, color: theme.colors.textSecondary, fontFamily: FONT_MEDIUM },
  chipTextSelected: { color: theme.colors.textInverse, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
  priorityList: { gap: 8, marginBottom: theme.spacing.lg },
  priorityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
  },
  prioritySelected: {
    borderColor: theme.colors.secondary,
    backgroundColor: theme.colors.accentLight,
  },
  priorityEmergency: {
    borderColor: theme.colors.error,
    backgroundColor: theme.colors.errorLight,
  },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: theme.colors.border,
  },
  radioSelected: {
    borderColor: theme.colors.secondary,
    backgroundColor: theme.colors.secondary,
  },
  priorityTitle: {
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    fontSize: 15,
  },
  priorityTitleSelected: { color: theme.colors.secondaryDark },
  priorityHint: {
    fontSize: 12,
    color: theme.colors.textMuted,
    marginTop: 2,
    fontFamily: FONT_MEDIUM,
  },
  footerNote: {
    textAlign: 'center',
    color: theme.colors.textMuted,
    fontSize: 12,
    fontFamily: FONT_MEDIUM,
    marginTop: theme.spacing.md,
    lineHeight: 18,
  },
});

export default function NewMaintenanceScreen() {
  const { hmore, user } = useAuth();
  if (hmore && user?.role === 'tenant') return <HmoreRepairForm />;
  return <LegacyNewMaintenanceScreen />;
}
