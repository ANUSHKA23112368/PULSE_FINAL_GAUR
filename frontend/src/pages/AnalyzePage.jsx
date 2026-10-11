import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  RotateCcw, 
  Download, 
  Copy, 
  Check, 
  AlertCircle, 
  Clock, 
  Calendar, 
  Activity, 
  Pill, 
  Stethoscope, 
  CheckCircle2, 
  FileText, 
  User, 
  Search,
  ExternalLink,
  HelpCircle,
  Tag,
  Volume2,
  VolumeX,
  Printer,
  ShieldAlert,
  Sparkles,
  CheckCircle,
  X
} from 'lucide-react';
import { fetchReports, fetchReport, analyzeHandover } from '../services/api';

export function AnalyzePage({ selectedReportId, onSelectReport, onStoreResults }) {
  const [reportList, setReportList] = useState([]);
  const [chosenReportId, setChosenReportId] = useState(selectedReportId || '0');
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [error, setError] = useState(null);
  
  // Navigation & Sub-views
  const [activeTab, setActiveTab] = useState('structured'); 
  const [handoverFormat, setHandoverFormat] = useState('isbar'); // 'isbar' | '9categories'
  const [selectedEngine, setSelectedEngine] = useState('hybrid'); // 'hybrid' | 'clinical_bert' | 'rule'
  const [copied, setCopied] = useState(false);
  const [showPrintModal, setShowPrintModal] = useState(false);

  // Audio Speech Synthesis state
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const speechUtteranceRef = useRef(null);

  // Quick preset clinical cases
  const clinicalPresets = [
    { id: '0', label: 'Report #0 (Neuro / Michael I Wu)', tag: 'Neurology' },
    { id: '1', label: 'Report #1 (Chest Pain / Vera Abbott)', tag: 'Cardiology' },
    { id: '12', label: 'Report #12 (Type 1 DM / Leila Sonya)', tag: 'Endocrine' },
    { id: '15', label: 'Report #15 (Post-Op Surgical)', tag: 'Surgical' },
    { id: '56', label: 'Report #56 (Respiratory / COPD)', tag: 'Respiratory' }
  ];

  // Load report list for dropdown
  useEffect(() => {
    async function loadReports() {
      try {
        const data = await fetchReports();
        setReportList(data.reports || []);
      } catch (err) {
        console.error("Failed to load report dropdown options:", err);
      }
    }
    loadReports();
  }, []);

  // Sync selectedReportId changes
  useEffect(() => {
    if (selectedReportId) {
      setChosenReportId(selectedReportId);
      loadReportContent(selectedReportId);
    } else {
      loadReportContent('0');
    }
  }, [selectedReportId]);

  // Clean up speech synthesis on unmount
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  async function loadReportContent(id) {
    if (!id) return;
    try {
      setLoading(true);
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
      const data = await fetchReport(id);
      setInputText(data.raw_text);
      setError(null);
    } catch (err) {
      console.error("Failed to load report:", err);
      setError(`Failed to load report #${id}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function handleSelectChange(e) {
    const id = e.target.value;
    setChosenReportId(id);
    if (onSelectReport) onSelectReport(id);
  }

  function handleClear() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setIsPlayingAudio(false);
    setInputText('');
    setAnalysisResult(null);
    setError(null);
  }

  // Realistic Text-to-Speech audio handover playback
  function toggleAudioPlayback() {
    if (!window.speechSynthesis) {
      alert("Audio dictation is not supported by your browser.");
      return;
    }

    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
    } else {
      const textToRead = inputText || "No handover text loaded.";
      const utterance = new SpeechSynthesisUtterance(textToRead);
      utterance.rate = 0.95; // realistic nurse cadence
      utterance.pitch = 1.0;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      speechUtteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
      setIsPlayingAudio(true);
    }
  }

  async function handleAnalyze() {
    if (!inputText.trim()) {
      setError("Please enter or load a nursing handover report before analyzing.");
      return;
    }

    try {
      setAnalyzing(true);
      setError(null);
      const result = await analyzeHandover({
        reportId: chosenReportId,
        rawText: inputText,
        engine: selectedEngine
      });

      setAnalysisResult(result);
      if (onStoreResults) onStoreResults(result);
    } catch (err) {
      console.error("Analysis failed:", err);
      setError(err.message || "An unexpected error occurred during pipeline analysis.");
    } finally {
      setAnalyzing(false);
    }
  }

  function handleCopyStructured() {
    if (!analysisResult) return;
    let textToCopy = "";

    if (handoverFormat === 'isbar' && analysisResult.isbar) {
      const isbar = analysisResult.isbar;
      textToCopy = [
        "==================================================",
        "ISBAR CLINICAL SHIFT HANDOVER REPORT (PULSE)",
        "==================================================",
        `EXECUTIVE BRIEF: ${analysisResult.executive_summary}`,
        "\n[I] IDENTIFY:",
        ...isbar.identify.map(i => `  • ${i}`),
        "\n[S] SITUATION:",
        ...isbar.situation.map(i => `  • ${i}`),
        "\n[B] BACKGROUND:",
        ...isbar.background.map(i => `  • ${i}`),
        "\n[A] ASSESSMENT:",
        ...isbar.assessment.map(i => `  • ${i}`),
        "\n[R] RECOMMENDATION & ACTIONS:",
        ...isbar.recommendation.map(i => `  • ${i}`),
        "\n==================================================",
        "Handover Protocol: ISBAR Clinical Standard | PULSE Prototype"
      ].join('\n');
    } else {
      const sh = analysisResult.structured_handover;
      textToCopy = [
        "==================================================",
        "STRUCTURED CLINICAL HANDOVER (9 CATEGORIES)",
        "==================================================",
        `EXECUTIVE BRIEF: ${analysisResult.executive_summary}`,
        "\n1. PATIENT INFORMATION:",
        ...sh.patient_information.map(i => `  • ${i}`),
        "\n2. CURRENT CONDITION:",
        ...sh.current_condition.map(i => `  • ${i}`),
        "\n3. MEDICAL HISTORY:",
        ...sh.medical_history.map(i => `  • ${i}`),
        "\n4. MEDICATIONS / TREATMENT:",
        ...sh.medications_treatment.map(i => `  • ${i}`),
        "\n5. INVESTIGATIONS:",
        ...sh.investigations.map(i => `  • ${i}`),
        "\n6. CLINICAL EVENTS:",
        ...sh.clinical_events.map(i => `  • ${i}`),
        "\n7. TEMPORAL INFORMATION:",
        ...sh.temporal_information.map(i => `  • ${i}`),
        "\n8. PENDING TASKS:",
        ...sh.pending_tasks.map(i => `  • ${i}`),
        "\n9. FOLLOW-UP:",
        ...sh.follow_up.map(i => `  • ${i}`),
        "\n==================================================",
        "PULSE Research Prototype | Verified Against Reference Corpus"
      ].join('\n');
    }

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // Extract patient avatar initials
  function getPatientInitials() {
    if (!analysisResult?.entities?.patient_information) return "PT";
    const nameItem = analysisResult.entities.patient_information.find(p => p.field === "Patient Name");
    if (!nameItem || !nameItem.value) return "PT";
    const parts = nameItem.value.split(" ");
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return parts[0].substring(0, 2).toUpperCase();
  }

  function getPatientField(fieldName, fallback = "Not documented") {
    if (!analysisResult?.entities?.patient_information) return fallback;
    const item = analysisResult.entities.patient_information.find(p => p.field === fieldName);
    return item ? item.value : fallback;
  }

  // Highlighted text generation
  function renderHighlightedText() {
    if (!analysisResult) return null;
    const text = analysisResult.preprocessed_text;
    const spans = [];
    const ent = analysisResult.entities || {};

    (ent.conditions || []).forEach(c => {
      (c.all_spans || [(c.start_char, c.end_char)]).forEach(span => {
        if (span && span[0] !== undefined) {
          spans.push({ start: span[0], end: span[1], type: 'condition', label: 'Condition: ' + c.normalized });
        }
      });
    });
    (ent.symptoms || []).forEach(s => {
      (s.all_spans || [(s.start_char, s.end_char)]).forEach(span => {
        if (span && span[0] !== undefined) {
          spans.push({ start: span[0], end: span[1], type: 'symptom', label: 'Symptom: ' + s.normalized });
        }
      });
    });
    (ent.medications || []).forEach(m => {
      (m.all_spans || [(m.start_char, m.end_char)]).forEach(span => {
        if (span && span[0] !== undefined) {
          spans.push({ start: span[0], end: span[1], type: 'medication', label: 'Medication: ' + m.normalized });
        }
      });
    });
    (ent.investigations || []).forEach(i => {
      (i.all_spans || [(i.start_char, i.end_char)]).forEach(span => {
        if (span && span[0] !== undefined) {
          spans.push({ start: span[0], end: span[1], type: 'investigation', label: 'Investigation: ' + i.normalized });
        }
      });
    });
    (ent.treatments || []).forEach(t => {
      (t.all_spans || [(t.start_char, t.end_char)]).forEach(span => {
        if (span && span[0] !== undefined) {
          spans.push({ start: span[0], end: span[1], type: 'treatment', label: 'Treatment: ' + t.normalized });
        }
      });
    });
    (ent.measurements || []).forEach(ms => {
      if (ms.start_char !== undefined && ms.end_char !== undefined) {
        spans.push({ start: ms.start_char, end: ms.end_char, type: 'measurement', label: 'Measurement: ' + ms.type });
      }
    });
    (ent.abbreviations || []).forEach(a => {
      if (a.start_char !== undefined && a.end_char !== undefined) {
        spans.push({ start: a.start_char, end: a.end_char, type: 'abbr', label: 'Abbreviation: ' + a.expansion });
      }
    });

    spans.sort((a, b) => a.start - b.start);

    const nonOverlapping = [];
    let lastEnd = 0;
    for (const s of spans) {
      if (s.start >= lastEnd && s.start < s.end && s.end <= text.length) {
        nonOverlapping.push(s);
        lastEnd = s.end;
      }
    }

    const fragments = [];
    let currentIndex = 0;
    nonOverlapping.forEach((span, i) => {
      if (span.start > currentIndex) {
        fragments.push(text.substring(currentIndex, span.start));
      }
      fragments.push(
        <span 
          key={i} 
          className={`highlight-span ${span.type}`} 
          title={span.label}
        >
          {text.substring(span.start, span.end)}
        </span>
      );
      currentIndex = span.end;
    });

    if (currentIndex < text.length) {
      fragments.push(text.substring(currentIndex));
    }

    return fragments;
  }

  return (
    <div className="analyze-container">
      {/* Top Input Card */}
      <div className="pulse-card" style={{ marginBottom: '1.75rem' }}>
        <div className="pulse-card-header">
          <div>
            <h2 className="card-title">
              <Activity size={20} color="#06b6d4" /> Clinical Handover Structuring Engine
            </h2>
            <p className="card-subtitle">
              Ingest unstructured nursing shift report, execute clinical NER, and structure into ISBAR / 9-category formats
            </p>
          </div>

          {/* Sample report selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>Sample Report:</span>
            <select 
              className="pulse-select"
              value={chosenReportId}
              onChange={handleSelectChange}
            >
              {reportList.length > 0 ? (
                reportList.map(r => (
                  <option key={r.report_id} value={r.report_id}>
                    Report {r.report_id} ({r.word_count}w) - {r.filename}
                  </option>
                ))
              ) : (
                Array.from({ length: 101 }, (_, i) => (
                  <option key={i} value={i}>Report {i}</option>
                ))
              )}
            </select>
            <button 
              className="btn-secondary" 
              onClick={() => loadReportContent(chosenReportId)} 
              disabled={loading}
              title="Reload report text"
            >
              <FileText size={15} /> Load
            </button>
          </div>
        </div>

        {/* Clinical Quick Presets Bar */}
        <div style={{ marginBottom: '1rem' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Quick Clinical Cases:
          </span>
          <div className="preset-pills-bar">
            {clinicalPresets.map(preset => (
              <button
                key={preset.id}
                className={`preset-pill ${chosenReportId === preset.id ? 'active' : ''}`}
                onClick={() => {
                  setChosenReportId(preset.id);
                  if (onSelectReport) onSelectReport(preset.id);
                  loadReportContent(preset.id);
                }}
              >
                <span style={{ color: '#06b6d4', marginRight: '4px' }}>•</span>
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Text Area with Live Dictation Playback */}
        <div className="input-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <label className="input-label" style={{ margin: 0 }}>
              Enter or paste nursing handover narrative:
            </label>

            {/* Audio Handover Dictation Player */}
            <div className="audio-player-widget">
              <button 
                className="audio-play-btn" 
                onClick={toggleAudioPlayback}
                title={isPlayingAudio ? "Stop Dictation" : "Listen to Nursing Handover"}
              >
                {isPlayingAudio ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
              <div className={`sound-wave ${isPlayingAudio ? 'playing' : ''}`}>
                <div className="sound-bar" />
                <div className="sound-bar" />
                <div className="sound-bar" />
                <div className="sound-bar" />
                <div className="sound-bar" />
              </div>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#cbd5e1' }}>
                {isPlayingAudio ? "Dictating handover..." : "Listen to Handover"}
              </span>
            </div>
          </div>

          <textarea
            className="pulse-textarea"
            rows={5}
            placeholder="Paste unstructured nursing handover report text here, or choose a report from the dropdown above..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button 
              className="btn-primary" 
              onClick={handleAnalyze} 
              disabled={analyzing || !inputText.trim()}
              style={{ minWidth: '200px' }}
            >
              <Play size={16} fill="currentColor" /> {analyzing ? 'Executing Pipeline...' : 'Analyze Handover'}
            </button>
            <button 
              className="btn-secondary" 
              onClick={handleClear}
              disabled={analyzing || !inputText}
            >
              <RotateCcw size={15} /> Clear
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 600 }}>Inference Engine:</span>
            <select
              className="pulse-select"
              value={selectedEngine}
              onChange={(e) => setSelectedEngine(e.target.value)}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.78rem', minWidth: '220px' }}
              title="Select NLP extraction engine"
            >
              <option value="hybrid">Hybrid (Bio_ClinicalBERT + ConText Rules)</option>
              <option value="clinical_bert">Bio_ClinicalBERT (Pure Neural)</option>
              <option value="rule">Rule Baseline (Deterministic Regex/Dict)</option>
            </select>
            <span className="chip" style={{ 
              background: selectedEngine === 'rule' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(99, 102, 241, 0.15)', 
              borderColor: selectedEngine === 'rule' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(99, 102, 241, 0.4)', 
              color: selectedEngine === 'rule' ? '#fde68a' : '#a5b4fc',
              fontSize: '0.72rem'
            }}>
              {selectedEngine === 'rule' ? 'Deterministic Baseline' : 'Neural Token Classification'}
            </span>
          </div>
        </div>

        {/* Authentic Pipeline Execution Status Indicator */}
        {analyzing && (
          <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'rgba(6, 182, 212, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#38bdf8', fontSize: '0.85rem', fontWeight: 600 }}>
              <div className="pulse-anim" style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#06b6d4', flexShrink: 0 }} />
              <span>
                Executing <strong>{selectedEngine === 'rule' ? 'Deterministic Rule Baseline' : (selectedEngine === 'clinical_bert' ? 'Bio_ClinicalBERT Token Classifier' : 'Hybrid Pipeline (Bio_ClinicalBERT + ConText)')}</strong>: Normalizing clinical formatting, extracting entities, evaluating assertion contexts, and structuring handover...
              </span>
            </div>
          </div>
        )}

        {error && (
          <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'rgba(244, 63, 94, 0.1)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(244, 63, 94, 0.3)', color: '#fda4af', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} /> {error}
          </div>
        )}
      </div>

      {/* Analysis Results View */}
      {analysisResult && (
        <div className="results-container">
          {/* Authentic Hospital Patient EHR Header Banner */}
          <div className="patient-ehr-banner">
            <div className="patient-info-left">
              <div className="patient-avatar-circle">
                {getPatientInitials()}
              </div>

              <div className="patient-meta-grid">
                <div className="patient-meta-item">
                  <span className="patient-meta-label">Patient Name</span>
                  <span className="patient-meta-val">{getPatientField("Patient Name", "Unnamed Patient")}</span>
                </div>

                <div className="patient-meta-item">
                  <span className="patient-meta-label">Bed / Location</span>
                  <span className="patient-meta-val" style={{ color: '#38bdf8' }}>{getPatientField("Bed / Room", "Ward Bed")}</span>
                </div>

                <div className="patient-meta-item">
                  <span className="patient-meta-label">Age & Sex</span>
                  <span className="patient-meta-val">
                    {getPatientField("Age", "Age N/A")} • {getPatientField("Gender / Sex", "Sex N/A")}
                  </span>
                </div>

                <div className="patient-meta-item">
                  <span className="patient-meta-label">Attending Consultant</span>
                  <span className="patient-meta-val" style={{ color: '#a5b4fc' }}>{getPatientField("Attending Consultant", "Medical Team")}</span>
                </div>
              </div>
            </div>

            {/* Clinical Safety & Risk Badges */}
            <div className="risk-alerts-strip">
              {analysisResult.clinical_risks && analysisResult.clinical_risks.length > 0 ? (
                analysisResult.clinical_risks.map((risk, idx) => (
                  <span 
                    key={idx} 
                    className={`risk-badge ${risk.severity === 'High' ? 'high' : 'medium'}`}
                    title={risk.care_directive}
                  >
                    <ShieldAlert size={14} /> {risk.risk_type}
                  </span>
                ))
              ) : (
                <span className="chip" style={{ background: 'rgba(52, 211, 153, 0.1)', borderColor: '#34d399', color: '#a7f3d0' }}>
                  <CheckCircle size={13} /> Routine Ward Surveillance
                </span>
              )}
            </div>
          </div>

          {/* Executive Nursing Shift Brief */}
          {analysisResult.executive_summary && (
            <div className="executive-summary-banner">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem', color: '#38bdf8', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <Sparkles size={15} /> Executive Nursing Shift Brief
              </div>
              <p className="executive-summary-text">
                "{analysisResult.executive_summary}"
              </p>
            </div>
          )}

          {/* Highlighted Source Text Card */}
          <div className="pulse-card" style={{ marginBottom: '1.75rem' }}>
            <div className="pulse-card-header">
              <div>
                <h3 className="card-title">
                  <Tag size={18} color="#38bdf8" /> Highlighted Source Handover Text
                </h3>
                <p className="card-subtitle">
                  Visually verified clinical entities extracted from verbatim nursing report
                </p>
              </div>
              <span className="chip" style={{ background: 'rgba(56, 189, 248, 0.15)', borderColor: '#38bdf8', color: '#7dd3fc' }}>
                {analysisResult.word_count} Words
              </span>
            </div>

            {/* Legend */}
            <div className="legend-bar">
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginRight: '0.3rem' }}>LEGEND:</span>
              <span className="legend-chip" style={{ background: 'var(--cat-condition-bg)', border: '1px solid var(--cat-condition-border)', color: 'var(--cat-condition-text)' }}>
                Medical Condition
              </span>
              <span className="legend-chip" style={{ background: 'var(--cat-symptom-bg)', border: '1px solid var(--cat-symptom-border)', color: 'var(--cat-symptom-text)' }}>
                Symptom
              </span>
              <span className="legend-chip" style={{ background: 'var(--cat-medication-bg)', border: '1px solid var(--cat-medication-border)', color: 'var(--cat-medication-text)' }}>
                Medication
              </span>
              <span className="legend-chip" style={{ background: 'var(--cat-investigation-bg)', border: '1px solid var(--cat-investigation-border)', color: 'var(--cat-investigation-text)' }}>
                Investigation
              </span>
              <span className="legend-chip" style={{ background: 'var(--cat-treatment-bg)', border: '1px solid var(--cat-treatment-border)', color: 'var(--cat-treatment-text)' }}>
                Treatment
              </span>
              <span className="legend-chip" style={{ background: 'var(--cat-measurement-bg)', border: '1px solid var(--cat-measurement-border)', color: 'var(--cat-measurement-text)' }}>
                Measurement
              </span>
              <span className="legend-chip" style={{ background: 'var(--cat-abbr-bg)', border: '1px solid var(--cat-abbr-border)', color: 'var(--cat-abbr-text)' }}>
                Abbreviation
              </span>
            </div>

            <div className="highlight-container">
              {renderHighlightedText()}
            </div>
          </div>

          {/* Results Navigation Tabs */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            <button 
              className={`nav-tab ${activeTab === 'structured' ? 'active' : ''}`}
              onClick={() => setActiveTab('structured')}
            >
              <CheckCircle2 size={16} /> Structured Handover (ISBAR & 9 Categories)
            </button>
            <button 
              className={`nav-tab ${activeTab === 'entities' ? 'active' : ''}`}
              onClick={() => setActiveTab('entities')}
            >
              <Pill size={16} /> Clinical Entities ({
                (analysisResult.entities?.conditions?.length || 0) + 
                (analysisResult.entities?.medications?.length || 0) + 
                (analysisResult.entities?.investigations?.length || 0) +
                (analysisResult.entities?.measurements?.length || 0)
              })
            </button>
            <button 
              className={`nav-tab ${activeTab === 'events' ? 'active' : ''}`}
              onClick={() => setActiveTab('events')}
            >
              <Clock size={16} /> Clinical Events & Timeline ({analysisResult.events?.length || 0})
            </button>
            <button 
              className={`nav-tab ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => setActiveTab('tasks')}
            >
              <AlertCircle size={16} /> Pending Tasks ({analysisResult.pending_tasks?.length || 0})
            </button>
            <button 
              className={`nav-tab ${activeTab === 'preprocessing' ? 'active' : ''}`}
              onClick={() => setActiveTab('preprocessing')}
            >
              <RotateCcw size={16} /> Preprocessing Comparison
            </button>
            <button 
              className={`nav-tab ${activeTab === 'evidence' ? 'active' : ''}`}
              onClick={() => setActiveTab('evidence')}
            >
              <FileText size={16} /> Evidence Attribution ({analysisResult.evidence?.length || 0})
            </button>
          </div>

          {/* TAB 1: Structured Clinical Handover (ISBAR + 9 Categories) */}
          {activeTab === 'structured' && (
            <div className="handover-output-sheet">
              {/* Header with format switcher */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <Activity size={22} color="#06b6d4" /> STRUCTURED CLINICAL HANDOVER
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    Standardized clinical handover structured in accordance with authentic nursing handover protocols
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  {/* Format Switcher Pills */}
                  <div style={{ display: 'flex', background: 'rgba(0, 0, 0, 0.4)', borderRadius: 'var(--radius-full)', padding: '2px', border: '1px solid var(--border-subtle)' }}>
                    <button 
                      onClick={() => setHandoverFormat('isbar')}
                      style={{
                        padding: '0.35rem 0.9rem',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        borderRadius: 'var(--radius-full)',
                        border: 'none',
                        cursor: 'pointer',
                        background: handoverFormat === 'isbar' ? 'linear-gradient(135deg, #4f46e5, #06b6d4)' : 'transparent',
                        color: handoverFormat === 'isbar' ? '#ffffff' : '#94a3b8'
                      }}
                    >
                      ISBAR Format
                    </button>
                    <button 
                      onClick={() => setHandoverFormat('9categories')}
                      style={{
                        padding: '0.35rem 0.9rem',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        borderRadius: 'var(--radius-full)',
                        border: 'none',
                        cursor: 'pointer',
                        background: handoverFormat === '9categories' ? 'linear-gradient(135deg, #4f46e5, #06b6d4)' : 'transparent',
                        color: handoverFormat === '9categories' ? '#ffffff' : '#94a3b8'
                      }}
                    >
                      9 Standard Categories
                    </button>
                  </div>

                  <button 
                    className="btn-secondary" 
                    onClick={handleCopyStructured}
                    style={{ borderColor: 'rgba(99, 102, 241, 0.4)' }}
                  >
                    {copied ? <Check size={16} color="#10b981" /> : <Copy size={16} />}
                    {copied ? 'Copied to Clipboard!' : 'Copy Summary'}
                  </button>

                  <button 
                    className="btn-secondary" 
                    onClick={() => setShowPrintModal(true)}
                    title="Print / View Shift Handover Sheet"
                  >
                    <Printer size={16} /> Print Sheet
                  </button>
                </div>
              </div>

              {/* Sub-view: ISBAR Clinical Framework */}
              {handoverFormat === 'isbar' && analysisResult.isbar && (
                <div>
                  <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'rgba(99, 102, 241, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(99, 102, 241, 0.25)', fontSize: '0.8rem', color: '#c7d2fe' }}>
                    <strong>ISBAR Protocol:</strong> The internationally recognized communication framework (Identify, Situation, Background, Assessment, Recommendation) ensuring patient safety during nursing shift handovers.
                  </div>

                  <div className="isbar-grid">
                    {/* [I] Identify */}
                    <div className="isbar-card i">
                      <div className="isbar-card-title">
                        <span className="isbar-card-letter">I</span>
                        <span>IDENTIFY (Patient & Ward)</span>
                      </div>
                      <ul className="isbar-list">
                        {analysisResult.isbar.identify.map((it, idx) => (
                          <li key={idx} className="isbar-item">{it}</li>
                        ))}
                      </ul>
                    </div>

                    {/* [S] Situation */}
                    <div className="isbar-card s">
                      <div className="isbar-card-title">
                        <span className="isbar-card-letter">S</span>
                        <span>SITUATION (Acute Presentation)</span>
                      </div>
                      <ul className="isbar-list">
                        {analysisResult.isbar.situation.map((it, idx) => (
                          <li key={idx} className="isbar-item">{it}</li>
                        ))}
                      </ul>
                    </div>

                    {/* [B] Background */}
                    <div className="isbar-card b">
                      <div className="isbar-card-title">
                        <span className="isbar-card-letter">B</span>
                        <span>BACKGROUND (History & Comorbidities)</span>
                      </div>
                      <ul className="isbar-list">
                        {analysisResult.isbar.background.map((it, idx) => (
                          <li key={idx} className="isbar-item">{it}</li>
                        ))}
                      </ul>
                    </div>

                    {/* [A] Assessment */}
                    <div className="isbar-card a">
                      <div className="isbar-card-title">
                        <span className="isbar-card-letter">A</span>
                        <span>ASSESSMENT (Vitals & Observations)</span>
                      </div>
                      <ul className="isbar-list">
                        {analysisResult.isbar.assessment.map((it, idx) => (
                          <li key={idx} className="isbar-item">{it}</li>
                        ))}
                      </ul>
                    </div>

                    {/* [R] Recommendation */}
                    <div className="isbar-card r" style={{ gridColumn: '1 / -1' }}>
                      <div className="isbar-card-title">
                        <span className="isbar-card-letter">R</span>
                        <span>RECOMMENDATION (Shift Tasks & Critical Actions)</span>
                      </div>
                      <ul className="isbar-list">
                        {analysisResult.isbar.recommendation.map((it, idx) => (
                          <li key={idx} className="isbar-item" style={{ color: '#fecdd3', fontWeight: 500 }}>
                            {it}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Sub-view: Standard 9 Categories */}
              {handoverFormat === '9categories' && (
                <div>
                  {/* 1. Patient Information */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title"><User size={16} /> 1. PATIENT INFORMATION</h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.patient_information.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 2. Current Condition */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title"><Activity size={16} /> 2. CURRENT CONDITION</h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.current_condition.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 3. Medical History */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title"><FileText size={16} /> 3. MEDICAL HISTORY</h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.medical_history.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 4. Medications / Treatment */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title"><Pill size={16} /> 4. MEDICATIONS / TREATMENT</h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.medications_treatment.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 5. Investigations */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title"><Stethoscope size={16} /> 5. INVESTIGATIONS</h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.investigations.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 6. Clinical Events */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title"><Calendar size={16} /> 6. CLINICAL EVENTS</h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.clinical_events.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 7. Temporal Information */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title"><Clock size={16} /> 7. TEMPORAL INFORMATION</h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.temporal_information.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 8. Pending Tasks */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title" style={{ color: '#f43f5e' }}>
                      <AlertCircle size={16} /> 8. PENDING TASKS
                    </h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.pending_tasks.map((item, i) => (
                        <li key={i} className="handover-bullet-item" style={{ color: '#fecdd3' }}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 9. Follow-up */}
                  <div className="handover-category-block">
                    <h4 className="handover-category-title" style={{ color: '#34d399' }}>
                      <CheckCircle2 size={16} /> 9. FOLLOW-UP
                    </h4>
                    <ul className="handover-bullet-list">
                      {analysisResult.structured_handover.follow_up.map((item, i) => (
                        <li key={i} className="handover-bullet-item">{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Extracted Clinical Entities */}
          {activeTab === 'entities' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Demographics Card */}
              <div className="pulse-card">
                <h3 className="card-title" style={{ marginBottom: '1rem', color: '#7dd3fc' }}>
                  <User size={18} /> Patient Demographics & Allocation
                </h3>
                {analysisResult.entities?.patient_information?.length > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                    {analysisResult.entities.patient_information.map((p, i) => (
                      <div key={i} style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>{p.field}</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginTop: '0.2rem' }}>{p.value}</div>
                        <div style={{ fontSize: '0.72rem', color: '#38bdf8', marginTop: '0.25rem' }}>{p.confidence}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Not identified in this report.</p>
                )}
              </div>

              {/* Conditions & Symptoms */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                <div className="pulse-card">
                  <h3 className="card-title" style={{ marginBottom: '1rem', color: 'var(--cat-condition-border)' }}>
                    Medical Conditions & History
                  </h3>
                  {analysisResult.entities?.conditions?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {analysisResult.entities.conditions.map((c, i) => (
                        <div key={i} style={{ padding: '0.6rem 0.8rem', background: 'var(--cat-condition-bg)', border: '1px solid var(--cat-condition-border)', borderRadius: 'var(--radius-sm)' }}>
                          <div style={{ fontWeight: 600, color: 'var(--cat-condition-text)' }}>{c.normalized}</div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Matched: "{c.text}" • {c.confidence}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Not identified in this report.</p>
                  )}
                </div>

                <div className="pulse-card">
                  <h3 className="card-title" style={{ marginBottom: '1rem', color: 'var(--cat-symptom-border)' }}>
                    Reported Symptoms
                  </h3>
                  {analysisResult.entities?.symptoms?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {analysisResult.entities.symptoms.map((s, i) => (
                        <div key={i} style={{ padding: '0.6rem 0.8rem', background: 'var(--cat-symptom-bg)', border: '1px solid var(--cat-symptom-border)', borderRadius: 'var(--radius-sm)' }}>
                          <div style={{ fontWeight: 600, color: 'var(--cat-symptom-text)' }}>
                            {s.normalized} {s.occurrences > 1 && `(${s.occurrences} mentions)`}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Matched: "{s.text}" • {s.confidence}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Not identified in this report.</p>
                  )}
                </div>
              </div>

              {/* Medications, Investigations, Treatments */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                <div className="pulse-card">
                  <h3 className="card-title" style={{ marginBottom: '1rem', color: 'var(--cat-medication-border)' }}>
                    Medications & Dosages
                  </h3>
                  {analysisResult.entities?.medications?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {analysisResult.entities.medications.map((m, i) => (
                        <div key={i} style={{ padding: '0.6rem 0.8rem', background: 'var(--cat-medication-bg)', border: '1px solid var(--cat-medication-border)', borderRadius: 'var(--radius-sm)' }}>
                          <div style={{ fontWeight: 600, color: 'var(--cat-medication-text)' }}>{m.normalized}</div>
                          <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                            Dose: <strong>{m.dosage}</strong> | Route: <strong>{m.route}</strong> | Freq: <strong>{m.frequency}</strong>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Not identified in this report.</p>
                  )}
                </div>

                <div className="pulse-card">
                  <h3 className="card-title" style={{ marginBottom: '1rem', color: 'var(--cat-investigation-border)' }}>
                    Diagnostic Investigations
                  </h3>
                  {analysisResult.entities?.investigations?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {analysisResult.entities.investigations.map((inv, i) => (
                        <div key={i} style={{ padding: '0.6rem 0.8rem', background: 'var(--cat-investigation-bg)', border: '1px solid var(--cat-investigation-border)', borderRadius: 'var(--radius-sm)' }}>
                          <div style={{ fontWeight: 600, color: 'var(--cat-investigation-text)' }}>{inv.normalized}</div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Matched: "{inv.text}"</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Not identified in this report.</p>
                  )}
                </div>

                <div className="pulse-card">
                  <h3 className="card-title" style={{ marginBottom: '1rem', color: 'var(--cat-measurement-border)' }}>
                    Vital Signs & Observations
                  </h3>
                  {analysisResult.entities?.measurements?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {analysisResult.entities.measurements.map((ms, i) => (
                        <div key={i} style={{ padding: '0.6rem 0.8rem', background: 'var(--cat-measurement-bg)', border: '1px solid var(--cat-measurement-border)', borderRadius: 'var(--radius-sm)' }}>
                          <div style={{ fontWeight: 600, color: 'var(--cat-measurement-text)' }}>{ms.type}</div>
                          <div style={{ fontSize: '0.85rem', color: '#ffffff' }}>{ms.text}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Not identified in this report.</p>
                  )}
                </div>
              </div>

              {/* Abbreviations Glossary */}
              <div className="pulse-card">
                <h3 className="card-title" style={{ marginBottom: '1rem', color: 'var(--cat-abbr-border)' }}>
                  Clinical Abbreviations Discovered in Handover
                </h3>
                {analysisResult.entities?.abbreviations?.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
                    {analysisResult.entities.abbreviations.map((abbr, i) => (
                      <span key={i} className="chip" style={{ background: 'var(--cat-abbr-bg)', borderColor: 'var(--cat-abbr-border)', color: 'var(--cat-abbr-text)', padding: '0.4rem 0.8rem' }}>
                        <strong>{abbr.abbreviation}</strong>: {abbr.expansion}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No clinical abbreviations detected in this report.</p>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: Clinical Events & Timeline */}
          {activeTab === 'events' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div className="pulse-card">
                <h3 className="card-title" style={{ marginBottom: '1rem' }}>
                  <Clock size={18} color="#06b6d4" /> Extracted Clinical Events & Actions
                </h3>
                {analysisResult.events?.length > 0 ? (
                  <table className="pulse-table">
                    <thead>
                      <tr>
                        <th>Clinical Action</th>
                        <th>Classification</th>
                        <th>Time / Anchor</th>
                        <th>Source Sentence Evidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysisResult.events.map((ev, i) => (
                        <tr key={i}>
                          <td style={{ fontWeight: 600, color: '#ffffff' }}>{ev.event}</td>
                          <td><span className="chip" style={{ fontSize: '0.7rem' }}>{ev.type}</span></td>
                          <td style={{ color: '#38bdf8' }}>{ev.time}</td>
                          <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>"{ev.source_sentence}"</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p style={{ color: '#94a3b8' }}>No discrete clinical events identified.</p>
                )}
              </div>

              <div className="pulse-card">
                <h3 className="card-title" style={{ marginBottom: '1rem' }}>
                  <Calendar size={18} color="#6366f1" /> Extracted Temporal Expressions
                </h3>
                {analysisResult.temporal_information?.length > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                    {analysisResult.temporal_information.map((t, i) => (
                      <div key={i} style={{ background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.25)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontWeight: 700, color: '#a5b4fc', fontSize: '1rem' }}>"{t.expression}"</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>Type: {t.type}</div>
                        <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.4rem' }}>
                          Associated Event: <strong>{t.associated_event}</strong>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: '#94a3b8' }}>No temporal information identified.</p>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: Pending Tasks & Follow-up */}
          {activeTab === 'tasks' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              <div className="pulse-card">
                <h3 className="card-title" style={{ marginBottom: '1rem', color: '#f43f5e' }}>
                  <AlertCircle size={18} /> Outstanding Pending Tasks
                </h3>
                {analysisResult.pending_tasks?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {analysisResult.pending_tasks.map((task, i) => (
                      <div key={i} style={{ background: 'rgba(244, 63, 94, 0.08)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                          <span className={task.priority === 'High' ? 'chip chip-priority-high' : 'chip chip-priority-medium'}>
                            {task.priority} Priority
                          </span>
                          <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{task.type}</span>
                        </div>
                        <div style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.92rem' }}>{task.task}</div>
                        <div style={{ fontSize: '0.78rem', color: '#fda4af', marginTop: '0.4rem' }}>
                          Source: "{task.source_sentence}"
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: '#94a3b8' }}>No outstanding pending tasks recorded.</p>
                )}
              </div>

              <div className="pulse-card">
                <h3 className="card-title" style={{ marginBottom: '1rem', color: '#34d399' }}>
                  <CheckCircle2 size={18} /> Future Follow-Up Requirements
                </h3>
                {analysisResult.follow_up?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {analysisResult.follow_up.map((fu, i) => (
                      <div key={i} style={{ background: 'rgba(52, 211, 153, 0.08)', border: '1px solid rgba(52, 211, 153, 0.3)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>{fu.type}</div>
                        <div style={{ fontWeight: 600, color: '#ffffff', marginTop: '0.2rem', fontSize: '0.92rem' }}>{fu.action}</div>
                        <div style={{ fontSize: '0.78rem', color: '#a7f3d0', marginTop: '0.4rem' }}>
                          Source: "{fu.source_sentence}"
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: '#94a3b8' }}>No specific follow-up actions recorded.</p>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: Preprocessing Comparison */}
          {activeTab === 'preprocessing' && (
            <div className="pulse-card">
              <div className="pulse-card-header">
                <div>
                  <h3 className="card-title">
                    <RotateCcw size={18} color="#06b6d4" /> Preprocessing Comparison
                  </h3>
                  <p className="card-subtitle">
                    "Clean the formatting, preserve the clinical meaning" (Preserves @, +, _, numbers, units, and clinical terminology)
                  </p>
                </div>
              </div>

              <div className="comparison-grid">
                <div className="comparison-box">
                  <div className="comparison-header">
                    <span className="comparison-title" style={{ color: '#94a3b8' }}>RAW NURSING TEXT (PRESERVED VERBATIM)</span>
                    <span className="chip" style={{ fontSize: '0.7rem' }}>{analysisResult.raw_text.length} Chars</span>
                  </div>
                  <div className="comparison-content">
                    {analysisResult.raw_text}
                  </div>
                </div>

                <div className="comparison-box" style={{ borderColor: 'rgba(6, 182, 212, 0.3)' }}>
                  <div className="comparison-header">
                    <span className="comparison-title" style={{ color: '#38bdf8' }}>PREPROCESSED CLINICAL TEXT</span>
                    <span className="chip" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#67e8f9', fontSize: '0.7rem' }}>
                      {analysisResult.preprocessed_text.length} Chars
                    </span>
                  </div>
                  <div className="comparison-content">
                    {analysisResult.preprocessed_text}
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '1.5rem' }}>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '0.5rem' }}>
                  NORMALIZATION AUDIT LOG ({analysisResult.changes_made?.length || 0} checks)
                </h4>
                <div className="changes-list">
                  {(analysisResult.changes_made || []).map((change, i) => (
                    <div key={i} className="change-item">
                      <Check size={14} /> {change}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: Evidence Attribution */}
          {activeTab === 'evidence' && (
            <div className="pulse-card">
              <h3 className="card-title" style={{ marginBottom: '1rem' }}>
                <FileText size={18} color="#6366f1" /> Source Text Evidence Attribution
              </h3>
              <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
                Every extracted clinical item is explicitly attributed to its exact source sentence in the original handover.
              </p>

              <table className="pulse-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Extracted Clinical Entity</th>
                    <th>Verbatim Source Sentence Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {(analysisResult.evidence || []).map((ev, i) => (
                    <tr key={i}>
                      <td><span className="chip" style={{ fontSize: '0.72rem' }}>{ev.category}</span></td>
                      <td style={{ fontWeight: 600, color: '#ffffff' }}>{ev.entity}</td>
                      <td style={{ color: '#cbd5e1', fontStyle: 'italic' }}>"{ev.source_sentence}"</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Official Hospital Handover Printable Sheet Modal */}
      {showPrintModal && analysisResult && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 2000,
          padding: '1.5rem'
        }}>
          <div style={{
            maxWidth: '850px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            background: '#ffffff',
            color: '#0f172a',
            borderRadius: 'var(--radius-md)',
            padding: '2rem',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #0f172a', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
              <div>
                <h2 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#0f172a', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  CLINICAL NURSING SHIFT HANDOVER SHEET
                </h2>
                <div style={{ fontSize: '0.75rem', color: '#475569' }}>
                  Hospital Inpatient Ward Handover • PULSE Electronic Handover System
                </div>
              </div>
              <button 
                onClick={() => setShowPrintModal(false)}
                style={{ background: '#e2e8f0', border: 'none', borderRadius: '50%', width: '32px', height: '32px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <X size={18} color="#0f172a" />
              </button>
            </div>

            {/* Patient Header Box */}
            <div style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '1rem', marginBottom: '1.25rem', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', fontSize: '0.85rem' }}>
              <div><strong>Patient:</strong> {getPatientField("Patient Name", "Unnamed")}</div>
              <div><strong>Bed:</strong> {getPatientField("Bed / Room", "Ward Bed")}</div>
              <div><strong>Age/Sex:</strong> {getPatientField("Age", "N/A")} / {getPatientField("Gender / Sex", "N/A")}</div>
              <div><strong>Consultant:</strong> {getPatientField("Attending Consultant", "Medical Team")}</div>
            </div>

            {/* Brief */}
            <div style={{ marginBottom: '1.25rem', padding: '0.75rem', background: '#e0f2fe', borderRadius: '6px', borderLeft: '4px solid #0284c7', fontSize: '0.85rem' }}>
              <strong>Clinical Executive Summary:</strong> {analysisResult.executive_summary}
            </div>

            {/* ISBAR Sections in Print Sheet */}
            {analysisResult.isbar && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', fontSize: '0.85rem' }}>
                <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
                  <strong style={{ color: '#0369a1' }}>[S] SITUATION:</strong>
                  <ul style={{ paddingLeft: '1.2rem', marginTop: '0.25rem' }}>
                    {analysisResult.isbar.situation.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>

                <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
                  <strong style={{ color: '#6d28d9' }}>[B] BACKGROUND:</strong>
                  <ul style={{ paddingLeft: '1.2rem', marginTop: '0.25rem' }}>
                    {analysisResult.isbar.background.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>

                <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
                  <strong style={{ color: '#047857' }}>[A] ASSESSMENT:</strong>
                  <ul style={{ paddingLeft: '1.2rem', marginTop: '0.25rem' }}>
                    {analysisResult.isbar.assessment.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>

                <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
                  <strong style={{ color: '#b91c1c' }}>[R] RECOMMENDATION & PENDING TASKS:</strong>
                  <ul style={{ paddingLeft: '1.2rem', marginTop: '0.25rem' }}>
                    {analysisResult.isbar.recommendation.map((s, i) => <li key={i} style={{ fontWeight: 600, color: '#991b1b' }}>{s}</li>)}
                  </ul>
                </div>
              </div>
            )}

            {/* Sign-off signatures */}
            <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed #94a3b8', paddingTop: '1rem', fontSize: '0.8rem', color: '#475569' }}>
              <div>Outgoing Nurse Signature: _______________________</div>
              <div>Incoming Nurse Signature: _______________________</div>
              <div>Shift Date/Time: ___________________</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button 
                onClick={() => window.print()}
                style={{ background: '#0f172a', color: '#ffffff', border: 'none', padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: 600, cursor: 'pointer' }}
              >
                Print Document
              </button>
              <button 
                onClick={() => setShowPrintModal(false)}
                style={{ background: '#e2e8f0', color: '#0f172a', border: 'none', padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: 600, cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
