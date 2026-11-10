import { HmoreApiError, hmoreFetch } from '@/lib/hmore/client';
import { activityIdFromAsk, submitActivityFeedback } from '@/lib/hmore/services/assistant';

export interface DailyLogRewriteResult {
  rewritten_text: string;
  activity_id: string | null;
  request_id: string | null;
  prompt_version: string | null;
}

/**
 * Ask for a professional rewrite of draft text.
 * This function only calls POST /daily-logs/rewrite. It does not create a daily log.
 */
export async function rewriteDailyLogNote(input: {
  text: string;
  tenant_id?: string | null;
}): Promise<DailyLogRewriteResult> {
  const text = input.text.trim();
  if (!text) {
    throw new HmoreApiError(422, 'Enter a note before asking for a rewrite.');
  }
  const body: { text: string; tenant_id?: string } = { text };
  if (input.tenant_id) body.tenant_id = input.tenant_id;
  const raw = await hmoreFetch<{
    rewritten_text?: string;
    activity_id?: string | null;
    request_id?: string | null;
    prompt_version?: string | null;
  }>('/daily-logs/rewrite', { method: 'POST', body });
  const rewritten = (raw?.rewritten_text || '').trim();
  if (!rewritten) {
    throw new HmoreApiError(502, 'AI rewrite did not return text. The note was not saved.');
  }
  return {
    rewritten_text: rewritten,
    activity_id: activityIdFromAsk(raw),
    request_id: typeof raw.request_id === 'string' && raw.request_id.trim() ? raw.request_id : null,
    prompt_version: typeof raw.prompt_version === 'string' && raw.prompt_version.trim() ? raw.prompt_version : null,
  };
}

export function reportIncorrectRewrite(activityId: string | null): Promise<{ id?: string }> {
  if (!activityId) {
    throw new HmoreApiError(400, 'There is no AI activity to report.');
  }
  return submitActivityFeedback(activityId, {
    category: 'incorrect_information',
    explanation: 'The daily note professional rewrite was incorrect.',
  });
}
