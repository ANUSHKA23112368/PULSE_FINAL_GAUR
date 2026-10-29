import React, { useState, useEffect } from 'react';
import { 
  History, 
  Clock, 
  Layers, 
  RefreshCw,
  ShieldCheck,
  Sparkles
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatientNotes, fetchHistory } from '../services/api';

export function HistoryPage({ selectedPatient, onSwitchPatient, onNavigate, allPatients, onSelectPatient }) {
  const [patientNotes, setPatientNotes] = useState([]);
  const [globalHistory, setGlobalHistory] = useState([]);
  const [viewScope, setViewScope] = useState('patient'); // 'patient' or 'system'
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, [selectedPatient, viewScope]);

  async function loadHistory() {
    setLoading(true);
    try {
      if (selectedPatient) {
        const pData = await fetchPatientNotes(selectedPatient.display_id || selectedPatient.id);
        setPatientNotes(pData.notes || []);
      }
      const gData = await fetchHistory();
      setGlobalHistory(gData.history || []);
    } catch (err) {
      console.warn("Could not load history:", err);
    } finally {
      setLoading(false);
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

      {/* Header and Scope Toggle */}
      <div className="section-header-row">
        <div>
          <h2 className="page-heading">
            Clinical Handover & Audit Trail
          </h2>
          <p className="page-subheading">
            Chronological log of clinical note authoring, AI structuring runs, and clinician verification timestamps.
          </p>
        </div>

        <div className="header-actions-group">
          <div className="segmented-control">
            <button
              className={`segmented-btn ${viewScope === 'patient' ? 'active' : ''}`}
              onClick={() => setViewScope('patient')}
            >
              Patient Notes ({patientNotes.length})
            </button>
            <button
              className={`segmented-btn ${viewScope === 'system' ? 'active' : ''}`}
              onClick={() => setViewScope('system')}
            >
              System Ledger ({globalHistory.length})
            </button>
          </div>

          <button 
            className="btn btn-outline btn-icon-only" 
            onClick={loadHistory}
            disabled={loading}
            title="Refresh history"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* History Items */}
      {loading ? (
        <div className="hospital-card loading-state-card">
          <RefreshCw size={24} className="animate-spin text-primary" />
          <span>Loading execution records...</span>
        </div>
      ) : viewScope === 'patient' ? (
        patientNotes.length === 0 ? (
          <div className="hospital-card empty-state-card">
            <History size={36} className="text-muted" />
            <h3>No notes logged for this patient yet</h3>
            <p>Create a note on the Clinical Notes page to start building this patient's chronological history.</p>
          </div>
        ) : (
          <div className="history-list">
            {patientNotes.map((n) => {
              const isReviewed = n.status === 'Reviewed';
              const isProcessed = n.status === 'Processed';

              return (
                <div key={n.id} className={`hospital-card history-card history-status-${n.status.toLowerCase()}`}>
                  <div className="history-card-header">
                    <div className="history-tags-group">
                      <span className="history-id-tag">Note #{n.id}</span>
                      <span className={`status-pill status-${n.status.toLowerCase()}`}>
                        {n.status}
                      </span>
                      {isReviewed && (
                        <span className="status-pill status-verified">
                          <ShieldCheck size={12} /> Verified by Clinician
                        </span>
                      )}
                      {isProcessed && (
                        <span className="status-pill status-ai">
                          <Sparkles size={11} /> Bio_ClinicalBERT Processed
                        </span>
                      )}
                    </div>

                    <div className="history-timestamp">
                      <Clock size={13} />
                      <span>{new Date(n.created_at).toLocaleString()}</span>
                      <span>•</span>
                      <span>{n.author_identifier || 'Clinician'}</span>
                    </div>
                  </div>

                  <div className="history-verbatim-text">
                    {n.raw_text}
                  </div>

                  {n.status !== 'Draft' && (
                    <div className="history-footer-actions">
                      <button
                        className="btn btn-outline btn-xs"
                        onClick={() => onNavigate && onNavigate('summary')}
                      >
                        <Layers size={12} /> View Structured ISBAR
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )
      ) : (
        /* System Execution History */
        globalHistory.length === 0 ? (
          <div className="hospital-card empty-state-card">
            <History size={36} className="text-muted" />
            <h3>No system execution events logged yet</h3>
            <p>System audit events appear as notes are parsed and handovers verified.</p>
          </div>
        ) : (
          <div className="history-list">
            {globalHistory.map((h, idx) => (
              <div key={idx} className="hospital-card history-card">
                <div className="history-card-header">
                  <div className="history-tags-group">
                    <span className="history-id-tag">{h.action || 'NLP Execution'}</span>
                    <span className="status-pill status-processed">{h.status || 'Success'}</span>
                  </div>
                  <div className="history-timestamp">
                    <Clock size={13} />
                    <span>{h.timestamp ? new Date(h.timestamp).toLocaleString() : 'Recent'}</span>
                  </div>
                </div>
                <div className="history-verbatim-text">
                  {h.details || h.description || JSON.stringify(h)}
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}

export default HistoryPage;
