import React, { useState } from 'react';
import { 
  Bed, 
  Stethoscope, 
  AlertCircle, 
  ArrowRightLeft, 
  Copy, 
  Check, 
  Activity, 
  FileText, 
  Layers, 
  ListTodo, 
  ChevronDown,
  Flame,
  CheckCircle2
} from 'lucide-react';

export function PatientBanner({ 
  patient, 
  onSwitchPatient, 
  allPatients = [], 
  onSelectPatient,
  onNavigate 
}) {
  const [copied, setCopied] = useState(false);
  const [showQuickSelect, setShowQuickSelect] = useState(false);

  function handleCopyId(e) {
    e.stopPropagation();
    if (!patient?.display_id) return;
    navigator.clipboard.writeText(patient.display_id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  // Calculate clinical acuity tag based on diagnosis/vitals
  function getAcuity() {
    if (!patient) return null;
    const diag = (patient.admitting_diagnosis || '').toLowerCase();
    const vitals = patient.vitals || {};
    
    if (diag.includes('embolism') || diag.includes('chest pain') || diag.includes('vertigo') || (vitals.hr && vitals.hr > 100)) {
      return { label: 'High Attention', color: 'amber', icon: AlertCircle };
    }
    if (diag.includes('icu') || diag.includes('sepsis') || diag.includes('critical')) {
      return { label: 'Critical Unit', color: 'rose', icon: Flame };
    }
    return { label: 'Clinical Stable', color: 'emerald', icon: CheckCircle2 };
  }

  if (!patient) {
    return (
      <div className="hospital-card patient-banner-empty">
        <div className="banner-empty-inner">
          <div className="banner-empty-text">
            <AlertCircle size={20} className="text-primary" />
            <span><strong>No patient currently selected.</strong> Choose a synthetic demonstration patient to evaluate handover flows.</span>
          </div>
          {onSwitchPatient && (
            <button 
              className="btn btn-primary" 
              onClick={onSwitchPatient}
            >
              Select Patient from Dashboard
            </button>
          )}
        </div>
      </div>
    );
  }

  const acuity = getAcuity();
  const AcuityIcon = acuity?.icon || CheckCircle2;

  return (
    <div className="patient-banner">
      <div className="banner-top-row">
        {/* Left: Patient Demographics & Ward */}
        <div className="patient-main-info">
          <div className="patient-title-group">
            <span 
              className="patient-id-badge" 
              onClick={handleCopyId} 
              title="Click to copy Patient MRN ID"
            >
              {patient.display_id}
              {copied ? <Check size={12} className="copy-check-icon" /> : <Copy size={11} className="copy-icon" />}
            </span>

            <h2 className="patient-name">
              {patient.name}
            </h2>

            <span className="patient-meta-pill">
              {patient.age || 'Age unrecorded'} • {patient.gender || 'Unspecified'}
            </span>

            {acuity && (
              <span className={`acuity-pill acuity-${acuity.color}`}>
                <AcuityIcon size={12} />
                <span>{acuity.label}</span>
              </span>
            )}
          </div>

          {/* Clinical Location & Attending Team */}
          <div className="patient-sub-details">
            <span className="detail-item">
              <Bed size={14} className="detail-icon" />
              <strong>Ward:</strong> {patient.ward || 'General Medical'}
              {patient.bed_number ? ` (${patient.bed_number})` : ''}
            </span>
            <span className="detail-separator">•</span>
            <span className="detail-item">
              <Stethoscope size={14} className="detail-icon" />
              <strong>Consultant:</strong> {patient.consultant || 'Dr. Attending'}
            </span>
            {patient.admitting_diagnosis && (
              <>
                <span className="detail-separator">•</span>
                <span className="detail-item presenting-item">
                  <strong>Admitting Presentation:</strong> {patient.admitting_diagnosis}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Right: Fast Navigation & Patient Switcher */}
        <div className="banner-actions">
          {/* Quick patient switch dropdown */}
          {allPatients && allPatients.length > 0 && onSelectPatient ? (
            <div className="quick-switch-dropdown-container">
              <button 
                type="button"
                className="btn btn-outline btn-quick-switch"
                onClick={() => setShowQuickSelect(prev => !prev)}
                title="Quick switch patient"
              >
                <ArrowRightLeft size={13} />
                <span>Change Patient</span>
                <ChevronDown size={13} />
              </button>

              {showQuickSelect && (
                <div className="quick-patient-menu">
                  <div className="quick-menu-header">Select Demo Patient:</div>
                  <div className="quick-menu-list">
                    {allPatients.map(p => (
                      <div 
                        key={p.id}
                        className={`quick-menu-item ${p.id === patient.id ? 'active' : ''}`}
                        onClick={() => {
                          onSelectPatient(p);
                          setShowQuickSelect(false);
                        }}
                      >
                        <div className="quick-menu-item-info">
                          <strong>{p.name}</strong>
                          <small>{p.display_id} • {p.ward}</small>
                        </div>
                        {p.id === patient.id && <Check size={14} className="quick-menu-check" />}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : onSwitchPatient ? (
            <button 
              className="btn btn-outline"
              onClick={onSwitchPatient}
              title="Return to Dashboard to select patient"
            >
              <ArrowRightLeft size={13} />
              <span>Switch Patient</span>
            </button>
          ) : null}

          {/* Quick Jump Buttons if onNavigate provided */}
          {onNavigate && (
            <div className="banner-quick-links">
              <button 
                className="quick-link-btn" 
                onClick={() => onNavigate('vitals')}
                title="Jump to Simulated Vitals"
              >
                <Activity size={13} /> Vitals
              </button>
              <button 
                className="quick-link-btn" 
                onClick={() => onNavigate('notes')}
                title="Jump to Clinical Notes"
              >
                <FileText size={13} /> Notes
              </button>
              <button 
                className="quick-link-btn" 
                onClick={() => onNavigate('summary')}
                title="Jump to Handover Summary"
              >
                <Layers size={13} /> ISBAR
              </button>
              <button 
                className="quick-link-btn" 
                onClick={() => onNavigate('tasks')}
                title="Jump to Clinical Tasks"
              >
                <ListTodo size={13} /> Tasks
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PatientBanner;
