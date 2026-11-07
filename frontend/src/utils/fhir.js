/**
 * FHIR R4 export helpers shared by the handover and analysis pages.
 */

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fieldValue(patientInformation, field) {
  return patientInformation?.find((item) => item.field === field)?.value;
}

export function buildBundleFromAnalysis(analysisResult) {
  const patientName = fieldValue(analysisResult?.entities?.patient_information, 'Patient Name') || 'Demo Patient';
  const patientId = 'pulse-patient-demo';
  const now = new Date().toISOString();
  const isbar = analysisResult?.isbar || {};
  const join = (value) => (Array.isArray(value) ? value.join(' ') : value || 'Not recorded');

  const compositionSections = [
    { title: 'Identify', code: '55188-7', text: join(isbar.identify) },
    { title: 'Situation', code: '46241-6', text: join(isbar.situation) },
    { title: 'Background', code: '11348-0', text: join(isbar.background) },
    { title: 'Assessment', code: '51848-0', text: join(isbar.assessment) },
    { title: 'Recommendation', code: '18776-5', text: join(isbar.recommendation) },
  ];

  return {
    resourceType: 'Bundle',
    type: 'document',
    id: `pulse-handover-${Date.now()}`,
    timestamp: now,
    entry: [
      {
        resource: {
          resourceType: 'Patient',
          id: patientId,
          name: [{ text: patientName }],
          gender: (fieldValue(analysisResult?.entities?.patient_information, 'Gender / Sex') || 'unknown').toLowerCase(),
        },
      },
      {
        resource: {
          resourceType: 'Composition',
          id: 'pulse-composition-1',
          status: 'final',
          type: {
            coding: [{ system: 'http://loinc.org', code: '34133-9', display: 'Nursing shift handover note' }],
          },
          subject: { reference: `Patient/${patientId}` },
          date: now,
          title: 'PULSE Structured Clinical Handover',
          section: compositionSections.map((section) => ({
            title: section.title,
            code: { coding: [{ system: 'http://loinc.org', code: section.code, display: section.title }] },
            text: { status: 'generated', div: `<div xmlns="http://www.w3.org/1999/xhtml">${escapeHtml(section.text)}</div>` },
          })),
        },
      },
      ...(analysisResult?.entities?.conditions || []).map((condition, index) => ({
        resource: {
          resourceType: 'Condition',
          id: `condition-${index + 1}`,
          clinicalStatus: { coding: [{ code: 'active' }] },
          code: { text: condition.normalized || condition.text },
          subject: { reference: `Patient/${patientId}` },
        },
      })),
      ...(analysisResult?.entities?.medications || []).map((medication, index) => ({
        resource: {
          resourceType: 'MedicationStatement',
          id: `medication-${index + 1}`,
          status: 'active',
          medicationCodeableConcept: { text: medication.normalized || medication.text },
          dosage: [{ text: `${medication.dosage || ''} ${medication.route || ''} ${medication.frequency || ''}`.trim() }],
          subject: { reference: `Patient/${patientId}` },
        },
      })),
      ...(analysisResult?.structured_handover?.pending_tasks || []).map((task, index) => ({
        resource: {
          resourceType: 'Task',
          id: `task-${index + 1}`,
          status: 'requested',
          intent: 'order',
          description: typeof task === 'string' ? task : task.task || 'Pending clinical task',
          subject: { reference: `Patient/${patientId}` },
        },
      })),
    ],
  };
}

function resourceSummary(resource) {
  const code = resource.code?.coding?.[0];
  const typeCode = resource.type?.coding?.[0];
  const valueQuantity = resource.valueQuantity;
  const value = valueQuantity
    ? `${valueQuantity.value ?? ''} ${valueQuantity.unit || ''}`.trim()
    : resource.dosage?.[0]?.text ||
      resource.description ||
      resource.text?.div?.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() ||
      '';

  return {
    resource_type: resource.resourceType || '',
    id: resource.id || '',
    status: resource.status || resource.clinicalStatus?.coding?.[0]?.code || '',
    code: code?.code || typeCode?.code || '',
    display: code?.display || typeCode?.display || resource.medicationCodeableConcept?.text || '',
    subject: resource.subject?.reference || '',
    value,
    effective: resource.date || resource.effectiveDateTime || '',
  };
}

export function bundleToCsv(bundle) {
  const headers = ['resource_type', 'id', 'status', 'code', 'display', 'subject', 'value', 'effective'];
  const rows = (bundle?.entry || []).map((entry) => resourceSummary(entry.resource || {}));
  const escapeCell = (value) => `"${String(value ?? '').replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`;
  return [headers.join(','), ...rows.map((row) => headers.map((header) => escapeCell(row[header])).join(','))].join('\n');
}

export function downloadTextFile(filename, content, mimeType = 'text/plain') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => URL.revokeObjectURL(url), 400);
}
