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
  GitCompare,
  ListTodo,
  BarChart3,
  BrainCircuit,
  Moon,
  Sun,
  Clock,
  Building2,
  Search
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
import { CommandPalette } from './components/CommandPalette';
import { fetchHealth, fetchPatients } from './services/api';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [allPatients, setAllPatients] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [totalPatients, setTotalPatients] = useState(null);

  // Command Palette State
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Workstation Environment State (Dark Theme Default for Clinical HUD)
  const [theme, setTheme] = useState(() => localStorage.getItem('pulse_theme') || 'dark');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [selectedWard, setSelectedWard] = useState('Surgical Ward 4B');
  const [clinicianRole, setClinicianRole] = useState('Dr. A. Gupta (Attending)');

  useEffect(() => {
    localStorage.setItem('pulse_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Real-time Shift Clock
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Global Ctrl+K hotkey for Command Palette
  useEffect(() => {
    function handleKeyDown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  function toggleTheme() {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  }

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
          setAllPatients(patientsData.patients);
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
    <div className={`app-container hospital-theme theme-${theme}`}>
      {/* Persistent Research Prototype & Clinical Safety Banner */}
      <div className="clinical-scope-banner">
        <div className="banner-content">
          <ShieldAlert size={14} className="scope-icon" />
          <span>
            <strong>PULSE Clinical AI Research Prototype:</strong> Real-time neural ISBAR structuring & Bio_ClinicalBERT handover engine. Demonstration and evaluation environment.
          </span>
        </div>
      </div>

      {/* Hospital Workstation Header */}
      <header className="hospital-header">
        <div className="header-inner">
          {/* Hospital Brand & Prototype Tag */}
          <div className="hospital-brand" onClick={() => setActiveTab('dashboard')} style={{ cursor: 'pointer' }}>
            <div className="brand-icon">
              <HeartPulse size={20} color="#ffffff" />
            </div>
            <div className="brand-text">
              <div className="brand-title">
                PULSE
                <span className="prototype-tag">v2.0 Neural</span>
              </div>
              <div className="brand-sub">Clinical Handover HUD</div>
            </div>
          </div>

          {/* Primary Hospital Navigation */}
          <nav className="hospital-nav">
            <button
              className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <Users size={14} /> Dashboard
            </button>

            <button
              className={`nav-item ${activeTab === 'vitals' ? 'active' : ''}`}
              onClick={() => setActiveTab('vitals')}
            >
              <Activity size={14} /> Vitals & NEWS2
            </button>

            <button
              className={`nav-item ${activeTab === 'notes' ? 'active' : ''}`}
              onClick={() => setActiveTab('notes')}
            >
              <FileText size={14} /> Notes
            </button>

            <button
              className={`nav-item ${activeTab === 'summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('summary')}
            >
              <Layers size={14} /> ISBAR
            </button>

            <button
              className={`nav-item ${activeTab === 'changes' ? 'active' : ''}`}
              onClick={() => setActiveTab('changes')}
            >
              <GitCompare size={14} /> Changes
            </button>

            <button
              className={`nav-item ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => setActiveTab('tasks')}
            >
              <ListTodo size={14} /> Tasks
            </button>

            <button
              className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              <History size={14} /> History
            </button>

            <button
              className={`nav-item ${activeTab === 'evaluation' ? 'active' : ''}`}
              onClick={() => setActiveTab('evaluation')}
            >
              <BarChart3 size={14} /> Benchmarks
            </button>

            <button
              className={`nav-item nav-item-highlight ${activeTab === 'training' ? 'active' : ''}`}
              onClick={() => setActiveTab('training')}
            >
              <BrainCircuit size={14} /> BioClinicalBERT
            </button>
          </nav>

          {/* Workstation Controls: Command Palette, Clock, Ward, Clinician & Dark Mode */}
          <div className="workstation-controls">
            {/* Quick Command Palette Button */}
            <button 
              className="command-bar-trigger"
              onClick={() => setIsCommandPaletteOpen(true)}
              title="Open Command & Patient Search (Ctrl+K)"
            >
              <Search size={13} />
              <span className="command-trigger-text">Search patients & tools...</span>
              <kbd className="command-kbd">Ctrl K</kbd>
            </button>

            <div className="workstation-clock" title="Hospital Station Time">
              <Clock size={13} />
              <span className="clock-time">{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
              <span className="shift-pill">Night Shift</span>
            </div>

            <div className="ward-pill">
              <Building2 size={13} />
              <select
                value={selectedWard}
                onChange={(e) => setSelectedWard(e.target.value)}
                className="ward-select"
              >
                <option value="Surgical Ward 4B">Surgical 4B</option>
                <option value="ICU Critical Unit 2">ICU Unit 2</option>
                <option value="Emergency Triage">Emergency</option>
                <option value="Cardiology Stepdown">Cardiology</option>
              </select>
            </div>

            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
            </button>
          </div>
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
            allPatients={allPatients}
            onSelectPatient={handleSelectPatient}
          />
        )}

        {activeTab === 'notes' && (
          <ClinicalNotesPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
            allPatients={allPatients}
            onSelectPatient={handleSelectPatient}
          />
        )}

        {activeTab === 'summary' && (
          <HandoverSummaryPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
            allPatients={allPatients}
            onSelectPatient={handleSelectPatient}
          />
        )}

        {activeTab === 'changes' && (
          <WhatChangedPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
            allPatients={allPatients}
            onSelectPatient={handleSelectPatient}
          />
        )}

        {activeTab === 'tasks' && (
          <PendingActionsPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
            allPatients={allPatients}
            onSelectPatient={handleSelectPatient}
          />
        )}

        {activeTab === 'history' && (
          <HistoryPage
            selectedPatient={selectedPatient}
            onSwitchPatient={handleSwitchPatient}
            onNavigate={(tab) => setActiveTab(tab)}
            allPatients={allPatients}
            onSelectPatient={handleSelectPatient}
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

      {/* Command Palette Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        patients={allPatients}
        onSelectPatient={handleSelectPatient}
        onNavigate={(tab) => setActiveTab(tab)}
        theme={theme}
        toggleTheme={toggleTheme}
      />

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
