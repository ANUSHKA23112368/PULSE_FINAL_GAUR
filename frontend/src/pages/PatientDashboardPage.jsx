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
  X,
  AlertTriangle,
  Plus
} from 'lucide-react';
import { fetchPatients, createPatient } from '../services/api';

export function PatientDashboardPage({ selectedPatient, onSelectPatient, onNavigate, onPatientCountChange }) {
  const [patients, setPatients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
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
    ward: 'Acute Medical Unit (Demo Ward A)',
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
      // If no selected patient yet and patients available, default select first patient
      if (!selectedPatient && list.length > 0) {
        onSelectPatient(list[0]);
      }
    } catch (err) {
      setError("Unable to load patient records from backend. Please ensure the PULSE FastAPI service is running.");
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

    // Validation
    const trimmedName = newPatientForm.name.trim();
    if (!trimmedName) {
      setFormError("Patient display name is required and cannot be whitespace only.");
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
      // Reload list and immediately select newly created patient
      await loadPatients(searchTerm);
      onSelectPatient(created);
    } catch (err) {
      // Retain form inputs so user does not need to re-type
      setFormError(err.message || "Failed to create synthetic demonstration patient.");
    } finally {
      setFormSubmitting(false);
    }
  }

  return (
    <div className="page-container">
      {/* Page Title & Scope Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a', margin: '0 0 0.35rem 0' }}>
            Patient Dashboard
          </h1>
          <p style={{ color: '#475569', fontSize: '0.95rem', margin: 0 }}>
            Select a synthetic demonstration patient to review clinical notes, simulated vitals, and structured handover records.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{
            background: '#f8fafc',
            border: '1px solid #cbd5e1',
            borderRadius: '6px',
            padding: '0.5rem 0.85rem',
            fontSize: '0.825rem',
            color: '#334155',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Users size={16} color="#0284c7" />
            <span><strong>{patients.length} Demonstration Patients</strong> (Synthetic Hospital Corpus)</span>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setFormError(null);
              setShowAddModal(true);
            }}
            style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', padding: '0.5rem 1rem' }}
          >
            <UserPlus size={16} /> + Add New Patient
          </button>
        </div>
      </div>

      {/* Creation Success Alert */}
      {creationSuccess && (
        <div style={{
          background: '#ecfdf5',
          border: '1px solid #a7f3d0',
          borderRadius: '8px',
          padding: '0.85rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <CheckCircle2 size={20} color="#059669" />
            <div style={{ fontSize: '0.9rem', color: '#065f46' }}>
              <strong>Synthetic demo patient created successfully!</strong> Registered as{' '}
              <strong>{creationSuccess.name}</strong> ({creationSuccess.display_id}). Now active for handover testing.
            </div>
          </div>
          <button
            onClick={() => setCreationSuccess(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#059669' }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="hospital-card" style={{ marginBottom: '1.5rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '260px' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
            <input 
              type="text"
              placeholder="Search by patient name, display ID (e.g. PULSE-DEMO-001), ward, or consultant..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ paddingLeft: '2.5rem', width: '100%' }}
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Search size={16} /> Search
          </button>
          {searchTerm && (
            <button type="button" className="btn btn-outline" onClick={handleClearSearch}>
              Clear
            </button>
          )}
          <button 
            type="button" 
            className="btn btn-outline" 
            onClick={() => loadPatients(searchTerm)}
            title="Refresh patient list"
            style={{ padding: '0.55rem' }}
          >
            <RefreshCw size={16} />
          </button>
        </form>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="hospital-card" style={{ background: '#fef2f2', borderColor: '#fca5a5', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertCircle size={20} color="#b91c1c" />
            <span style={{ color: '#991b1b', fontSize: '0.9rem' }}>{error}</span>
          </div>
          <button className="btn btn-outline" onClick={() => loadPatients(searchTerm)}>Retry</button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <RefreshCw size={28} className="spinner" style={{ color: '#0284c7', margin: '0 auto 1rem auto' }} />
          <div style={{ fontWeight: 600, color: '#334155' }}>Loading synthetic patient profiles...</div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && patients.length === 0 && (
        <div className="hospital-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <AlertCircle size={32} color="#64748b" style={{ margin: '0 auto 1rem auto' }} />
          <h3 style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '0.5rem' }}>No patients found matching "{searchTerm}"</h3>
          <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Try searching by display ID like "PULSE-DEMO-001" or patient name like "Michael Wu".
          </p>
          <button className="btn btn-primary" onClick={handleClearSearch}>Reset Search</button>
        </div>
      )}

      {/* Patients Grid */}
      {!loading && !error && patients.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '1rem' }}>
          {patients.map((p) => {
            const isSelected = selectedPatient && String(selectedPatient.id) === String(p.id);

            return (
              <div 
                key={p.id}
                className="hospital-card patient-card"
                onClick={() => onSelectPatient(p)}
                style={{
                  cursor: 'pointer',
                  borderColor: isSelected ? '#0284c7' : '#e2e8f0',
                  boxShadow: isSelected ? '0 0 0 2px #0284c7, 0 2px 4px rgba(0,0,0,0.05)' : '0 1px 3px rgba(0,0,0,0.03)',
                  background: isSelected ? '#f0f9ff' : '#ffffff',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  transition: 'all 0.15s ease'
                }}
              >
                <div>
                  {/* Card Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                    <span style={{
                      fontWeight: 700,
                      fontSize: '0.8rem',
                      color: isSelected ? '#0369a1' : '#475569',
                      background: isSelected ? '#bae6fd' : '#f1f5f9',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      letterSpacing: '0.03em'
                    }}>
                      {p.display_id}
                    </span>

                    {isSelected ? (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#0284c7', fontWeight: 600, fontSize: '0.8rem' }}>
                        <CheckCircle2 size={15} /> Active Patient
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        Click to Select
                      </span>
                    )}
                  </div>

                  {/* Name and Demographics */}
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', margin: '0 0 0.35rem 0' }}>
                    {p.name}
                  </h3>
                  <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '0.75rem' }}>
                    {p.age || 'Age unavailable'} • {p.gender || 'Gender unavailable'}
                  </div>

                  {/* Location & Consultant */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '0.85rem', fontSize: '0.85rem', color: '#334155' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                      <Bed size={15} color="#0284c7" />
                      <span>{p.ward || 'Ward unassigned'} {p.bed_number ? `(${p.bed_number})` : ''}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                      <Stethoscope size={15} color="#0284c7" />
                      <span>{p.consultant || 'Consultant not assigned'}</span>
                    </div>
                  </div>

                  {/* Admitting Narrative */}
                  <div style={{
                    background: '#f8fafc',
                    padding: '0.6rem 0.75rem',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    color: '#475569',
                    border: '1px solid #e2e8f0',
                    lineHeight: '1.4'
                  }}>
                    <strong>Presenting Issue:</strong> {p.admitting_diagnosis || 'Demonstration handover evaluation record.'}
                  </div>
                </div>

                {/* Card Actions */}
                <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Synthetic Demo Profile
                  </span>
                  <div style={{ display: 'flex', gap: '0.4rem' }}>
                    <button 
                      className="btn btn-outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPatient(p);
                        onNavigate('vitals');
                      }}
                      style={{ fontSize: '0.75rem', padding: '0.3rem 0.55rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                    >
                      <Activity size={13} /> Vitals
                    </button>
                    <button 
                      className="btn btn-outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPatient(p);
                        onNavigate('notes');
                      }}
                      style={{ fontSize: '0.75rem', padding: '0.3rem 0.55rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                    >
                      <FileText size={13} /> Notes
                    </button>
                    <button 
                      className="btn btn-primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPatient(p);
                        onNavigate('summary');
                      }}
                      style={{ fontSize: '0.75rem', padding: '0.3rem 0.55rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                    >
                      <Layers size={13} /> Handover
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add New Synthetic Demo Patient Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.5)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #cbd5e1',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
            maxWidth: '600px',
            width: '100%',
            maxHeight: '92vh',
            overflowY: 'auto',
            padding: '1.5rem'
          }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '0 0 0.25rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <UserPlus size={20} color="#0284c7" />
                  Add Synthetic Demonstration Patient
                </h2>
                <div style={{ fontSize: '0.825rem', color: '#64748b' }}>
                  Register a simulated demonstration patient to test the complete hospital handover workflow.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: '4px' }}
                title="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            {/* Mandatory Demonstration Safety Notice */}
            <div style={{
              background: '#fffbeb',
              border: '1px solid #fde68a',
              borderLeft: '4px solid #f59e0b',
              borderRadius: '6px',
              padding: '0.65rem 0.85rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem'
            }}>
              <AlertTriangle size={18} color="#d97706" style={{ flexShrink: 0 }} />
              <div style={{ fontSize: '0.8rem', color: '#92400e' }}>
                <strong>Synthetic Simulation Only:</strong> This patient will be saved to the local prototype database for clinical handover demonstration. Do not enter real patient identifying information.
              </div>
            </div>

            {/* Error Feedback */}
            {formError && (
              <div style={{
                background: '#fef2f2',
                border: '1px solid #fca5a5',
                borderRadius: '6px',
                padding: '0.65rem 0.85rem',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: '#991b1b',
                fontSize: '0.85rem'
              }}>
                <AlertCircle size={16} color="#dc2626" />
                <span>{formError}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleCreatePatientSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.85rem', marginBottom: '1rem' }}>
                {/* Name */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Full Patient Name <span style={{ color: '#dc2626' }}>*</span>
                  </label>
                  <input
                    type="text"
                    name="name"
                    required
                    value={newPatientForm.name}
                    onChange={handleFormChange}
                    placeholder="e.g. Eleanor Vance"
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.9rem' }}
                  />
                </div>

                {/* Age */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Age (Years)
                  </label>
                  <input
                    type="text"
                    name="age"
                    value={newPatientForm.age}
                    onChange={handleFormChange}
                    placeholder="e.g. 58 years"
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.9rem' }}
                  />
                </div>

                {/* Gender */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Gender
                  </label>
                  <select
                    name="gender"
                    value={newPatientForm.gender}
                    onChange={handleFormChange}
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.9rem' }}
                  >
                    <option value="Female">Female</option>
                    <option value="Male">Male</option>
                    <option value="Other">Other</option>
                    <option value="Unspecified">Unspecified</option>
                  </select>
                </div>

                {/* Ward */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Ward / Department
                  </label>
                  <input
                    type="text"
                    name="ward"
                    value={newPatientForm.ward}
                    onChange={handleFormChange}
                    placeholder="e.g. Acute Assessment (Demo Ward A)"
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.9rem' }}
                  />
                </div>

                {/* Bed Number */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Bed Number
                  </label>
                  <input
                    type="text"
                    name="bed_number"
                    value={newPatientForm.bed_number}
                    onChange={handleFormChange}
                    placeholder="e.g. Bed 4"
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.9rem' }}
                  />
                </div>

                {/* Consultant */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Attending Consultant
                  </label>
                  <input
                    type="text"
                    name="consultant"
                    value={newPatientForm.consultant}
                    onChange={handleFormChange}
                    placeholder="e.g. Dr. Sarah Hanlen"
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.9rem' }}
                  />
                </div>

                {/* Admitting Diagnosis / Presenting Issue */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Presenting Complaint / Diagnosis Narrative
                  </label>
                  <textarea
                    name="admitting_diagnosis"
                    rows={2}
                    value={newPatientForm.admitting_diagnosis}
                    onChange={handleFormChange}
                    placeholder="e.g. Acute shortness of breath and pleuritic chest discomfort (Synthetic demonstration narrative)"
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.875rem' }}
                  />
                </div>

                {/* Optional Custom Display ID */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: '#334155', marginBottom: '0.3rem' }}>
                    Patient Display ID <span style={{ fontWeight: 400, color: '#64748b' }}>(Optional — leave blank to auto-generate)</span>
                  </label>
                  <input
                    type="text"
                    name="display_id"
                    value={newPatientForm.display_id}
                    onChange={handleFormChange}
                    placeholder="e.g. PULSE-DEMO-011 (Auto-assigned if omitted)"
                    className="form-input"
                    style={{ width: '100%', fontSize: '0.875rem' }}
                  />
                </div>
              </div>

              {/* Modal Actions */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid #e2e8f0', paddingTop: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowAddModal(false)}
                  disabled={formSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={formSubmitting}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <Plus size={16} />
                  {formSubmitting ? 'Creating Patient...' : 'Create Synthetic Patient'}
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
