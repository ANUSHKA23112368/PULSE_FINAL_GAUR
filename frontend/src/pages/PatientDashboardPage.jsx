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
    try {
      const data = await fetchPatients();
      setPatients(data.patients || []);
    } finally {
      setLoading(false);
    }
  }

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
