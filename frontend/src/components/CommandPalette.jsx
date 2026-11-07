import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Users, 
  Activity, 
  FileText, 
  Layers, 
  GitCompare, 
  ListTodo, 
  History, 
  BarChart3, 
  BrainCircuit, 
  Moon, 
  Sun, 
  ArrowRight,
  Database,
  FileSpreadsheet,
  ShieldAlert,
  Sparkles
} from 'lucide-react';

export function CommandPalette({ 
  isOpen, 
  onClose, 
  patients = [], 
  onSelectPatient, 
  onNavigate, 
  theme, 
  toggleTheme 
}) {
  const [search, setSearch] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setSearch('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Global key listener for Ctrl+K / Escape
  useEffect(() => {
    function handleKeyDown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredPatients = patients.filter(p => 
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.display_id || '').toLowerCase().includes(search.toLowerCase()) ||
    (p.ward || '').toLowerCase().includes(search.toLowerCase())
  ).slice(0, 5);

  const navigationItems = [
    // Clinical Ward Workspace
    { id: 'dashboard', label: 'Patient Roster', icon: Users, sub: 'Ward bed rosters, admissions, and quick filters' },
    { id: 'vitals', label: 'Bedside Vitals & NEWS2', icon: Activity, sub: 'Physiological telemetry monitor & early warning score' },
    { id: 'notes', label: 'Shift Notes & Dictation', icon: FileText, sub: 'Nursing handover input, voice dictation & free-text' },
    { id: 'summary', label: 'ISBAR Handover Summary', icon: Layers, sub: 'Standardized ISBAR clinical report, audio readout & FHIR export' },
    { id: 'changes', label: 'What Changed? (Shift Delta)', icon: GitCompare, sub: 'Consecutive handover differential and vital trends' },
    { id: 'tasks', label: 'Pending Actions & Orders', icon: ListTodo, sub: 'Prioritized checklist, status toggles & deadline alerts' },
    { id: 'history', label: 'Analysis & Note History', icon: History, sub: 'SQLite stored execution records and past handover logs' },

    // NLP Handover & Research Studio
    { id: 'analyze', label: 'Live Handover Structuring Engine', icon: Sparkles, sub: 'Ingest 101 reports or free-text, multi-color entity highlights, 9 categories' },
    { id: 'overview', label: 'PULSE Architecture & Dynamic EDA', icon: Database, sub: 'Dynamic corpus statistics, 6-stage NLP pipeline diagram' },
    { id: 'reports', label: 'Browse 101 Handover Reports', icon: FileSpreadsheet, sub: 'Library of 101 NICTA reports with word counts and 1-click analyze' },
    { id: 'dataset', label: 'Multi-Corpus Dataset Explorer', icon: Database, sub: 'Corpus browser, raw vs preprocessed text, token normalization' },
    { id: 'training', label: 'BioClinicalBERT Studio', icon: BrainCircuit, sub: 'Live training telemetry, loss sparkline, hot reload & latency benchmark' },
    { id: 'evaluation', label: 'Model Evaluation Benchmarks', icon: BarChart3, sub: '5-fold cross-validation metrics, strict & lenient F1 scores' },
    { id: 'about', label: 'About PULSE & Clinical Scope', icon: ShieldAlert, sub: 'Technical specifications, ethics disclosure & research architecture' },
  ].filter(item => 
    item.label.toLowerCase().includes(search.toLowerCase()) ||
    item.sub.toLowerCase().includes(search.toLowerCase()) ||
    item.id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="command-palette-backdrop" onClick={onClose}>
      <div className="command-palette-modal" onClick={e => e.stopPropagation()}>
        <div className="command-search-header">
          <Search size={18} className="command-search-icon" />
          <input
            ref={inputRef}
            type="text"
            className="command-search-input"
            placeholder="Search patients, wards, NLP tools, 101 reports, or benchmark models..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <div className="command-shortcut-hint">
            <kbd>ESC</kbd>
          </div>
        </div>

        <div className="command-results-list">
          {/* Quick Patients Section */}
          {filteredPatients.length > 0 && (
            <div className="command-section">
              <div className="command-section-title">Patients ({filteredPatients.length})</div>
              {filteredPatients.map(p => (
                <div
                  key={p.id}
                  className="command-item"
                  onClick={() => {
                    onSelectPatient(p);
                    onClose();
                  }}
                >
                  <div className="command-item-icon patient-icon">
                    <Users size={16} />
                  </div>
                  <div className="command-item-content">
                    <span className="command-item-main">{p.name}</span>
                    <span className="command-item-sub">{p.display_id} • {p.ward} ({p.bed_number || 'Bed'})</span>
                  </div>
                  <span className="command-item-action">Select <ArrowRight size={12} /></span>
                </div>
              ))}
            </div>
          )}

          {/* Navigation Section */}
          {navigationItems.length > 0 && (
            <div className="command-section">
              <div className="command-section-title">Clinical & Research Navigation ({navigationItems.length})</div>
              {navigationItems.map(item => {
                const Icon = item.icon;
                return (
                  <div
                    key={item.id}
                    className="command-item"
                    onClick={() => {
                      onNavigate(item.id);
                      onClose();
                    }}
                  >
                    <div className="command-item-icon">
                      <Icon size={16} />
                    </div>
                    <div className="command-item-content">
                      <span className="command-item-main">{item.label}</span>
                      <span className="command-item-sub">{item.sub}</span>
                    </div>
                    <span className="command-item-action">Jump <ArrowRight size={12} /></span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Theme Quick Toggle */}
          <div className="command-section">
            <div className="command-section-title">Preferences & Environment</div>
            <div 
              className="command-item"
              onClick={() => {
                toggleTheme();
                onClose();
              }}
            >
              <div className="command-item-icon">
                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              </div>
              <div className="command-item-content">
                <span className="command-item-main">Switch to {theme === 'dark' ? 'Light Theme' : 'Dark Clinical HUD'}</span>
                <span className="command-item-sub">Toggle workstation interface appearance</span>
              </div>
              <span className="command-item-action">Toggle</span>
            </div>
          </div>
        </div>

        <div className="command-footer">
          <span>Use <kbd>↑</kbd> <kbd>↓</kbd> to navigate</span>
          <span><kbd>↵</kbd> to select</span>
          <span><kbd>ESC</kbd> to close</span>
        </div>
      </div>
    </div>
  );
}

export default CommandPalette;
