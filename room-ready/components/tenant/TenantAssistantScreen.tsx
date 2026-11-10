import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { activityIdFromAsk, askAssistant, getAssistantAvailability, submitActivityFeedback } from '@/lib/hmore/services/assistant';
import type { AssistantMessage } from '@/lib/hmore/types';

type ShownMessage = AssistantMessage & { activityId: string | null };

export function TenantAssistantScreen() {
  const { t, fontScale, prefs } = useI18n();
  const availability = useQuery({
    queryKey: ['hmore', 'assistant-availability'],
    queryFn: getAssistantAvailability,
  });
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ShownMessage[]>([]);
  const [feedbackSent, setFeedbackSent] = useState<Record<string, boolean>>({});
  const [feedbackError, setFeedbackError] = useState<Record<string, string>>({});

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
          activityId: null,
        },
        { ...result.message, activityId: activityIdFromAsk(result) },
      ]);
      setQuestion('');
    },
  });

  const feedback = useMutation({
    mutationFn: (activityId: string) =>
      submitActivityFeedback(activityId, { category: 'incorrect_information' }),
    onSuccess: (_result, activityId) => {
      setFeedbackSent((current) => ({ ...current, [activityId]: true }));
      setFeedbackError((current) => ({ ...current, [activityId]: '' }));
    },
    onError: (error, activityId) => {
      setFeedbackSent((current) => ({ ...current, [activityId]: false }));
      setFeedbackError((current) => ({ ...current, [activityId]: hmoreErrorMessage(error, t('assistant.feedbackError')) }));
    },
  });

  if (availability.isLoading) return <LoadingScreen message={t('assistant.checking')} />;

  const info = availability.data;
  const blocked = availability.error || (info && !info.available);
  const contrast = prefs.highContrast;

  return (
    <ScrollView
      style={[styles.page, contrast && styles.contrast]}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={[styles.lead, { fontSize: 14 * fontScale }]}>
        {info?.notice || t('assistant.leadFallback')}
      </Text>
      {info ? (
        <Text style={styles.meta}>
          {t('assistant.decisions')}: {info.makes_official_decisions ? 'yes' : t('assistant.decisionsNo')}
        </Text>
      ) : null}
      {blocked ? (
        <Card>
          <Text style={styles.body}>
            {availability.error
              ? hmoreErrorMessage(availability.error, t('assistant.unavailableError'))
              : t('assistant.unavailable')}
          </Text>
        </Card>
      ) : (
        <Card>
          <Input
            label={t('assistant.question')}
            value={question}
            onChangeText={setQuestion}
            placeholder={t('assistant.placeholder')}
            multiline
            accessibilityLabel={t('assistant.question')}
          />
          {ask.error ? <Text style={styles.error}>{hmoreErrorMessage(ask.error)}</Text> : null}
          <Button
            title={t('assistant.ask')}
            accessibilityLabel={t('assistant.ask')}
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
          <Text style={styles.role}>{message.role === 'user' ? t('assistant.you') : t('assistant.bot')}</Text>
          <Text style={[styles.body, { fontSize: 15 * fontScale }]}>{message.body}</Text>
          {message.source_refs?.length ? (
            <Text style={styles.meta}>
              {t('assistant.sources')}:{' '}
              {message.source_refs.map((ref) => ref.title || ref.source_type || t('assistant.sources')).join(', ')}
            </Text>
          ) : null}
          {message.activityId ? (
            <View style={styles.feedback}>
              {feedbackSent[message.activityId] ? (
                <Text style={styles.saved}>{t('assistant.feedbackSent')}</Text>
              ) : (
                <Button
                  title={t('assistant.feedback')}
                  accessibilityLabel={t('assistant.feedback')}
                  variant="outline"
                  onPress={() => feedback.mutate(message.activityId!)}
                  loading={feedback.isPending && feedback.variables === message.activityId}
                />
              )}
              {feedbackError[message.activityId] ? <Text style={styles.error}>{feedbackError[message.activityId]}</Text> : null}
            </View>
          ) : null}
        </Card>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
  contrast: { backgroundColor: '#FFFFFF' },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  lead: { fontFamily: FONT_MEDIUM, lineHeight: 20, color: theme.colors.textSecondary, marginBottom: 6 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginBottom: theme.spacing.md },
  body: { fontFamily: FONT_MEDIUM, lineHeight: 22, color: theme.colors.text },
  error: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginTop: 8, marginBottom: 8 },
  saved: { color: theme.colors.success, fontFamily: FONT_MEDIUM, marginTop: 8 },
  bubble: { marginTop: theme.spacing.sm },
  role: { fontFamily: FONT_BOLD, fontSize: 12, color: theme.colors.secondaryDark, marginBottom: 4 },
  feedback: { marginTop: theme.spacing.sm },
});
