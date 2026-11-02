import React from 'react';

/**
 * FHIR R4 Bundle Export Modal Preview for Interoperability
 */
export function FhirExportModal({ isOpen, onClose, analysisResult }) {
  if (!isOpen || !analysisResult) return null;

  // Build simulated FHIR R4 Bundle
  const fhirBundle = {
    resourceType: "Bundle",
    type: "collection",
    timestamp: new Date().toISOString(),
    entry: [
      {
        resource: {
          resourceType: "Patient",
          id: "pulse-patient-demo",
          name: [{ text: analysisResult.entities?.patient_information?.find(p => p.field === "Patient Name")?.value || "Demo Patient" }],
          gender: analysisResult.entities?.patient_information?.find(p => p.field === "Gender / Sex")?.value?.toLowerCase() || "unknown"
        }
      },
      {
        resource: {
          resourceType: "Composition",
          status: "final",
          type: {
            coding: [{ system: "http://loinc.org", code: "34133-9", display: "Nursing shift handover note" }]
          },
          subject: { reference: "Patient/pulse-patient-demo" },
          text: {
            status: "generated",
            div: `<div xmlns="http://www.w3.org/1999/xhtml">${analysisResult.executive_summary}</div>`
          }
        }
      },
      ...(analysisResult.entities?.medications || []).map((med, idx) => ({
        resource: {
          resourceType: "MedicationStatement",
          status: "active",
          medicationCodeableConcept: { text: med.normalized },
          dosage: [{ text: `${med.dosage || ''} ${med.route || ''} ${med.frequency || ''}`.trim() }],
          subject: { reference: "Patient/pulse-patient-demo" }
        }
      }))
    ]
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="fhir-modal-dialog" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <h3>HL7 FHIR R4 Interoperability Bundle</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>×</button>
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
