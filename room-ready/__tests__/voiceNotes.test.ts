import { readFileSync } from 'fs';
import path from 'path';

import { HmoreApiError, hmoreRequest } from '@/lib/hmore/client';
import { SPEECH_EMPTY_MESSAGE, shouldDropDuplicateFinal, speechStopPlan } from '@/hooks/useDeviceSpeechToText';
import { rewriteDailyLogNote } from '@/lib/hmore/services/staff/dailyLogRewrite';
import {
  AI_CAP_MESSAGE,
  AI_DISABLED_MESSAGE,
  AI_NETWORK_MESSAGE,
  applyFinalTranscript,
  canSubmitDailyLog,
  rewriteFailureMessage,
  textAfterAccept,
  textAfterReject,
} from '@/lib/hmore/staff/voiceNotes';

jest.mock('@/lib/hmore/client', () => {
  const actual = jest.requireActual('@/lib/hmore/client');
  return { ...actual, hmoreFetch: jest.fn() };
});

const { hmoreFetch } = jest.requireMock('@/lib/hmore/client') as { hmoreFetch: jest.Mock };

describe('speech helpers', () => {
  it('fills an empty note and appends instead of replacing an edit', () => {
    expect(applyFinalTranscript({ current: '   ', transcript: 'Fresh dictation', userEdited: true })).toEqual({
      text: 'Fresh dictation',
      action: 'fill',
    });

    const current = 'Typed by staff: maybe unwell';
    const merged = applyFinalTranscript({
      current,
      transcript: 'and they seemed fine',
      userEdited: true,
      mode: 'replace_if_unedited',
    });
    expect(merged.action).toBe('append');
    expect(merged.text.startsWith(current)).toBe(true);
    expect(merged.text).toContain('maybe unwell');
    expect(merged.text).not.toBe('and they seemed fine');
  });

  it('commits a leftover partial on stop and discards it when nothing was heard', () => {
    expect(speechStopPlan({ interim: 'partial phrase', receivedResult: true })).toEqual({
      commitText: 'partial phrase',
      message: null,
    });
    expect(speechStopPlan({ interim: '', receivedResult: false })).toEqual({
      commitText: null,
      message: SPEECH_EMPTY_MESSAGE,
    });
    expect(speechStopPlan({ interim: '', receivedResult: true })).toEqual({
      commitText: null,
      message: null,
    });
    expect(shouldDropDuplicateFinal('partial phrase', 'partial phrase')).toBe(true);
    expect(shouldDropDuplicateFinal('partial phrase', 'a different final')).toBe(false);
  });
});

describe('rewrite client', () => {
  it('calls the rewrite endpoint and does not create a daily log', async () => {
    hmoreFetch.mockReset();
    hmoreFetch.mockResolvedValue({
      rewritten_text: 'Clearer wording.',
      activity_id: '11111111-1111-4111-8111-111111111111',
      request_id: 'req-1',
      prompt_version: '1.0.0',
    });
    const result = await rewriteDailyLogNote({ text: '  wording  ', tenant_id: 'tenant-1' });
    expect(result.rewritten_text).toBe('Clearer wording.');
    expect(result.activity_id).toBe('11111111-1111-4111-8111-111111111111');
    expect(hmoreFetch).toHaveBeenCalledTimes(1);
    expect(hmoreFetch.mock.calls[0][0]).toBe('/daily-logs/rewrite');
    const source = readFileSync(path.join(__dirname, '../lib/hmore/services/staff/dailyLogRewrite.ts'), 'utf8');
    expect(source).not.toContain('createDailyLog');
    expect(source).not.toMatch(/['"]\/daily-logs['"]/);
    expect(canSubmitDailyLog(false)).toBe(false);
    expect(canSubmitDailyLog(true)).toBe(true);
  });

  it('maps disabled, capped, and network failures without claiming success', () => {
    expect(rewriteFailureMessage(new HmoreApiError(402, 'cap'))).toBe(AI_CAP_MESSAGE);
    expect(rewriteFailureMessage(new HmoreApiError(403, 'This AI feature is not enabled for your organisation.'))).toBe(
      AI_DISABLED_MESSAGE,
    );
    expect(rewriteFailureMessage(new HmoreApiError(403, 'Not assigned to this tenant'))).toMatch(/assigned/i);
    expect(rewriteFailureMessage(new HmoreApiError(0, 'Could not reach HMore.'))).toBe(AI_NETWORK_MESSAGE);
    expect(rewriteFailureMessage(new HmoreApiError(503, 'down'))).toMatch(/unavailable/i);
    for (const message of [AI_CAP_MESSAGE, AI_DISABLED_MESSAGE, AI_NETWORK_MESSAGE]) {
      expect(message.toLowerCase()).not.toContain('saved on the server');
    }
  });
});

describe('rewrite comparison', () => {
  it('accepts rewritten text into the editor without marking it saved', () => {
    const accepted = textAfterAccept('  Professional wording. Outcome still unclear.  ');
    expect(accepted).toEqual({ notes: 'Professional wording. Outcome still unclear.', saved: false });
  });

  it('reject leaves a manual edit in the editor', () => {
    const editor = 'Original plus my edit';
    expect(textAfterReject(editor)).toEqual({ notes: editor, saved: false });
  });
});

describe('api error details', () => {
  it('reads a feature-disabled message from an object detail', async () => {
    const fetchImpl = jest.fn(async () => ({
      ok: false,
      status: 403,
      json: async () => ({
        detail: { code: 'ai_feature_disabled', message: 'This AI feature is not enabled for your organisation.' },
      }),
    }));
    await expect(
      hmoreRequest(
        '/daily-logs/rewrite',
        { method: 'POST', body: { text: 'note' } },
        {
          getAccessToken: async () => 'token',
          getContext: () => ({ organisationId: 'org-1', role: 'support_worker' }),
          fetchImpl: fetchImpl as unknown as typeof fetch,
          baseUrl: 'http://api.test/api/v1',
        },
      ),
    ).rejects.toMatchObject({
      status: 403,
      detail: 'This AI feature is not enabled for your organisation.',
    });
  });
});
