import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export function splitIntoSentences(text) {
  if (!text || !text.trim()) return [];
  return (text.match(/[^.!?\n]+[.!?]+|[^.!?\n]+$/g) || [])
    .map((sentence) => sentence.trim())
    .filter(Boolean);
}

const VALID_RATES = [0.9, 1, 1.25, 1.5];

/**
 * Sentence-level Web Speech narration. One utterance per sentence keeps
 * highlighting accurate and avoids the long-utterance pause bug in Chromium.
 */
export function useNarration(text, { defaultRate = 1, lang = 'en-GB' } = {}) {
  const sentences = useMemo(() => splitIntoSentences(text), [text]);
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const [status, setStatus] = useState('idle');
  const [activeIndex, setActiveIndex] = useState(-1);
  const [rate, setRateState] = useState(VALID_RATES.includes(defaultRate) ? defaultRate : 1);

  const runIdRef = useRef(0);
  const indexRef = useRef(0);
  const rateRef = useRef(rate);

  const cancel = useCallback(() => {
    runIdRef.current += 1;
    indexRef.current = 0;
    if (supported) window.speechSynthesis.cancel();
    setStatus('idle');
    setActiveIndex(-1);
  }, [supported]);

  const speakAt = useCallback(
    (startIndex = 0) => {
      if (!supported || sentences.length === 0) return;
      window.speechSynthesis.cancel();
      const runId = runIdRef.current + 1;
      runIdRef.current = runId;
      indexRef.current = Math.max(0, Math.min(startIndex, sentences.length - 1));
      setStatus('playing');
      setActiveIndex(indexRef.current);

      const speakNext = () => {
        if (runId !== runIdRef.current) return;
        const index = indexRef.current;
        if (index >= sentences.length) {
          setStatus('idle');
          setActiveIndex(-1);
          return;
        }

        const utterance = new SpeechSynthesisUtterance(sentences[index]);
        utterance.lang = lang;
        utterance.rate = rateRef.current;
        utterance.pitch = 1.0;
        utterance.volume = 1;
        utterance.onend = () => {
          if (runId !== runIdRef.current) return;
          const next = index + 1;
          indexRef.current = next;
          if (next < sentences.length) {
            setActiveIndex(next);
            speakNext();
          } else {
            setStatus('idle');
            setActiveIndex(-1);
            indexRef.current = 0;
          }
        };
        utterance.onerror = (event) => {
          if (runId !== runIdRef.current) return;
          if (event.error === 'interrupted' || event.error === 'canceled') return;
          setStatus('idle');
          setActiveIndex(-1);
        };
        window.speechSynthesis.speak(utterance);
      };

      window.setTimeout(speakNext, 60);
    },
    [lang, sentences, supported]
  );

  const play = useCallback(() => {
    if (!supported || sentences.length === 0) return;
    if (status === 'paused') {
      window.speechSynthesis.resume();
      setStatus('playing');
      return;
    }
    speakAt(status === 'idle' ? 0 : Math.max(0, indexRef.current));
  }, [sentences.length, speakAt, status, supported]);

  const pause = useCallback(() => {
    if (!supported || status !== 'playing') return;
    window.speechSynthesis.pause();
    setStatus('paused');
  }, [status, supported]);

  const toggle = useCallback(() => {
    if (status === 'playing') pause();
    else play();
  }, [pause, play, status]);

  const setRate = useCallback(
    (nextRate) => {
      const parsed = Number(nextRate);
      if (!VALID_RATES.includes(parsed)) return;
      rateRef.current = parsed;
      setRateState(parsed);
      if (status === 'playing' || status === 'paused') {
        speakAt(indexRef.current);
      }
    },
    [speakAt, status]
  );

  const seek = useCallback(
    (index) => {
      if (!supported) return;
      speakAt(index);
    },
    [speakAt, supported]
  );

  useEffect(() => {
    cancel();
    return undefined;
  }, [cancel, text]);

  useEffect(() => {
    return () => {
      runIdRef.current += 1;
      if (supported) window.speechSynthesis.cancel();
    };
  }, [supported]);

  return {
    supported,
    sentences,
    status,
    activeIndex,
    rate,
    rates: VALID_RATES,
    play,
    pause,
    toggle,
    setRate,
    seek,
    cancel,
  };
}

export default useNarration;
