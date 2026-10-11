import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  TrendingDown,
  TrendingUp,
  FileCheck2,
  Clock,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Layers,
  RefreshCw,
  FileText,
  UserCheck
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import {
  fetchPatientNotes,
  createPatientNote,
  processPatientNote,
  comparePatientHandovers
} from '../services/api';

export function WhatChangedPage({ selectedPatient, onSwitchPatient, onNavigate }) {
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
      // Chronological sort
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
    if (!pId || !cId || String(pId) === String(cId)) return;
    setComparing(true);
    try {
      const result = await comparePatientHandovers(
        selectedPatient.display_id || selectedPatient.id,
        Number(pId),
        Number(cId)
      );
      setComparison(result);
    } catch (err) {
      console.warn("Handover comparison error:", err);
      setStatusMessage({ type: 'error', text: 'Failed to run consecutive handover comparison.' });
    } finally {
      setComparing(false);
    }
  }

  async function handleLoadConsecutiveDemo() {
    if (!selectedPatient) return;
    setSeedingDemo(true);
    setStatusMessage({ type: 'info', text: 'Seeding consecutive shift notes (Morning Shift 1 & Evening Shift 2)...' });
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
      {/* Patient Header Banner */}
      <PatientBanner
        patient={selectedPatient}
        onSwitchPatient={onSwitchPatient}
        activeTab="changes"
        onNavigate={onNavigate}
      />

      {/* Page Header */}
      <div className="section-header" style={{ marginTop: '1rem', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 600, color: '#1e293b', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <GitCompare size={22} color="#0284c7" />
              What Changed? — Consecutive Handover Update Tracking
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#64748b' }}>
              Compares consecutive clinical handovers for <strong>{selectedPatient?.name || 'the patient'}</strong> to detect clinical observation deltas, lab transitions, task progressions, and ongoing conditions.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              onClick={handleLoadConsecutiveDemo}
              disabled={seedingDemo}
              className="btn-secondary"
              style={{
                fontSize: '0.8125rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                background: '#f0fdf4',
                color: '#15803d',
                borderColor: '#bbf7d0',
                fontWeight: 600
              }}
            >
              <Sparkles size={14} color="#15803d" />
              {seedingDemo ? 'Loading Demo Notes...' : 'Load Rahul 2-Shift Demo'}
            </button>

            <button
              onClick={loadNotesAndCompare}
              disabled={loading || comparing}
              className="btn-secondary"
              style={{ fontSize: '0.8125rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <RefreshCw size={14} className={loading || comparing ? 'spin' : ''} />
              Refresh Comparison
            </button>
          </div>
        </div>
      </div>

      {statusMessage && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '6px',
          marginBottom: '1rem',
          fontSize: '0.875rem',
          background: statusMessage.type === 'success' ? '#f0fdf4' : statusMessage.type === 'error' ? '#fef2f2' : '#f0f9ff',
          color: statusMessage.type === 'success' ? '#166534' : statusMessage.type === 'error' ? '#991b1b' : '#0369a1',
          border: `1px solid ${statusMessage.type === 'success' ? '#bbf7d0' : statusMessage.type === 'error' ? '#fecaca' : '#bae6fd'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={16} />
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Handover Note Selector Controls */}
      {notes.length >= 2 && (
        <div style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '0.875rem 1.25rem',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#475569' }}>
              Compare Handovers:
            </span>

            {/* Prior Note Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Prior Shift:</span>
              <select
                value={priorNoteId}
                onChange={(e) => {
                  setPriorNoteId(e.target.value);
                  runComparison(e.target.value, currentNoteId);
                }}
                style={{
                  fontSize: '0.8125rem',
                  padding: '0.35rem 0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  background: '#f8fafc',
                  color: '#1e293b'
                }}
              >
                {notes.map(n => (
                  <option key={`prior-${n.id}`} value={n.id}>
                    Note #{n.id} ({n.author_identifier?.split(' ')[0] || 'Clinician'}) — {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </option>
                ))}
              </select>
            </div>

            <ArrowRight size={16} color="#94a3b8" />

            {/* Current Note Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Current Shift:</span>
              <select
                value={currentNoteId}
                onChange={(e) => {
                  setCurrentNoteId(e.target.value);
                  runComparison(priorNoteId, e.target.value);
                }}
                style={{
                  fontSize: '0.8125rem',
                  padding: '0.35rem 0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  background: '#f8fafc',
                  color: '#1e293b'
                }}
              >
                {notes.map(n => (
                  <option key={`current-${n.id}`} value={n.id}>
                    Note #{n.id} ({n.author_identifier?.split(' ')[0] || 'Clinician'}) — {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            <span>Notes logged for this patient: <strong>{notes.length}</strong></span>
          </div>
        </div>
      )}

      {/* Main Viewport Content */}
      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem' }} />
          <div>Loading handover history...</div>
        </div>
      ) : notes.length < 2 ? (
        /* Empty State */
        <div style={{
          background: '#ffffff',
          border: '1px dashed #cbd5e1',
          borderRadius: '8px',
          padding: '2.5rem 1.5rem',
          textAlign: 'center',
          maxWidth: '680px',
          margin: '1.5rem auto'
        }}>
          <GitCompare size={36} color="#94a3b8" style={{ margin: '0 auto 0.75rem' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.5rem' }}>
            Consecutive Handover Tracking Needs at Least 2 Notes
          </h3>
          <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.5, marginBottom: '1.25rem' }}>
            PULSE compares consecutive clinical shifts (e.g. Morning vs Evening) to identify what changed:
            temperature observations, diagnostic test report statuses, scheduled task progression, and persistent symptoms.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem' }}>
            <button
              onClick={handleLoadConsecutiveDemo}
              disabled={seedingDemo}
              className="btn-primary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <Sparkles size={15} />
              {seedingDemo ? 'Creating Demo Notes...' : 'Load Rahul 2-Shift Demonstration Notes'}
            </button>
            <button
              onClick={() => onNavigate && onNavigate('notes')}
              className="btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <FileText size={15} />
              Enter Handover Note
            </button>
          </div>
        </div>
      ) : comparison ? (
        /* Active Comparison Cards */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Executive Delta Synthesis Banner */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderLeft: '4px solid #0284c7',
            borderRadius: '6px',
            padding: '1rem 1.25rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <Layers size={16} color="#0284c7" />
              <strong style={{ fontSize: '0.875rem', color: '#0f172a' }}>Consecutive Shift Delta Synthesis:</strong>
              <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: 'auto' }}>
                Note #{comparison.prior_note_id} → Note #{comparison.current_note_id}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#334155', lineHeight: 1.5 }}>
              {comparison.summary_narrative}
            </p>
          </div>

          {/* 1. Changed Clinical Observations */}
          <div className="card" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.875rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingDown size={18} color="#0284c7" />
                Changed Clinical Observations
              </h3>
              <span style={{ fontSize: '0.75rem', background: '#f1f5f9', padding: '0.2rem 0.5rem', borderRadius: '4px', color: '#475569' }}>
                {comparison.observations_changed?.length || 0} documented change(s)
              </span>
            </div>

            {comparison.observations_changed?.length === 0 ? (
              <div style={{ fontSize: '0.8125rem', color: '#64748b', fontStyle: 'italic' }}>
                No significant numeric observation or vital changes identified between these consecutive handovers.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {comparison.observations_changed.map((obs, idx) => (
                  <div key={idx} style={{
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    padding: '1rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.9375rem', color: '#0f172a' }}>
                          {obs.type}:
                        </span>
                        <span style={{
                          background: '#e0f2fe',
                          color: '#0369a1',
                          padding: '0.2rem 0.6rem',
                          borderRadius: '12px',
                          fontWeight: 700,
                          fontSize: '0.875rem'
                        }}>
                          {obs.prior_value} → {obs.current_value}
                        </span>
                        <span style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: obs.direction === 'Decreased' ? '#16a34a' : (obs.direction === 'Increased' ? '#dc2626' : '#64748b'),
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.2rem'
                        }}>
                          {obs.direction === 'Decreased' ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
                          {obs.delta} ({obs.direction})
                        </span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {obs.prior_time} → {obs.current_time}
                      </span>
                    </div>

                    {/* Source Sentences Traceability */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
                      <div style={{ background: '#ffffff', padding: '0.625rem 0.75rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
                        <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                          Prior Shift Evidence:
                        </span>
                        <div style={{ fontSize: '0.8125rem', color: '#1e293b', marginTop: '0.2rem', fontStyle: 'italic' }}>
                          "{obs.prior_sentence || 'Not documented'}"
                        </div>
                      </div>

                      <div style={{ background: '#ffffff', padding: '0.625rem 0.75rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
                        <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                          Current Shift Evidence:
                        </span>
                        <div style={{ fontSize: '0.8125rem', color: '#1e293b', marginTop: '0.2rem', fontStyle: 'italic' }}>
                          "{obs.current_sentence || 'Not documented'}"
                        </div>
                      </div>
                    </div>

                    {/* Safety Precaution Disclaimer */}
                    {obs.clinical_caution && (
                      <div style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.4rem',
                        fontSize: '0.75rem',
                        color: '#b45309',
                        background: '#fefce8',
                        padding: '0.5rem 0.75rem',
                        borderRadius: '4px',
                        border: '1px solid #fef08a'
                      }}>
                        <ShieldAlert size={14} style={{ marginTop: '0.1rem', flexShrink: 0 }} />
                        <span>{obs.clinical_caution}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 2. Diagnostic & Laboratory Status Updates */}
          <div className="card" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.875rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileCheck2 size={18} color="#059669" />
                Diagnostic & Laboratory Status Updates
              </h3>
              <span style={{ fontSize: '0.75rem', background: '#f1f5f9', padding: '0.2rem 0.5rem', borderRadius: '4px', color: '#475569' }}>
                {comparison.investigations_updated?.length || 0} transition(s)
              </span>
            </div>

            {comparison.investigations_updated?.length === 0 ? (
              <div style={{ fontSize: '0.8125rem', color: '#64748b', fontStyle: 'italic' }}>
                No diagnostic test status transitions identified between these handovers.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                {comparison.investigations_updated.map((inv, idx) => (
                  <div key={idx} style={{
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: '6px',
                    padding: '0.875rem 1rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.875rem', color: '#166534' }}>
                        {inv.name}
                      </span>
                      <span style={{
                        background: '#dcfce7',
                        color: '#15803d',
                        border: '1px solid #86efac',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 700
                      }}>
                        {inv.transition}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.5rem' }}>
                      <div style={{ fontSize: '0.75rem', color: '#374151' }}>
                        <strong>Prior Shift:</strong> <em>"{inv.prior_sentence}"</em>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#374151' }}>
                        <strong>Current Shift:</strong> <em>"{inv.current_sentence}"</em>
                      </div>
                    </div>

                    {inv.clinical_implication && (
                      <div style={{ fontSize: '0.75rem', color: '#15803d', marginTop: '0.5rem' }}>
                        • {inv.clinical_implication}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 3. Task Progression & Actions Completed */}
          <div className="card" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.875rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 size={18} color="#16a34a" />
                Task Progression & Documented Completions
              </h3>
              <span style={{ fontSize: '0.75rem', background: '#f1f5f9', padding: '0.2rem 0.5rem', borderRadius: '4px', color: '#475569' }}>
                {comparison.tasks_progressed?.length || 0} progressed
              </span>
            </div>

            {comparison.tasks_progressed?.length === 0 ? (
              <div style={{ fontSize: '0.8125rem', color: '#64748b', fontStyle: 'italic' }}>
                No task state transitions detected across consecutive handovers.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {comparison.tasks_progressed.map((t, idx) => (
                  <div key={idx} style={{
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    padding: '0.875rem 1rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                      <strong style={{ fontSize: '0.875rem', color: '#1e293b' }}>{t.task}</strong>
                      <span style={{
                        background: '#dcfce7',
                        color: '#15803d',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600
                      }}>
                        {t.prior_status} → {t.current_status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#475569', fontStyle: 'italic' }}>
                      Documented Evidence: "{t.current_sentence}"
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 4. Ongoing Conditions & New Directives */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
            {/* Ongoing Conditions */}
            <div className="card" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Clock size={16} color="#d97706" />
                Ongoing / Persisting Conditions
              </h3>

              {comparison.ongoing_conditions?.length === 0 ? (
                <div style={{ fontSize: '0.8125rem', color: '#64748b', fontStyle: 'italic' }}>
                  No ongoing conditions explicitly documented across both handovers.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {comparison.ongoing_conditions.map((oc, idx) => (
                    <div key={idx} style={{
                      background: '#fffbeb',
                      border: '1px solid #fef3c7',
                      borderRadius: '4px',
                      padding: '0.625rem 0.75rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.8125rem', color: '#92400e' }}>
                          {oc.condition}
                        </span>
                        <span style={{ fontSize: '0.6875rem', background: '#fde68a', color: '#78350f', padding: '0.1rem 0.4rem', borderRadius: '4px', fontWeight: 600 }}>
                          {oc.status}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#451a03', marginTop: '0.25rem', fontStyle: 'italic' }}>
                        Current shift: "{oc.current_sentence}"
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* New Directives & Instructions */}
            <div className="card" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserCheck size={16} color="#7c3aed" />
                New Directives & Clinician Instructions
              </h3>

              {comparison.new_directives?.length === 0 ? (
                <div style={{ fontSize: '0.8125rem', color: '#64748b', fontStyle: 'italic' }}>
                  No new directives documented in current handover note.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {comparison.new_directives.map((nd, idx) => (
                    <div key={idx} style={{
                      background: '#f5f3ff',
                      border: '1px solid #ddd6fe',
                      borderRadius: '4px',
                      padding: '0.625rem 0.75rem'
                    }}>
                      <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: '#5b21b6' }}>
                        {nd.directive}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#4c1d95', marginTop: '0.25rem', fontStyle: 'italic' }}>
                        "{nd.source_sentence}"
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Clinician Non-Hallucinatory Audit Guarantee */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            padding: '0.875rem 1.25rem',
            fontSize: '0.75rem',
            color: '#64748b',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <ShieldAlert size={16} color="#94a3b8" />
            <span>
              <strong>Clinical Guardrail Compliance:</strong> PULSE compares notes strictly on documented facts. It never marks an omitted condition as resolved, nor does it infer full patient recovery from a numeric temperature reduction.
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default WhatChangedPage;
