import React, { lazy, Suspense, useEffect, useRef, useState } from 'react';
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
  Search,
  Database,
  FileSpreadsheet,
  Sparkles,
  Info,
  Menu,
} from 'lucide-react';

import { CommandPalette } from './components/CommandPalette';
import { Logo } from './components/Logo';
import { AppErrorBoundary } from './components/AppErrorBoundary';
import { MobileNav } from './components/MobileNav';
import { PageLoader } from './components/PageLoader';
import { fetchHealth, fetchPatients } from './services/api';
import {
  TAB_TITLES,
  ensureInitialHash,
  navigateToTab,
  parseRoute,
  replaceQuery,
} from './router';

// Route-level code splitting keeps the initial clinical shell small and loads
// the heavy research/telemetry views only when they are opened.
const PatientDashboardPage = lazy(() => import('./pages/PatientDashboardPage').then((m) => ({ default: m.PatientDashboardPage })));
const VitalsPage = lazy(() => import('./pages/VitalsPage').then((m) => ({ default: m.VitalsPage })));
const ClinicalNotesPage = lazy(() => import('./pages/ClinicalNotesPage').then((m) => ({ default: m.ClinicalNotesPage })));
const HandoverSummaryPage = lazy(() => import('./pages/HandoverSummaryPage').then((m) => ({ default: m.HandoverSummaryPage })));
const WhatChangedPage = lazy(() => import('./pages/WhatChangedPage').then((m) => ({ default: m.WhatChangedPage })));
const PendingActionsPage = lazy(() => import('./pages/PendingActionsPage').then((m) => ({ default: m.PendingActionsPage })));
const HistoryPage = lazy(() => import('./pages/HistoryPage').then((m) => ({ default: m.HistoryPage })));
const AnalyzePage = lazy(() => import('./pages/AnalyzePage').then((m) => ({ default: m.AnalyzePage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const SampleReportsPage = lazy(() => import('./pages/SampleReportsPage').then((m) => ({ default: m.SampleReportsPage })));
const DatasetPage = lazy(() => import('./pages/DatasetPage').then((m) => ({ default: m.DatasetPage })));
const ModelTrainingDashboardPage = lazy(() => import('./pages/ModelTrainingDashboardPage').then((m) => ({ default: m.ModelTrainingDashboardPage })));
const ResearchEvaluationPage = lazy(() => import('./pages/ResearchEvaluationPage').then((m) => ({ default: m.ResearchEvaluationPage })));
const AboutPage = lazy(() => import('./pages/AboutPage').then((m) => ({ default: m.AboutPage })));
const LandingPage = lazy(() => import('./pages/LandingPage').then((m) => ({ default: m.LandingPage })));

const WARD_NAV = [
  { id: 'dashboard', label: 'Roster', icon: Users, sub: 'Patient bed roster and admissions' },
  { id: 'vitals', label: 'Vitals & NEWS2', icon: Activity, sub: 'Bedside telemetry and early warning score' },
  { id: 'notes', label: 'Notes', icon: FileText, sub: 'Author and structure shift handover notes' },
  { id: 'summary', label: 'ISBAR', icon: Layers, sub: 'Standardised ISBAR handover summary' },
  { id: 'changes', label: 'Changes', icon: GitCompare, sub: 'Consecutive shift delta and clinical trends' },
  { id: 'tasks', label: 'Tasks', icon: ListTodo, sub: 'Pending actions and clinical directives' },
];const STUDIO_NAV = [
  { id: 'analyze', label: 'Analyze Handover', icon: Sparkles, sub: 'Live NLP extraction and 9-category output' },
  { id: 'reports', label: '101 Reports', icon: FileSpreadsheet, sub: 'Browse the NICTA handover corpus' },
  { id: 'overview', label: 'EDA & Pipeline', icon: Database, sub: 'Dynamic corpus statistics and architecture' },
  { id: 'dataset', label: 'Dataset', icon: Database, sub: 'Raw versus preprocessed corpus explorer' },
  { id: 'training', label: 'BioClinicalBERT', icon: BrainCircuit, sub: 'Training telemetry and inference sandbox' },
  { id: 'evaluation', label: 'Benchmarks', icon: BarChart3, sub: '5-fold cross-validation metrics' },
  { id: 'about', label: 'About', icon: Info, sub: 'Clinical scope, ethics and architecture' },];

const HISTORY_NAV = { id: 'history', label: 'History', icon: History, sub: 'Note audit trail and system ledger' };

const NLP_RESEARCH_TABS = [...STUDIO_NAV.map((item) => item.id), HISTORY_NAV.id];

const MOBILE_NAV_GROUPS = [
  { label: 'Clinical Ward', items: WARD_NAV },
  { label: 'NLP & Research Studio', items: STUDIO_NAV },
  { label: 'Audit', items: [HISTORY_NAV] },
];

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

function SidebarGroup({ label, items, activeTab, onNavigate }) {
  return (
    <div className="sidebar-group">
      <div className="sidebar-group-label">{label}</div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={`sidebar-item ${isActive ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
            aria-current={isActive ? 'page' : undefined}
            title={item.sub}
          >
            <span className="sidebar-item-icon">
              <Icon size={15} />
            </span>
            <span className="sidebar-item-copy">
              <strong>{item.label}</strong>
            </span>
            <span className="sidebar-item-marker" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}

function RouteNotFound({ onNavigate }) {
  return (
    <div className="route-not-found hospital-card">
      <div className="route-not-found-icon">
        <Info size={28} />
      </div>
      <h2>This workspace route does not exist</h2>
      <p>The address you opened is not part of the PULSE clinical workspace. The roster is the safest place to resume.</p>
      <div className="route-not-found-actions">
        <button type="button" className="btn btn-primary" onClick={() => onNavigate('dashboard')}>
          <Users size={15} /> Open patient roster
        </button>
        <button type="button" className="btn btn-outline" onClick={() => onNavigate('analyze')}>
          <Sparkles size={15} /> Open NLP studio
        </button>
      </div>
    </div>
  );
}

export function App() {
  const [route, setRoute] = useState(() => parseRoute());
  const activeTab = route.tab;
  const isNlpSuite = NLP_RESEARCH_TABS.includes(activeTab);

  const [selectedPatient, setSelectedPatient] = useState(null);
  const [allPatients, setAllPatients] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [totalPatients, setTotalPatients] = useState(null);
  const [selectedReportId, setSelectedReportId] = useState(() => parseRoute().report || '0');

  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  const [theme, setTheme] = useState(() => localStorage.getItem('pulse_theme') || 'dark');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [selectedWard, setSelectedWard] = useState('Surgical Ward 4B');

  const mainRef = useRef(null);
  const bootstrappedRef = useRef(false);
  const lastTabRef = useRef(activeTab);

  // Keep React state in sync with browser history (back/forward/deep links).
  useEffect(() => {
    ensureInitialHash();
    function syncFromLocation() {
      setRoute(parseRoute());
    }
    window.addEventListener('hashchange', syncFromLocation);
    window.addEventListener('popstate', syncFromLocation);
    return () => {
      window.removeEventListener('hashchange', syncFromLocation);
      window.removeEventListener('popstate', syncFromLocation);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem('pulse_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    function handleKeyDown(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Route change: title, scroll position, and keyboard focus.
  useEffect(() => {
    if (lastTabRef.current !== activeTab) {
      lastTabRef.current = activeTab;
      window.scrollTo({ top: 0, behavior: 'auto' });
      mainRef.current?.focus({ preventScroll: true });
    }
    document.title = `${TAB_TITLES[activeTab] || 'PULSE'} · PULSE Clinical Handover`;
  }, [activeTab]);

  useEffect(() => {
    if (route.report) setSelectedReportId(String(route.report));
  }, [route.report]);

  // A deep link or history entry can point at a different patient.
  useEffect(() => {
    if (!route.patient || allPatients.length === 0) return;
    const match = allPatients.find(
      (patient) => String(patient.display_id) === route.patient || String(patient.id) === route.patient
    );
    if (match && String(match.id) !== String(selectedPatient?.id)) {
      setSelectedPatient(match);
    }
  }, [route.patient, allPatients, selectedPatient]);

  useEffect(() => {
    if (bootstrappedRef.current) return;
    bootstrappedRef.current = true;

    async function initApp() {
      try {
        const [healthData, patientsData] = await Promise.all([
          fetchHealth(),
          fetchPatients(),
        ]);
        setSystemHealth(healthData);

        const list = patientsData?.patients || [];
        setAllPatients(list);
        const count = patientsData?.total_patients ?? list.length ?? healthData?.total_patients ?? 0;
        setTotalPatients(count);

        const requested = parseRoute().patient;
        const preferred = requested
          ? list.find((patient) => String(patient.display_id) === requested || String(patient.id) === requested)
          : null;
        const chosen = preferred || list[0] || null;

        if (chosen) {
          setSelectedPatient(chosen);
          replaceQuery({ patient: chosen.display_id });
        }
      } catch (err) {
        console.warn('Backend initialization check:', err);
      }
    }

    initApp();
  }, []);

  function toggleTheme() {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }

  function handleSelectPatient(patient) {
    setSelectedPatient(patient);
    replaceQuery({ patient: patient?.display_id || null });
  }

  function handleSwitchPatient() {
    handleNavigate('dashboard');
  }

  function handleSelectReport(reportId) {
    const nextId = String(reportId);
    setSelectedReportId(nextId);
    navigateToTab('analyze', { patient: selectedPatient?.display_id, report: nextId });
  }

  function handleNavigate(tab) {
    setIsMobileNavOpen(false);
    if (tab === 'analyze' && !selectedReportId) setSelectedReportId('0');
    navigateToTab(tab, {
      patient: selectedPatient?.display_id,
      report: tab === 'analyze' ? selectedReportId : undefined,
    });
  }

  function focusMain() {
    mainRef.current?.focus();
  }

  if (activeTab === 'landing') {
    return <LandingPage onNavigate={handleNavigate} />;
  }

  function renderActivePage() {
    const patientProps = {
      selectedPatient,
      onSwitchPatient: handleSwitchPatient,
      onNavigate: handleNavigate,
      allPatients,
      onSelectPatient: handleSelectPatient,
    };

    switch (activeTab) {
      case 'dashboard':
        return (
          <PatientDashboardPage
            selectedPatient={selectedPatient}
            onSelectPatient={handleSelectPatient}
            onNavigate={handleNavigate}
            onPatientCountChange={(count) => setTotalPatients(count)}
          />
        );
      case 'vitals':
        return <VitalsPage {...patientProps} />;
      case 'notes':
        return <ClinicalNotesPage {...patientProps} />;
      case 'summary':
        return <HandoverSummaryPage {...patientProps} />;
      case 'changes':
        return <WhatChangedPage {...patientProps} />;
      case 'tasks':
        return <PendingActionsPage {...patientProps} />;
      case 'history':
        return <HistoryPage {...patientProps} />;
      case 'analyze':
        return (
          <AnalyzePage
            selectedReportId={selectedReportId}
            onSelectReport={setSelectedReportId}
            onNavigate={handleNavigate}
          />
        );
      case 'overview':
        return <DashboardPage onNavigate={handleNavigate} onSelectReport={handleSelectReport} />;
      case 'reports':
        return <SampleReportsPage onNavigate={handleNavigate} onSelectReport={handleSelectReport} />;
      case 'dataset':
        return <DatasetPage onNavigate={handleNavigate} onSelectReport={handleSelectReport} />;
      case 'training':
        return <ModelTrainingDashboardPage onNavigate={handleNavigate} />;
      case 'evaluation':
        return <ResearchEvaluationPage onNavigate={handleNavigate} onSelectReport={handleSelectReport} />;
      case 'about':
        return <AboutPage onNavigate={handleNavigate} />;
      default:
        return <RouteNotFound onNavigate={handleNavigate} />;
    }
  }

  return (
    <div className={`app-container hospital-theme theme-${theme}`}>
      <button type="button" className="skip-link" onClick={focusMain}>
        Skip to main clinical content
      </button>

      {/* Persistent Research Prototype & Clinical Safety Banner */}
      <div className="clinical-scope-banner">
        <div className="banner-content">
          <ShieldAlert size={14} className="scope-icon" />
          <span>
            <strong>PULSE Clinical AI Research Prototype:</strong> Real-time neural ISBAR structuring &amp; Bio_ClinicalBERT handover engine. Demonstration and evaluation environment.
          </span>
        </div>
      </div>

      {/* Hospital Workstation Header */}
      <header className="hospital-header">
        <div className="header-inner">
          {/* Hospital Brand & Prototype Tag */}
          <div className="hospital-brand" onClick={() => handleNavigate('dashboard')} style={{ cursor: 'pointer' }}>
            <Logo size={42} />
            <div className="brand-text">
              <div className="brand-title">
                PULSE
                <span className="prototype-tag">v2.0 Neural</span>
              </div>
              <div className="brand-sub">Clinical Handover HUD</div>
            </div>
          </div>

          {/* Current workspace context */}
          <div className="topbar-context" aria-hidden="true">
            <span>Workspace</span>
            <strong>{TAB_TITLES[activeTab] || 'Clinical Handover'}</strong>
          </div>

          {/* Workstation Controls: Command Palette, Clock, Ward, & Theme */}
          <div className="workstation-controls">
            <button
              className="command-bar-trigger"
              onClick={() => setIsCommandPaletteOpen(true)}
              title="Open Command & Patient Search (Ctrl+K)"
            >
              <Search size={13} />
              <span className="command-trigger-text">Search patients &amp; tools...</span>
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
                aria-label="Active ward"
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
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            >
              {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
            </button>

            <button
              type="button"
              className="mobile-nav-toggle"
              onClick={() => setIsMobileNavOpen(true)}
              aria-label="Open navigation menu"
              aria-expanded={isMobileNavOpen}
              aria-controls="mobile-navigation"
            >
              <Menu size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* Left-hand clinical section rail */}
      <aside className="workspace-sidebar" aria-label="Workspace sections">
        <div className="sidebar-suite-switcher">
          <button
            type="button"
            className={`suite-tab-btn ${!isNlpSuite ? 'active' : ''}`}
            onClick={() => handleNavigate('dashboard')}
            title="Clinical Ward HUD: Roster, Vitals, Notes, ISBAR, and Action Items"
          >
            <HeartPulse size={13} />
            <span>Ward HUD</span>
          </button>
          <button
            type="button"
            className={`suite-tab-btn ${isNlpSuite ? 'active' : ''}`}
            onClick={() => handleNavigate('analyze')}
            title="NLP Handover Studio: Live Extraction, 101 Reports, BioClinicalBERT, and Benchmarks"
          >
            <BrainCircuit size={13} />
            <span>NLP Studio</span>
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Workspace navigation">
          <SidebarGroup label="Clinical Ward" items={WARD_NAV} activeTab={activeTab} onNavigate={handleNavigate} />
          <SidebarGroup label="NLP & Research Studio" items={STUDIO_NAV} activeTab={activeTab} onNavigate={handleNavigate} />
          <SidebarGroup label="Audit" items={[HISTORY_NAV]} activeTab={activeTab} onNavigate={handleNavigate} />
        </nav>

        {selectedPatient && (
          <button type="button" className="sidebar-patient" onClick={() => handleNavigate('summary')} title="Open ISBAR handover for the active patient">
            <span className="sidebar-patient-avatar">{getInitials(selectedPatient.name)}</span>
            <span className="sidebar-patient-copy">
              <span className="sidebar-patient-label">Active patient</span>
              <strong>{selectedPatient.name}</strong>
              <small>{selectedPatient.display_id} · {selectedPatient.bed_number || 'Unassigned bed'}</small>
            </span>
          </button>
        )}

        <div className="sidebar-footer">
          <span className="sidebar-status">
            <span className="sidebar-status-dot" />
            {systemHealth ? 'Backend online' : 'Connecting to backend'}
          </span>
          <span className="sidebar-scope">
            <ShieldAlert size={12} />
            Research prototype — not a diagnostic device.
          </span>
        </div>
      </aside>

      {/* Active Workstation Body */}
      <main className="main-viewport" id="main-content" ref={mainRef} tabIndex={-1}>
        <AppErrorBoundary resetKey={`${activeTab}:${route.patient || ''}`}>
          <Suspense
            fallback={<PageLoader label={`Loading ${(TAB_TITLES[activeTab] || 'clinical workspace').toLowerCase()}`} />}
          >
            {route.known ? renderActivePage() : <RouteNotFound onNavigate={handleNavigate} />}
          </Suspense>
        </AppErrorBoundary>
      </main>

      {/* Command Palette Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        patients={allPatients}
        onSelectPatient={(patient) => {
          handleSelectPatient(patient);
          handleNavigate('dashboard');
        }}
        onNavigate={handleNavigate}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      {/* Mobile Navigation Drawer */}
      <MobileNav
        open={isMobileNavOpen}
        onClose={() => setIsMobileNavOpen(false)}
        groups={MOBILE_NAV_GROUPS}
        activeTab={activeTab}
        onNavigate={handleNavigate}
        theme={theme}
        onToggleTheme={toggleTheme}
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
                ? `Live Bio_ClinicalBERT${systemHealth?.model_status?.realtime?.average_inference_ms ? ` • ${systemHealth.model_status.realtime.average_inference_ms} ms avg` : ''}${systemHealth?.model_status?.hybrid_ner_loaded && systemHealth?.model_status?.hybrid_ner_metrics?.strict_f1 != null ? ` • CRF opt-in ${systemHealth.model_status.hybrid_ner_metrics.strict_f1}%` : ''}`
                : (systemHealth?.model_status?.hybrid_ner_loaded
                  ? `Hybrid CRF NER${systemHealth?.model_status?.hybrid_ner_metrics?.strict_f1 != null ? ` • strict F1 ${systemHealth.model_status.hybrid_ner_metrics.strict_f1}% (5-fold)` : ''}`
                  : (systemHealth?.status?.includes('Cloud')
                    ? 'Model: Bio_ClinicalBERT client fallback'
                    : 'Model: hybrid rules (neural checkpoint pending)'))}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
