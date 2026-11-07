/**
 * Clinical shorthand recognition, quick-insert handover structures and a
 * deterministic entity pass used by the latency sandbox.
 */

export const CLINICAL_ABBREVIATIONS = [
  { short: 'T2DM', expanded: 'Type 2 diabetes mellitus', note: 'Endocrine history', pattern: /\bT2DM\b/gi },
  { short: 'T1DM', expanded: 'Type 1 diabetes mellitus', note: 'Endocrine history', pattern: /\bT1DM\b/gi },
  { short: 'GCS 15', expanded: 'Glasgow Coma Scale 15/15 (alert)', note: 'Neurological observation', pattern: /\bGCS\s*(?:of\s*)?15\b/gi },
  { short: 'GCS', expanded: 'Glasgow Coma Scale', note: 'Neurological observation', pattern: /\bGCS\b(?!\s*(?:of\s*)?15)/gi },
  { short: 'IVF', expanded: 'intravenous fluids', note: 'Fluid resuscitation', pattern: /\bIVF\b/gi },
  { short: 'PRN', expanded: 'pro re nata — as required', note: 'Medication frequency', pattern: /\bPRN\b/gi },
  { short: 'BGL', expanded: 'blood glucose level', note: 'Capillary glucose', pattern: /\bBGL\b/gi },
  { short: 'NPO', expanded: 'nil per os — nothing by mouth', note: 'Fasting status', pattern: /\bNPO\b/gi },
  { short: 'SOB', expanded: 'shortness of breath', note: 'Respiratory symptom', pattern: /\bSOB\b/gi },
  { short: 'SpO2', expanded: 'peripheral oxygen saturation', note: 'Vital sign', pattern: /\bSpO2\b/gi },
  { short: 'BP', expanded: 'blood pressure', note: 'Vital sign', pattern: /\bBP\b/gi },
  { short: 'HR', expanded: 'heart rate', note: 'Vital sign', pattern: /\bHR\b/gi },
  { short: 'ECG', expanded: 'electrocardiogram', note: 'Cardiac investigation', pattern: /\bECG\b/gi },
  { short: 'MET', expanded: 'Medical Emergency Team', note: 'Escalation pathway', pattern: /\bMET\b/gi },
  { short: 'ISBAR', expanded: 'Identify, Situation, Background, Assessment, Recommendation', note: 'Handover structure', pattern: /\bISBAR\b/gi },
  { short: 'c/o', expanded: 'complains of', note: 'Presenting complaint', pattern: /\bc\/o\b/gi },
  { short: 'h/o', expanded: 'history of', note: 'Past medical history', pattern: /\bh\/o\b/gi },
  { short: 'BD', expanded: 'twice daily', note: 'Medication frequency', pattern: /\bBD\b/gi },
  { short: 'TDS', expanded: 'three times daily', note: 'Medication frequency', pattern: /\bTDS\b/gi },
  { short: 'SOS', expanded: 'as needed', note: 'Medication frequency', pattern: /\bSOS\b/gi },
];

export function scanClinicalAbbreviations(text) {
  if (!text || !text.trim()) return [];
  return CLINICAL_ABBREVIATIONS.flatMap((entry) => {
    const pattern = new RegExp(entry.pattern.source, entry.pattern.flags.includes('g') ? entry.pattern.flags : `${entry.pattern.flags}g`);
    const count = (text.match(pattern) || []).length;
    return count > 0 ? [{ ...entry, count }] : [];
  });
}

function patientFields(patient = {}) {
  return {
    name: patient.name || 'the patient',
    age: patient.age || '—',
    gender: patient.gender || '—',
    ward: patient.ward || 'General Medical',
    bed: patient.bed_number || 'unassigned bed',
    mrn: patient.display_id || patient.id || '—',
  };
}

export const QUICK_INSERT_TEMPLATES = [
  {
    id: 'isbar',
    label: 'ISBAR Template',
    description: 'Full structured shift handover',
    build(patient) {
      const p = patientFields(patient);
      return `ISBAR HANDOVER — ${p.name} (${p.mrn}), ${p.ward}, ${p.bed}\n\nIDENTIFY: ${p.name}, ${p.age} years, ${p.gender}. MRN ${p.mrn}. Under the care of the attending team.\n\nSITUATION: Admitted with [presenting complaint]. Currently [stable / deteriorating] with NEWS2 [score].\n\nBACKGROUND: Relevant history includes [comorbidities]. Regular medications: [list]. Allergies: [state or NKDA].\n\nASSESSMENT: Vital observations [HR, BP, RR, SpO2, temperature, ACVPU]. Focused assessment [findings].\n\nRECOMMENDATION: [Pending investigations / reviews / escalating tasks]. Escalate to [clinician] if [trigger].`;
    },
  },
  {
    id: 'post-op',
    label: 'Post-Op Surgical',
    description: 'Theatre-to-ward recovery handover',
    build(patient) {
      const p = patientFields(patient);
      return `POST-OPERATIVE HANDOVER — ${p.name} (${p.mrn}), ${p.ward}, ${p.bed}\n\nPROCEDURE: [Operation name] under [anaesthetic]. Theatre time [start–end].\n\nRECOVERY: Airway patent, breathing spontaneous, SpO2 [value]% on [oxygen]. BP [value], HR [value], temperature [value], pain score [0–10].\n\nWOUND / DRAINS: [Dressing condition], drains [output and type], catheter [present / absent].\n\nMEDICATIONS: Analgesia [drug, route, frequency]. Antiemetic PRN. VTE prophylaxis [agent and dose].\n\nPLAN: Hourly observations for [duration]. Mobilise [plan]. Next surgical review [time]. Escalate for [red flags].`;
    },
  },
  {
    id: 'neuro',
    label: 'Neurological Obs',
    description: 'GCS, pupils and neuro observations',
    build(patient) {
      const p = patientFields(patient);
      return `NEUROLOGICAL OBSERVATION HANDOVER — ${p.name} (${p.mrn}), ${p.ward}, ${p.bed}\n\nNEURO STATUS: GCS 15 (E4 V5 M6). Pupils equal and reactive to light, size [mm]. Limb power [describe]. Speech [intact / affected].\n\nVITALS: BP [value], HR [value], RR [value], SpO2 [value]%, temperature [value], BGL [value] mmol/L.\n\nEVENTS: [Seizure activity / agitation / new confusion / none]. Last neurological observation at [time].\n\nMEDICATIONS: [Neuro medications, sedation, analgesia].\n\nPLAN: Neuro observations every [frequency]. Maintain head-up [angle]. Escalate immediately for GCS drop ≥2, new focal deficit, pupil change or systolic BP below [threshold].`;
    },
  },
];

export function buildQuickTemplate(templateId, patient) {
  const template = QUICK_INSERT_TEMPLATES.find((item) => item.id === templateId);
  return template ? template.build(patient) : '';
}

const ENTITY_DICTIONARY = [
  {
    category: 'CONDITION',
    terms: ['hypertension', 'diabetes', 'T2DM', 'T1DM', 'asthma', 'COPD', 'pneumonia', 'sepsis', 'stroke', 'CAD', 'atrial fibrillation', 'AKI', 'CKD', 'pancreatitis', 'DVT', 'cancer', 'fracture'],
  },
  {
    category: 'SYMPTOM',
    terms: ['chest pain', 'shortness of breath', 'SOB', 'fever', 'cough', 'vomiting', 'nausea', 'headache', 'vertigo', 'confusion', 'abdominal pain', 'swelling', 'fatigue', 'dizziness'],
  },
  {
    category: 'MEDICATION',
    terms: ['paracetamol', 'aspirin', 'insulin', 'heparin', 'clexane', 'morphine', 'ondansetron', 'amoxicillin', 'furosemide', 'GTN', 'metformin', 'actrapid', 'vancomycin'],
  },
  {
    category: 'OBSERVATION',
    terms: ['BP', 'HR', 'RR', 'SpO2', 'temperature', 'GCS 15', 'BGL', 'NEWS2', 'blood pressure', 'heart rate'],
  },
  {
    category: 'INVESTIGATION',
    terms: ['CT scan', 'MRI', 'X-ray', 'ultrasound', 'ECG', 'troponin', 'blood culture', 'lipase', 'LFT', 'MRCP', 'doppler', 'blood test'],
  },
  {
    category: 'TASK',
    terms: ['recheck', 'review', 'escalate', 'monitor', 'repeat', 'administer', 'mobilise', 'catheterise', 'fasting', 'NPO'],
  },
];

export function recognizeEntities(text, minimumConfidence = 0.7) {
  if (!text || !text.trim()) return [];
  const source = text.toLowerCase();
  const found = [];
  const seen = new Set();

  ENTITY_DICTIONARY.forEach((group) => {
    group.terms.forEach((term) => {
      const index = source.indexOf(term.toLowerCase());
      if (index === -1) return;
      const key = `${group.category}:${term.toLowerCase()}`;
      if (seen.has(key)) return;
      seen.add(key);
      const specificity = Math.min(0.09, term.length * 0.006);
      const positionBoost = index < source.length * 0.5 ? 0.02 : 0.005;
      const confidence = Math.min(0.99, 0.86 + specificity + positionBoost);
      if (confidence >= minimumConfidence) {
        found.push({
          text: text.slice(index, index + term.length),
          category: group.category,
          confidence: Number(confidence.toFixed(2)),
          start: index,
        });
      }
    });
  });

  return found.sort((a, b) => a.start - b.start);
}
