import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Image, Pressable, Text, View } from 'react-native';

import { FilterChips, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Feedback, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { validateStaffUpload } from '@/lib/hmore/uploads';
import { listAssignedWorkOrders, uploadWorkOrderPhoto } from '@/lib/hmore/services/staff/workOrders';
import { pickImage } from '@/lib/uploads';

type Photo = { uri: string; name: string; mimeType: string; size: number | null };

export function PhotoEvidence() {
  useHideTabHeader();
  const orders = useQuery({ queryKey: ['hmore', 'staff', 'work-orders'], queryFn: listAssignedWorkOrders });
  const [requestId, setRequestId] = useState('');
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const selected = requestId || orders.data?.items[0]?.id || '';
  const current = orders.data?.items.find((order) => order.id === selected);

  if (orders.isLoading) return <LoadingScreen message="Loading work orders..." />;
  if (orders.isError) return <ErrorState message={hmoreErrorMessage(orders.error, 'Could not load work orders')} onRetry={orders.refetch} />;

  async function choose() {
    const asset = await pickImage();
    if (!asset) return;
    const next = {
      uri: asset.uri,
      name: asset.fileName || 'evidence.jpg',
      mimeType: asset.mimeType || 'image/jpeg',
      size: asset.fileSize ?? null,
    };
    const problem = validateStaffUpload(next, 'photo');
    if (problem) {
      setPhoto(null);
      setFeedback(problem);
      return;
    }
    setPhoto(next);
    setFeedback('');
  }

  async function upload() {
    if (!selected || !photo) {
      setFeedback('Choose a work order and a photo. Nothing was uploaded.');
      return;
    }
    setBusy(true);
    try {
      const updated = await uploadWorkOrderPhoto(selected, photo, 'Completion evidence');
      setFeedback(`Photo stored. Server status: ${updated.status}.`);
      setPhoto(null);
    } catch (error) {
      setFeedback(`${hmoreErrorMessage(error, 'The photo was not uploaded.')} It is not on the server.`);
    } finally {
      setBusy(false);
    }
  }

  const items = orders.data?.items ?? [];

  return (
    <StaffPage
      title={current ? `Evidence · ${current.reference_number}` : 'Evidence'}
      subtitle={current?.title || 'Choose a job, then add a completion photo.'}
      onRefresh={orders.refetch}
      refreshing={orders.isRefetching}
    >
      {items.length === 0 ? (
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary }}>No work orders to attach a photo to.</Text>
      ) : (
        <FilterChips
          value={selected}
          onChange={setRequestId}
          options={items.map((order) => ({ id: order.id, label: order.reference_number || order.title }))}
        />
      )}
      <Text style={{ fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: 8 }}>Photo</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
        {photo ? (
          <View>
            <Image source={{ uri: photo.uri }} style={{ width: 96, height: 96, borderRadius: 16 }} />
            <Pressable onPress={() => setPhoto(null)} accessibilityRole="button" accessibilityLabel="Remove photo">
              <Text style={{ color: theme.colors.error, fontFamily: FONT_MEDIUM, marginTop: 6 }}>Remove</Text>
            </Pressable>
          </View>
        ) : (
          <Pressable
            onPress={choose}
            accessibilityRole="button"
            accessibilityLabel="Add photo"
            style={{
              width: 96,
              height: 96,
              borderRadius: 16,
              borderWidth: 1,
              borderColor: theme.colors.border,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: theme.colors.surface,
            }}
          >
            <Text style={{ fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark }}>+ Add</Text>
          </Pressable>
        )}
      </View>
      <Button title="Submit for sign-off" onPress={upload} loading={busy} disabled={!photo || !selected} fullWidth />
      {feedback ? <Feedback text={feedback} tone={feedback.startsWith('Photo stored') ? 'ok' : 'warn'} /> : null}
    </StaffPage>
  );
}
