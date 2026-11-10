import { HmoreApiError, hmoreErrorMessage } from '@/lib/hmore/client';

/**
 * Speech merge (F4.4).
 *
 * Partial transcripts stay outside the note until they are final.
 * A final transcript fills the note when the field is empty, including after Clear
 * or when the staff member deleted the text and is dictating a fresh note.
 * When the field already has text, the final transcript is appended after a newline.
 * That includes text the staff member edited. A new final result does not replace it.
 * The default mode is append. `replace_if_unedited` still appends once the staff member has edited.
 */

export type SpeechMergeMode = 'append' | 'replace_if_unedited';

export const AI_DISABLED_MESSAGE =
  'AI professional rewrite is not enabled for your organisation. You can still save the original note.';

export const AI_CAP_MESSAGE =
  'AI usage limit has been reached. You can still save the original note.';

export const AI_UNAVAILABLE_MESSAGE =
  'AI rewrite is unavailable right now. You can still save the original note.';

export const AI_NETWORK_MESSAGE =
  'Could not reach HMore. The note was not rewritten. You can still save a draft on this device.';

export const EMPTY_REWRITE_MESSAGE = 'Enter a note before asking for a rewrite.';

export const SAVE_CONFIRM_MESSAGE =
  'This sends the text in the note field to the server. Dictation and rewrite do not save it until you confirm.';

export function applyFinalTranscript(input: {
  current: string;
  transcript: string;
  userEdited: boolean;
  mode?: SpeechMergeMode;
}): { text: string; action: 'ignore' | 'fill' | 'append' | 'replace' } {
  const transcript = input.transcript.trim();
  if (!transcript) return { text: input.current, action: 'ignore' };
  if (!input.current.trim()) return { text: transcript, action: 'fill' };
  const mode = input.mode ?? 'append';
  if (input.userEdited || mode === 'append') {
    const base = input.current.replace(/\s+$/, '');
    return { text: `${base}\n${transcript}`, action: 'append' };
  }
  return { text: transcript, action: 'replace' };
}

export function textAfterAccept(editedRewritten: string): { notes: string; saved: false } {
  const notes = editedRewritten.trim();
  if (!notes) {
    throw new Error('Rewritten text is empty.');
  }
  return { notes, saved: false };
}

export function textAfterReject(editorNotes: string): { notes: string; saved: false } {
  return { notes: editorNotes, saved: false };
}

/** Server save runs only after the staff member confirms. Rewrite never sets this to true by itself. */
export function canSubmitDailyLog(confirmed: boolean): boolean {
  return confirmed === true;
}

export function rewriteFailureMessage(error: unknown): string {
  if (error instanceof HmoreApiError) {
    if (error.status === 402) return AI_CAP_MESSAGE;
    if (error.status === 0) return AI_NETWORK_MESSAGE;
    if (error.status === 403 && /not enabled|ai_feature_disabled/i.test(error.detail)) return AI_DISABLED_MESSAGE;
    if (error.status === 403) return error.detail || 'You cannot rewrite a note for this tenant.';
    if (error.status === 503 || error.status === 504) return AI_UNAVAILABLE_MESSAGE;
    if (/could not reach/i.test(error.detail)) return AI_NETWORK_MESSAGE;
    return hmoreErrorMessage(error, AI_UNAVAILABLE_MESSAGE);
  }
  if (error instanceof Error && /network|failed to fetch|could not reach/i.test(error.message)) {
    return AI_NETWORK_MESSAGE;
  }
  return hmoreErrorMessage(error, AI_UNAVAILABLE_MESSAGE);
}
