import React, { useState, useEffect } from 'react';
import { 
  History, 
  Clock, 
  FileText, 
  Layers, 
  CheckCircle2, 
  RefreshCw,
  Search,
  ShieldCheck
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatientNotes, fetchHistory } from '../services/api';

export function HistoryPage({ selectedPatient, onSwitchPatient, onNavigate }) {
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
      <PatientBanner patient={selectedPatient} onSwitchPatient={onSwitchPatient} />

      {/* Header and Toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', margin: '0 0 0.25rem 0' }}>
            Clinical Note & Execution History
          </h2>
          <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
            Auditable chronological record of clinical note authoring and NLP structuring runs.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ background: '#f1f5f9', padding: '3px', borderRadius: '6px', display: 'flex' }}>
            <button
              className="btn"
              onClick={() => setViewScope('patient')}
              style={{
                background: viewScope === 'patient' ? '#ffffff' : 'transparent',
                color: viewScope === 'patient' ? '#0f172a' : '#64748b',
                fontWeight: viewScope === 'patient' ? 700 : 500,
                boxShadow: viewScope === 'patient' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                padding: '0.35rem 0.75rem',
                fontSize: '0.8rem',
                border: 'none'
              }}
            >
              This Patient's Notes ({patientNotes.length})
            </button>
            <button
              className="btn"
              onClick={() => setViewScope('system')}
              style={{
                background: viewScope === 'system' ? '#ffffff' : 'transparent',
                color: viewScope === 'system' ? '#0f172a' : '#64748b',
                fontWeight: viewScope === 'system' ? 700 : 500,
                boxShadow: viewScope === 'system' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                padding: '0.35rem 0.75rem',
                fontSize: '0.8rem',
                border: 'none'
              }}
            >
              System History ({globalHistory.length})
            </button>
          </div>

          <button 
            className="btn btn-outline" 
            onClick={loadHistory}
            disabled={loading}
            style={{ padding: '0.45rem', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
          </button>
        </div>
      </div>

      {/* History Items */}
      {loading ? (
        <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <div style={{ color: '#64748b', fontSize: '0.9rem' }}>Loading execution records...</div>
        </div>
      ) : viewScope === 'patient' ? (
        patientNotes.length === 0 ? (
          <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <History size={32} color="#94a3b8" style={{ margin: '0 auto 1rem auto' }} />
            <h3 style={{ fontSize: '1.1rem', color: '#0f172a', marginBottom: '0.4rem' }}>No notes logged for this patient</h3>
            <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
              Create a note in Clinical Notes to begin building this patient's chronological history.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {patientNotes.map((n) => {
              const isReviewed = n.status === 'Reviewed';
              const isProcessed = n.status === 'Processed';
              const borderLeftColor = isReviewed ? '4px solid #059669' : isProcessed ? '4px solid #0284c7' : '4px solid #94a3b8';
              const statusBg = isReviewed ? '#ecfdf5' : isProcessed ? '#e0f2fe' : '#f1f5f9';
              const statusColor = isReviewed ? '#065f46' : isProcessed ? '#0369a1' : '#475569';

              return (
                <div key={n.id} className="hospital-card" style={{ padding: '1rem', borderLeft: borderLeftColor }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 700, color: '#0f172a' }}>Note #{n.id}</span>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: statusBg,
                        color: statusColor
                      }}>
                        {n.status}
                      </span>
                      {isReviewed && (
                        <span style={{
                          fontSize: '0.75rem',
                          color: '#065f46',
                          background: '#ecfdf5',
                          border: '1px solid #a7f3d0',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}>
                          <ShieldCheck size={12} color="#059669" />
                          Clinician Verified
                          {n.reviewer_identifier ? ` (${n.reviewer_identifier})` : ''}
                        </span>
                      )}
                      {isProcessed && (
                        <span style={{ fontSize: '0.75rem', color: '#92400e', background: '#fef3c7', padding: '2px 6px', borderRadius: '4px' }}>
                          AI-generated (Unreviewed)
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Clock size={13} />
                      <span>{new Date(n.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                <div style={{ fontSize: '0.875rem', color: '#334155', background: '#f8fafc', padding: '0.5rem 0.75rem', borderRadius: '4px', border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap' }}>
                  {n.raw_text}
                </div>
              </div>
            );
          })}
          </div>
        )
      ) : (
        globalHistory.length === 0 ? (
          <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <History size={32} color="#94a3b8" style={{ margin: '0 auto 1rem auto' }} />
            <h3 style={{ fontSize: '1.1rem', color: '#0f172a', marginBottom: '0.4rem' }}>No system executions recorded</h3>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {globalHistory.map((h) => (
              <div key={h.id} className="hospital-card" style={{ padding: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 700, color: '#0f172a' }}>Run #{h.id}</span>
                    <span style={{ fontSize: '0.8rem', color: '#0369a1', background: '#e0f2fe', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                      Report: {h.report_id}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      {h.word_count} words
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Clock size={13} />
                    <span>{new Date(h.timestamp).toLocaleString()}</span>
                  </div>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#475569' }}>
                  {h.snippet}...
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
