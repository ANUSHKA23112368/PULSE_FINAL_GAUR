import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Bed, 
  Stethoscope, 
  FileText, 
  Activity, 
  Layers, 
  CheckCircle2, 
  AlertCircle,
  RefreshCw,
  UserPlus,
  Heart,
  Gauge
} from 'lucide-react';
import { fetchPatients, createPatient } from '../services/api';

const WARDS_FILTER = [
  'All Wards',
  'Acute Medical Unit (Demo Ward A)',
  'Surgical Ward 4B',
  'ICU Critical Unit 2',
  'Emergency Triage',
  'Cardiology Stepdown'
];

export function PatientDashboardPage({ selectedPatient, onSelectPatient, onNavigate, onPatientCountChange }) {
  const [patients, setPatients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedWard, setSelectedWard] = useState('All Wards');
  const [acuityFilter, setAcuityFilter] = useState('ALL'); // 'ALL' | 'CRITICAL' | 'STABLE'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Add Patient Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [creationSuccess, setCreationSuccess] = useState(null);

  const initialFormState = {
    name: '',
    age: '',
    gender: 'Female',
    ward: 'Surgical Ward 4B',
    bed_number: 'Bed 4',
    consultant: 'Dr. Sarah Hanlen',
    admitting_diagnosis: '',
    display_id: ''
  };

  const [newPatientForm, setNewPatientForm] = useState(initialFormState);

  useEffect(() => {
    loadPatients(searchTerm);
  }, []);

  async function loadPatients(search = '') {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPatients(search);
      const list = data.patients || [];
      setPatients(list);
      if (onPatientCountChange && (!search || search.trim() === '')) {
        onPatientCountChange(data.total_patients ?? list.length);
      }
      if (!selectedPatient && list.length > 0) {
        onSelectPatient(list[0]);
      }
    } catch (err) {
      setError("Unable to load patient records from backend. Using local engine synthetic corpus.");
    } finally {
      setLoading(false);
    }
  }

  function handleSearchSubmit(e) {
    e.preventDefault();
    loadPatients(searchTerm);
  }

  function handleClearSearch() {
    setSearchTerm('');
    loadPatients('');
  }

  function handleFormChange(e) {
    const { name, value } = e.target;
    setNewPatientForm(prev => ({ ...prev, [name]: value }));
  }

  async function handleCreatePatientSubmit(e) {
    e.preventDefault();
    setFormError(null);

    const trimmedName = newPatientForm.name.trim();
    if (!trimmedName) {
      setFormError("Patient display name is required.");
      return;
    }

    let formattedAge = newPatientForm.age.trim();
    if (formattedAge && /^\d+$/.test(formattedAge)) {
      formattedAge = `${formattedAge} years`;
    }

    const payload = {
      name: trimmedName,
      age: formattedAge || undefined,
      gender: newPatientForm.gender.trim() || undefined,
      ward: newPatientForm.ward.trim() || undefined,
      bed_number: newPatientForm.bed_number.trim() || undefined,
      consultant: newPatientForm.consultant.trim() || undefined,
      admitting_diagnosis: newPatientForm.admitting_diagnosis.trim() || undefined
    };

    if (newPatientForm.display_id.trim()) {
      payload.display_id = newPatientForm.display_id.trim();
    }

    setFormSubmitting(true);
    try {
      const created = await createPatient(payload);
      setCreationSuccess({
        name: created.name,
        display_id: created.display_id
      });
      setShowAddModal(false);
      setNewPatientForm(initialFormState);
      await loadPatients(searchTerm);
      onSelectPatient(created);
    } catch (err) {
      setFormError(err.message || "Failed to create synthetic demonstration patient.");
    } finally {
      setFormSubmitting(false);
    }
  }

  // Filter patients based on ward and acuity
  const filteredPatients = patients.filter(p => {
    // Ward match
    if (selectedWard !== 'All Wards') {
      const pWard = (p.ward || '').toLowerCase();
      const sWard = selectedWard.toLowerCase();
      if (!pWard.includes(sWard) && !sWard.includes(pWard)) {
        return false;
      }
    }
    // Acuity match
    if (acuityFilter !== 'ALL') {
      const diag = (p.admitting_diagnosis || '').toLowerCase();
      const isCritical = diag.includes('embolism') || diag.includes('chest pain') || diag.includes('vertigo') || diag.includes('icu') || diag.includes('sepsis');
      if (acuityFilter === 'CRITICAL' && !isCritical) return false;
      if (acuityFilter === 'STABLE' && isCritical) return false;
    }
    return true;
  });

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="dashboard-header-row">
        <div>
          <h1 className="page-heading">
            Clinical Patient Dashboard
          </h1>
          <p className="page-subheading">
            Select a patient profile to review telemetry, record handover notes, and examine AI ISBAR extractions.
          </p>
        </div>

        <div className="dashboard-top-actions">
          <div className="registered-count-badge">
            <Users size={16} className="text-primary" />
            <span><strong>{patients.length} Registered Demo Patients</strong></span>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setFormError(null);
              setShowAddModal(true);
            }}
          >
            <UserPlus size={15} /> Add Demo Patient
          </button>
        </div>
      </div>

      {/* Creation Success Alert */}
      {creationSuccess && (
        <div className="feedback-alert feedback-success">
          <CheckCircle2 size={18} className="text-emerald" />
          <span className="feedback-text">
            Demo patient registered successfully: <strong>{creationSuccess.name}</strong> ({creationSuccess.display_id}). Now active for handover testing.
          </span>
          <button className="feedback-close" onClick={() => setCreationSuccess(null)}>×</button>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="hospital-card search-card">
        <form onSubmit={handleSearchSubmit} className="search-form-row">
          <div className="search-input-wrapper">
            <Search size={18} className="search-icon" />
            <input 
              type="text"
              placeholder="Search by patient name, display ID (e.g. PULSE-DEMO-001), ward, or diagnosis..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input search-input"
            />
          </div>
          <button type="submit" className="btn btn-primary">
            <Search size={15} /> Search
          </button>
          {searchTerm && (
            <button type="button" className="btn btn-outline" onClick={handleClearSearch}>
              Clear
            </button>
          )}
          <button 
            type="button" 
            className="btn btn-outline btn-icon-only" 
            onClick={() => loadPatients(searchTerm)}
            title="Refresh patient roster"
          >
            <RefreshCw size={15} />
          </button>
        </form>

        {/* Quick Ward Filter Tabs */}
        <div className="ward-filter-row">
          <div className="ward-tabs">
            {WARDS_FILTER.map(w => (
              <button
                key={w}
                type="button"
                className={`ward-filter-pill ${selectedWard === w ? 'active' : ''}`}
                onClick={() => setSelectedWard(w)}
              >
                {w}
              </button>
            ))}
          </div>

          {/* Acuity Toggles */}
          <div className="acuity-filter-group">
            <button
              type="button"
              className={`acuity-toggle-btn ${acuityFilter === 'ALL' ? 'active' : ''}`}
              onClick={() => setAcuityFilter('ALL')}
            >
              All Acuities
            </button>
            <button
              type="button"
              className={`acuity-toggle-btn ${acuityFilter === 'CRITICAL' ? 'active' : ''}`}
              onClick={() => setAcuityFilter('CRITICAL')}
            >
              <AlertCircle size={12} className="text-amber" /> High Attention
            </button>
            <button
              type="button"
              className={`acuity-toggle-btn ${acuityFilter === 'STABLE' ? 'active' : ''}`}
              onClick={() => setAcuityFilter('STABLE')}
            >
              <CheckCircle2 size={12} className="text-emerald" /> Stable
            </button>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="feedback-alert feedback-error">
          <AlertCircle size={18} className="text-rose" />
          <span className="feedback-text">{error}</span>
          <button className="btn btn-outline btn-xs" onClick={() => loadPatients(searchTerm)}>Retry</button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="hospital-card loading-state-card">
          <RefreshCw size={28} className="animate-spin text-primary" />
          <span>Loading synthetic patient roster...</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredPatients.length === 0 && (
        <div className="hospital-card empty-state-card">
          <AlertCircle size={32} className="text-muted" />
          <h3>No patients found matching your search or filters</h3>
          <p>Try resetting the ward filter or clearing the search query.</p>
          <button className="btn btn-primary" onClick={handleClearSearch}>Reset Filters</button>
        </div>
      )}

      {/* Patient Cards Grid */}
      {!loading && !error && filteredPatients.length > 0 && (
        <div className="patient-cards-grid">
          {filteredPatients.map((p) => {
            const isSelected = selectedPatient && String(selectedPatient.id) === String(p.id);
            const diag = (p.admitting_diagnosis || '').toLowerCase();
            const isCritical = diag.includes('embolism') || diag.includes('chest pain') || diag.includes('vertigo') || diag.includes('icu') || diag.includes('sepsis');

            return (
              <div 
                key={p.id}
                className={`hospital-card patient-card ${isSelected ? 'patient-card-selected' : ''}`}
                onClick={() => onSelectPatient(p)}
              >
                <div>
                  {/* Card Header */}
                  <div className="patient-card-header">
                    <span className="patient-card-id">
                      {p.display_id}
                    </span>

                    <div className="patient-card-badges">
                      {isCritical ? (
                        <span className="acuity-pill acuity-amber">
                          <AlertCircle size={11} /> High Attention
                        </span>
                      ) : (
                        <span className="acuity-pill acuity-emerald">
                          <CheckCircle2 size={11} /> Stable
                        </span>
                      )}

                      {isSelected && (
                        <span className="active-patient-indicator">
                          <CheckCircle2 size={13} /> Active
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Patient Name & Demographics */}
                  <h3 className="patient-card-name">
                    {p.name}
                  </h3>
                  <div className="patient-card-demographics">
                    {p.age || 'Age unrecorded'} • {p.gender || 'Unspecified'}
                  </div>

                  {/* Ward & Consultant */}
                  <div className="patient-card-locations">
                    <div className="location-row">
                      <Bed size={14} className="text-primary" />
                      <span>{p.ward || 'General Medical'} {p.bed_number ? `(${p.bed_number})` : ''}</span>
                    </div>
                    <div className="location-row">
                      <Stethoscope size={14} className="text-primary" />
                      <span>{p.consultant || 'Attending Physician'}</span>
                    </div>
                  </div>

                  {/* Presenting Clinical Issue */}
                  <div className="patient-card-presenting">
                    <strong>Presenting Issue:</strong> {p.admitting_diagnosis || 'Synthetic demonstration handover record.'}
                  </div>

                  {/* Bedside Vitals Micro-Telemetry Preview if available */}
                  {p.vitals && (
                    <div className="card-micro-vitals">
                      <span className="micro-vital-item">
                        <Heart size={11} className="text-rose" />
                        <span>{p.vitals.hr || 78} <small>bpm</small></span>
                      </span>
                      <span className="micro-vital-item">
                        <Activity size={11} className="text-sky" />
                        <span>{p.vitals.spo2 || 98}%</span>
                      </span>
                      <span className="micro-vital-item">
                        <Gauge size={11} className="text-violet" />
                        <span>{p.vitals.bp_sys || 120}/{p.vitals.bp_dia || 80}</span>
                      </span>
                    </div>
                  )}
                </div>

                {/* Card Actions Footer */}
                <div className="patient-card-footer">
                  <span className="card-profile-type">
                    Synthetic Demo
                  </span>
                  <div className="card-footer-buttons">
                    <button 
                      type="button"
                      className="btn btn-outline btn-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPatient(p);
                        onNavigate('vitals');
                      }}
                    >
                      <Activity size={12} /> Vitals
                    </button>
                    <button 
                      type="button"
                      className="btn btn-outline btn-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPatient(p);
                        onNavigate('notes');
                      }}
                    >
                      <FileText size={12} /> Notes
                    </button>
                    <button 
                      type="button"
                      className="btn btn-primary btn-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPatient(p);
                        onNavigate('summary');
                      }}
                    >
                      <Layers size={12} /> Handover
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add New Demo Patient Modal */}
      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="add-patient-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <UserPlus size={20} className="modal-icon" />
                <h3>Add Synthetic Demonstration Patient</h3>
              </div>
              <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>×</button>
            </div>

            <form onSubmit={handleCreatePatientSubmit}>
              <div className="modal-body">
                {formError && (
                  <div className="feedback-alert feedback-error">
                    <AlertCircle size={16} className="text-rose" />
                    <span>{formError}</span>
                  </div>
                )}

                <div className="form-grid-2col">
                  <div className="form-group">
                    <label className="form-label">Full Patient Name *</label>
                    <input 
                      type="text" 
                      name="name" 
                      className="form-input" 
                      placeholder="e.g. Eleanor Vance" 
                      value={newPatientForm.name} 
                      onChange={handleFormChange} 
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Display ID / MRN (Optional)</label>
                    <input 
                      type="text" 
                      name="display_id" 
                      className="form-input" 
                      placeholder="e.g. PULSE-DEMO-025" 
                      value={newPatientForm.display_id} 
                      onChange={handleFormChange} 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Age (Years)</label>
                    <input 
                      type="text" 
                      name="age" 
                      className="form-input" 
                      placeholder="e.g. 52" 
                      value={newPatientForm.age} 
                      onChange={handleFormChange} 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Gender</label>
                    <select 
                      name="gender" 
                      className="form-input" 
                      value={newPatientForm.gender} 
                      onChange={handleFormChange}
                    >
                      <option value="Female">Female</option>
                      <option value="Male">Male</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Ward Department</label>
                    <input 
                      type="text" 
                      name="ward" 
                      className="form-input" 
                      value={newPatientForm.ward} 
                      onChange={handleFormChange} 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Bed Location</label>
                    <input 
                      type="text" 
                      name="bed_number" 
                      className="form-input" 
                      value={newPatientForm.bed_number} 
                      onChange={handleFormChange} 
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Attending Consultant</label>
                  <input 
                    type="text" 
                    name="consultant" 
                    className="form-input" 
                    value={newPatientForm.consultant} 
                    onChange={handleFormChange} 
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Admitting Clinical Presentation / Chief Complaint</label>
                  <textarea 
                    name="admitting_diagnosis" 
                    className="form-input" 
                    rows={3} 
                    placeholder="e.g. Admitted with acute respiratory distress and productive cough query pneumonia..." 
                    value={newPatientForm.admitting_diagnosis} 
                    onChange={handleFormChange} 
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button 
                  type="button" 
                  className="modal-action-btn secondary" 
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="modal-action-btn primary" 
                  disabled={formSubmitting}
                >
                  {formSubmitting ? 'Registering...' : '+ Create Patient Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default PatientDashboardPage;
