import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Search, 
  X, 
  CheckCircle2, 
  Layers,
  Activity,
  ShieldCheck,
  Info,
  Check,
  FileSpreadsheet,
  SplitSquareVertical
} from 'lucide-react';
import { fetchReports, fetchReport } from '../services/api';

export function DatasetPage({ onSelectReport, onNavigate }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedReport, setSelectedReport] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalTab, setModalTab] = useState('comparison'); // 'comparison' | 'sentences' | 'audit'

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await fetchReports();
        setReports(data.reports || []);
      } catch (err) {
        console.error("Failed to fetch reports:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function openReportDetails(reportId) {
    try {
      setModalLoading(true);
      setModalTab('comparison');
      const data = await fetchReport(reportId);
      setSelectedReport(data);
    } catch (err) {
      console.error("Failed to load report detail:", err);
    } finally {
      setModalLoading(false);
    }
  }

  const filteredReports = reports.filter(r => {
    const q = searchQuery.toLowerCase();
    return (
      r.report_id.toString().includes(q) ||
      r.filename.toLowerCase().includes(q) ||
      (r.preview && r.preview.toLowerCase().includes(q))
    );
  });

  return (
    <div className="dataset-container">
      {/* Dataset Overview Information Card */}
      <div className="pulse-card" style={{ marginBottom: '2rem' }}>
        <div className="pulse-card-header">
          <div>
            <h2 className="card-title">
              <Database size={20} color="#06b6d4" /> Research Dataset Specifications
            </h2>
            <p className="card-subtitle">
              Synthetic Nursing Handover Training and Development Data Set – Primary Text Corpus
            </p>
          </div>
          <span className="chip" style={{ background: 'rgba(6, 182, 212, 0.15)', borderColor: '#06b6d4', color: '#67e8f9', fontWeight: 700 }}>
            Read-Only Preserved
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Primary Gold Dataset</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', marginTop: '0.25rem' }}>
              Synthetic Nursing Handover
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>NICTA/ANU 101 Gold Notes (2,103 Spans)</div>
          </div>

          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Hospital Training Pack</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#38bdf8', marginTop: '0.2rem' }}>
              261 Reports
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>101 Gold + 160 ISBAR Augmentations</div>
          </div>

          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>External Ingestion Engine</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#a5b4fc', marginTop: '0.35rem' }} className="mono">
              n2c2 2018 & i2b2 2010
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>Loaded via ExternalDatasetLoader</div>
          </div>

          <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Pretrained Foundation</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#34d399', marginTop: '0.25rem' }}>
              MIMIC-III Clinical BERT
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>emilyalsentzer/Bio_ClinicalBERT</div>
          </div>
        </div>

        {/* Multi-Corpus Extended Catalog */}
        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem' }}>
          <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Database size={16} color="#38bdf8" /> Integrated Datasets & Clinical Benchmark Corpora
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
            {/* NICTA Gold */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#38bdf8' }}>1. NICTA Synthetic Nursing Handover</span>
                <span className="badge-tag" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>Primary Gold</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '0.6rem' }}>
                101 authentic nursing shift handovers from acute medical/surgical hospital wards. Annotated with 2,103 clinically verified entity spans and ground truth 9-category slot structures.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.7rem' }}>
                <span className="pill-mini">101 Handover Notes</span>
                <span className="pill-mini">2,103 Gold Spans</span>
                <span className="pill-mini">9 Macro Categories</span>
              </div>
            </div>

            {/* Hospital Training Pack */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#34d399' }}>2. Hospital Training Pack (ISBAR)</span>
                <span className="badge-tag" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>Augmentation</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '0.6rem' }}>
                160 de-identified synthetic multi-shift handovers across ICU, PACU, and telemetry wards. Expands vocabulary with IV titration rates, NEWS2 early warning deterioration scores, and PRN analgesia.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.7rem' }}>
                <span className="pill-mini">261 Total Reports</span>
                <span className="pill-mini">9,500+ Tokens</span>
                <span className="pill-mini">Multi-Ward ISBAR</span>
              </div>
            </div>

            {/* n2c2 2018 Track 2 */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(168, 85, 247, 0.25)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#c084fc' }}>3. n2c2 2018 Track 2 Benchmark</span>
                <span className="badge-tag" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>Supported Ingestion</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '0.6rem' }}>
                National NLP Clinical Challenges benchmark for Adverse Drug Events (ADE) and medication extraction. Ingested via ExternalDatasetLoader with automated label mapping.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.7rem' }}>
                <span className="pill-mini">.txt + .ann Ingestion</span>
                <span className="pill-mini">Drugs & Dosages</span>
                <span className="pill-mini">ADEs & Reasons</span>
              </div>
            </div>

            {/* i2b2 2010 Challenge */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fbbf24' }}>4. i2b2 2010 Clinical Relations</span>
                <span className="badge-tag" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>Supported Ingestion</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '0.6rem' }}>
                Hospital discharge summaries and clinical progress notes. Ingests problem, treatment, and clinical test annotations normalized to PULSE macro categories.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.7rem' }}>
                <span className="pill-mini">Discharge Summaries</span>
                <span className="pill-mini">Problems & Treatments</span>
                <span className="pill-mini">Configs/label_map.yaml</span>
              </div>
            </div>

            {/* MIMIC-III Corpus */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#818cf8' }}>5. MIMIC-III Critical Care Corpus</span>
                <span className="badge-tag" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>Pretraining Foundation</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '0.6rem' }}>
                Over 2 million de-identified critical care notes from Beth Israel Deaconess Medical Center. Provides foundational domain-specific clinical vocabulary for Bio_ClinicalBERT.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.7rem' }}>
                <span className="pill-mini">2M+ Clinical Notes</span>
                <span className="pill-mini">ICU Vocabulary</span>
                <span className="pill-mini">Domain Embeddings</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dataset Table Browser */}
      <div className="pulse-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 className="card-title">
              <Layers size={18} color="#6366f1" /> Corpus Report Index ({filteredReports.length} shown)
            </h3>
            <p className="card-subtitle">
              Browse report ID, word count, character length, and preview text
            </p>
          </div>

          <div style={{ position: 'relative', width: '280px' }}>
            <Search size={16} color="#64748b" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }} />
            <input 
              type="text" 
              className="input-field" 
              placeholder="Search Report ID (e.g. 12)..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '2.25rem', width: '100%', fontSize: '0.85rem' }}
            />
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            Loading dataset records...
          </div>
        ) : filteredReports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            No matching reports found in the corpus.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="pulse-table">
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>Report ID</th>
                  <th>Filename</th>
                  <th>Word Count</th>
                  <th>Character Count</th>
                  <th>Preview Excerpt</th>
                  <th>Status</th>
                  <th style={{ width: '110px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredReports.map((report) => (
                  <tr key={report.report_id}>
                    <td>
                      <span className="chip" style={{ background: 'rgba(99, 102, 241, 0.15)', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#a5b4fc', fontWeight: 700 }}>
                        #{report.report_id}
                      </span>
                    </td>
                    <td className="mono" style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                      {report.filename}
                    </td>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>
                      {report.word_count}
                    </td>
                    <td style={{ color: '#cbd5e1' }}>
                      {report.char_count}
                    </td>
                    <td style={{ color: '#94a3b8', fontSize: '0.8rem', maxWidth: '380px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      "{report.preview}"
                    </td>
                    <td>
                      <span className="chip" style={{ background: 'rgba(52, 211, 153, 0.1)', borderColor: 'rgba(52, 211, 153, 0.3)', color: '#34d399', fontSize: '0.7rem' }}>
                        <CheckCircle2 size={11} /> {report.status}
                      </span>
                    </td>
                    <td>
                      <button 
                        className="btn-secondary" 
                        style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                        onClick={() => openReportDetails(report.report_id)}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Report Modal */}
      {selectedReport && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1.5rem'
        }}>
          <div className="pulse-card" style={{ maxWidth: '920px', width: '100%', maxHeight: '90vh', overflowY: 'auto', background: '#0a101f', border: '1px solid rgba(6, 182, 212, 0.4)', boxShadow: '0 20px 40px rgba(0,0,0,0.6)' }}>
            
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileSpreadsheet size={20} color="#06b6d4" />
                  Report #{selectedReport.report_id} ({selectedReport.filename})
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  {selectedReport.word_count} words | {selectedReport.char_count} characters | Status: <strong style={{ color: '#34d399' }}>Verified Clinical Handover</strong>
                </span>
              </div>
              <button 
                onClick={() => setSelectedReport(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '0.25rem' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Clinical NLP Explanation Callout */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
              marginBottom: '1rem',
              display: 'flex',
              gap: '0.75rem',
              alignItems: 'flex-start'
            }}>
              <Info size={20} color="#38bdf8" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.45 }}>
                <strong style={{ color: '#38bdf8' }}>Clinical Non-Destructive Preprocessing Standard: </strong>
                In healthcare NLP, raw and preprocessed text look similar by design! Unlike web NLP (which converts text to lowercase, strips numbers, and drops words), medical preprocessing <strong>must never</strong> destroy clinical acronyms (<span className="mono" style={{ color: '#a5b4fc' }}>GCS, BP, IV</span>), measurements (<span className="mono" style={{ color: '#a5b4fc' }}>120/80, 5mg</span>), or critical negations (<span className="mono" style={{ color: '#f87171' }}>"no plan for discharge"</span>). PULSE cleans concatenated punctuation, standardizes Unicode quotes/dashes, fixes spacing, and segments sentences without endangering clinical facts.
              </div>
            </div>

            {/* Modal Tab Controls */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '0.5rem' }}>
              <button 
                className={`btn-secondary ${modalTab === 'comparison' ? 'active-tab' : ''}`}
                style={{ 
                  fontSize: '0.78rem', 
                  padding: '0.4rem 0.85rem',
                  background: modalTab === 'comparison' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                  borderColor: modalTab === 'comparison' ? '#06b6d4' : 'var(--border-subtle)',
                  color: modalTab === 'comparison' ? '#67e8f9' : '#94a3b8'
                }}
                onClick={() => setModalTab('comparison')}
              >
                Side-by-Side Comparison
              </button>
              <button 
                className={`btn-secondary ${modalTab === 'sentences' ? 'active-tab' : ''}`}
                style={{ 
                  fontSize: '0.78rem', 
                  padding: '0.4rem 0.85rem',
                  background: modalTab === 'sentences' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                  borderColor: modalTab === 'sentences' ? '#6366f1' : 'var(--border-subtle)',
                  color: modalTab === 'sentences' ? '#a5b4fc' : '#94a3b8'
                }}
                onClick={() => setModalTab('sentences')}
              >
                <SplitSquareVertical size={13} style={{ display: 'inline', marginRight: '4px' }} />
                NLP Sentence Segmentation ({(selectedReport.sentences || []).length})
              </button>
              <button 
                className={`btn-secondary ${modalTab === 'audit' ? 'active-tab' : ''}`}
                style={{ 
                  fontSize: '0.78rem', 
                  padding: '0.4rem 0.85rem',
                  background: modalTab === 'audit' ? 'rgba(52, 211, 153, 0.2)' : 'transparent',
                  borderColor: modalTab === 'audit' ? '#34d399' : 'var(--border-subtle)',
                  color: modalTab === 'audit' ? '#6ee7b7' : '#94a3b8'
                }}
                onClick={() => setModalTab('audit')}
              >
                <ShieldCheck size={13} style={{ display: 'inline', marginRight: '4px' }} />
                Normalization Audit Log ({(selectedReport.changes_made || []).length})
              </button>
            </div>

            {/* TAB 1: Comparison */}
            {modalTab === 'comparison' && (
              <>
                <div className="comparison-grid" style={{ marginBottom: '1.25rem' }}>
                  <div className="comparison-box">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span className="comparison-title" style={{ color: '#94a3b8' }}>RAW HANDOVER TEXT (ORIGINAL)</span>
                      <span className="chip" style={{ fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}>{selectedReport.raw_text.length} chars</span>
                    </div>
                    <div className="comparison-content" style={{ fontSize: '0.85rem', lineHeight: 1.5, background: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: '6px' }}>
                      {selectedReport.raw_text}
                    </div>
                  </div>

                  <div className="comparison-box" style={{ borderColor: 'rgba(6, 182, 212, 0.35)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span className="comparison-title" style={{ color: '#38bdf8' }}>PREPROCESSED CLINICAL TEXT (NORMALIZED)</span>
                      <span className="chip" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#67e8f9', fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}>
                        {selectedReport.preprocessed_text.length} chars
                      </span>
                    </div>
                    <div className="comparison-content" style={{ fontSize: '0.85rem', lineHeight: 1.5, background: 'rgba(6, 182, 212, 0.05)', padding: '0.75rem', borderRadius: '6px', border: '1px solid rgba(6, 182, 212, 0.15)' }}>
                      {selectedReport.preprocessed_text}
                    </div>
                  </div>
                </div>

                {/* Quick Audit Highlights */}
                <div style={{ background: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '0.85rem', marginBottom: '1.25rem' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                    Preprocessing Transformations Fired on this Document:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {(selectedReport.changes_made || []).map((ch, idx) => (
                      <span key={idx} className="chip" style={{ background: 'rgba(52, 211, 153, 0.1)', borderColor: 'rgba(52, 211, 153, 0.3)', color: '#6ee7b7', fontSize: '0.72rem' }}>
                        <Check size={11} style={{ marginRight: '3px' }} /> {ch}
                      </span>
                    ))}
                  </div>

                  <div style={{ marginTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.6rem' }}>
                    <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                      Clinical Safety Non-Destructive Invariants Preserved:
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {(selectedReport.preserved_clinical_elements || [
                        "Preserved numerical dosages, vitals and clinical measurement units",
                        "Preserved clinical acronyms (GCS, BP, IV, COPD) without destructive lowercasing",
                        "Preserved negative assertion terms ('no', 'without') to prevent dangerous false-positive inferences"
                      ]).map((item, idx) => (
                        <span key={idx} className="chip" style={{ background: 'rgba(99, 102, 241, 0.1)', borderColor: 'rgba(99, 102, 241, 0.25)', color: '#c7d2fe', fontSize: '0.72rem' }}>
                          <ShieldCheck size={11} style={{ marginRight: '3px', color: '#818cf8' }} /> {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* TAB 2: NLP Sentence Segmentation */}
            {modalTab === 'sentences' && (
              <div style={{ marginBottom: '1.25rem' }}>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
                  PULSE segments unstructured clinical narratives into individual semantic sentences for accurate entity & temporal extraction:
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                  {(selectedReport.sentences || [selectedReport.preprocessed_text]).map((sentence, idx) => (
                    <div key={idx} style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: '6px', padding: '0.65rem 0.85rem', display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                      <span className="chip" style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#a5b4fc', fontSize: '0.7rem', fontWeight: 700, flexShrink: 0 }}>
                        S#{idx + 1}
                      </span>
                      <div style={{ fontSize: '0.85rem', color: '#f1f5f9', lineHeight: 1.4 }}>
                        {sentence}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: Full Audit Log */}
            {modalTab === 'audit' && (
              <div style={{ marginBottom: '1.25rem' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '1rem' }}>
                  <h4 style={{ fontSize: '0.85rem', color: '#38bdf8', marginBottom: '0.5rem', fontWeight: 700 }}>
                    Deterministic Clinical Cleaning & Transformation Pipeline Log
                  </h4>
                  <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
                    {(selectedReport.changes_made || []).map((ch, idx) => (
                      <li key={idx} style={{ padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.82rem', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Check size={14} color="#34d399" />
                        <span>{ch}</span>
                      </li>
                    ))}
                  </ul>

                  <h4 style={{ fontSize: '0.85rem', color: '#a5b4fc', marginTop: '1rem', marginBottom: '0.5rem', fontWeight: 700 }}>
                    Mandatory Non-Destructive Clinical Invariants Preserved
                  </h4>
                  <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
                    {(selectedReport.preserved_clinical_elements || [
                      "Preserved numerical dosages, vitals and clinical measurement units",
                      "Preserved clinical acronyms (GCS, BP, IV, COPD) without destructive lowercasing",
                      "Preserved negative assertion terms ('no', 'without') to prevent dangerous false-positive inferences"
                    ]).map((item, idx) => (
                      <li key={idx} style={{ padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.82rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <ShieldCheck size={14} color="#818cf8" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Modal Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem' }}>
              <button className="btn-secondary" onClick={() => setSelectedReport(null)}>
                Close
              </button>
              <button 
                className="btn-primary" 
                onClick={() => {
                  onSelectReport(selectedReport.report_id);
                  setSelectedReport(null);
                  onNavigate('analyze');
                }}
              >
                <Activity size={16} /> Analyze in PULSE Engine
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
