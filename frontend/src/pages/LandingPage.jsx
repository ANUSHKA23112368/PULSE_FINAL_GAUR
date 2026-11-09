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

const IMPROVEMENTS = [
  {
    tag: 'Engine',
    title: 'A second extraction engine, switchable at runtime',
    copy: 'Hybrid CRF + Gazetteer joins the Bio_ClinicalBERT pipeline as a selectable engine. The choice travels with the request, so the same note can be scored by either path and the two outputs compared directly.',
  },
  {
    tag: 'Extraction',
    title: 'Span cleanup that was measured, not assumed',
    copy: 'Predicted spans are split at sentence boundaries and de-duplicated before scoring. Trimming modifier words was tried and rejected because it moved fold 0 strict F1 from 60.91 down to 58.12, so it is documented as a negative result rather than shipped.',
  },
  {
    tag: 'Evaluation',
    title: 'Leak-free scoring, with the old headline retracted',
    copy: 'The BERT-to-CRF stack is scored with a checkpoint that never saw the evaluation fold. The earlier 87.66 strict / 94.36 lenient figure came from a checkpoint retrained on all 101 notes and is labelled invalid everywhere it appears.',
  },
  {
    tag: 'Runtime',
    title: 'Handover-speed inference',
    copy: 'CRF plus gazetteer extraction returns in under 5 ms per report, against roughly 153 ms for the transformer path. A full corpus pass drops from minutes to milliseconds and needs no GPU.',
  },
];

const TRADEOFFS = [
  {
    label: 'Why Bio_ClinicalBERT is still the default',
    copy: 'Its strict recall is 69.12 against 55.49 for the CRF. On a handover, an extra bullet a nurse deletes costs seconds; a pending scan that never appears can be missed entirely. The default is chosen for recall, not for the highest F1.',
  },
  {
    label: 'Why the CRF was added at all',
    copy: 'It leads on precision and strict F1 (66.53 / 60.51 against 46.73 / 55.76), it exposes its per-feature decisions for inspection, and it runs without a GPU, which makes batch scoring of the whole corpus practical.',
  },
  {
    label: 'Why both are scored identically',
    copy: 'Same preprocessing, same gold spans, same character-level scorer, reported both strictly (exact boundaries) and leniently (relaxed boundaries). The comparison is between models, not between measurement methods.',
  },
  {
    label: 'What was deliberately not done',
    copy: 'No training on the evaluation fold, no trimming chosen because it flattered the score, no redefining “strict” to raise a number. Where a change made the result worse, it is reported as a negative result.',
  },
];

const MODELS = [
  { name: 'Hybrid Bio_ClinicalBERT + ConText', setting: 'Default engine · fold 0', p: '46.73', r: '69.12', strict: '55.76', lenient: '77.29', latency: '~153 ms', note: 'Shipped default', accent: '#a5b4fc' },
  { name: 'Hybrid CRF + Gazetteer', setting: 'Opt-in engine · 5-fold micro', p: '66.53', r: '55.49', strict: '60.51', lenient: '74.46', latency: '<5 ms', note: 'Opt-in', accent: '#34d399' },
  { name: 'BERT → CRF stack', setting: 'Research · fold 0, leak-free', p: '69.37', r: '57.56', strict: '62.92', lenient: '76.23', latency: '<5 ms', note: 'Best single fold', accent: '#38bdf8' },
  { name: 'Gazetteer only', setting: 'Ablation · 5-fold micro', p: '56.29', r: '40.66', strict: '47.21', lenient: '60.24', latency: '<1 ms', note: 'Ablation', accent: '#94a3b8' },
  { name: 'CRF ⊕ gazetteer union', setting: 'Ablation · 5-fold micro', p: '61.37', r: '55.06', strict: '58.05', lenient: '72.58', latency: '<5 ms', note: 'Ablation', accent: '#94a3b8' },
  { name: 'Statistical classifier (logistic regression)', setting: 'Baseline · 5-fold, multi-model audit', p: '47.48', r: '58.09', strict: '52.20', lenient: '80.19', latency: '3.8 ms', note: 'Classical ML baseline', accent: '#fbbf24' },
  { name: 'Rule engine (deterministic lexicon)', setting: 'Naive baseline · 5-fold, multi-model audit', p: '44.48', r: '17.26', strict: '24.84', lenient: '47.72', latency: '1.2 ms', note: 'Naive comparison', accent: '#f59e0b' },
  { name: 'Bio_ClinicalBERT (pure neural)', setting: 'Comparator · 5-fold, multi-model audit', p: '12.56', r: '10.64', strict: '11.38', lenient: '47.72', latency: '42.5 ms', note: 'BERT without the hybrid layer', accent: '#c084fc' },
];

const NUMERIC_NOTES = [
  {
    label: 'Strict vs lenient',
    copy: 'Strict requires exact character boundaries, so a span one word too long is wrong. Lenient accepts boundary overlap and measures whether the clinical concept was found at all.',
  },
  {
    label: 'What the numbers are computed on',
    copy: '101 NICTA gold handover notes holding 2,103 adjudicated spans, plus 160 synthetic ISBAR augmentations used for training. Scores are micro-averaged over 5 folds, about 20 notes per fold.',
  },
  {
    label: 'Where the default engine loses spans',
    copy: 'Strict matching counts 329 true positives against 375 false positives and 147 misses. Lenient matching counts 456 true positives against 248 false positives and 20 misses: the concepts are usually found, the boundaries are often too wide.',
  },
  {
    label: 'Why BERT appears twice',
    copy: 'The pure-neural row (11.38 strict) and the default hybrid row (55.76) are different runs: an earlier multi-model audit against the current checkpoint scored on fold 0 with ConText and span post-processing. Both are measured, but the gap between them is not a like-for-like ablation of one component.',
  },
  {
    label: 'Target status',
    copy: '70–90 strict F1 was the stated goal and no leak-free configuration reached it. The best 5-fold strict score is 60.51 and the best single-fold stack is 62.92. With roughly 20 notes per fold, a few points of movement sit inside noise.',
  },
];

const FAQS = [
  {
    q: 'If lenient F1 is so much higher, why report strict F1 at all?',
    a: 'Lenient matching only asks whether the predicted span shares any character with the gold span, so a prediction that swallows a whole clause still counts as correct. Strict matching requires both boundaries to be exact, which is what the interface depends on to highlight the verbatim evidence behind each handover line. Reporting only the lenient figure would hide a fourteen-point boundary error, so both are published and the gap between them is the interesting part.',
  },
  {
    q: 'Why keep the CRF when the statistical classifier has the best lenient score?',
    a: 'The statistical classifier scores 80.19 lenient but only 52.20 strict: it finds the right concepts with visibly loose boundaries. The CRF scores 60.51 strict and 74.46 lenient, so it leads by 8.31 points on the measure the product actually uses, answers in under 5 ms, and exists as a saved checkpoint that can serve a request. The 80.19 is a cross-validation mean over five models that were fitted per fold and never persisted, so there is nothing there to deploy.',
  },
  {
    q: 'Why is BERT still the default if the CRF scores higher on strict F1?',
    a: 'Recall. Bio_ClinicalBERT recovers 69.12% of gold spans under strict matching against 55.49% for the CRF. A missed pending investigation or medication change is the failure that damages a handover; an extra span costs a nurse one glance before deleting it. The default is tuned for recall, and the CRF sits one dropdown away for precision-critical work.',
  },
  {
    q: 'Why not just use the 87.66 strict / 94.36 lenient result?',
    a: 'Because it is not a generalisation score. That checkpoint was retrained on all 101 gold notes, so the evaluation fold was inside its training data and the figure measures memorisation. It is labelled retracted wherever it appears rather than quietly deleted, so the correction stays auditable.',
  },
  {
    q: 'What exactly do these percentages measure?',
    a: 'Character-level span recovery where the clinical category must also match, over 101 gold handover notes holding 2,103 adjudicated spans, micro-averaged across five folds from identical splits. They are not token accuracy: token accuracy on the same corpus is 78.52%, a far friendlier number that says almost nothing about whether a usable span was produced.',
  },
  {
    q: 'Is 60.51% good enough to use clinically?',
    a: 'No, and nothing here claims otherwise. The stated target was 70–90 strict F1 and no leak-free configuration reached it. PULSE is a research prototype for organising information a clinician has already documented, and every generated summary is meant to be read and confirmed by a person before it is acted on.',
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
            <button type="button" onClick={() => scrollTo('models')} style={ghostButton}>
              Model scores
              <BarChart3 size={15} />
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

        <section id="models" style={{ maxWidth: '1160px', margin: '0 auto', padding: '3.5rem 1.5rem' }}>
          <SectionTitle kicker="Model and evaluation">What changed, why this design, and how it scores</SectionTitle>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
            {IMPROVEMENTS.map((item) => (
              <div key={item.title} style={card}>
                <span style={{ fontSize: '0.68rem', fontWeight: 800, letterSpacing: '0.12em', textTransform: 'uppercase', color: ACCENT }}>{item.tag}</span>
                <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: '#ffffff', margin: '0.55rem 0 0.45rem' }}>{item.title}</h3>
                <p style={{ fontSize: '0.86rem', lineHeight: 1.65, color: MUTED, margin: 0 }}>{item.copy}</p>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '1.25rem', ...card, padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.02rem', fontWeight: 700, color: '#ffffff', margin: '0 0 1.1rem' }}>Why we opted for this arrangement</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.1rem' }}>
              {TRADEOFFS.map((t) => (
                <div key={t.label} style={{ borderLeft: '2px solid rgba(56, 189, 248, 0.35)', paddingLeft: '0.95rem' }}>
                  <div style={{ fontSize: '0.87rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.3rem' }}>{t.label}</div>
                  <p style={{ fontSize: '0.84rem', lineHeight: 1.62, color: MUTED, margin: 0 }}>{t.copy}</p>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: '1.25rem', ...card, padding: '1.5rem' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', justifyContent: 'space-between', gap: '0.5rem' }}>
              <h3 style={{ fontSize: '1.02rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>Measured scores</h3>
              <span style={{ fontSize: '0.76rem', color: MUTED }}>Character-level span matching · strict and lenient</span>
            </div>

            <div style={{ overflowX: 'auto', marginTop: '1.1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', color: '#94a3b8', fontSize: '0.7rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    <th style={{ padding: '0.5rem 0.6rem', borderBottom: '1px solid ' + BORDER }}>Engine</th>
                    <th style={{ padding: '0.5rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right' }}>Strict P</th>
                    <th style={{ padding: '0.5rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right' }}>Strict R</th>
                    <th style={{ padding: '0.5rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right' }}>Strict F1</th>
                    <th style={{ padding: '0.5rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right' }}>Lenient F1</th>
                    <th style={{ padding: '0.5rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right' }}>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {MODELS.map((m) => (
                    <tr key={m.name}>
                      <td style={{ padding: '0.65rem 0.6rem', borderBottom: '1px solid ' + BORDER }}>
                        <div style={{ fontWeight: 700, color: m.accent }}>{m.name}</div>
                        <div style={{ fontSize: '0.74rem', color: MUTED }}>{m.setting} · {m.note}</div>
                      </td>
                      <td style={{ padding: '0.65rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right', color: '#cbd5e1' }}>{m.p}%</td>
                      <td style={{ padding: '0.65rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right', color: '#cbd5e1' }}>{m.r}%</td>
                      <td style={{ padding: '0.65rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right', fontWeight: 800, color: m.accent }}>{m.strict}%</td>
                      <td style={{ padding: '0.65rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right', fontWeight: 700, color: '#e2e8f0' }}>{m.lenient}%</td>
                      <td style={{ padding: '0.65rem 0.6rem', borderBottom: '1px solid ' + BORDER, textAlign: 'right', color: MUTED }}>{m.latency}</td>
                    </tr>
                  ))}
                  <tr>
                    <td colSpan={6} style={{ padding: '0.75rem 0.6rem', fontSize: '0.78rem', lineHeight: 1.6, color: '#fca5a5' }}>
                      Retracted, not plotted: 87.66 strict / 94.36 lenient came from a checkpoint retrained on all 101 gold notes, so the evaluation fold was inside its training data. It is not a valid generalisation score.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem', marginTop: '1.3rem', paddingTop: '1.1rem', borderTop: '1px solid ' + BORDER }}>
              {NUMERIC_NOTES.map((n) => (
                <div key={n.label}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.3rem' }}>{n.label}</div>
                  <p style={{ fontSize: '0.78rem', lineHeight: 1.6, color: MUTED, margin: 0 }}>{n.copy}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="faq" style={{ maxWidth: '1160px', margin: '0 auto', padding: '3.5rem 1.5rem' }}>
          <SectionTitle kicker="Frequently asked">Why the scores are reported this way</SectionTitle>
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {FAQS.map((f) => (
              <details key={f.q} style={{ ...card, padding: '1.05rem 1.25rem' }}>
                <summary style={{ cursor: 'pointer', fontSize: '0.92rem', fontWeight: 700, color: '#ffffff', lineHeight: 1.5 }}>
                  {f.q}
                </summary>
                <p style={{ fontSize: '0.86rem', lineHeight: 1.72, color: MUTED, margin: '0.7rem 0 0' }}>{f.a}</p>
              </details>
            ))}
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
