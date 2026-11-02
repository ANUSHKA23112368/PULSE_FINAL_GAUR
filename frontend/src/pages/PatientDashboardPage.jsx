import React, { useState, useEffect } from 'react';
import {
  Users, Search, Bed, Stethoscope, FileText, Activity, Layers,
  CheckCircle2, AlertCircle, RefreshCw, UserPlus, Gauge, Filter
} from 'lucide-react';
import { fetchPatients, createPatient } from '../services/api';

export function PatientDashboardPage({ selectedPatient, onSelectPatient, onNavigate, onPatientCountChange }) {
  const [patients, setPatients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPatients();
  }, []);

  async function loadPatients() {
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
