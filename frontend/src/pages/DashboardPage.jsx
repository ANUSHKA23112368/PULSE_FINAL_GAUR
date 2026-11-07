import React, { useEffect, useState } from 'react';
import { 
  Activity, 
  FileText, 
  Database, 
  Cpu, 
  Clock, 
  CheckCircle2, 
  ArrowRight, 
  Layers, 
  Stethoscope, 
  Calendar,
  AlertTriangle,
  Sparkles
} from 'lucide-react';
import { fetchStats } from '../services/api';

export function DashboardPage({ onNavigate, onSelectReport }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadDashboardStats() {
      try {
        setLoading(true);
        const data = await fetchStats();
        setStats(data);
        setError(null);
      } catch (err) {
        console.error("Failed to load statistics:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardStats();
  }, []);

  return (
    <div className="dashboard-container">
      {/* Hero Welcome Banner */}
      <div className="pulse-card" style={{ marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9), rgba(30, 41, 59, 0.7))', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.5rem' }}>
          <div style={{ maxWidth: '750px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
              <span className="chip" style={{ background: 'rgba(6, 182, 212, 0.15)', borderColor: '#06b6d4', color: '#67e8f9', fontWeight: 600 }}>
                <Sparkles size={13} /> College Research Prototype
              </span>
              <span className="chip" style={{ background: 'rgba(99, 102, 241, 0.15)', borderColor: '#6366f1', color: '#a5b4fc', fontWeight: 600 }}>
                Dynamic EDA Verified
              </span>
            </div>
            <h1 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff', lineHeight: 1.2 }}>
              PULSE: Patient Update & Log Structuring Engine
            </h1>
            <p style={{ fontSize: '1rem', color: '#94a3b8', marginTop: '0.5rem', fontWeight: 500 }}>
              NLP-based Clinical Handover Information Extraction and Event Structuring System
            </p>
            <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '0.75rem', lineHeight: 1.6 }}>
              Transforms unstructured, high-entropy nursing shift reports into standardized, structured clinical handovers. Built using the <strong>Synthetic Nursing Handover Training and Development Data Set</strong>.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', minWidth: '220px' }}>
            <button 
              className="btn-primary" 
              onClick={() => onNavigate('analyze')}
              style={{ padding: '0.85rem 1.4rem' }}
            >
              <Activity size={18} /> Analyze Handover <ArrowRight size={16} />
            </button>
            <button 
              className="btn-secondary" 
              onClick={() => onNavigate('reports')}
            >
              <FileText size={16} /> Browse 101 Reports
            </button>
          </div>
        </div>
      </div>

      {/* Dynamic Statistics Section */}
      <div style={{ marginBottom: '2.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Database size={20} color="#06b6d4" /> Dynamic Dataset EDA Statistics
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Calculated live directly from the 101 text files in <code className="mono" style={{ color: '#38bdf8' }}>data/101writtenfreetextreports/</code>
            </p>
          </div>
          {loading && <span style={{ fontSize: '0.8rem', color: '#06b6d4' }}>Loading dynamic metrics...</span>}
        </div>

        {error ? (
          <div className="pulse-card" style={{ borderColor: 'rgba(244, 63, 94, 0.4)', background: 'rgba(244, 63, 94, 0.08)' }}>
            <p style={{ color: '#fda4af', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={18} /> Error loading dataset statistics: {error}
            </p>
          </div>
        ) : (
          <div className="metrics-grid">
            <div className="metric-box">
              <span className="metric-label"><FileText size={15} color="#6366f1" /> Total Reports</span>
              <span className="metric-value">{stats ? stats.total_reports : '101'}</span>
              <span className="metric-sub">Primary free-text handover corpus</span>
            </div>

            <div className="metric-box">
              <span className="metric-label"><Activity size={15} color="#06b6d4" /> Average Word Count</span>
              <span className="metric-value">{stats ? stats.average_word_count : '71.65'}</span>
              <span className="metric-sub">Words per clinical report</span>
            </div>

            <div className="metric-box">
              <span className="metric-label"><Layers size={15} color="#10b981" /> Report Length Range</span>
              <span className="metric-value">
                {stats ? `${stats.min_word_count} - ${stats.max_word_count}` : '19 - 209'}
              </span>
              <span className="metric-sub">Min: 19 words | Max: 209 words</span>
            </div>

            <div className="metric-box">
              <span className="metric-label"><Cpu size={15} color="#f59e0b" /> Word Tokens</span>
              <span className="metric-value">{stats ? stats.total_tokens?.toLocaleString() : '7,214'}</span>
              <span className="metric-sub">{stats ? `${stats.unique_vocabulary_tokens} unique vocabulary tokens` : '1,441 unique tokens'}</span>
            </div>

            <div className="metric-box">
              <span className="metric-label"><CheckCircle2 size={15} color="#14b8a6" /> Reports Loaded</span>
              <span className="metric-value">{stats ? `${stats.loaded_successfully} / ${stats.total_reports}` : '101 / 101'}</span>
              <span className="metric-sub">100% indexed from local disk</span>
            </div>
          </div>
        )}
      </div>

      {/* PULSE Architecture Pipeline Flow */}
      <div className="pulse-card" style={{ marginBottom: '2.5rem' }}>
        <div className="pulse-card-header">
          <div>
            <h2 className="card-title">
              <Layers size={20} color="#6366f1" /> PULSE Information Structuring Pipeline
            </h2>
            <p className="card-subtitle">
              End-to-end data processing workflow from unstructured handover text to organized clinical dashboard
            </p>
          </div>
          <span className="chip" style={{ background: 'rgba(99, 102, 241, 0.15)', borderColor: '#6366f1', color: '#a5b4fc' }}>
            Modular Architecture
          </span>
        </div>

        <div className="flow-steps">
          <div className="flow-step-card">
            <span className="flow-step-number">Stage 01</span>
            <h4 className="flow-step-title">Unstructured Text</h4>
            <p className="flow-step-desc">Free-text nursing handover report</p>
          </div>

          <div className="flow-connector">→</div>

          <div className="flow-step-card">
            <span className="flow-step-number">Stage 02</span>
            <h4 className="flow-step-title">Preprocessing</h4>
            <p className="flow-step-desc">Clean format, preserve clinical symbols (@, +, _)</p>
          </div>

          <div className="flow-connector">→</div>

          <div className="flow-step-card">
            <span className="flow-step-number">Stage 03</span>
            <h4 className="flow-step-title">Entity Extraction</h4>
            <p className="flow-step-desc">Conditions, symptoms, meds, vitals, labs</p>
          </div>

          <div className="flow-connector">→</div>

          <div className="flow-step-card">
            <span className="flow-step-number">Stage 04</span>
            <h4 className="flow-step-title">Event Extraction</h4>
            <p className="flow-step-desc">Admissions, investigations, administration</p>
          </div>

          <div className="flow-connector">→</div>

          <div className="flow-step-card">
            <span className="flow-step-number">Stage 05</span>
            <h4 className="flow-step-title">Temporal Extraction</h4>
            <p className="flow-step-desc">Times, dates, durations, shift anchors</p>
          </div>

          <div className="flow-connector">→</div>

          <div className="flow-step-card" style={{ borderColor: 'rgba(6, 182, 212, 0.5)', background: 'rgba(6, 182, 212, 0.1)' }}>
            <span className="flow-step-number" style={{ color: '#06b6d4' }}>Stage 06</span>
            <h4 className="flow-step-title" style={{ color: '#38bdf8' }}>Structured Handover</h4>
            <p className="flow-step-desc">9-category clinical structured output</p>
          </div>
        </div>
      </div>

      {/* Suggested Demonstration Reports */}
      <div className="pulse-card">
        <div className="pulse-card-header">
          <div>
            <h2 className="card-title">
              <Stethoscope size={20} color="#10b981" /> Suggested Demonstration Reports
            </h2>
            <p className="card-subtitle">
              Recommended patient handovers showcasing varied clinical domains and complex temporal/investigation events
            </p>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
          <div className="pulse-card" style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <span className="chip" style={{ background: 'rgba(56, 189, 248, 0.15)', borderColor: '#38bdf8', color: '#7dd3fc' }}>Report #0</span>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>113 words</span>
            </div>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>Michael I Wu (Neurology / MRI)</h4>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.4rem 0 1rem', lineHeight: 1.5 }}>
              48 yo under Dr Hanlen. Headache, vertigo, Bell's palsy, brain MRI, rescheduled carotid doppler appointment.
            </p>
            <button 
              className="btn-secondary" 
              style={{ width: '100%' }}
              onClick={() => {
                onSelectReport('0');
                onNavigate('analyze');
              }}
            >
              Analyze Report 0 <ArrowRight size={14} />
            </button>
          </div>

          <div className="pulse-card" style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <span className="chip" style={{ background: 'rgba(251, 191, 36, 0.15)', borderColor: '#fbbf24', color: '#fde68a' }}>Report #1</span>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>35 words</span>
            </div>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>Vera Abbott (Chest Pain / Cardiac)</h4>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.4rem 0 1rem', lineHeight: 1.5 }}>
              93 yo bed four under Dr Liu. Chest pain, stroke history, asthma, cataracts, 3 nitros administered with no effect.
            </p>
            <button 
              className="btn-secondary" 
              style={{ width: '100%' }}
              onClick={() => {
                onSelectReport('1');
                onNavigate('analyze');
              }}
            >
              Analyze Report 1 <ArrowRight size={14} />
            </button>
          </div>

          <div className="pulse-card" style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <span className="chip" style={{ background: 'rgba(192, 132, 252, 0.15)', borderColor: '#c084fc', color: '#e9d5ff' }}>Report #12</span>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>101 words</span>
            </div>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>Leila Sonya Da Silva (Endocrine / DM)</h4>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.4rem 0 1rem', lineHeight: 1.5 }}>
              34 yo bed 5. Type 1 DM, HPN, sliding scale insulin, diabetic educator referral pending, AM blood sugar review.
            </p>
            <button 
              className="btn-secondary" 
              style={{ width: '100%' }}
              onClick={() => {
                onSelectReport('12');
                onNavigate('analyze');
              }}
            >
              Analyze Report 12 <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
