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
