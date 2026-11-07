import React, { useMemo, useState } from 'react';
import { Check, Copy, Download, FileCode, FileText, Printer, X } from 'lucide-react';
import { useToast } from './Toast';
import { ClinicalPrintSheet } from './ClinicalPrintSheet';
import { buildBundleFromAnalysis, bundleToCsv, downloadTextFile } from '../utils/fhir';

const TABS = [
  { id: 'json', label: 'FHIR R4 JSON', icon: FileCode },
  { id: 'csv', label: 'CSV Table', icon: FileText },
  { id: 'document', label: 'Handover Sheet', icon: Printer },
];

/**
 * Interoperability export modal. Accepts either a pre-built bundle or an
 * analysis result, then exposes JSON, CSV and a print-ready clipboard sheet.
 */
export function FhirExportModal({
  isOpen,
  onClose,
  analysisResult,
  bundle,
  patient,
  isbar,
  title = 'Clinical Shift Handover',
}) {
  const showToast = useToast();
  const [activeTab, setActiveTab] = useState('json');
  const [copied, setCopied] = useState(false);

  const generatedBundle = useMemo(() => buildBundleFromAnalysis(analysisResult), [analysisResult]);
  const activeBundle = bundle || generatedBundle;
  const json = useMemo(() => JSON.stringify(activeBundle, null, 2), [activeBundle]);
  const csv = useMemo(() => bundleToCsv(activeBundle), [activeBundle]);
  const baseName = (patient?.display_id || patient?.id || 'PULSE_HANDOVER').toString().replace(/[^a-zA-Z0-9_-]/g, '_');

  if (!isOpen) return null;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(activeTab === 'csv' ? csv : json);
      setCopied(true);
      showToast?.(`${activeTab === 'csv' ? 'CSV table' : 'FHIR R4 bundle'} copied to clipboard.`, 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      showToast?.('Clipboard access was blocked by the browser.', 'error');
    }
  }

  function handleDownloadJson() {
    downloadTextFile(`${baseName}_FHIR_R4.json`, json, 'application/fhir+json');
    showToast?.('FHIR R4 JSON bundle downloaded.', 'success');
  }

  function handleDownloadCsv() {
    downloadTextFile(`${baseName}_handover.csv`, csv, 'text/csv;charset=utf-8');
    showToast?.('CSV handover table downloaded.', 'success');
  }

  function handlePrint() {
    document.body.classList.add('print-sheet-mode');
    window.print();
    window.setTimeout(() => document.body.classList.remove('print-sheet-mode'), 900);
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="fhir-modal-dialog fhir-export-dialog" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-label="Interoperability export">
        <div className="modal-header">
          <div className="modal-title-group">
            <FileCode size={20} className="modal-icon text-primary" />
            <div>
              <h3>Interoperability Export</h3>
              <p className="modal-subtitle">FHIR R4 · CSV · printable clipboard sheet</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close export dialog">
            <X size={18} />
          </button>
        </div>

        <div className="fhir-tabbar" role="tablist" aria-label="Export format">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className={`fhir-tab ${activeTab === tab.id ? 'is-active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={14} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="modal-body fhir-export-body">
          {activeTab === 'json' && (
            <>
              <p className="fhir-description">
                HL7 FHIR R4 document bundle with Patient, Composition, Condition, MedicationStatement and Task resources for
                Epic, Cerner or NHS EHR ingestion.
              </p>
              <pre className="fhir-code-preview">{json}</pre>
            </>
          )}

          {activeTab === 'csv' && (
            <>
              <p className="fhir-description">
                Flat resource table for spreadsheet review, audit sampling and data-quality checks. Values are quoted and
                newline-safe for Excel and R.
              </p>
              <pre className="fhir-code-preview">{csv}</pre>
            </>
          )}

          {activeTab === 'document' && (
            <>
              <p className="fhir-description">
                Print-ready shift handover sheet in black and white. Use your browser print dialog to choose A4 and save as
                PDF if a signed digital copy is required.
              </p>
              <div className="fhir-document-preview">
                <div className="fhir-document-preview-head">
                  <strong>{title}</strong>
                  <span>{patient?.name || 'Handover document'}</span>
                </div>
                <ul>
                  <li>Patient identification and NEWS2 risk</li>
                  <li>ISBAR narrative with all five sections</li>
                  <li>Active conditions, medications and pending tasks</li>
                  <li>Handover / receiving nurse signature lines</li>
                </ul>
              </div>
            </>
          )}
        </div>

        <div className="modal-footer fhir-export-footer">
          <button className="modal-action-btn secondary" onClick={handleCopy}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
          <button className="modal-action-btn secondary" onClick={handleDownloadJson}>
            <Download size={14} />
            <span>Download .json</span>
          </button>
          <button className="modal-action-btn secondary" onClick={handleDownloadCsv}>
            <Download size={14} />
            <span>Download .csv</span>
          </button>
          <button className="modal-action-btn primary" onClick={handlePrint}>
            <Printer size={14} />
            <span>Print Clipboard Sheet</span>
          </button>
        </div>
      </div>
    </div>
  );
}
