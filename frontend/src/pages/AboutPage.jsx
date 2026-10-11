import React from 'react';
import { 
  Info, 
  Cpu, 
  Layers, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  Sparkles, 
  BookOpen, 
  ExternalLink,
  ShieldCheck
} from 'lucide-react';

export function AboutPage() {
  return (
    <div className="about-container" style={{ maxWidth: '1000px', margin: '0 auto' }}>
      {/* Title Card */}
      <div className="pulse-card" style={{ marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9), rgba(30, 41, 59, 0.7))', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem' }}>
          <span className="chip" style={{ background: 'rgba(6, 182, 212, 0.15)', borderColor: '#06b6d4', color: '#67e8f9', fontWeight: 700 }}>
            College Research Project
          </span>
          <span className="chip" style={{ background: 'rgba(99, 102, 241, 0.15)', borderColor: '#6366f1', color: '#a5b4fc', fontWeight: 600 }}>
            Architecture v1.0.0
          </span>
        </div>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em', lineHeight: 1.2 }}>
          PULSE: Patient Update & Log Structuring Engine
        </h1>
        <h3 style={{ fontSize: '1.1rem', color: '#38bdf8', fontWeight: 600, marginTop: '0.4rem' }}>
          NLP-based Clinical Handover Information Extraction and Event Structuring System
        </h3>
        <p style={{ fontSize: '0.9rem', color: '#94a3b8', marginTop: '0.75rem', lineHeight: 1.6 }}>
          A working research prototype demonstrating the transformation of unstructured free-text nursing shift handovers into structured, standardized clinical handovers across 9 core categories.
        </p>
      </div>

      {/* Mandatory Safety & Clinical Scope Notice */}
      <div className="pulse-card" style={{ marginBottom: '2rem', borderColor: 'rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.06)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
          <ShieldCheck size={26} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fef3c7', marginBottom: '0.3rem' }}>
              Essential Clinical Research Scope & Disclaimer
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#fde68a', lineHeight: 1.6 }}>
              <strong>"PULSE is an AI-assisted clinical information-organization prototype. It does not diagnose, prescribe treatment, or replace professional clinical judgment."</strong>
            </p>
            <p style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.4rem', lineHeight: 1.5 }}>
              This system is strictly designed for clinical information structuring, documentation assistance, and handover continuity support. It does not provide medical diagnoses, treatment recommendations, or clinical triage advice.
            </p>
          </div>
        </div>
      </div>

      {/* Model & Technical Specifications Card */}
      <div className="pulse-card" style={{ marginBottom: '2rem' }}>
        <h3 className="card-title" style={{ marginBottom: '1.25rem', color: '#a5b4fc' }}>
          <Cpu size={20} /> Model Status & 5-Fold Cross-Validation Benchmark
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>
              Active Inference Engine
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', marginTop: '0.4rem' }}>
              Bio_ClinicalBERT + ConText Hybrid Pipeline
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.5rem', lineHeight: 1.5 }}>
              Integrates fine-tuned neural token classification with clinical assertion scoping (negation, temporality, uncertainty) and regex measurement capture.
            </div>
          </div>

          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>
              Neural Backbone Architecture
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#38bdf8', marginTop: '0.4rem' }}>
              Bio_ClinicalBERT (Emily Alsentzer et al.)
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.5rem', lineHeight: 1.5 }}>
              Transformer architecture initialized from Bio_ClinicalBERT (MIMIC-III pre-trained) and fine-tuned for clinical entity token classification.
            </div>
          </div>

          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>
              Evaluation Status
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#10b981', marginTop: '0.4rem' }}>
              5-Fold Cross-Validation Completed
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.5rem', lineHeight: 1.5 }}>
              Strict and lenient span-level F1 benchmarked across all 101 gold documents against Rule and Statistical baselines.
            </div>
          </div>
        </div>

        {/* 5-Fold Benchmark Table */}
        <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1.25rem', marginBottom: '1.25rem' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles size={16} color="#38bdf8" /> Official 5-Fold Cross-Validation Benchmark Comparison
          </h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Model / Paradigm</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Strict Span Precision</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Strict Span Recall</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Strict Span F1</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Lenient Span F1</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600, color: '#cbd5e1' }}>1. Rule Engine Baseline</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#94a3b8' }}>44.48% ± 3.79%</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#94a3b8' }}>17.26% ± 2.21%</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: '#f59e0b' }}>24.84% ± 2.81%</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#94a3b8' }}>47.72% ± 3.28%</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1e293b', background: 'rgba(56, 189, 248, 0.05)' }}>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600, color: '#38bdf8' }}>2. Statistical Sequence Classifier</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#94a3b8' }}>47.48% ± 5.61%</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#94a3b8' }}>58.09% ± 3.27%</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: '#38bdf8' }}>52.20% ± 4.62%</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: '#38bdf8' }}>80.19% ± 3.47%</td>
                </tr>
                <tr>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600, color: '#a5b4fc' }}>3. Bio_ClinicalBERT (Fine-Tuned)</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#94a3b8' }}>12.56% ± 5.57%</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#94a3b8' }}>10.64% ± 7.10%</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: '#a5b4fc' }}>11.38% ± 6.46%</td>
                  <td style={{ padding: '0.6rem 0.8rem', color: '#a5b4fc' }}>47.72% ± 3.47%</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.75rem', lineHeight: 1.5 }}>
            * Evaluated on 101 synthetic nursing handovers using exact character-level verbatim offsets. Bio_ClinicalBERT best individual fold reached Strict F1 22.26% and Lenient F1 54.27%. The Statistical Classifier achieved superior sample-efficiency on this small-scale corpus, while Bio_ClinicalBERT provides neural contextual embeddings integrated into the hybrid deployment.
          </p>
        </div>
      </div>

      {/* Research Background & Problem Definition */}
      <div className="pulse-card" style={{ marginBottom: '2rem' }}>
        <h3 className="card-title" style={{ marginBottom: '1rem', color: '#f8fafc' }}>
          <BookOpen size={20} color="#06b6d4" /> Research Problem & Clinical Motivation
        </h3>

        <div style={{ fontSize: '0.875rem', color: '#cbd5e1', lineHeight: 1.7, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p>
            Clinical nursing handover is one of the most critical communication touchpoints in healthcare delivery. During shift handovers, outgoing nurses verbally convey patient updates, vital sign trajectories, pending diagnostic investigations, medication adjustments, and follow-up duties to incoming nursing staff.
          </p>
          <p>
            However, free-text and verbal handover records often suffer from <strong>high information entropy</strong>, ambiguous medical abbreviations, non-standardized phrasing, and omitted temporal anchors. These factors can contribute to medical errors, delayed investigations, and communication breakdown.
          </p>
          <p>
            <strong>PULSE</strong> tackles this problem by applying computational clinical natural language processing to ingest unstructured nursing notes, systematically extract entities and events, and generate a structured 9-category summary.
          </p>
        </div>
      </div>

      {/* 9 Standard Categories */}
      <div className="pulse-card" style={{ marginBottom: '2rem' }}>
        <h3 className="card-title" style={{ marginBottom: '1rem', color: '#f8fafc' }}>
          <Layers size={20} color="#10b981" /> Standardized Handover Schema (9 Categories)
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
          {[
            { num: "1", title: "Patient Information", desc: "Identifier, Bed/Room, Age, Gender, Attending Doctor" },
            { num: "2", title: "Current Condition", desc: "Admission reasons, acute symptoms, vital status" },
            { num: "3", title: "Medical History", desc: "Chronic diseases, prior surgeries, comorbidities" },
            { num: "4", title: "Medications / Treatment", desc: "Medications, doses, routes, frequencies, ongoing therapies" },
            { num: "5", title: "Investigations", desc: "Radiology, pathology, labs, bedside monitoring" },
            { num: "6", title: "Clinical Events", desc: "Discrete events, admissions, procedures, observations" },
            { num: "7", title: "Temporal Information", desc: "Clock times, shifts, relative intervals, associations" },
            { num: "8", title: "Pending Tasks", desc: "Prioritized outstanding duties requiring handover attention" },
            { num: "9", title: "Follow-up", desc: "Future evaluations, repeat tests, outpatient planning" },
          ].map(cat => (
            <div key={cat.num} style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 1rem' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#38bdf8' }}>
                {cat.num}. {cat.title}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                {cat.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Technology Stack */}
      <div className="pulse-card">
        <h3 className="card-title" style={{ marginBottom: '1rem', color: '#f8fafc' }}>
          <Cpu size={20} color="#6366f1" /> Technology Stack
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Backend Framework</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '0.2rem' }}>Python FastAPI</div>
          </div>
          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Frontend Framework</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '0.2rem' }}>React (Vite)</div>
          </div>
          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Styling & UX</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '0.2rem' }}>Vanilla CSS Design System</div>
          </div>
          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Prototype Storage</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '0.2rem' }}>SQLite Database</div>
          </div>
        </div>
      </div>
    </div>
  );
}
