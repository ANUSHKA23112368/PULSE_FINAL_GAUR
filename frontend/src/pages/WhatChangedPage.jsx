import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  TrendingDown,
  FileCheck2,
  Clock,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Layers,
  RefreshCw,
  FileText
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import {
  fetchPatientNotes,
  createPatientNote,
  processPatientNote,
  comparePatientHandovers
} from '../services/api';

export function WhatChangedPage({ selectedPatient, onSwitchPatient, onNavigate, allPatients, onSelectPatient }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [priorNoteId, setPriorNoteId] = useState('');
  const [currentNoteId, setCurrentNoteId] = useState('');
  const [seedingDemo, setSeedingDemo] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  useEffect(() => {
    if (selectedPatient) {
      loadNotesAndCompare();
    }
  }, [selectedPatient]);

  async function loadNotesAndCompare() {
    if (!selectedPatient) return;
    setLoading(true);
    setStatusMessage(null);
    try {
      const data = await fetchPatientNotes(selectedPatient.display_id || selectedPatient.id);
      const patientNotes = data.notes || [];
      const chrono = [...patientNotes].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      setNotes(chrono);

      if (chrono.length >= 2) {
        const prior = chrono[chrono.length - 2];
        const current = chrono[chrono.length - 1];
        setPriorNoteId(String(prior.id));
        setCurrentNoteId(String(current.id));
        await runComparison(prior.id, current.id);
      } else {
        setComparison(null);
      }
    } catch (err) {
      console.warn("Could not load handover notes:", err);
    } finally {
      setLoading(false);
    }
  }

  async function runComparison(pId, cId) {
    if (!pId || !cId || !selectedPatient) return;
    setComparing(true);
    try {
      const result = await comparePatientHandovers(
        selectedPatient.display_id || selectedPatient.id,
        pId,
        cId
      );
      setComparison(result);
    } catch (err) {
      console.error("Comparison failed:", err);
      setStatusMessage({ type: 'error', text: 'Failed to compute consecutive shift differences.' });
    } finally {
      setComparing(false);
    }
  }

  async function handleLoadConsecutiveDemo() {
    if (!selectedPatient) return;
    setSeedingDemo(true);
    setStatusMessage(null);
    try {
      const pKey = selectedPatient.display_id || selectedPatient.id;

      // Shift 1 Morning Note
      const note1Text = "Rahul, 55 years old, admitted with fever and cough. Temperature was 102°F in the morning. Paracetamol given at 8 AM. Blood test report is pending. Patient's temperature should be checked again at 12 PM.";
      const n1 = await createPatientNote(pKey, note1Text, "Morning Shift Nurse (8:00 AM Handover)");
      await processPatientNote(pKey, n1.id);

      // Shift 2 Evening Note
      const note2Text = "At 12 PM, Rahul's temperature was 100°F. Blood report received. Doctor reviewed the report and advised continued monitoring. Patient's cough persists.";
      const n2 = await createPatientNote(pKey, note2Text, "Evening Shift Nurse (12:30 PM Handover)");
      await processPatientNote(pKey, n2.id);

      setStatusMessage({ type: 'success', text: 'Consecutive handover shift notes saved and processed successfully!' });
      await loadNotesAndCompare();
    } catch (err) {
      console.error("Demo seeding error:", err);
      setStatusMessage({ type: 'error', text: 'Failed to seed consecutive demonstration handovers.' });
    } finally {
      setSeedingDemo(false);
    }
  }

  return (
    <div className="page-container">
      {/* Patient Banner */}
      <PatientBanner
        patient={selectedPatient}
        onSwitchPatient={onSwitchPatient}
        allPatients={allPatients}
        onSelectPatient={onSelectPatient}
        onNavigate={onNavigate}
      />

      {/* Page Header */}
      <div className="section-header-row">
        <div>
          <h2 className="page-heading">
            Shift-to-Shift Delta: What Changed?
          </h2>
          <p className="page-subheading">
            Compares consecutive clinical handovers for <strong>{selectedPatient?.name || 'the patient'}</strong> to detect physiological deltas, lab transitions, completed tasks, and ongoing symptoms.
          </p>
        </div>

        <div className="header-actions-group">
          <button
            onClick={handleLoadConsecutiveDemo}
            disabled={seedingDemo}
            className="btn btn-outline"
          >
            <Sparkles size={14} className="text-emerald" />
            <span>{seedingDemo ? 'Seeding Multi-Shift...' : 'Load Rahul 2-Shift Demo'}</span>
          </button>

          <button
            onClick={loadNotesAndCompare}
            disabled={loading || comparing}
            className="btn btn-outline"
          >
            <RefreshCw size={14} className={loading || comparing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className={`feedback-alert feedback-${statusMessage.type}`}>
          <AlertCircle size={16} />
          <span>{statusMessage.text}</span>
          <button className="feedback-close" onClick={() => setStatusMessage(null)}>×</button>
        </div>
      )}

      {/* Shift Note Selectors */}
      {notes.length >= 2 && (
        <div className="hospital-card shift-selector-card">
          <div className="shift-selector-row">
            <span className="selector-title">Compare Handovers:</span>

            {/* Prior Shift Selector */}
            <div className="selector-group">
              <span className="selector-label">Prior Shift:</span>
              <select
                value={priorNoteId}
                onChange={(e) => {
                  setPriorNoteId(e.target.value);
                  runComparison(e.target.value, currentNoteId);
                }}
                className="form-input selector-input"
              >
                {notes.map(n => (
                  <option key={`prior-${n.id}`} value={n.id}>
                    Note #{n.id} ({n.author_identifier?.split(' ')[0] || 'Clinician'}) — {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </option>
                ))}
              </select>
            </div>

            <ArrowRight size={16} className="text-muted" />

            {/* Current Shift Selector */}
            <div className="selector-group">
              <span className="selector-label">Current Shift:</span>
              <select
                value={currentNoteId}
                onChange={(e) => {
                  setCurrentNoteId(e.target.value);
                  runComparison(priorNoteId, e.target.value);
                }}
                className="form-input selector-input"
              >
                {notes.map(n => (
                  <option key={`current-${n.id}`} value={n.id}>
                    Note #{n.id} ({n.author_identifier?.split(' ')[0] || 'Clinician'}) — {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <span className="notes-counter">
            Total notes logged: <strong>{notes.length}</strong>
          </span>
        </div>
      )}

      {/* Main Comparison Body */}
      {loading ? (
        <div className="hospital-card loading-state-card">
          <RefreshCw size={24} className="animate-spin text-primary" />
          <span>Calculating consecutive shift differences...</span>
        </div>
      ) : notes.length < 2 ? (
        <div className="hospital-card empty-state-card">
          <GitCompare size={36} className="text-muted" />
          <h3>Consecutive Handover Tracking Requires at Least 2 Notes</h3>
          <p>
            PULSE compares consecutive clinical shifts (e.g. Morning vs Evening) to identify what changed:
            temperature observations, diagnostic test report statuses, scheduled task progression, and persistent symptoms.
          </p>
          <div className="empty-state-buttons">
            <button
              onClick={handleLoadConsecutiveDemo}
              disabled={seedingDemo}
              className="btn btn-primary"
            >
              <Sparkles size={15} />
              <span>{seedingDemo ? 'Creating Demo Notes...' : 'Load Rahul 2-Shift Demo'}</span>
            </button>
            <button
              onClick={() => onNavigate && onNavigate('notes')}
              className="btn btn-outline"
            >
              <FileText size={15} />
              <span>Enter Handover Note</span>
            </button>
          </div>
        </div>
      ) : comparison ? (
        <div className="comparison-results-stack">
          {/* Executive Delta Banner */}
          <div className="hospital-card delta-synthesis-card">
            <div className="delta-header">
              <Layers size={16} className="text-primary" />
              <strong>Consecutive Shift Delta Synthesis:</strong>
              <span className="delta-range-pill">
                Note #{comparison.prior_note_id} → Note #{comparison.current_note_id}
              </span>
            </div>
            <p className="delta-narrative">
              {comparison.summary_narrative}
            </p>
          </div>

          {/* Observations Changed */}
          <div className="hospital-card delta-section-card">
            <div className="delta-card-header">
              <h3 className="section-heading text-primary">
                <TrendingDown size={18} />
                <span>Changed Clinical Observations</span>
              </h3>
              <span className="count-pill">
                {comparison.observations_changed?.length || 0} change(s)
              </span>
            </div>

            {comparison.observations_changed?.length === 0 ? (
              <span className="empty-delta-text">No physiological observations changed between shifts.</span>
            ) : (
              <div className="delta-items-grid">
                {comparison.observations_changed.map((obs, idx) => (
                  <div key={idx} className="delta-item-card">
                    <div className="item-title-row">
                      <strong className="param-name">{obs.parameter}</strong>
                      <span className="pill-mini pill-changed">Changed</span>
                    </div>
                    <div className="value-transition-row">
                      <span className="prior-val">Prior: {obs.prior_value}</span>
                      <ArrowRight size={14} className="text-primary" />
                      <span className="current-val">Current: {obs.current_value}</span>
                    </div>
                    {obs.clinical_significance && (
                      <div className="significance-note">{obs.clinical_significance}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* New Events or Orders */}
          <div className="hospital-card delta-section-card">
            <div className="delta-card-header">
              <h3 className="section-heading text-emerald">
                <FileCheck2 size={18} />
                <span>New Events & Diagnostic Updates</span>
              </h3>
              <span className="count-pill">
                {comparison.new_events?.length || 0} new item(s)
              </span>
            </div>

            {comparison.new_events?.length === 0 ? (
              <span className="empty-delta-text">No new clinical events reported during this shift.</span>
            ) : (
              <div className="delta-events-list">
                {comparison.new_events.map((ev, idx) => (
                  <div key={idx} className="delta-event-pill">
                    <CheckCircle2 size={15} className="text-emerald" />
                    <span>{typeof ev === 'string' ? ev : ev.description || ev.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tasks & Directives Progression */}
          <div className="hospital-card delta-section-card">
            <div className="delta-card-header">
              <h3 className="section-heading text-amber">
                <Clock size={18} />
                <span>Task Progression & Follow-ups</span>
              </h3>
              <span className="count-pill">
                {comparison.task_status_updates?.length || 0} progression(s)
              </span>
            </div>

            {comparison.task_status_updates?.length === 0 ? (
              <span className="empty-delta-text">No task updates detected between these handovers.</span>
            ) : (
              <div className="delta-tasks-list">
                {comparison.task_status_updates.map((tsk, idx) => (
                  <div key={idx} className="delta-task-row">
                    <div className="task-desc">
                      <strong>{tsk.task}</strong>
                      <span className="task-evidence">{tsk.evidence}</span>
                    </div>
                    <span className={`status-pill status-${(tsk.new_status || 'Pending').toLowerCase().replace(' ', '-')}`}>
                      {tsk.new_status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default WhatChangedPage;
