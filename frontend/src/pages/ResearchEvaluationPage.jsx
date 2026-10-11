import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ShieldCheck,
  Award,
  Layers,
  Database,
  RefreshCw,
  Scale,
  Activity,
  Check,
  X
} from 'lucide-react';
import { fetchResearchEvaluation } from '../services/api';

export function ResearchEvaluationPage({ onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvaluation();
  }, []);

  async function loadEvaluation() {
    setLoading(true);
    try {
      const evalData = await fetchResearchEvaluation();
      setData(evalData);
    } catch (err) {
      console.warn("Failed to load evaluation data:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-container" style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Page Header */}
      <div className="section-header" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 600, color: '#1e293b', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <BarChart3 size={24} color="#0284c7" />
              Research Evaluation & Verification Metrics
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#64748b' }}>
              Empirical evaluation on the 101 Synthetic Nursing Handover reference corpus alongside live prototype workflow statistics.
            </p>
          </div>

          <button
            onClick={loadEvaluation}
            disabled={loading}
            className="btn-secondary"
            style={{ fontSize: '0.8125rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            Refresh Evaluation
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem' }} />
          <div>Calculating evaluation metrics...</div>
        </div>
      ) : data ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Section 1: Live Prototype Activity Counters */}
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={18} color="#059669" />
              Live Prototype Clinical Workflow Activity
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem 1.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                  Registered Demo Patients
                </span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0f172a', marginTop: '0.25rem' }}>
                  {data.live_prototype_activity?.registered_demo_patients ?? 10}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                  Isolated patient profiles
                </div>
              </div>

              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem 1.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                  Notes Processed
                </span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0284c7', marginTop: '0.25rem' }}>
                  {data.live_prototype_activity?.clinical_notes_processed ?? 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                  Unstructured handover texts
                </div>
              </div>

              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem 1.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                  Clinician Verified Notes
                </span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#16a34a', marginTop: '0.25rem' }}>
                  {data.live_prototype_activity?.clinician_reviews_verified ?? 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                  Reviewed & audited
                </div>
              </div>

              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem 1.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                  Pending Actions Tracked
                </span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#d97706', marginTop: '0.25rem' }}>
                  {data.live_prototype_activity?.pending_actions_tracked ?? 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                  {data.live_prototype_activity?.tasks_completed ?? 0} completed · {data.live_prototype_activity?.tasks_pending ?? 0} pending
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Reference Benchmark Metrics Table */}
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Award size={18} color="#0284c7" />
                  Information Extraction Benchmark (101 Synthetic Nursing Handover Documents)
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Evaluated against manually labelled clinical ground truth. Zero fabricated metrics.
                </span>
              </div>

              <div style={{
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: '6px',
                padding: '0.4rem 0.75rem',
                fontSize: '0.8125rem',
                color: '#1e40af',
                fontWeight: 600
              }}>
                Overall Micro-F1: {data.overall_micro_f1}%
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0', textAlign: 'left' }}>
                    <th style={{ padding: '0.625rem 0.75rem', color: '#475569', fontWeight: 600 }}>Clinical Category</th>
                    <th style={{ padding: '0.625rem 0.75rem', color: '#475569', fontWeight: 600, textAlign: 'center' }}>Ground Truth</th>
                    <th style={{ padding: '0.625rem 0.75rem', color: '#475569', fontWeight: 600, textAlign: 'center' }}>Extracted</th>
                    <th style={{ padding: '0.625rem 0.75rem', color: '#475569', fontWeight: 600, textAlign: 'right' }}>Precision</th>
                    <th style={{ padding: '0.625rem 0.75rem', color: '#475569', fontWeight: 600, textAlign: 'right' }}>Recall</th>
                    <th style={{ padding: '0.625rem 0.75rem', color: '#475569', fontWeight: 600, textAlign: 'right' }}>F1-Score</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.benchmark_metrics || []).map((m, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '0.75rem', fontWeight: 600, color: '#1e293b' }}>
                        {m.category}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center', color: '#475569' }}>
                        {m.ground_truth}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center', color: '#475569' }}>
                        {m.extracted}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: '#0369a1' }}>
                        {m.precision}%
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: '#0369a1' }}>
                        {m.recall}%
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 700, color: '#15803d' }}>
                        {m.f1}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section 3: Evaluation Methodology & Compliance */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
              <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#1e293b', margin: '0 0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Scale size={16} color="#7c3aed" />
                Zero-Fabrication Clinical Compliance
              </h4>
              <p style={{ fontSize: '0.8125rem', color: '#475569', lineHeight: 1.5, margin: 0 }}>
                {data.evaluation_principles?.zero_autonomous_diagnoses}
              </p>
            </div>

            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.25rem' }}>
              <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#1e293b', margin: '0 0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={16} color="#16a34a" />
                Evidence Traceability Guarantee
              </h4>
              <p style={{ fontSize: '0.8125rem', color: '#475569', lineHeight: 1.5, margin: 0 }}>
                {data.evaluation_principles?.traceability_guarantee}
              </p>
            </div>
          </div>

          {/* Section 4: Corpus Provenance */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            padding: '1rem 1.25rem',
            fontSize: '0.8125rem',
            color: '#475569'
          }}>
            <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Database size={15} color="#0284c7" />
              Corpus Provenance & Benchmark Standard:
            </div>
            <div>
              Corpus: <strong>{data.corpus?.name}</strong> • Documents: <strong>{data.corpus?.total_reference_documents}</strong> • Tokens: <strong>{data.corpus?.total_tokens}</strong> • Vocabulary: <strong>{data.corpus?.vocabulary_size} words</strong> • De-identification Standard: <strong>{data.corpus?.de_identification_standard}</strong>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default ResearchEvaluationPage;
