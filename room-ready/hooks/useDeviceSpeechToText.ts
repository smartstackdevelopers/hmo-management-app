import { useCallback, useEffect, useRef, useState } from 'react';

export const SPEECH_UNSUPPORTED_MESSAGE =
  'Speech recognition is not available on this device. Type the note instead.';

export const SPEECH_PERMISSION_MESSAGE = 'Microphone permission is required to dictate a note.';

export const SPEECH_EMPTY_MESSAGE = 'No speech was captured. Try again or type the note.';

// Final text is handed to the caller. The caller merges it so a manual edit is not overwritten.
// Partial text stays in `interim` until a final result, or until stop commits a leftover partial.
// Cancel discards the partial and does not emit text.

export interface SpeechRecognitionLike {
  start: (options: { lang: string; interimResults: boolean; continuous: boolean }) => void;
  stop: () => void;
  abort?: () => void;
  requestPermissionsAsync: () => Promise<{ granted?: boolean; status?: string }>;
  isRecognitionAvailable?: () => boolean;
  addListener?: (
    event: string,
    listener: (event: { isFinal?: boolean; results?: { transcript?: string }[]; error?: string; message?: string }) => void,
  ) => { remove: () => void };
}

export function speechAvailability(module: SpeechRecognitionLike | null | undefined): {
  supported: boolean;
  message: string;
} {
  if (!module || typeof module.start !== 'function' || typeof module.requestPermissionsAsync !== 'function') {
    return { supported: false, message: SPEECH_UNSUPPORTED_MESSAGE };
  }
  try {
    if (typeof module.isRecognitionAvailable === 'function' && module.isRecognitionAvailable() === false) {
      return { supported: false, message: SPEECH_UNSUPPORTED_MESSAGE };
    }
  } catch {
    return { supported: false, message: SPEECH_UNSUPPORTED_MESSAGE };
  }
  return { supported: true, message: '' };
}

export function loadSpeechRecognition(): SpeechRecognitionLike | null {
  try {
    const mod = require('expo-speech-recognition') as { ExpoSpeechRecognitionModule?: SpeechRecognitionLike };
    const speech = mod.ExpoSpeechRecognitionModule ?? null;
    return speechAvailability(speech).supported ? speech : null;
  } catch {
    return null;
  }
}

export async function beginDictation(
  module: SpeechRecognitionLike | null,
): Promise<{ ok: true } | { ok: false; message: string }> {
  const availability = speechAvailability(module);
  if (!availability.supported || !module) return { ok: false, message: availability.message };
  try {
    const permission = await module.requestPermissionsAsync();
    const granted = permission.granted === true || permission.status === 'granted';
    if (!granted) return { ok: false, message: SPEECH_PERMISSION_MESSAGE };
    module.start({ lang: 'en-GB', interimResults: true, continuous: true });
    return { ok: true };
  } catch {
    return { ok: false, message: SPEECH_UNSUPPORTED_MESSAGE };
  }
}

/** Stop keeps a leftover partial. Cancel never emits it. */
export function speechStopPlan(input: { interim: string; receivedResult: boolean }): {
  commitText: string | null;
  message: string | null;
} {
  const interim = input.interim.trim();
  if (interim) return { commitText: interim, message: null };
  if (!input.receivedResult) return { commitText: null, message: SPEECH_EMPTY_MESSAGE };
  return { commitText: null, message: null };
}

export function shouldDropDuplicateFinal(consumedInterim: string | null, transcript: string): boolean {
  const consumed = consumedInterim?.trim() ?? '';
  return consumed.length > 0 && consumed === transcript.trim();
}

export function useDeviceSpeechToText(onFinalText: (text: string) => void) {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [module, setModule] = useState<SpeechRecognitionLike | null>(null);
  const onFinalRef = useRef(onFinalText);
  const interimRef = useRef('');
  const receivedResult = useRef(false);
  const consumedInterim = useRef<string | null>(null);
  onFinalRef.current = onFinalText;

  useEffect(() => {
    const loaded = loadSpeechRecognition();
    setModule(loaded);
    setSupported(speechAvailability(loaded).supported);
  }, []);

  useEffect(() => {
    if (!module?.addListener) return undefined;
    const resultSub = module.addListener('result', (event) => {
      const transcript = event.results?.[0]?.transcript?.trim() ?? '';
      if (!transcript) return;
      receivedResult.current = true;
      if (event.isFinal) {
        interimRef.current = '';
        setInterim('');
        if (shouldDropDuplicateFinal(consumedInterim.current, transcript)) {
          consumedInterim.current = null;
          return;
        }
        consumedInterim.current = null;
        onFinalRef.current(transcript);
      } else {
        interimRef.current = transcript;
        setInterim(transcript);
      }
    });
    const errorSub = module.addListener('error', () => {
      setListening(false);
      setMessage(SPEECH_UNSUPPORTED_MESSAGE);
    });
    const endSub = module.addListener('end', () => setListening(false));
    return () => {
      resultSub.remove();
      errorSub.remove();
      endSub.remove();
    };
  }, [module]);

  const start = useCallback(async () => {
    setMessage(null);
    receivedResult.current = false;
    consumedInterim.current = null;
    interimRef.current = '';
    setInterim('');
    const result = await beginDictation(module);
    if (!result.ok) {
      setListening(false);
      setMessage(result.message);
      return;
    }
    setListening(true);
  }, [module]);

  const stop = useCallback(() => {
    try {
      module?.stop();
    } catch {
      setMessage(SPEECH_UNSUPPORTED_MESSAGE);
    }
    const plan = speechStopPlan({ interim: interimRef.current, receivedResult: receivedResult.current });
    interimRef.current = '';
    setInterim('');
    setListening(false);
    if (plan.commitText) {
      consumedInterim.current = plan.commitText;
      onFinalRef.current(plan.commitText);
      return;
    }
    if (plan.message) setMessage(plan.message);
  }, [module]);

  const cancel = useCallback(() => {
    try {
      if (typeof module?.abort === 'function') module.abort();
      else module?.stop();
    } catch {
      setMessage(SPEECH_UNSUPPORTED_MESSAGE);
    }
    interimRef.current = '';
    consumedInterim.current = null;
    receivedResult.current = false;
    setInterim('');
    setListening(false);
  }, [module]);

  return {
    supported: supported === true,
    checking: supported === null,
    listening,
    interim,
    message: supported === false ? SPEECH_UNSUPPORTED_MESSAGE : message,
    start,
    stop,
    cancel,
  };
}
