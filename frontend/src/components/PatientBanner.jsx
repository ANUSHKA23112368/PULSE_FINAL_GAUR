import React from 'react';
import { User, Bed, Stethoscope, AlertCircle, ArrowRightLeft } from 'lucide-react';

export function PatientBanner({ patient, onSwitchPatient }) {
  if (!patient) {
    return (
      <div className="hospital-card" style={{ marginBottom: '1.25rem', borderLeft: '4px solid #0284c7', background: '#f0f9ff' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertCircle size={20} color="#0284c7" />
            <span style={{ fontWeight: 600, color: '#0369a1' }}>No patient currently selected.</span>
          </div>
          {onSwitchPatient && (
            <button 
              className="btn btn-primary" 
              onClick={onSwitchPatient}
              style={{ padding: '0.4rem 0.85rem', fontSize: '0.85rem' }}
            >
              Select Patient from Dashboard
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="patient-banner" style={{
      background: '#ffffff',
      border: '1px solid #e2e8f0',
      borderLeft: '5px solid #0284c7',
      borderRadius: '8px',
      padding: '1rem 1.25rem',
      marginBottom: '1.5rem',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.35rem' }}>
            <span style={{
              background: '#e0f2fe',
              color: '#0369a1',
              fontWeight: 700,
              fontSize: '0.8rem',
              padding: '2px 8px',
              borderRadius: '4px',
              letterSpacing: '0.04em'
            }}>
              {patient.display_id}
            </span>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
              {patient.name}
            </h2>
            <span style={{ color: '#64748b', fontSize: '0.9rem' }}>
              ({patient.age || 'Age unavailable'} • {patient.gender || 'Gender unavailable'})
            </span>
            <span style={{
              background: '#f1f5f9',
              color: '#475569',
              fontSize: '0.75rem',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: '4px'
            }}>
              Synthetic Demo
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap', fontSize: '0.875rem', color: '#334155' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Bed size={15} color="#0284c7" />
              <strong>Ward:</strong> {patient.ward || 'General'}
              {patient.bed_number && ` (${patient.bed_number})`}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Stethoscope size={15} color="#0284c7" />
              <strong>Consultant:</strong> {patient.consultant || 'Not specified'}
            </span>
          </div>

          {patient.admitting_diagnosis && (
            <div style={{ marginTop: '0.4rem', fontSize: '0.825rem', color: '#64748b' }}>
              <strong style={{ color: '#475569' }}>Admitting Presentation:</strong> {patient.admitting_diagnosis}
            </div>
          )}
        </div>

        {onSwitchPatient && (
          <button 
            className="btn btn-outline"
            onClick={onSwitchPatient}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.45rem 0.85rem',
              fontSize: '0.85rem',
              alignSelf: 'center'
            }}
          >
            <ArrowRightLeft size={14} />
            Switch Patient
          </button>
        )}
      </div>
    </div>
  );
}

export default PatientBanner;
