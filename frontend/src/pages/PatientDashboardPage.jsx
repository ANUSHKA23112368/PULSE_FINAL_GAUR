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
  Gauge,
  Building2
} from 'lucide-react';
import { fetchPatients, createPatient } from '../services/api';
import { News2Badge } from '../components/News2ScorePanel';
import { Sparkline } from '../components/Sparkline';
import { buildVitalsTrend, calculateNews2, getPatientVitals } from '../utils/news2';

function isHighAttention(patient) {
  const diagnosis = (patient?.admitting_diagnosis || '').toLowerCase();
  return ['embolism', 'chest pain', 'vertigo', 'icu', 'sepsis'].some((term) => diagnosis.includes(term));
}

function getInitials(name = '') {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
  return initials || 'PT';
}

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
      const highAttention = isHighAttention(p);
      if (acuityFilter === 'CRITICAL' && !highAttention) return false;
      if (acuityFilter === 'STABLE' && highAttention) return false;
    }
    return true;
  });

  const criticalCount = patients.filter(isHighAttention).length;
  const stableCount = patients.length - criticalCount;
  const wardCount = new Set(patients.map((p) => p.ward).filter(Boolean)).size;

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

      {/* Ward pulse summary */}
      <div className="roster-stats">
        <div className="roster-stat">
          <span className="roster-stat-icon"><Users size={17} /></span>
          <div className="roster-stat-copy">
            <strong>{patients.length}</strong>
            <span>Registered patients</span>
          </div>
        </div>
        <div className="roster-stat roster-stat-amber">
          <span className="roster-stat-icon"><AlertCircle size={17} /></span>
          <div className="roster-stat-copy">
            <strong>{criticalCount}</strong>
            <span>High attention</span>
          </div>
        </div>
        <div className="roster-stat roster-stat-emerald">
          <span className="roster-stat-icon"><CheckCircle2 size={17} /></span>
          <div className="roster-stat-copy">
            <strong>{stableCount}</strong>
            <span>Clinically stable</span>
          </div>
        </div>
        <div className="roster-stat roster-stat-sky">
          <span className="roster-stat-icon"><Building2 size={17} /></span>
          <div className="roster-stat-copy">
            <strong>{wardCount}</strong>
            <span>Wards covered</span>
          </div>
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

            <div className="patient-card-locations">
              <div className="location-row"><Bed size={14} /> {p.ward} • {p.bed_number}</div>
              <div className="location-row"><Stethoscope size={14} /> {p.consultant}</div>
            </div>

            <div className="patient-card-footer">
              <button className="btn btn-outline btn-xs" onClick={() => onNavigate('vitals')}>Vitals</button>
              <button className="btn btn-outline btn-xs" onClick={() => onNavigate('notes')}>Notes</button>
              <button className="btn btn-primary btn-xs" onClick={() => onNavigate('summary')}>Handover</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
