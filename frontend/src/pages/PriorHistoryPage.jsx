import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Clock,
  FileText,
  Layers,
  ListTodo,
  Pill,
  Play,
  RotateCcw,
  ShieldCheck,
  Trash2,
  Upload,
} from 'lucide-react';
import { analyzeHandover, fetchPatients } from '../services/api';

/**
 * Patient prior history intake.
 *
 * The prototype has no EHR integration, so an existing history document is
 * uploaded as plain text, run through the same extraction pipeline used for
 * handovers, and the resulting entities/events are shown as reference context.
 * Nothing here diagnoses: the analysis only re-structures what the document
 * already states, and every item is flagged for clinician review.
 */

const ACCEPTED = '.txt,.text,.md,.markdown,.log';
const MAX_CHARS = 40000;

const card = {
  background: 'rgba(17, 24, 39, 0.65)',
  border: '1px solid rgba(148, 163, 184, 0.16)',
  borderRadius: '14px',
  padding: '1.35rem',
};
const muted = { color: '#94a3b8' };
const accent = '#38bdf8';
const label = {
  fontSize: '0.72rem',
  fontWeight: 800,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: accent,
};

function storageKey(patientKey) {
  return `pulse_prior_history_${patientKey || 'unassigned'}`;
}

function loadSaved(patientKey) {
  try {
    const raw = localStorage.getItem(storageKey(patientKey));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persist(patientKey, items) {
  try {
    localStorage.setItem(storageKey(patientKey), JSON.stringify(items.slice(0, 10)));
  } catch {
    /* storage full or blocked: the analysis still renders for this session */
  }
}

function entityText(entity) {
  if (!entity || typeof entity !== 'object') return '';
  return entity.text || entity.value || entity.field || entity.condition || '';
}

function entityFlags(entity) {
  const flags = [];
  if (entity?.is_negated) flags.push('Negated');
  if (entity?.is_historical) flags.push('Historical');
  if (entity?.is_uncertain) flags.push('Uncertain');
  if (entity?.is_planned) flags.push('Planned');
  return flags;
}

function prettyCategory(key) {
  return String(key || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function PriorHistoryPage({ selectedPatient }) {
  const [patients, setPatients] = useState([]);
  const [patientKey, setPatientKey] = useState(selectedPatient?.display_id || selectedPatient?.id || '');
  const [filename, setFilename] = useState('');
  const [text, setText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [step, setStep] = useState('');
  const [result, setResult] = useState(null);
  const [engine, setEngine] = useState('hybrid');
  const [engineUsed, setEngineUsed] = useState('');
  const [latencyMs, setLatencyMs] = useState(null);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(() => loadSaved(patientKey));

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchPatients();
        if (!cancelled) setPatients(data?.patients || []);
      } catch {
        if (!cancelled) setPatients([]);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selectedPatient) {
      setPatientKey(selectedPatient.display_id || selectedPatient.id || '');
    }
  }, [selectedPatient]);

  useEffect(() => {
    setSaved(loadSaved(patientKey));
  }, [patientKey]);

  const groups = useMemo(() => {
    const entities = result?.entities;
    if (!entities || typeof entities !== 'object') return [];
    return Object.entries(entities)
      .filter(([, value]) => Array.isArray(value) && value.length > 0)
      .map(([key, value]) => ({
        key,
        title: prettyCategory(key),
        items: value.filter((item) => entityText(item)),
      }))
      .filter((group) => group.items.length > 0);
  }, [result]);

  const counts = useMemo(() => {
    const total = groups.reduce((sum, group) => sum + group.items.length, 0);
    const historical = groups.reduce(
      (sum, group) => sum + group.items.filter((item) => item?.is_historical).length,
      0,
    );
    const negated = groups.reduce(
      (sum, group) => sum + group.items.filter((item) => item?.is_negated).length,
      0,
    );
    return {
      total,
      historical,
      negated,
      events: Array.isArray(result?.events) ? result.events.length : 0,
      tasks: Array.isArray(result?.pending_tasks) ? result.pending_tasks.length : 0,
    };
  }, [groups, result]);

  function handleFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result || '');
      setFilename(file.name);
      setText(raw.slice(0, MAX_CHARS));
      setResult(null);
    };
    reader.onerror = () => setError('That file could not be read as plain text.');
    reader.readAsText(file);
  }

  async function handleAnalyze() {
    const trimmed = text.trim();
    if (!trimmed) {
      setError('Upload a history document or paste its text before analysing.');
      return;
    }
    setError(null);
    setAnalyzing(true);
    setStep('preprocess');
    try {
      const data = await analyzeHandover({
        rawText: trimmed,
        engine,
        onStep: (next) => setStep(next),
      });
      setResult(data || null);
      setEngineUsed(data?.model_metadata?.pipeline || data?.engine_used || 'PULSE extraction pipeline');
      setLatencyMs(data?.model_metadata?.total_inference_ms ?? null);
      if (data) {
        const entry = {
          id: `${Date.now()}`,
          filename: filename || 'Pasted history',
          savedAt: new Date().toISOString(),
          chars: trimmed.length,
          entityCount: Object.values(data.entities || {}).reduce(
            (sum, value) => sum + (Array.isArray(value) ? value.length : 0),
            0,
          ),
          text: trimmed,
          analysis: data,
        };
        const next = [entry, ...loadSaved(patientKey)].slice(0, 10);
        persist(patientKey, next);
        setSaved(next);
      }
    } catch (err) {
      setError(err?.message || 'The history document could not be analysed.');
    } finally {
      setAnalyzing(false);
      setStep('');
    }
  }

  function handleReset() {
    setFilename('');
    setText('');
    setResult(null);
    setEngineUsed('');
    setLatencyMs(null);
    setError(null);
  }

  function handleLoad(entry) {
    setFilename(entry.filename);
    setText(entry.text || '');
    setResult(entry.analysis || null);
    setEngineUsed(entry.analysis?.model_metadata?.pipeline || 'Saved analysis');
    setError(null);
  }

  function handleDelete(id) {
    const next = saved.filter((entry) => entry.id !== id);
    persist(patientKey, next);
    setSaved(next);
  }

  return (
    <div className="page-stack" style={{ display: 'grid', gap: '1.25rem' }}>
      <section style={card}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ maxWidth: '46rem' }}>
            <div style={label}>Patient context</div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff', margin: '0.4rem 0 0.5rem' }}>
              Prior history upload and analysis
            </h2>
            <p style={{ fontSize: '0.88rem', lineHeight: 1.7, margin: 0, ...muted }}>
              Attach an existing history document (plain text or Markdown) for the selected patient. PULSE runs the
              same extraction pipeline used for shift handovers and returns the conditions, medications,
              investigations, events and outstanding tasks it can ground in the document, with negation and
              historical status preserved.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.74rem', color: '#7dd3fc', border: '1px solid rgba(56, 189, 248, 0.35)', background: 'rgba(6, 182, 212, 0.1)', borderRadius: '999px', padding: '0.35rem 0.7rem', fontWeight: 700 }}>
            <ShieldCheck size={13} /> Reference only · clinician review required
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '0.85rem', marginTop: '1.25rem' }}>
          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.35rem', ...muted }}>Patient</div>
            <select
              className="pulse-select"
              value={patientKey}
              onChange={(event) => setPatientKey(event.target.value)}
              style={{ width: '100%', padding: '0.5rem 0.7rem', fontSize: '0.82rem' }}
            >
              <option value="">Unassigned</option>
              {patients.map((patient) => {
                const key = patient.display_id || patient.id;
                return (
                  <option key={key} value={key}>
                    {patient.display_id || patient.id} · {patient.name || patient.full_name || 'Unnamed patient'}
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.35rem', ...muted }}>History document</div>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                cursor: 'pointer',
                borderRadius: '10px',
                border: '1px dashed rgba(56, 189, 248, 0.45)',
                background: 'rgba(56, 189, 248, 0.07)',
                color: '#7dd3fc',
                padding: '0.55rem 0.75rem',
                fontSize: '0.82rem',
                fontWeight: 700,
              }}
            >
              <Upload size={15} />
              {filename || 'Choose .txt / .md file'}
              <input type="file" accept={ACCEPTED} onChange={handleFile} style={{ display: 'none' }} />
            </label>
          </div>
        </div>

        <div style={{ marginTop: '0.9rem' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.35rem', ...muted }}>
            Extraction engine
          </div>
          <select
            className="pulse-select"
            value={engine}
            onChange={(event) => setEngine(event.target.value)}
            style={{ width: '100%', maxWidth: '27rem', padding: '0.5rem 0.7rem', fontSize: '0.82rem' }}
          >
            <option value="hybrid">Hybrid Bio_ClinicalBERT + ConText (ML, default)</option>
            <option value="hybrid_crf">Hybrid CRF + Gazetteer (ML, 60.51 strict F1)</option>
            <option value="clinical_bert">Bio_ClinicalBERT (pure neural)</option>
            <option value="rule">Rule baseline (no ML)</option>
          </select>
        </div>

        <div style={{ marginTop: '0.9rem' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '0.5rem' }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, ...muted }}>Document text</div>
            <div style={{ fontSize: '0.72rem', ...muted }}>
              {text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
            </div>
          </div>
          <textarea
            value={text}
            onChange={(event) => {
              setText(event.target.value.slice(0, MAX_CHARS));
              setResult(null);
            }}
            placeholder="Paste the patient's prior history here, or upload a text file above."
            style={{
              width: '100%',
              minHeight: '9rem',
              marginTop: '0.4rem',
              padding: '0.8rem 0.9rem',
              borderRadius: '12px',
              border: '1px solid rgba(148, 163, 184, 0.25)',
              background: 'rgba(10, 15, 29, 0.75)',
              color: '#e2e8f0',
              fontSize: '0.85rem',
              lineHeight: 1.65,
              fontFamily: "'JetBrains Mono', monospace",
              resize: 'vertical',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.6rem', marginTop: '0.9rem' }}>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={analyzing || !text.trim()}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              border: '1px solid transparent',
              borderRadius: '10px',
              padding: '0.6rem 1.1rem',
              fontSize: '0.85rem',
              fontWeight: 700,
              cursor: analyzing || !text.trim() ? 'not-allowed' : 'pointer',
              opacity: analyzing || !text.trim() ? 0.6 : 1,
              background: 'linear-gradient(135deg, #38bdf8, #06b6d4)',
              color: '#04121f',
            }}
          >
            <Play size={15} /> {analyzing ? `Analysing${step ? ` · ${step}` : ''}` : 'Analyse history'}
          </button>
          <button
            type="button"
            onClick={handleReset}
            disabled={analyzing}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              border: '1px solid rgba(148, 163, 184, 0.35)',
              borderRadius: '10px',
              padding: '0.6rem 1rem',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              background: 'transparent',
              color: '#e2e8f0',
            }}
          >
            <RotateCcw size={15} /> Clear
          </button>
          <span style={{ fontSize: '0.74rem', ...muted }}>
            ML engines need the Python service; the bundled client engine runs when it is unreachable.
          </span>
        </div>

        {error && (
          <div style={{ marginTop: '0.9rem', padding: '0.75rem 0.9rem', borderRadius: '10px', border: '1px solid rgba(244, 63, 94, 0.35)', background: 'rgba(244, 63, 94, 0.1)', color: '#fda4af', fontSize: '0.82rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}
      </section>

      {result && (
        <section style={card}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', justifyContent: 'space-between', gap: '0.5rem' }}>
            <div>
              <div style={label}>Analysis</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ffffff', margin: '0.35rem 0 0.25rem' }}>
                {filename || 'Uploaded history'}
              </h3>
              <div style={{ fontSize: '0.75rem', ...muted }}>
                {engineUsed || 'PULSE extraction pipeline'}
                {latencyMs != null ? ` · ${latencyMs} ms` : ''}
                {/client/i.test(engineUsed || '') ? ' · no ML weights loaded (client fallback)' : ''}
              </div>
            </div>
            <div style={{ fontSize: '0.75rem', ...muted }}>{new Date().toLocaleString()}</div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', marginTop: '1.1rem' }}>
            {[
              { icon: FileText, label: 'Entities grounded', value: counts.total },
              { icon: Clock, label: 'Historical items', value: counts.historical },
              { icon: AlertCircle, label: 'Negated findings', value: counts.negated },
              { icon: Activity, label: 'Events', value: counts.events },
              { icon: ListTodo, label: 'Outstanding tasks', value: counts.tasks },
            ].map((stat) => {
              const Icon = stat.icon;
              return (
                <div key={stat.label} style={{ border: '1px solid rgba(148, 163, 184, 0.14)', borderRadius: '12px', padding: '0.7rem 0.8rem', background: 'rgba(10, 15, 29, 0.5)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', ...muted }}>
                    <Icon size={13} /> {stat.label}
                  </div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff', marginTop: '0.25rem' }}>{stat.value}</div>
                </div>
              );
            })}
          </div>

          {result.executive_summary && (
            <p style={{ marginTop: '1.1rem', padding: '0.85rem 1rem', borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.25)', background: 'rgba(6, 182, 212, 0.08)', fontSize: '0.86rem', lineHeight: 1.7, color: '#e2e8f0' }}>
              {result.executive_summary}
            </p>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginTop: '1.15rem' }}>
            {groups.map((group) => (
              <div key={group.key} style={{ border: '1px solid rgba(148, 163, 184, 0.14)', borderRadius: '12px', padding: '0.85rem 0.95rem', background: 'rgba(10, 15, 29, 0.45)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#e2e8f0' }}>{group.title}</div>
                  <div style={{ fontSize: '0.72rem', ...muted }}>{group.items.length}</div>
                </div>
                <ul style={{ listStyle: 'none', margin: '0.6rem 0 0', padding: 0, display: 'grid', gap: '0.4rem' }}>
                  {group.items.slice(0, 12).map((item, index) => {
                    const flags = entityFlags(item);
                    return (
                      <li key={`${group.key}-${index}`} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '0.4rem', fontSize: '0.82rem', color: '#cbd5e1' }}>
                        <span>{entityText(item)}</span>
                        {flags.map((flag) => (
                          <span
                            key={flag}
                            style={{
                              fontSize: '0.64rem',
                              fontWeight: 800,
                              letterSpacing: '0.05em',
                              textTransform: 'uppercase',
                              padding: '0.1rem 0.35rem',
                              borderRadius: '999px',
                              border: '1px solid rgba(148, 163, 184, 0.3)',
                              color: flag === 'Negated' ? '#fda4af' : flag === 'Historical' ? '#fcd34d' : '#a5b4fc',
                            }}
                          >
                            {flag}
                          </span>
                        ))}
                      </li>
                    );
                  })}
                  {group.items.length > 12 && (
                    <li style={{ fontSize: '0.74rem', ...muted }}>+{group.items.length - 12} more</li>
                  )}
                </ul>
              </div>
            ))}
          </div>

          {groups.length === 0 && (
            <p style={{ marginTop: '1rem', fontSize: '0.85rem', ...muted }}>
              No clinical entities were grounded in this document. Check that it contains narrative clinical text rather
              than a table or scanned image.
            </p>
          )}

          <div style={{ marginTop: '1.1rem', fontSize: '0.74rem', lineHeight: 1.6, ...muted }}>
            Extracted items are verbatim references from the uploaded document. Negated and historical findings are kept
            rather than discarded, so the incoming shift can see what has already been ruled out. PULSE does not
            diagnose, stage or recommend treatment.
          </div>
        </section>
      )}

      <section style={card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Layers size={16} color={accent} />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>Saved history documents</h3>
          <span style={{ fontSize: '0.72rem', marginLeft: 'auto', ...muted }}>{patientKey || 'Unassigned'}</span>
        </div>

        {saved.length === 0 ? (
          <p style={{ marginTop: '0.7rem', fontSize: '0.84rem', ...muted }}>
            Nothing stored yet. Analyses are kept in this browser for the selected patient so they can be reopened
            without re-uploading.
          </p>
        ) : (
          <ul style={{ listStyle: 'none', margin: '0.75rem 0 0', padding: 0, display: 'grid', gap: '0.5rem' }}>
            {saved.map((entry) => (
              <li
                key={entry.id}
                style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.6rem', border: '1px solid rgba(148, 163, 184, 0.14)', borderRadius: '10px', padding: '0.6rem 0.75rem', background: 'rgba(10, 15, 29, 0.45)' }}
              >
                <Pill size={14} color={accent} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '0.84rem', fontWeight: 600, color: '#e2e8f0' }}>{entry.filename}</div>
                  <div style={{ fontSize: '0.72rem', ...muted }}>
                    {new Date(entry.savedAt).toLocaleString()} · {entry.entityCount} entities · {entry.chars} chars
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', marginLeft: 'auto' }}>
                  <button
                    type="button"
                    onClick={() => handleLoad(entry)}
                    style={{ border: '1px solid rgba(56, 189, 248, 0.4)', background: 'rgba(56, 189, 248, 0.12)', color: '#7dd3fc', borderRadius: '8px', padding: '0.3rem 0.6rem', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    Reopen
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(entry.id)}
                    title="Remove from this browser"
                    style={{ border: '1px solid rgba(244, 63, 94, 0.35)', background: 'rgba(244, 63, 94, 0.1)', color: '#fda4af', borderRadius: '8px', padding: '0.3rem 0.5rem', fontSize: '0.75rem', cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default PriorHistoryPage;
