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
  ArrowRight
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
        } else {
          // Trigger open via parent
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
    { id: 'dashboard', label: 'Patient Dashboard', icon: Users, sub: 'All patient rosters and admissions' },
    { id: 'vitals', label: 'Simulated Vitals & NEWS2', icon: Activity, sub: 'Bedside telemetry monitor & early warning score' },
    { id: 'notes', label: 'Clinical Handover Notes', icon: FileText, sub: 'Voice dictation & free-text entry' },
    { id: 'summary', label: 'ISBAR Handover Summary', icon: Layers, sub: 'Structured handover, audio briefing & FHIR export' },
    { id: 'changes', label: 'What Changed (Shift Delta)', icon: GitCompare, sub: 'Temporal shift comparison and changes' },
    { id: 'tasks', label: 'Pending Actions & Tasks', icon: ListTodo, sub: 'Ward task kanban and clinical orders' },
    { id: 'history', label: 'Execution & Note History', icon: History, sub: 'Audit log of handover transitions' },
    { id: 'training', label: 'BioClinicalBERT Neural Engine', icon: BrainCircuit, sub: 'Live fine-tuning telemetry & inference sandbox' },
    { id: 'evaluation', label: 'Research Evaluation', icon: BarChart3, sub: 'Benchmark F1-scores and validation' },
  ].filter(item => 
    item.label.toLowerCase().includes(search.toLowerCase()) ||
    item.sub.toLowerCase().includes(search.toLowerCase())
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
            placeholder="Type a command, patient name, ward, or clinical tool..."
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
              <div className="command-section-title">Navigation & Tools</div>
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

          {/* Quick Actions */}
          <div className="command-section">
            <div className="command-section-title">Actions & Workstation</div>
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
                <span className="command-item-main">Switch to {theme === 'dark' ? 'Light Workstation' : 'Dark Cyber-HUD'} Mode</span>
                <span className="command-item-sub">Toggle interface contrast theme</span>
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
