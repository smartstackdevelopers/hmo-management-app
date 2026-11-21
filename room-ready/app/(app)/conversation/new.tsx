import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useContacts, useCreateConversation, useProperties } from '@/hooks/useApi';

export default function NewConversationScreen() {
  useHideTabHeader();
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
  if (contactsError) return <ErrorState message="Could not load contacts" onRetry={refetchContacts} />;

  const contacts = contactsData?.contacts ?? [];
  const properties = propertiesData?.properties ?? [];

  async function handleSubmit() {
    if (!participantId || !message.trim()) {
      Alert.alert('Missing fields', 'Choose a recipient and write a message');
      return;
    }
    try {
      const { conversation } = await create.mutateAsync({
        participantIds: [participantId],
        propertyId: propertyId || undefined,
        subject: subject.trim() || undefined,
        initialMessage: message.trim(),
      });
      router.replace(`/(app)/conversation/${conversation.id}`);
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not start conversation');
    }
  }

  if (contacts.length === 0) {
    const isTenant = user?.role === 'tenant';
    return (
      <View style={styles.container}>
        <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
          <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
          <Text style={styles.backText}>Back</Text>
        </Pressable>
        <EmptyState
          title="No contacts yet"
          message={isTenant ? 'Contacts appear once you have an active tenancy or ongoing application.' : 'Add a property and people you can message will appear here.'}
          icon="people-outline"
          actionLabel={isTenant ? 'Find a room' : 'Add property'}
          onAction={() => (isTenant ? router.push('/(app)/(tabs)/find' as never) : router.push('/(app)/property/new'))}
        />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <Text style={styles.title}>New message</Text>

      <Text style={styles.label}>Recipient</Text>
      {contacts.map((contact) => {
        const selected = participantId === contact.id;
        return (
          <Pressable
            key={contact.id}
            onPress={() => setParticipantId(contact.id)}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            style={[styles.option, selected && styles.optionSelected]}
          >
            <Text style={styles.optionText}>{contact.firstName} {contact.lastName}</Text>
            <Text style={styles.optionMeta}>{contact.role.replace(/_/g, ' ')} · {contact.email}</Text>
          </Pressable>
        );
      })}

      {properties.length > 0 ? (
        <>
          <Text style={styles.label}>Property</Text>
          {properties.map((property) => {
            const selected = propertyId === property.id;
            return (
              <Pressable
                key={property.id}
                onPress={() => setPropertyId(property.id === propertyId ? '' : property.id)}
                accessibilityRole="button"
                accessibilityState={{ selected }}
                style={[styles.option, selected && styles.optionSelected]}
              >
                <Text style={styles.optionText}>{property.addressLine1 || property.name}</Text>
              </Pressable>
            );
          })}
        </>
      ) : null}

      <Input label="Subject" value={subject} onChangeText={setSubject} placeholder="Optional" />
      <Input label="Message" value={message} onChangeText={setMessage} multiline numberOfLines={4} placeholder="Write a message..." />
      <Button title="Send" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  title: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.sm },
  option: { padding: 12, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border, marginBottom: 8 },
  optionSelected: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.accentLight },
  optionText: { color: theme.colors.text, fontFamily: FONT_SEMIBOLD },
  optionMeta: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2, fontFamily: FONT_MEDIUM },
});
