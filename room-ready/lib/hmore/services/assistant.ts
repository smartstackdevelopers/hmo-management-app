import { hmoreFetch } from '@/lib/hmore/client';
import type {
  AssistantAskResult,
  AssistantAvailability,
  AssistantConversation,
  AssistantConversationSummary,
} from '@/lib/hmore/types';

export function getAssistantAvailability(): Promise<AssistantAvailability> {
  return hmoreFetch<AssistantAvailability>('/tenant-assistant/availability', { method: 'GET' });
}

export function askAssistant(question: string, conversationId?: string | null): Promise<AssistantAskResult> {
  return hmoreFetch<AssistantAskResult>('/tenant-assistant/ask', {
    method: 'POST',
    body: {
      question,
      conversation_id: conversationId ?? null,
    },
  });
}

export function listAssistantConversations(): Promise<{ items: AssistantConversationSummary[]; notice: string }> {
  return hmoreFetch('/tenant-assistant/conversations', { method: 'GET' });
}

export function getAssistantConversation(id: string): Promise<AssistantConversation> {
  return hmoreFetch<AssistantConversation>(`/tenant-assistant/conversations/${id}`, { method: 'GET' });
}

/** Real activity id from an ask response. Missing or blank ids cannot be sent as feedback. */
export function activityIdFromAsk(result: { activity_id?: string | null } | null | undefined): string | null {
  const id = result?.activity_id;
  if (typeof id !== 'string') return null;
  const trimmed = id.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function submitActivityFeedback(
  activityId: string,
  input: { category: string; explanation?: string | null },
): Promise<{ id?: string }> {
  return hmoreFetch(`/ai-activity/${activityId}/feedback`, {
    method: 'POST',
    body: {
      category: input.category,
      explanation: input.explanation ?? null,
    },
  });
}
