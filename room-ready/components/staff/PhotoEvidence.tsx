import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Image, Pressable, Text } from 'react-native';

import { Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { validateStaffUpload } from '@/lib/hmore/uploads';
import { listAssignedWorkOrders, uploadWorkOrderPhoto } from '@/lib/hmore/services/staff/workOrders';
import { pickImage } from '@/lib/uploads';

type Photo = { uri: string; name: string; mimeType: string; size: number | null };

export function PhotoEvidence() {
  const orders = useQuery({ queryKey: ['hmore', 'staff', 'work-orders'], queryFn: listAssignedWorkOrders });
  const [requestId, setRequestId] = useState('');
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const selected = requestId || orders.data?.items[0]?.id || '';

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

  return (
    <StaffPage title="Photos" subtitle="Completion photos use the maintenance upload. JPEG, PNG, or WebP, up to 10 MB." onRefresh={orders.refetch} refreshing={orders.isRefetching}>
      {(orders.data?.items ?? []).map((order) => (
        <RecordCard key={order.id} title={order.title} status={order.status} detail={order.reference_number} onPress={() => setRequestId(order.id)} />
      ))}
      {photo ? (
        <>
          <Image source={{ uri: photo.uri }} style={{ width: 160, height: 160, borderRadius: 12, marginBottom: 8 }} />
          <Pressable onPress={() => setPhoto(null)}>
            <Text style={{ color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: 8 }}>Remove photo</Text>
          </Pressable>
        </>
      ) : (
        <Button title="Choose photo" variant="outline" onPress={choose} fullWidth />
      )}
      <Button title="Upload photo" onPress={upload} loading={busy} disabled={!photo || !selected} fullWidth />
      {feedback ? <Feedback text={feedback} tone={feedback.startsWith('Photo stored') ? 'ok' : 'warn'} /> : null}
    </StaffPage>
  );
}
