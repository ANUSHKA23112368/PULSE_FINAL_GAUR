import React, { useEffect, useRef } from 'react';
import { Pause, Play, Square, Volume2 } from 'lucide-react';
import { useNarration } from '../hooks/useNarration';

/**
 * Nurse-cadence handover readout. Each sentence is a separate utterance, so
 * the active sentence stays highlighted and tapping any sentence seeks to it.
 */
export function AudioHandoverPlayer({
  text,
  title = 'Audio handover briefing',
  subtitle = 'Synchronized read-along · nurse cadence',
  compact = false,
}) {
  const { supported, sentences, status, activeIndex, rate, rates, toggle, cancel, setRate, seek } =
    useNarration(text);
  const listRef = useRef(null);

  useEffect(() => {
    if (activeIndex < 0) return;
    const active = listRef.current?.querySelector('[aria-current="true"]');
    if (active && typeof active.scrollIntoView === 'function') {
      active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [activeIndex]);

  if (!supported) {
    return (
      <div className={`audio-handover-player ${compact ? 'is-compact' : ''}`.trim()}>
        <p className="audio-unsupported">
          Audio read-along is unavailable in this browser. The transcript remains available below.
        </p>
      </div>
    );
  }

  const playing = status === 'playing';
  const paused = status === 'paused';
  const hasText = sentences.length > 0;

  return (
    <section className={`audio-handover-player ${compact ? 'is-compact' : ''}`.trim()} aria-label="Audio handover player">
      <div className="audio-player-head">
        <div className="audio-player-identity">
          <span className={`audio-player-icon ${playing ? 'is-playing' : ''}`}>
            <Volume2 size={17} />
          </span>
          <div>
            <h4>{title}</h4>
            <p>{hasText ? subtitle : 'Load or type a narrative to enable playback.'}</p>
          </div>
        </div>

        <div className="audio-player-controls">
          <button
            type="button"
            className="audio-control audio-control-primary"
            onClick={toggle}
            disabled={!hasText}
            aria-label={playing ? 'Pause handover narration' : paused ? 'Resume handover narration' : 'Play handover narration'}
          >
            {playing ? <Pause size={16} /> : <Play size={16} fill="currentColor" />}
          </button>
          <button
            type="button"
            className="audio-control"
            onClick={cancel}
            disabled={!playing && !paused}
            aria-label="Stop handover narration"
          >
            <Square size={13} fill="currentColor" />
          </button>
          <label className="audio-speed">
            <span>Speed</span>
            <select
              value={rate}
              onChange={(event) => setRate(event.target.value)}
              aria-label="Playback speed"
              disabled={!hasText}
            >
              {rates.map((option) => (
                <option key={option} value={option}>
                  {option.toFixed(2).replace(/0$/, '')}x
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {hasText && (
        <div className="narration-transcript" ref={listRef} aria-live="polite">
          {sentences.map((sentence, index) => (
            <button
              key={`${index}-${sentence.slice(0, 24)}`}
              type="button"
              className={`narration-sentence ${index === activeIndex ? 'is-active' : ''} ${index < activeIndex ? 'is-spoken' : ''}`.trim()}
              onClick={() => seek(index)}
              aria-current={index === activeIndex ? 'true' : 'false'}
              title={`Read from sentence ${index + 1}`}
            >
              <span className="narration-sentence-number">{String(index + 1).padStart(2, '0')}</span>
              <span>{sentence}</span>
            </button>
          ))}
        </div>
      )}

      <div className="audio-player-foot">
        <span className={`audio-status ${playing ? 'is-playing' : paused ? 'is-paused' : ''}`}>
          <span className="audio-status-dot" />
          {playing ? 'Speaking' : paused ? 'Paused' : 'Ready'}
        </span>
        <span className="audio-progress">
          {activeIndex >= 0 ? `Sentence ${activeIndex + 1} of ${sentences.length}` : `${sentences.length} sentences`}
        </span>
        <span className="audio-cadence">Pitch 1.0 · en-GB</span>
      </div>
    </section>
  );
}

export default AudioHandoverPlayer;
