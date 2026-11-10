import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { Image, Pressable, Text } from 'react-native';

import { ChoiceRow, Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { validateStaffUpload } from '@/lib/hmore/uploads';
import { listCaseload } from '@/lib/hmore/services/staff/caseload';
import { listDocumentCategories, uploadLinkedDocument } from '@/lib/hmore/services/staff/documents';
import { createIncident, listIncidents } from '@/lib/hmore/services/staff/incidents';
import { pickImage } from '@/lib/uploads';

const SEVERITIES = ['low', 'normal', 'high', 'critical'] as const;

type Photo = { uri: string; name: string; mimeType: string; size: number | null };

export function IncidentBoard() {
  const { user } = useAuth();
  const incidents = useQuery({ queryKey: ['hmore', 'staff', 'incidents'], queryFn: listIncidents });
  const tenants = useQuery({
    queryKey: ['hmore', 'staff', 'caseload', user?.role],
    queryFn: () => listCaseload(user?.role, { page: 1, page_size: 50, status: 'active' }),
  });
  const categories = useQuery({ queryKey: ['hmore', 'staff', 'doc-categories'], queryFn: listDocumentCategories });
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<(typeof SEVERITIES)[number]>('normal');
  const [tenantId, setTenantId] = useState('');
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [feedback, setFeedback] = useState('');
  const [savedOnServer, setSavedOnServer] = useState(false);
  const [busy, setBusy] = useState(false);

  if (incidents.isLoading) return <LoadingScreen message="Loading incidents..." />;
  if (incidents.isError) return <ErrorState message={hmoreErrorMessage(incidents.error, 'Could not load incidents')} onRetry={incidents.refetch} />;

  async function choosePhoto() {
    const asset = await pickImage();
    if (!asset) return;
    const next = {
      uri: asset.uri,
      name: asset.fileName || 'incident.jpg',
      mimeType: asset.mimeType || 'image/jpeg',
      size: asset.fileSize ?? null,
    };
    const problem = validateStaffUpload(next, 'document');
    if (problem) {
      setPhoto(null);
      setFeedback(problem);
      return;
    }
    setPhoto(next);
    setFeedback('');
  }

  async function save(submit: boolean) {
    if (!title.trim() || !description.trim()) {
      setFeedback('Enter a title and description.');
      setSavedOnServer(false);
      return;
    }
    setBusy(true);
    setSavedOnServer(false);
    try {
      const created = await createIncident({
        title: title.trim(),
        description: description.trim(),
        severity,
        occurred_at: new Date().toISOString(),
        tenant_id: tenantId || null,
        submit,
      });
      if (!created?.id) throw new Error('The server did not confirm the incident.');
      let evidenceNote = 'No file was attached.';
      const categoryId = categories.data?.find((item) => item.is_active !== false)?.id;
      if (photo && categoryId) {
        const uploaded = await uploadLinkedDocument({
          categoryId,
          title: `Incident evidence ${created.reference_number || created.id}`,
          description: `Evidence for incident ${created.id}`,
          linkType: 'other',
          linkId: created.id,
          file: photo,
        });
        evidenceNote = uploaded?.id ? 'Evidence file stored as an organisation document.' : 'The file upload was not confirmed.';
      } else if (photo && !categoryId) {
        evidenceNote = 'The incident was saved. Evidence was not uploaded because no document category is available.';
      }
      setSavedOnServer(true);
      setFeedback(`Saved on the server. Status: ${created.status}. ${evidenceNote}`);
      setTitle('');
      setDescription('');
      setPhoto(null);
      await incidents.refetch();
    } catch (error) {
      setFeedback(`${hmoreErrorMessage(error, 'Could not save the incident.')} It was not saved.`);
    } finally {
      setBusy(false);
    }
  }

  const tenantOptions = [{ id: '', label: 'No tenant' }, ...(tenants.data?.items ?? []).map((item) => ({
    id: item.tenant_id,
    label: item.tenant_preferred_name || item.tenant_full_name || 'Tenant',
  }))];

  return (
    <StaffPage title="Incidents" subtitle="Create a report with the server status. There is no separate incident file API, so a photo is stored as a document when a category exists." onRefresh={incidents.refetch} refreshing={incidents.isRefetching}>
      <Input label="Title" value={title} onChangeText={setTitle} />
      <Input label="What happened" value={description} onChangeText={setDescription} multiline />
      <ChoiceRow value={severity} onChange={(value) => setSeverity(value as typeof severity)} options={SEVERITIES.map((item) => ({ id: item, label: item }))} />
      <ChoiceRow value={tenantId} onChange={setTenantId} options={tenantOptions} />
      {photo ? (
        <>
          <Image source={{ uri: photo.uri }} style={{ width: 120, height: 120, borderRadius: 12, marginBottom: 8 }} />
          <Pressable onPress={() => setPhoto(null)}><Text style={{ color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: 8 }}>Remove photo</Text></Pressable>
        </>
      ) : (
        <Button title="Add evidence photo" variant="outline" onPress={choosePhoto} fullWidth />
      )}
      <Button title="Save draft report" variant="outline" onPress={() => save(false)} loading={busy} fullWidth />
      <Button title="Submit report" onPress={() => save(true)} loading={busy} fullWidth />
      {feedback ? <Feedback text={feedback} tone={savedOnServer ? 'ok' : 'warn'} /> : null}
      {(incidents.data?.items ?? []).map((item) => (
        <RecordCard
          key={item.id}
          title={item.title}
          status={item.status}
          detail={item.reference_number}
          onPress={() => router.push(`/(app)/staff/incident/${item.id}`)}
        />
      ))}
    </StaffPage>
  );
}
