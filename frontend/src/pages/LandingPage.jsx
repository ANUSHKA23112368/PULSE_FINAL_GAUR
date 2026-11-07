import React from 'react';
import {
  Activity,
  Sparkles,
  Database,
  BarChart3,
  ArrowRight,
  ShieldCheck,
  Layers,
  BrainCircuit,
  FileText,
} from 'lucide-react';

const ACCENT = '#38bdf8';
const MUTED = '#94a3b8';
const BORDER = 'rgba(148, 163, 184, 0.16)';

const STATS = [
  { value: '101', label: 'Gold handover notes' },
  { value: '2,103', label: 'Annotated clinical spans' },
  { value: '9', label: 'ISBAR categories' },
  { value: '5-fold', label: 'Cross-validation' },
];

const MODULES = [
  {
    id: 'dashboard',
    icon: Activity,
    title: 'Clinical Ward',
    copy: 'Bed roster, vitals with NEWS2 early warning scoring, note authoring, and the structured handover sheet for the active patient.',
    action: 'Open ward',
  },
  {
    id: 'analyze',
    icon: Sparkles,
    title: 'Handover analysis',
    copy: 'Paste or load a free-text shift note and watch entities resolve into the nine-category ISBAR structure with highlighted evidence.',
    action: 'Analyse a note',
  },
  {
    id: 'dataset',
    icon: Database,
    title: 'Corpus explorer',
    copy: 'Inspect the synthetic nursing handover corpus report by report, comparing raw text against the preprocessed and annotated view.',
    action: 'Browse corpus',
  },
  {
    id: 'evaluation',
    icon: BarChart3,
    title: 'Training and benchmarks',
    copy: 'Training telemetry for the clinical language model plus span-level precision, recall and F1 from cross-validation runs.',
    action: 'View benchmarks',
  },
];

const STEPS = [
  {
    n: '01',
    icon: FileText,
    title: 'Ingest',
    copy: 'A nurse writes or dictates a shift handover. The raw note is normalised, sentence-split and prepared for extraction.',
  },
  {
    n: '02',
    icon: BrainCircuit,
    title: 'Extract',
    copy: 'Entity recognition locates patients, conditions, medications, investigations, events and time references, with negation and uncertainty handled explicitly.',
  },
  {
    n: '03',
    icon: Layers,
    title: 'Structure',
    copy: 'Extracted spans are mapped into the nine ISBAR categories so the incoming shift reads one consistent, prioritised summary.',
  },
];

function SectionTitle({ children, kicker }) {
  return (
    <div style={{ marginBottom: '1.75rem' }}>
      {kicker ? (
        <div style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: ACCENT, marginBottom: '0.5rem' }}>
          {kicker}
        </div>
      ) : null}
      <h2 style={{ fontSize: 'clamp(1.6rem, 3vw, 2.1rem)', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff', lineHeight: 1.2, margin: 0 }}>
        {children}
      </h2>
    </div>
  );
}

export function LandingPage({ onNavigate }) {
  const go = (tab) => () => onNavigate(tab);

  function scrollTo(id) {
    const el = document.getElementById(id);
    if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const primaryButton = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    background: 'linear-gradient(135deg, #38bdf8, #06b6d4)',
    color: '#04121f',
    border: '1px solid transparent',
    borderRadius: '10px',
    padding: '0.75rem 1.35rem',
    fontSize: '0.92rem',
    fontWeight: 700,
    cursor: 'pointer',
  };

  const ghostButton = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    background: 'transparent',
    color: '#e2e8f0',
    border: '1px solid rgba(148, 163, 184, 0.35)',
    borderRadius: '10px',
    padding: '0.75rem 1.35rem',
    fontSize: '0.92rem',
    fontWeight: 600,
    cursor: 'pointer',
  };

  const card = {
    background: 'rgba(17, 24, 39, 0.65)',
    border: '1px solid ' + BORDER,
    borderRadius: '14px',
    padding: '1.4rem',
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0a0f1d', color: '#e2e8f0', fontFamily: "'Inter', system-ui, -apple-system, sans-serif" }}>
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 20,
          borderBottom: '1px solid ' + BORDER,
          background: 'rgba(10, 15, 29, 0.9)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <div
          style={{
            maxWidth: '1160px',
            margin: '0 auto',
            padding: '0.85rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <span
              aria-hidden="true"
              style={{
                width: 34,
                height: 34,
                borderRadius: 9,
                background: 'linear-gradient(135deg, #38bdf8, #06b6d4)',
                color: '#04121f',
                fontWeight: 800,
                fontSize: '1rem',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              P
            </span>
            <div>
              <div style={{ fontWeight: 800, letterSpacing: '0.04em', lineHeight: 1.1 }}>PULSE</div>
              <div style={{ fontSize: '0.7rem', color: MUTED, lineHeight: 1.3 }}>Clinical handover intelligence</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <button type="button" onClick={() => scrollTo('research')} style={{ ...ghostButton, border: '1px solid transparent', padding: '0.6rem 0.85rem' }}>
              Research and data
            </button>
            <button type="button" onClick={go('dashboard')} style={{ ...primaryButton, padding: '0.6rem 1.1rem', fontSize: '0.86rem' }}>
              Open workspace
            </button>
          </div>
        </div>
      </header>

      <main>
        <section style={{ maxWidth: '1160px', margin: '0 auto', padding: '4.5rem 1.5rem 3rem' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              background: 'rgba(6, 182, 212, 0.1)',
              color: '#7dd3fc',
              borderRadius: '999px',
              padding: '0.32rem 0.75rem',
              fontSize: '0.74rem',
              fontWeight: 700,
              letterSpacing: '0.04em',
            }}
          >
            <ShieldCheck size={13} />
            Clinical NLP research prototype
          </div>

          <h1
            style={{
              fontSize: 'clamp(2.4rem, 6vw, 4.1rem)',
              fontWeight: 800,
              letterSpacing: '-0.035em',
              lineHeight: 1.04,
              color: '#ffffff',
              margin: '1.1rem 0 0',
              maxWidth: '22ch',
            }}
          >
            Unstructured ward notes in.
            <br />
            <span style={{ color: ACCENT }}>Structured handoffs out.</span>
          </h1>

          <p style={{ maxWidth: '44rem', fontSize: '1.03rem', lineHeight: 1.75, color: MUTED, marginTop: '1.4rem' }}>
            PULSE reads free-text nursing shift notes and produces an ISBAR-aligned summary across nine clinical
            categories, so the incoming shift can see condition, history, medications, investigations, events, pending
            tasks and follow-up in one consistent place.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '2rem' }}>
            <button type="button" onClick={go('dashboard')} style={primaryButton}>
              Launch workspace
              <ArrowRight size={16} />
            </button>
            <button type="button" onClick={() => scrollTo('modules')} style={ghostButton}>
              See what is inside
            </button>
          </div>

          <dl
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: '1rem',
              marginTop: '3.5rem',
              paddingTop: '1.75rem',
              borderTop: '1px solid ' + BORDER,
            }}
          >
            {STATS.map((s) => (
              <div key={s.label}>
                <dt style={{ fontSize: '0.74rem', color: MUTED, letterSpacing: '0.06em', textTransform: 'uppercase', fontWeight: 700 }}>
                  {s.label}
                </dt>
                <dd style={{ margin: '0.35rem 0 0', fontSize: '1.7rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em' }}>
                  {s.value}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        <section id="modules" style={{ maxWidth: '1160px', margin: '0 auto', padding: '3.5rem 1.5rem' }}>
          <SectionTitle kicker="Inside the workspace">Four views, one clinical record</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
            {MODULES.map((m) => {
              const Icon = m.icon;
              return (
                <div key={m.id} style={card}>
                  <span
                    style={{
                      display: 'inline-grid',
                      placeItems: 'center',
                      width: 36,
                      height: 36,
                      borderRadius: 9,
                      background: 'rgba(56, 189, 248, 0.12)',
                      color: ACCENT,
                    }}
                  >
                    <Icon size={18} />
                  </span>
                  <h3 style={{ fontSize: '1.02rem', fontWeight: 700, color: '#ffffff', margin: '0.9rem 0 0.45rem' }}>{m.title}</h3>
                  <p style={{ fontSize: '0.88rem', lineHeight: 1.65, color: MUTED, margin: '0 0 1rem' }}>{m.copy}</p>
                  <button
                    type="button"
                    onClick={go(m.id)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      background: 'transparent',
                      border: 'none',
                      padding: 0,
                      color: ACCENT,
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {m.action}
                    <ArrowRight size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        <section style={{ maxWidth: '1160px', margin: '0 auto', padding: '3.5rem 1.5rem' }}>
          <SectionTitle kicker="How it works">From a spoken shift note to a signed handover</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
            {STEPS.map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.n} style={card}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ color: ACCENT }}>
                      <Icon size={18} />
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 800, letterSpacing: '0.1em', color: '#475569' }}>{s.n}</span>
                  </div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff', margin: '0.85rem 0 0.4rem' }}>{s.title}</h3>
                  <p style={{ fontSize: '0.87rem', lineHeight: 1.65, color: MUTED, margin: 0 }}>{s.copy}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section id="research" style={{ maxWidth: '1160px', margin: '0 auto', padding: '3.5rem 1.5rem' }}>
          <SectionTitle kicker="Research and data">Corpus, training and validation</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
            <div style={card}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', margin: '0 0 0.5rem' }}>Corpus</h3>
              <p style={{ fontSize: '0.87rem', lineHeight: 1.65, color: MUTED, margin: 0 }}>
                A synthetic nursing handover corpus drawn from acute medical and surgical wards, annotated span by span
                against the nine ISBAR categories. The corpus and its annotations ship with the prototype so results can
                be reproduced.
              </p>
            </div>
            <div style={card}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', margin: '0 0 0.5rem' }}>Training</h3>
              <p style={{ fontSize: '0.87rem', lineHeight: 1.65, color: MUTED, margin: 0 }}>
                A clinical language model initialised from domain-pretrained weights is fine-tuned for token-level entity
                classification. Rule-based and statistical baselines are trained alongside it so the neural approach is
                measured against something rather than assumed.
              </p>
            </div>
            <div style={card}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', margin: '0 0 0.5rem' }}>Validation</h3>
              <p style={{ fontSize: '0.87rem', lineHeight: 1.65, color: MUTED, margin: 0 }}>
                Every configuration is scored with cross-validation using span-level precision, recall and F1, reported
                under both strict and lenient matching. The live numbers and per-fold breakdown sit in the benchmarks view.
              </p>
            </div>
          </div>

          <div style={{ marginTop: '1rem', ...card, display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
            <div style={{ maxWidth: '38rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', margin: '0 0 0.35rem' }}>Read the full evaluation</h3>
              <p style={{ fontSize: '0.86rem', lineHeight: 1.6, color: MUTED, margin: 0 }}>
                Per-fold scores, baseline comparisons and training telemetry are documented in the dedicated benchmark view.
              </p>
            </div>
            <button type="button" onClick={go('evaluation')} style={{ ...ghostButton, padding: '0.6rem 1.1rem', fontSize: '0.85rem' }}>
              Open benchmarks
              <ArrowRight size={15} />
            </button>
          </div>
        </section>

        <section style={{ maxWidth: '1160px', margin: '0 auto', padding: '1rem 1.5rem 4rem' }}>
          <div
            style={{
              border: '1px solid rgba(245, 158, 11, 0.35)',
              background: 'rgba(245, 158, 11, 0.07)',
              borderRadius: '14px',
              padding: '1.35rem 1.4rem',
              display: 'flex',
              gap: '0.9rem',
              alignItems: 'flex-start',
            }}
          >
            <ShieldCheck size={20} style={{ color: '#fbbf24', flexShrink: 0, marginTop: 2 }} />
            <div>
              <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fef3c7', margin: '0 0 0.35rem' }}>Research scope</h3>
              <p style={{ fontSize: '0.85rem', lineHeight: 1.65, color: '#e2e8f0', margin: 0 }}>
                PULSE is an information-organisation prototype built on synthetic data. It structures what a clinician has
                already documented. It does not diagnose, recommend treatment, triage, or replace clinical judgement, and
                every generated summary is meant to be read and confirmed by a clinician.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer style={{ borderTop: '1px solid ' + BORDER }}>
        <div
          style={{
            maxWidth: '1160px',
            margin: '0 auto',
            padding: '1.5rem',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '1rem',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.82rem',
            color: MUTED,
          }}
        >
          <span>PULSE clinical handover intelligence. Research prototype, synthetic corpus.</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
            <button type="button" onClick={go('dataset')} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', fontSize: '0.82rem', padding: 0 }}>
              Corpus
            </button>
            <button type="button" onClick={go('evaluation')} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', fontSize: '0.82rem', padding: 0 }}>
              Benchmarks
            </button>
            <button type="button" onClick={go('about')} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', fontSize: '0.82rem', padding: 0 }}>
              About
            </button>
            <button type="button" onClick={go('dashboard')} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', fontSize: '0.82rem', padding: 0 }}>
              Open workspace
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
