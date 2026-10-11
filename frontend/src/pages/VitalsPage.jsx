import React, { useEffect, useState } from 'react';
import { 
  Heart, 
  Wind, 
  Gauge, 
  Thermometer, 
  Activity, 
  AlertTriangle, 
  Info,
  Clock,
  ArrowRight
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatient } from '../services/api';

export function VitalsPage({ selectedPatient, onSwitchPatient, onNavigate }) {
  const [patientDetails, setPatientDetails] = useState(selectedPatient);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadFresh() {
      if (!selectedPatient) return;
      setLoading(true);
      try {
        const fresh = await fetchPatient(selectedPatient.display_id || selectedPatient.id);
        if (fresh) {
          setPatientDetails(fresh);
        }
      } catch (err) {
        console.warn("Could not reload patient vitals:", err);
      } finally {
        setLoading(false);
      }
    }
    loadFresh();
  }, [selectedPatient]);

  const vitals = patientDetails?.vitals;

  return (
    <div className="page-container">
      {/* Patient Banner */}
      <PatientBanner patient={patientDetails || selectedPatient} onSwitchPatient={onSwitchPatient} />

      {/* Mandatory Clinical Simulation Disclosure */}
      <div style={{
        background: '#fffbeb',
        border: '1px solid #fde68a',
        borderLeft: '5px solid #f59e0b',
        borderRadius: '8px',
        padding: '0.85rem 1.25rem',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
      }}>
        <AlertTriangle size={20} color="#d97706" style={{ flexShrink: 0 }} />
        <div style={{ fontSize: '0.875rem', color: '#92400e' }}>
          <strong>Simulated demonstration data — not connected to a patient monitor.</strong>
          <span style={{ display: 'block', fontSize: '0.8rem', color: '#b45309', marginTop: '2px' }}>
            These parameters represent synthetic demonstration records for research and workflow testing. No automated alerts or diagnoses are computed.
          </span>
        </div>
      </div>

      {/* Section Header */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', margin: '0 0 0.25rem 0' }}>
          Simulated Vital Observations
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.85rem', color: '#64748b' }}>
          <Clock size={15} />
          <span>Recorded: {vitals?.recorded_at ? new Date(vitals.recorded_at).toLocaleString() : 'Synthetic Demonstration Dataset Record'}</span>
          <span>•</span>
          <span>Source: {vitals?.data_source || 'Simulated Demonstration Engine'}</span>
        </div>
      </div>

      {!vitals ? (
        <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <Info size={32} color="#64748b" style={{ margin: '0 auto 1rem auto' }} />
          <h3 style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '0.5rem' }}>
            No simulated vitals recorded for this patient
          </h3>
          <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Vital observations are recorded during handover transitions.
          </p>
          <button className="btn btn-primary" onClick={() => onNavigate('notes')}>
            Proceed to Clinical Notes
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          {/* Heart Rate */}
          {vitals.hr !== null && vitals.hr !== undefined && (
            <div className="hospital-card" style={{ borderTop: '4px solid #ef4444' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>Heart Rate</span>
                <Heart size={18} color="#ef4444" />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0f172a' }}>{vitals.hr}</span>
                <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 500 }}>bpm</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                Simulated rhythm: Regular sinus
              </div>
            </div>
          )}

          {/* SpO2 */}
          {vitals.spo2 !== null && vitals.spo2 !== undefined && (
            <div className="hospital-card" style={{ borderTop: '4px solid #0284c7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>Oxygen Saturation</span>
                <Activity size={18} color="#0284c7" />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0f172a' }}>{vitals.spo2}</span>
                <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 500 }}>%</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                Room air observation
              </div>
            </div>
          )}

          {/* Blood Pressure */}
          {(vitals.bp_sys !== null && vitals.bp_dia !== null) && (
            <div className="hospital-card" style={{ borderTop: '4px solid #6366f1' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>Blood Pressure</span>
                <Gauge size={18} color="#6366f1" />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0f172a' }}>
                  {vitals.bp_sys}/{vitals.bp_dia}
                </span>
                <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 500 }}>mmHg</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                Sys: {vitals.bp_sys} • Dia: {vitals.bp_dia}
              </div>
            </div>
          )}

          {/* Respiratory Rate */}
          {vitals.rr !== null && vitals.rr !== undefined && (
            <div className="hospital-card" style={{ borderTop: '4px solid #0d9488' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>Respiratory Rate</span>
                <Wind size={18} color="#0d9488" />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0f172a' }}>{vitals.rr}</span>
                <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 500 }}>/min</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                Spontaneous respiration
              </div>
            </div>
          )}

          {/* Temperature */}
          {vitals.temperature !== null && vitals.temperature !== undefined && (
            <div className="hospital-card" style={{ borderTop: '4px solid #f59e0b' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>Temperature</span>
                <Thermometer size={18} color="#f59e0b" />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0f172a' }}>{vitals.temperature}</span>
                <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 500 }}>°C</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                Tympanic reading (simulated)
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation Call-to-action */}
      <div className="hospital-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', background: '#f8fafc' }}>
        <div>
          <div style={{ fontWeight: 700, color: '#0f172a', fontSize: '0.95rem' }}>Ready to enter handover notes?</div>
          <div style={{ fontSize: '0.825rem', color: '#64748b' }}>
            Proceed to the Clinical Notes workstation to log and process this patient's handover.
          </div>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => onNavigate('notes')}
          style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
        >
          Clinical Notes <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}

export default VitalsPage;
