import React, { useState, useEffect } from 'react';
import {
  Users,
  Activity,
  Layers,
  FileText,
  History,
  HeartPulse,
  CheckCircle2,
  ShieldAlert,
  Info,
  GitCompare,
  ListTodo,
  BarChart3,
  BrainCircuit
} from 'lucide-react';
import { PatientDashboardPage } from './pages/PatientDashboardPage';
import { VitalsPage } from './pages/VitalsPage';
import { ClinicalNotesPage } from './pages/ClinicalNotesPage';
import { HandoverSummaryPage } from './pages/HandoverSummaryPage';
import { HistoryPage } from './pages/HistoryPage';
import { WhatChangedPage } from './pages/WhatChangedPage';
import { PendingActionsPage } from './pages/PendingActionsPage';
import { ResearchEvaluationPage } from './pages/ResearchEvaluationPage';
import { ModelTrainingDashboardPage } from './pages/ModelTrainingDashboardPage';
import { fetchHealth, fetchPatients } from './services/api';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [totalPatients, setTotalPatients] = useState(null);

  useEffect(() => {
    async function initApp() {
      try {
        const [healthData, patientsData] = await Promise.all([
          fetchHealth(),
          fetchPatients()
        ]);
        setSystemHealth(healthData);
        const count = patientsData?.total_patients ?? patientsData?.patients?.length ?? healthData?.total_patients ?? 10;
        setTotalPatients(count);
        if (patientsData?.patients?.length > 0) {
          setSelectedPatient(patientsData.patients[0]);
        }
      } catch (err) {
        console.warn("Backend initialization check:", err);
      }
    }
    initApp();
  }, []);

  function handleSelectPatient(patient) {
    setSelectedPatient(patient);
  }

  function handleSwitchPatient() {
    setActiveTab('dashboard');
  }

  return (
    <div className="app-container hospital-theme">
      {/* Persistent Research Prototype & Clinical Safety Banner */}
      <div className="clinical-scope-banner">
        <div className="banner-content">
          <ShieldAlert size={16} className="scope-icon" />
          <span>
            <strong>PULSE Research Prototype (Demonstration Only):</strong> Uses synthetic demonstration data. Not connected to live hospital EHR or patient monitors. Not for clinical diagnosis, prescribing, or treatment decisions.
          </span>
        </div>
      </div>

      {/* Hospital Workstation Header */}
      <header className="hospital-header">
        <div className="header-inner">
          {/* Hospital Brand & Prototype Tag */}
          <div className="hospital-brand" onClick={() => setActiveTab('dashboard')} style={{ cursor: 'pointer' }}>
            <div className="brand-icon">
              <HeartPulse size={22} color="#ffffff" />
            </div>
            <div className="brand-text">
              <div className="brand-title">
                PULSE
                <span className="prototype-tag">Research & Demo</span>
              </div>
              <div className="brand-sub">Hospital Handover Intelligence System</div>
            </div>
          </div>

          {/* Primary Hospital Navigation */}
          <nav className="hospital-nav">
            <button
              className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <Users size={16} /> Patient Dashboard
            </button>

            <button
              className={`nav-item ${activeTab === 'vitals' ? 'active' : ''}`}
              onClick={() => setActiveTab('vitals')}
            >
              <Activity size={16} /> Vitals
            </button>

            <button
              className={`nav-item ${activeTab === 'notes' ? 'active' : ''}`}
              onClick={() => setActiveTab('notes')}
            >
              <FileText size={16} /> Clinical Notes
            </button>

            <button
              className={`nav-item ${activeTab === 'changes' ? 'active' : ''}`}
              onClick={() => setActiveTab('changes')}
            >
              <GitCompare size={16} /> What Changed?
            </button>

            <button
              className={`nav-item ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => setActiveTab('tasks')}
            >
              <ListTodo size={16} /> Pending Actions
            </button>

            <button
              className={`nav-item ${activeTab === 'summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('summary')}
            >
              <Layers size={16} /> Handover Summary
            </button>

            <button
              className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              <History size={16} /> History
            </button>

            <button
              className={`nav-item ${activeTab === 'evaluation' ? 'active' : ''}`}
              onClick={() => setActiveTab('evaluation')}
            >
              <BarChart3 size={16} /> Evaluation
            </button>

            <button
              className={`nav-item nav-item-highlight ${activeTab === 'training' ? 'active' : ''}`}
              onClick={() => setActiveTab('training')}
            >
              <BrainCircuit size={16} /> BioClinicalBERT
            </button>
          </nav>
        </div>
      </header>

      {/* Active Workstation Body */}
      <main className="main-viewport">
        {activeTab === 'dashboard' && (
          <PatientDashboardPage
            selectedPatient={selectedPatient}
            onSelectPatient={handleSelectPatient}
            onNavigate={(tab) => setActiveTab(tab)}
            onPatientCountChange={(count) => setTotalPatients(count)}
          />
        )}

        {activeTab === 'vitals' && (
          <VitalsPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'notes' && (
          <ClinicalNotesPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'changes' && (
          <WhatChangedPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'tasks' && (
          <PendingActionsPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'summary' && (
          <HandoverSummaryPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'history' && (
          <HistoryPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'evaluation' && (
          <ResearchEvaluationPage
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'training' && (
          <ModelTrainingDashboardPage
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}
      </main>

      {/* Restrained Hospital Workstation Footer */}
      <footer className="hospital-footer">
        <div className="footer-inner">
          <div className="footer-info">
            <strong>PULSE Prototype</strong> • Hospital Handover Intelligence Engine
            <span className="footer-muted"> (Synthetic demonstration corpus • {totalPatients != null ? `${totalPatients} registered demo patients` : 'registered demo patients'})</span>

          </div>

          <div className="footer-status">
            <span className="status-indicator">
              <CheckCircle2 size={13} color="#059669" />
              <span>
                {systemHealth?.status?.includes('Cloud')
                  ? 'Cloud Client Engine (Vercel Ready)'
                  : (systemHealth ? 'FastAPI Backend Ready' : 'Backend Connecting')}
              </span>
            </span>
            <span className="status-separator">•</span>
            <span className="status-engine">
              {systemHealth?.model_status?.clinical_bert_loaded
                ? `Live Bio_ClinicalBERT${systemHealth?.model_status?.realtime?.average_inference_ms ? ` • ${systemHealth.model_status.realtime.average_inference_ms} ms avg` : ''}`
                : (systemHealth?.status?.includes('Cloud')
                  ? 'Model: Bio_ClinicalBERT client fallback'
                  : 'Model: hybrid rules (neural checkpoint pending)')}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
