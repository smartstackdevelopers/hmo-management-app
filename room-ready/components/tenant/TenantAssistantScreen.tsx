import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { askAssistant, getAssistantAvailability } from '@/lib/hmore/services/assistant';
import type { AssistantMessage } from '@/lib/hmore/types';

export function TenantAssistantScreen() {
  const availability = useQuery({
    queryKey: ['hmore', 'assistant-availability'],
    queryFn: getAssistantAvailability,
  });
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);

  const ask = useMutation({
    mutationFn: (text: string) => askAssistant(text, conversationId),
    onSuccess: (result, text) => {
      setConversationId(result.conversation_id);
      setMessages((current) => [
        ...current,
        {
          id: result.question_message_id,
          conversation_id: result.conversation_id,
          role: 'user',
          body: text,
          source_refs: [],
          ai_status: null,
          escalation: null,
          cache_status: null,
          created_at: null,
        },
        result.message,
      ]);
      setQuestion('');
    },
  });

  if (availability.isLoading) return <LoadingScreen message="Checking the assistant..." />;

  const info = availability.data;
  const blocked = availability.error || (info && !info.available);

  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.lead}>
        {info?.notice || 'Answers use approved organisation content only. This assistant does not make official decisions.'}
      </Text>
      {info ? <Text style={styles.meta}>Official decisions: {info.makes_official_decisions ? 'yes' : 'no'}</Text> : null}
      {blocked ? (
        <Card>
          <Text style={styles.body}>
            {availability.error
              ? hmoreErrorMessage(availability.error, 'The assistant is not available for this login.')
              : 'The assistant is not enabled for your organisation yet.'}
          </Text>
        </Card>
      ) : (
        <Card>
          <Input
            label="Question"
            value={question}
            onChangeText={setQuestion}
            placeholder="Ask about a published notice or emergency guidance"
            multiline
          />
          {ask.error ? <Text style={styles.error}>{hmoreErrorMessage(ask.error)}</Text> : null}
          <Button
            title="Ask"
            onPress={() => {
              const text = question.trim();
              if (text.length < 3) return;
              ask.mutate(text);
            }}
            loading={ask.isPending}
            fullWidth
          />
        </Card>
      )}

      {messages.map((message) => (
        <Card key={message.id} style={styles.bubble}>
          <Text style={styles.role}>{message.role === 'user' ? 'You' : 'Assistant'}</Text>
          <Text style={styles.body}>{message.body}</Text>
          {message.source_refs?.length ? (
            <Text style={styles.meta}>
              Sources: {message.source_refs.map((ref) => ref.title || ref.source_type || 'approved content').join(', ')}
            </Text>
          ) : null}
        </Card>
      ))}
      <View />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  lead: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary, marginBottom: 6 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginBottom: theme.spacing.md },
  body: { fontFamily: FONT_MEDIUM, fontSize: 15, lineHeight: 22, color: theme.colors.text },
  error: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: 8 },
  bubble: { marginTop: theme.spacing.sm },
  role: { fontFamily: FONT_BOLD, fontSize: 12, color: theme.colors.secondaryDark, marginBottom: 4 },
});
