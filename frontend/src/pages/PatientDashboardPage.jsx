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
      {/* Refined Dashboard Header */}
      <div className="dashboard-header-row">
        <div>
          <h1 className="page-heading">Patient Roster</h1>
          <p className="page-subheading">Review current ward state and handover status.</p>
        </div>
        <div className="dashboard-top-actions">
          <button className="btn btn-primary" onClick={() => {/* Add patient modal trigger */}}>
            <UserPlus size={16} /> Register Patient
          </button>
        </div>
      </div>

      {/* Modern Search/Filter Toolbar */}
      <div className="hospital-card search-card">
        <div className="search-row">
          <div className="search-input-wrapper">
            <Search size={18} className="search-icon" />
            <input
              className="form-input search-input"
              placeholder="Search by ID, Name, or Condition..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button className="btn btn-outline">
            <Filter size={16} /> Filters
          </button>
        </div>
      </div>

      {/* Organized Patient Grid */}
      <div className="patient-cards-grid">
        {patients.map((p) => (
          <div
            key={p.id}
            className={`hospital-card patient-card ${selectedPatient?.id === p.id ? 'patient-card-selected' : ''}`}
            onClick={() => onSelectPatient(p)}
          >
            <div className="patient-card-header">
              <span className="patient-card-id">{p.display_id}</span>
              <span className={`acuity-pill ${p.admitting_diagnosis?.includes('icu') ? 'acuity-rose' : 'acuity-emerald'}`}>
                {p.admitting_diagnosis?.includes('icu') ? 'Acute' : 'Stable'}
              </span>
            </div>

            <h3 className="patient-card-name">{p.name}</h3>
            <div className="patient-card-demographics">{p.age} • {p.gender}</div>

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
