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

        <div className="modal-body">
          <p className="fhir-description">
            Structured clinical handover exported as a standard HL7 FHIR R4 compliant JSON Bundle for electronic health record (EHR) integration.
          </p>
          <pre className="fhir-code-preview">
            {JSON.stringify(fhirBundle, null, 2)}
          </pre>
        </div>

        <div className="modal-footer">
          <button
            className="modal-action-btn secondary"
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(fhirBundle, null, 2));
              alert("FHIR R4 Bundle copied to clipboard!");
            }}
          >
            Copy JSON
          </button>
          <button
            className="modal-action-btn primary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
