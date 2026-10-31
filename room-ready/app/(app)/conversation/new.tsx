import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useCreateConversation, useContacts, useProperties } from '@/hooks/useApi';

export default function NewConversationScreen() {
  const { propertyId: initialPropertyId } = useLocalSearchParams<{ propertyId?: string }>();
  const { user } = useAuth();
  const { data: contactsData, isLoading: loadingContacts, error: contactsError, refetch: refetchContacts } = useContacts();
  const { data: propertiesData } = useProperties();
  const create = useCreateConversation();

  const [participantId, setParticipantId] = useState('');
  const [propertyId, setPropertyId] = useState(initialPropertyId ?? '');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');

  if (loadingContacts) return <LoadingScreen />;
  if (contactsError) {
    return <ErrorState message="Could not load contacts" onRetry={refetchContacts} />;
  }

  const contacts = contactsData?.contacts ?? [];
  const properties = propertiesData?.properties ?? [];

  async function handleSubmit() {
    if (!participantId || !message.trim()) {
      Alert.alert('Missing fields', 'Select a recipient and enter a message');
      return;
    }
    try {
      const { conversation } = await create.mutateAsync({
        participantIds: [participantId],
        propertyId: propertyId || undefined,
        subject: subject || undefined,
        initialMessage: message,
      });
      router.replace(`/(app)/conversation/${conversation.id}`);
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not start conversation');
    }
  }

  if (contacts.length === 0) {
    const isTenant = user?.role === 'tenant';
    return (
      <EmptyState
        title="No contacts yet"
        message={
          isTenant
            ? 'Contacts appear once you have an active tenancy or ongoing application.'
            : 'Add a property and tenants or contractors will appear here.'
        }
        icon="people-outline"
        actionLabel={isTenant ? 'Find a Room' : 'Add Property'}
        onAction={() =>
          isTenant ? router.push('/(app)/(tabs)/find' as never) : router.push('/(app)/property/new')
        }
      />
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.label}>Recipient *</Text>
      {contacts.map((c) => (
        <Pressable
          key={c.id}
          onPress={() => setParticipantId(c.id)}
          style={[styles.option, participantId === c.id && styles.optionSelected]}
        >
          <Text style={styles.optionText}>{c.firstName} {c.lastName}</Text>
          <Text style={styles.optionMeta}>{c.role.replace(/_/g, ' ')} · {c.email}</Text>
        </Pressable>
      ))}

      {properties.length > 0 && (
        <>
          <Text style={styles.label}>Property (optional)</Text>
          {properties.map((p) => (
            <Pressable
              key={p.id}
              onPress={() => setPropertyId(p.id)}
              style={[styles.option, propertyId === p.id && styles.optionSelected]}
            >
              <Text style={styles.optionText}>{p.name}</Text>
            </Pressable>
          ))}
        </>
      )}

      <Input label="Subject" value={subject} onChangeText={setSubject} placeholder="e.g. Rent payment query" />
      <Input label="Message *" value={message} onChangeText={setMessage} multiline numberOfLines={4} placeholder="Write your message..." />
      <Button title="Start Conversation" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  label: { ...theme.typography.label, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.md },
  option: { padding: 12, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border, marginBottom: 8 },
  optionSelected: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.infoLight },
  optionText: { color: theme.colors.text, fontWeight: '600' },
  optionMeta: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2 },
});
