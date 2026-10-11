/**
 * PULSE Client-Side Clinical NLP Engine
 * Enables 100% offline & static cloud execution (e.g. Vercel, Netlify, GitHub Pages).
 * Provides seamless fallback when Python FastAPI backend is not locally accessible.
 */

import datasetData from '../data/dataset.json';

// Clinical Abbreviations Map
const ABBREVIATIONS_MAP = {
  "BP": "Blood Pressure",
  "GCS": "Glasgow Coma Scale",
  "BGL": "Blood Glucose Level",
  "BGLS": "Blood Glucose Levels",
  "BSL": "Blood Sugar Level",
  "MRI": "Magnetic Resonance Imaging",
  "CT": "Computed Tomography",
  "ECG": "Electrocardiogram",
  "IV": "Intravenous",
  "PRN": "Pro Re Nata (As Needed)",
  "QID": "Quater In Die (Four Times Daily)",
  "BD": "Bis In Die (Twice Daily)",
  "TDS": "Ter Die Sumendum (Three Times Daily)",
  "AF": "Atrial Fibrillation",
  "COPD": "Chronic Obstructive Pulmonary Disease",
  "DM": "Diabetes Mellitus",
  "HPN": "Hypertension",
  "HTN": "Hypertension",
  "UTI": "Urinary Tract Infection",
  "MRSA": "Methicillin-Resistant Staphylococcus Aureus",
  "OBS": "Observations / Vital Signs",
  "CXR": "Chest X-Ray",
  "FBC": "Full Blood Count",
  "IDC": "Indwelling Catheter",
  "ADL": "Activities of Daily Living",
  "SOB": "Shortness of Breath"
};

// Preprocessor
export function preprocessTextLocal(rawText) {
  if (!rawText) {
    return { 
      raw_text: "", 
      preprocessed_text: "", 
      changes_made: ["Received empty input string"],
      preserved_clinical_elements: [],
      sentences: [],
      token_count: 0,
      char_count: 0,
      philosophy_note: "Non-destructive clinical normalization."
    };
  }

  let text = rawText;
  const changes = [];

  // 1. Strip UTF-8 BOM if present
  if (text.includes('\ufeff')) {
    text = text.replaceAll('\ufeff', '');
    changes.push("Stripped hidden UTF-8 Byte Order Mark (BOM)");
  }

  // 2. Unicode replacements for quotes & dashes
  const unicodeMap = {
    '’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-', '\u00a0': ' '
  };
  let replacedUnicode = false;
  for (const [k, v] of Object.entries(unicodeMap)) {
    if (text.includes(k)) {
      text = text.replaceAll(k, v);
      replacedUnicode = true;
    }
  }
  if (replacedUnicode) {
    changes.push("Normalized Unicode curly quotes, smart apostrophes, and typographical dashes to ASCII");
  }

  // 3. Spacing around commas: letter,letter or letter,digit or digit,letter
  const commaRegex1 = /([a-zA-Z]),([a-zA-Z0-9])/g;
  const commaRegex2 = /([0-9]),([a-zA-Z])/g;
  let hasCommaFixed = false;
  text = text.replace(commaRegex1, (m, p1, p2) => {
    hasCommaFixed = true;
    changes.push(`Fixed comma spacing: '${m}' -> '${p1}, ${p2}'`);
    return `${p1}, ${p2}`;
  });
  text = text.replace(commaRegex2, (m, p1, p2) => {
    hasCommaFixed = true;
    changes.push(`Fixed comma spacing: '${m}' -> '${p1}, ${p2}'`);
    return `${p1}, ${p2}`;
  });

  // 4. Resolve squished sentence boundaries after periods (e.g. 'her.no plan' -> 'her. No plan', 'glaucoma.almost' -> 'glaucoma. Almost')
  const periodRegex = /([a-zA-Z]{2,})\.([a-zA-Z])/g;
  text = text.replace(periodRegex, (m, before, after) => {
    const lowerBefore = before.toLowerCase();
    if (['dr', 'mr', 'ms', 'mrs', 'vs', 'eg', 'ie', 'st'].includes(lowerBefore)) {
      return m;
    }
    const capitalized = after.toUpperCase();
    changes.push(`Fixed sentence boundary spacing & capitalization: '${before}.${after}' -> '${before}. ${capitalized}'`);
    return `${before}. ${capitalized}`;
  });

  // 5. Normalize doctor titles/honorifics (e.g. 'DR Smith' -> 'Dr. Smith')
  const doctorRegex = /\b(?:DR|dr)\s+([A-Z])/g;
  text = text.replace(doctorRegex, (m, initial) => {
    changes.push(`Standardized doctor honorific: '${m}' -> 'Dr. ${initial}'`);
    return `Dr. ${initial}`;
  });

  // 6. Whitespace normalization: collapse multiple consecutive spaces
  if (/[ \t\r\n]{2,}/.test(text)) {
    changes.push("Collapsed redundant consecutive whitespace into single spaces");
    text = text.replace(/[ \t\r\n]+/g, ' ');
  }

  // 7. Trim leading/trailing whitespace
  const trimmed = text.trim();
  if (trimmed !== text) {
    changes.push("Trimmed leading/trailing whitespace");
    text = trimmed;
  }

  // 8. Record non-destructive clinical preservation guarantees
  const preserved = [];
  if (/[@\+_]/.test(text)) {
    preserved.push("Preserved clinically meaningful symbols (@, +, _)");
  }
  if (/\b\d+(\.\d+)?\s*(mg|mcg|g|ml|mmol|%|bpm|mmHg)?\b/i.test(text)) {
    preserved.push("Preserved numerical dosages, vitals (e.g. BP, BGL) and clinical measurement units");
  }
  if (/\b[A-Z]{2,}\b/.test(text)) {
    preserved.push("Preserved clinical acronyms (GCS, BP, IV, COPD) without destructive lowercasing");
  }
  if (/\b(no|not|denies|without|none|never)\b/i.test(text)) {
    preserved.push("Preserved negative assertion terms ('no', 'without') to prevent dangerous false-positive inferences");
  }

  if (changes.length === 0) {
    changes.push("Input text formatting conforms to clinical preprocessing standards");
  }

  // Split sentences for inspection
  const safeText = text.replace(/\b(Dr|Mr|Mrs|Ms|vs|eg|ie|St)\./gi, '$1<DOT>');
  const rawParts = safeText.split(/[.!?]+\s+/);
  const sentences = rawParts.map(p => {
    let cleanP = p.replaceAll('<DOT>', '.').trim();
    if (cleanP && !cleanP.endsWith('.') && !cleanP.endsWith('!') && !cleanP.endsWith('?')) {
      cleanP += '.';
    }
    return cleanP;
  }).filter(Boolean);

  const tokens = (text.match(/\b\w+\b/g) || []);

  return {
    raw_text: rawText,
    preprocessed_text: text,
    changes_made: changes,
    preserved_clinical_elements: preserved,
    sentences: sentences,
    token_count: tokens.length,
    char_count: text.length,
    philosophy_note: "Non-destructive clinical normalization: unlike traditional text mining, clinical NLP must never destroy clinical acronyms, vital numbers/dosages, or negations."
  };
}

// Split into sentences with offsets
function splitSentences(text) {
  const spans = [];
  const regex = /([^.!?]+(?:[.!?]+|$))/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const s = match[0].trim();
    if (s) {
      spans.push({ text: s, start: match.index, end: match.index + match[0].length });
    }
  }
  if (spans.length === 0 && text) {
    spans.push({ text, start: 0, end: text.length });
  }
  return spans;
}

function findSentence(pos, sList) {
  for (const s of sList) {
    if (s.start <= pos && pos <= s.end) return s.text;
  }
  return sList[0]?.text || "";
}

// Clinical ConText / Assertion Analyzer
function analyzeAssertion(entityText, startChar, endChar, fullText, sList) {
  let sentText = fullText;
  let sentStart = 0;
  for (const s of sList) {
    if (s.start <= startChar && startChar <= s.end) {
      sentText = s.text;
      sentStart = s.start;
      break;
    }
  }

  const relStart = Math.max(0, startChar - sentStart);
  const relEnd = Math.max(relStart, endChar - sentStart);
  let preText = sentText.slice(0, relStart);
  let postText = sentText.slice(relEnd);

  // Immediate compound suffix like "pain-free"
  if (/^-free\b/i.test(postText) || entityText.toLowerCase().endsWith('-free')) {
    return { assertion: "Negated", temporality: "Current", is_negated: true, is_uncertain: false, is_historical: false, is_planned: false, cue: "-free" };
  }

  // Pseudo-negation removal
  const pseudoNegs = [/\bno\s+further\b/gi, /\bno\s+increase\b/gi, /\bnot\s+only\b/gi, /\bnot\s+cause\b/gi, /\bwithout\s+difficulty\b/gi];
  for (const pnp of pseudoNegs) {
    preText = preText.replace(pnp, " ");
  }

  // Scope termination (take closest clause in preText)
  const scopeTerm = /\b(?:but|however|although|yet|except|aside\s+from|due\s+to)\b|[,;.!]/gi;
  let lastTermIdx = -1;
  let sm;
  while ((sm = scopeTerm.exec(preText)) !== null) {
    lastTermIdx = sm.index + sm[0].length;
  }
  const activePre = lastTermIdx >= 0 ? preText.slice(lastTermIdx) : preText;
  
  const postTermMatch = scopeTerm.exec(postText);
  const activePost = postTermMatch ? postText.slice(0, postTermMatch.index) : postText;

  // Pre-negation
  const preNegs = [
    /\b(?:denies|denied|denying)\b/i,
    /\b(?:no|not|non)\b/i,
    /\b(?:without|nil|none|never)\b/i,
    /\b(?:rules?\s*out|ruled\s*out|r\/o)\b/i,
    /\b(?:negative\s*(?:for)?)\b/i,
    /\b(?:absent|free\s*of)\b/i,
    /\b(?:no\s+evidence\s+of|no\s+sign\s+of|no\s+history\s+of)\b/i
  ];
  let assertion = "Affirmative";
  let cue = null;
  for (const pat of preNegs) {
    const pm = activePre.match(pat);
    if (pm) {
      assertion = "Negated";
      cue = pm[0];
      break;
    }
  }

  if (assertion === "Affirmative") {
    const postNegs = [/\bunlikely\b/i, /\b(?:free|resolved|ceased|negative)\b/i, /\bwas\s+ruled\s+out\b/i];
    for (const pat of postNegs) {
      const pm = activePost.match(pat);
      if (pm) {
        assertion = "Negated";
        cue = pm[0];
        break;
      }
    }
  }

  if (assertion === "Affirmative") {
    const uncPats = [
      /\b(?:may|might|could|possible|possibly)\b/i,
      /\b(?:query|\?|suspected|suspicion\s+of)\b/i,
      /\b(?:evaluating\s+for|assessing\s+for|consider)\b/i,
      /\b(?:potential|probable|likely)\b/i,
      /\b(?:may\s+have|may\s+be|may\s+die)\b/i
    ];
    for (const pat of uncPats) {
      const pm = activePre.match(pat) || activePost.match(pat);
      if (pm) {
        assertion = "Possible";
        cue = pm[0];
        break;
      }
    }
  }

  // Temporality
  let temporality = "Current";
  const planPats = [
    /\b(?:planned\s+for|is\s+planned\s+for|scheduled\s+for|booked\s+for|tomorrow|next\s+shift|later|is\s+for|awaiting|pending)\b/i
  ];
  for (const pat of planPats) {
    const pm = activePre.match(pat) || activePost.match(pat);
    if (pm) {
      temporality = "Planned";
      break;
    }
  }

  if (temporality === "Current") {
    const histPats = [
      /\b(?:history\s+of|hx\s+of|background\s+of|past|previous|previously|prior\s+to|yesterday|earlier|former|\d+\s+days?\s+ago|since\s+childhood)\b/i
    ];
    for (const pat of histPats) {
      const pm = activePre.match(pat) || activePost.match(pat);
      if (pm) {
        temporality = "Historical";
        break;
      }
    }
  }

  return {
    assertion,
    temporality,
    is_negated: assertion === "Negated",
    is_uncertain: assertion === "Possible",
    is_historical: temporality === "Historical",
    is_planned: temporality === "Planned",
    cue: cue || "Direct statement"
  };
}

// Entity & Event Extraction
export function analyzeLocalEngine({ reportId, rawText, engine }) {
  let text = rawText || "";
  if (reportId && !text.trim()) {
    const found = datasetData.reports.find(r => String(r.report_id) === String(reportId));
    if (found) text = found.raw_text;
  }

  const prep = preprocessTextLocal(text);
  const clean = prep.preprocessed_text;
  const sList = splitSentences(clean);

  // 1. Demographics
  const patientInfo = [];
  const bedM = clean.match(/\b(?:bed|room)\s+([a-zA-Z0-9]+)\b/i);
  if (bedM) {
    patientInfo.push({
      category: "Patient Information",
      field: "Bed / Room",
      value: bedM[0],
      detail: `Bed ${bedM[1]}`,
      confidence: "High (Rule Pattern)",
      source_sentence: findSentence(bedM.index, sList),
      start_char: bedM.index,
      end_char: bedM.index + bedM[0].length
    });
  }

  const namePatterns = [
    /(?:bed\s+[a-zA-Z0-9]+[\s,]+)([A-Z][a-zA-Z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z]+)/i,
    /^([A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+){1,3})(?:[\s,]+(?:bed|\d+|under))/i,
    /(?:patient\s+is\s+)([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)/i
  ];
  for (const pat of namePatterns) {
    const m = clean.match(pat);
    if (m) {
      const val = m[1].replace(/[,.]/g, '').trim();
      if (!['the patient', 'he came', 'she came', 'bed'].includes(val.toLowerCase())) {
        const idx = m.index + m[0].indexOf(m[1]);
        patientInfo.push({
          category: "Patient Information",
          field: "Patient Name",
          value: val,
          detail: val,
          confidence: "High (Named Entity Context)",
          source_sentence: findSentence(idx, sList),
          start_char: idx,
          end_char: idx + val.length
        });
        break;
      }
    }
  }

  const ageM = clean.match(/\b(\d{1,3})\s*(?:years|yo|y\.?o\.?|years\s*old)\b/i) ||
               clean.match(/\b(?:Forty-eight|Fifty|Sixty|Seventy|Eighty|Ninety|Twenty|Thirty)[-\s]?[a-zA-Z]*\s*years\b/i) ||
               clean.match(/,\s*(\d{1,3})\s*,\s*bed/i) ||
               clean.match(/bed\s+\d+[\s,]+(\d{1,3})\s+under/i);
  if (ageM) {
    const ageVal = ageM[1] ? `${ageM[1]} years` : ageM[0];
    patientInfo.push({
      category: "Patient Information",
      field: "Age",
      value: ageVal,
      detail: ageVal,
      confidence: "High (Rule Pattern)",
      source_sentence: findSentence(ageM.index, sList),
      start_char: ageM.index,
      end_char: ageM.index + ageM[0].length
    });
  }

  const genM = clean.match(/\b(he|his|him|she|her|hers|male|female)\b/i);
  if (genM) {
    const isMale = ['he', 'his', 'him', 'male'].includes(genM[1].toLowerCase());
    patientInfo.push({
      category: "Patient Information",
      field: "Gender / Sex",
      value: isMale ? "Male" : "Female",
      detail: `Verified via pronoun ('${genM[1]}')`,
      confidence: "High (Lexical Match)",
      source_sentence: findSentence(genM.index, sList),
      start_char: genM.index,
      end_char: genM.index + genM[0].length
    });
  }

  const docM = clean.match(/\b(?:under\s+)?(Dr\.?\s+[A-Z][a-zA-Z]+)\b/);
  if (docM) {
    const dVal = docM[1];
    const dIdx = docM.index + docM[0].indexOf(docM[1]);
    patientInfo.push({
      category: "Patient Information",
      field: "Attending Consultant",
      value: dVal,
      detail: dVal,
      confidence: "High (Named Entity Context)",
      source_sentence: findSentence(dIdx, sList),
      start_char: dIdx,
      end_char: dIdx + dVal.length
    });
  }

  // 2. Conditions
  const condPatterns = [
    [/\b(?:type\s*1\s*dm|type\s*1\s*diabetes)\b/gi, "Type 1 Diabetes Mellitus"],
    [/\b(?:type\s*2\s*dm|type\s*2\s*diabetes)\b/gi, "Type 2 Diabetes Mellitus"],
    [/\b(?:diabetes\s*mellitus|diabetes)\b/gi, "Diabetes Mellitus"],
    [/\b(?:hpn|htn|hypertension|high\s*blood\s*pressure)\b/gi, "Hypertension"],
    [/\b(?:copd|chronic\s*obstructive\s*pulmonary\s*disease)\b/gi, "Chronic Obstructive Pulmonary Disease"],
    [/\b(?:asthma)\b/gi, "Asthma"],
    [/\b(?:stroke|cva|transient\s*ischaemic\s*attack|tia)\b/gi, "Cerebrovascular Accident / Stroke"],
    [/\b(?:bell['']s\s*palsy|facial\s*palsy)\b/gi, "Bell's Palsy (Facial Palsy)"],
    [/\b(?:cataract|cataracts)\b/gi, "Cataracts"],
    [/\b(?:glaucoma)\b/gi, "Glaucoma"],
    [/\b(?:atrial\s*fibrillation|af)\b/gi, "Atrial Fibrillation"],
    [/\b(?:urinary\s*tract\s*infection|uti)\b/gi, "Urinary Tract Infection"],
    [/\b(?:infection|wound\s*infection|chest\s*infection)\b/gi, "Infection (Suspected / Documented)"]
  ];
  const conditionsMap = {};
  for (const [pat, norm] of condPatterns) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      const ctx = analyzeAssertion(m[0], m.index, m.index + m[0].length, clean, sList);
      const key = `${norm}_${ctx.assertion}_${ctx.temporality}`;
      if (!conditionsMap[key]) {
        conditionsMap[key] = {
          category: "Condition",
          text: m[0],
          normalized: norm,
          assertion: ctx.assertion,
          temporality: ctx.temporality,
          is_negated: ctx.is_negated,
          is_uncertain: ctx.is_uncertain,
          is_historical: ctx.is_historical,
          is_planned: ctx.is_planned,
          context_cue: ctx.cue,
          confidence: "High (Clinical Lexicon & Context Scope)",
          source_sentence: findSentence(m.index, sList),
          start_char: m.index,
          end_char: m.index + m[0].length,
          all_spans: [[m.index, m.index + m[0].length]],
          occurrences: 1
        };
      } else {
        conditionsMap[key].all_spans.push([m.index, m.index + m[0].length]);
        conditionsMap[key].occurrences++;
      }
    }
  }
  const conditions = Object.values(conditionsMap);

  // 3. Symptoms
  const sympPatterns = [
    [/\b(?:previous\s*chest\s*pains?|chest\s*pain[s]?)\b/gi, "Chest Pain / Angina Symptoms"],
    [/\b(?:headache[s]?)\b/gi, "Headache (Cephalgia)"],
    [/\b(?:vertigo)\b/gi, "Vertigo (Vestibular)"],
    [/\b(?:tinnitus)\b/gi, "Tinnitus"],
    [/\b(?:photophobia)\b/gi, "Photophobia (Light Sensitivity)"],
    [/\b(?:nausea|vomiting|emesis)\b/gi, "Nausea / Emesis"],
    [/\b(?:dizziness|lightheadedness|dizzy)\b/gi, "Dizziness / Presyncope"],
    [/\b(?:shortness\s*of\s*breath|dyspnoea|dyspnea|sob)\b/gi, "Dyspnea / Shortness of Breath"],
    [/\b(?:unsteady\s*(?:at\s*times)?|ataxia|unsteadiness|falls?|loss\s*of\s*balance)\b/gi, "Gait Unsteadiness / Ataxia"],
    [/\b(?:almost\s*blind|blind|impaired\s*vision|poor\s*vision)\b/gi, "Severe Visual Impairment"],
    [/\b(?:fever|febrile|pyrexia)\b/gi, "Febrile Episode / Fever"],
    [/\b(?:pain|ache)\b/gi, "Pain"]
  ];
  const symptomsMap = {};
  for (const [pat, norm] of sympPatterns) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      const ctx = analyzeAssertion(m[0], m.index, m.index + m[0].length, clean, sList);
      const key = `${norm}_${ctx.assertion}_${ctx.temporality}`;
      if (!symptomsMap[key]) {
        symptomsMap[key] = {
          category: "Symptom",
          text: m[0],
          normalized: norm,
          assertion: ctx.assertion,
          temporality: ctx.temporality,
          is_negated: ctx.is_negated,
          is_uncertain: ctx.is_uncertain,
          is_historical: ctx.is_historical,
          is_planned: ctx.is_planned,
          context_cue: ctx.cue,
          confidence: "High (Clinical Lexicon & Context Scope)",
          source_sentence: findSentence(m.index, sList),
          start_char: m.index,
          end_char: m.index + m[0].length,
          all_spans: [[m.index, m.index + m[0].length]],
          occurrences: 1
        };
      } else {
        symptomsMap[key].all_spans.push([m.index, m.index + m[0].length]);
        symptomsMap[key].occurrences++;
      }
    }
  }
  const symptoms = Object.values(symptomsMap);

  // 4. Medications
  const medPatterns = [
    [/\b(?:nitro|nitros|nitroglycerin|gtn)\b/gi, "Glyceryl Trinitrate (GTN / Nitro)"],
    [/\b(?:sliding\s*scale\s*insulin|variable\s*dose(?:\s*insulin)?|insulin|lantus|novorapid|actrapid)\b/gi, "Insulin (Subcutaneous Regimen)"],
    [/\b(?:antibiotic[s]?|ceftriaxone|augmentin|amoxicillin)\b/gi, "Antibiotic Therapy"],
    [/\b(?:paracetamol|panadol)\b/gi, "Paracetamol (Analgesia)"],
    [/\b(?:morphine|endone|oxycodone)\b/gi, "Opioid Analgesic"]
  ];
  const medsMap = {};
  for (const [pat, norm] of medPatterns) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      const src = findSentence(m.index, sList);
      const ctx = analyzeAssertion(m[0], m.index, m.index + m[0].length, clean, sList);
      const doseM = src.match(/\b(\d+\s*(?:mg|mcg|ml|units?|puffs?)|variable\s*dose|sliding\s*scale|\d+\s+nitros?)\b/i);
      const freqM = src.match(/\b(qid|bd|tds|prn|daily|mane|nocte)\b/i);
      const routeM = src.match(/\b(iv|oral|po|subcut|sc|topical|sublingual)\b/i);

      const key = `${norm}_${ctx.assertion}_${ctx.temporality}`;
      if (!medsMap[key]) {
        medsMap[key] = {
          category: "Medication",
          text: m[0],
          normalized: norm,
          dosage: doseM ? doseM[0] : "Unspecified dose in text",
          frequency: freqM ? freqM[0].toUpperCase() : "Per protocol",
          route: routeM ? routeM[0].toUpperCase() : "PO / Ward route",
          assertion: ctx.assertion,
          temporality: ctx.temporality,
          is_negated: ctx.is_negated,
          is_uncertain: ctx.is_uncertain,
          confidence: "High (Clinical Lexicon)",
          source_sentence: src,
          start_char: m.index,
          end_char: m.index + m[0].length,
          all_spans: [[m.index, m.index + m[0].length]],
          occurrences: 1
        };
      } else {
        medsMap[key].all_spans.push([m.index, m.index + m[0].length]);
        medsMap[key].occurrences++;
      }
    }
  }
  const medications = Object.values(medsMap);

  // 5. Investigations
  const invPatterns = [
    [/\b(?:brain\s*mri|mri(?:\s*scan)?)\b/gi, "Brain Magnetic Resonance Imaging (MRI)"],
    [/\b(?:carotid\s*doppler|doppler\s*ultrasound|carotid\s*ultrasound)\b/gi, "Carotid Doppler Ultrasound"],
    [/\b(?:ct(?:\s*scan)?|computed\s*tomography)\b/gi, "Computed Tomography (CT Scan)"],
    [/\b(?:ecg|electrocardiogram|telemetry)\b/gi, "12-Lead ECG / Telemetry"],
    [/\b(?:chest\s*x-?ray|cxr|x-?ray)\b/gi, "Chest Radiography (CXR)"],
    [/\b(?:bgl[s]?|blood\s*glucose|blood\s*sugar|bsl)\b/gi, "Blood Glucose Monitoring (BGL)"],
    [/\b(?:renal\s*biopsy|biopsy)\b/gi, "Renal Biopsy / Diagnostic Tissue Biopsy"]
  ];
  const invMap = {};
  for (const [pat, norm] of invPatterns) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      const ctx = analyzeAssertion(m[0], m.index, m.index + m[0].length, clean, sList);
      const key = `${norm}_${ctx.assertion}_${ctx.temporality}`;
      if (!invMap[key]) {
        invMap[key] = {
          category: "Investigation",
          text: m[0],
          normalized: norm,
          assertion: ctx.assertion,
          temporality: ctx.temporality,
          is_negated: ctx.is_negated,
          is_uncertain: ctx.is_uncertain,
          is_planned: ctx.is_planned,
          confidence: "High (Clinical Lexicon)",
          source_sentence: findSentence(m.index, sList),
          start_char: m.index,
          end_char: m.index + m[0].length,
          all_spans: [[m.index, m.index + m[0].length]],
          occurrences: 1
        };
      } else {
        invMap[key].all_spans.push([m.index, m.index + m[0].length]);
        invMap[key].occurrences++;
      }
    }
  }
  const investigations = Object.values(invMap);

  // 6. Treatments
  const trtPatterns = [
    [/\b(?:sliding\s*scale\s*insulin|variable\s*dose(?:\s*insulin)?)\b/gi, "Sliding Scale Glycemic Protocol"],
    [/\b(?:needs\s*assistance|assistance\s*with\s*adls?|assistance|self\s*caring|ambulant)\b/gi, "ADL & Ward Mobility Level"],
    [/\b(?:monitoring|under\s*monitoring|still\s*under\s*monitoring)\b/gi, "Clinical & Vital Sign Monitoring"],
    [/\b(?:referral\s*to\s*the\s*diabetic\s*educator|referral\s*to\s*[a-zA-Z\s]+)\b/gi, "Allied Health / Specialist Referral"]
  ];
  const trtMap = {};
  for (const [pat, norm] of trtPatterns) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      if (!trtMap[norm]) {
        trtMap[norm] = {
          category: "Treatment",
          text: m[0],
          normalized: norm,
          confidence: "High (Clinical Lexicon)",
          source_sentence: findSentence(m.index, sList),
          start_char: m.index,
          end_char: m.index + m[0].length,
          all_spans: [[m.index, m.index + m[0].length]],
          occurrences: 1
        };
      }
    }
  }
  const treatments = Object.values(trtMap);

  // 7. Measurements
  const measPatterns = [
    [/\b(?:bp|blood\s*pressure)(?:\s*(?:is|was|of|recorded\s*as)?)?\s*(\d{2,3}\s*\/\s*\d{2,3}(?:\s*mmhg)?|not\s*so\s*bad|high\s*normal(?:\s*range)?|stable|elevated|low|high)\b/gi, "Blood Pressure"],
    [/\b(?:gcs)(?:\s*(?:is|was|of)?)?\s*(\d{1,2}(?:\s*(?:pupils?\s*equal\s*and\s*reactive|pupils?\s*reactive)?)?)\b/gi, "Glasgow Coma Scale (GCS)"],
    [/\b(?:obs|observations)(?:\s*(?:are|were)?)?\s*(stable|unstable|satisfactory)\b/gi, "General Vital Observations"],
    [/\b(?:pupils?\s*(?:are\s*)?equal\s*and\s*reactive)\b/gi, "Pupillary Reflex"]
  ];
  const measurements = [];
  for (const [pat, type] of measPatterns) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      measurements.push({
        category: "Measurement",
        type,
        text: m[0],
        confidence: "High (Clinical Pattern)",
        source_sentence: findSentence(m.index, sList),
        start_char: m.index,
        end_char: m.index + m[0].length
      });
    }
  }

  // 8. Abbreviations
  const abbreviations = [];
  const seenAbbr = new Set();
  for (const [abbr, expansion] of Object.entries(ABBREVIATIONS_MAP)) {
    const reg = new RegExp(`\\b${abbr}\\b`, 'g');
    let m;
    while ((m = reg.exec(clean)) !== null) {
      if (!seenAbbr.has(abbr)) {
        seenAbbr.add(abbr);
        abbreviations.push({
          abbreviation: abbr,
          expansion,
          source_sentence: findSentence(m.index, sList),
          start_char: m.index,
          end_char: m.index + m[0].length
        });
      }
    }
  }

  // 9. Clinical Events
  const events = [];
  const evRules = [
    [/\b(?:came\s+in(?:\s+for|\s+with)?|admitted(?:\s+for|\s+with)?|presented(?:\s+with)?)\s+([^.,;]+)/gi, "Admission / Presentation", "Patient admitted with/for {0}"],
    [/\b(?:had|given|received|administered)\s+(\d+\s+nitros?|antibiotics?|insulin|medication[s]?[^.,;]*)/gi, "Medication Administration", "Administered {0}"],
    [/\b(?:just\s+came\s+back\s+from|returned\s+from|completed)\s+([^.,;]*(?:mri|scan|ct|doppler)[^.,;]*)/gi, "Investigation Completed", "Completed investigation: {0}"],
    [/\b(?:a\s+([a-zA-Z\s]+?(?:biopsy|procedure|surgery|scan))\s+is\s+planned\s+for\s+([^.,;]+))/gi, "Investigation / Procedure Scheduled", "Scheduled for {0} (timing: {1})"],
    [/\b(?:is\s+planned\s+for|planned\s+for|is\s+for|scheduled\s+for|supposed\s+to\s+have)\s+([^.,;]*(?:biopsy|carotid\s+doppler|mri|scan|procedure)[^.,;]*)/gi, "Investigation / Procedure Scheduled", "Scheduled for {0}"],
    [/\b(?:pushed\s+(?:it\s+)?back\s+to|rescheduled\s+to|needs\s+another)\s+([^.,;]+)/gi, "Investigation Rescheduled", "Investigation rescheduled/pending: {0}"],
    [/\b(gcs\s+is\s+\d+[^.,;]*|obs\s+are\s+stable|pupils?\s*equal\s*and\s*reactive)/gi, "Clinical Status Assessment", "Assessment: {0}"],
    [/\b(?:still\s+for\s+referral\s+to|referred\s+to)\s+([^.,;]+)/gi, "Consultation / Referral", "Referral requested for {0}"],
    [/\b(?:still\s+need\s+(?:the\s+)?team\s+to\s+review|still\s+for\s+review)\s*([^.,;]*)/gi, "Clinical Review Event", "Clinical review pending by medical team"]
  ];
  for (const [pat, type, template] of evRules) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      let desc = template;
      if (m.length > 2 && template.includes('{1}')) {
        desc = template.replace('{0}', (m[1] || '').trim()).replace('{1}', (m[2] || '').trim());
      } else {
        const arg = m[1] ? m[1].trim() : m[0].trim();
        desc = template.replace('{0}', arg);
      }
      const src = findSentence(m.index, sList);
      events.push({
        event: desc,
        type,
        time: src.match(/\b(\d{3,4}|this\s+morning|tomorrow|yesterday)\b/i)?.[0] || "Not specified",
        source_sentence: src,
        start_char: m.index,
        end_char: m.index + m[0].length
      });
    }
  }

  // 10. Temporal Expressions
  const temporal = [];
  const tempPats = [
    [/\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b/gi, "Clock Time"],
    [/\b(?:at|to)\s+(\d{3,4})\b/gi, "Clinical Clock Time"],
    [/\b(today|tonight|this\s+morning|this\s+afternoon)\b/gi, "Immediate Shift"],
    [/\b(tomorrow|yesterday|next\s+shift)\b/gi, "Relative Anchor"],
    [/\b(for\s+the\s+last\s+(?:\d+|three|four|five)\s+years)\b/gi, "Duration"],
    [/\b(since\s+(?:childhood|yesterday))\b/gi, "Onset Anchor"]
  ];
  for (const [pat, type] of tempPats) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      const src = findSentence(m.index, sList);
      temporal.push({
        expression: m[0],
        type,
        associated_event: events.find(e => e.source_sentence === src)?.event || "Clinical event in shift",
        source_sentence: src,
        start_char: m.index,
        end_char: m.index + m[0].length
      });
    }
  }

  // 11. Pending Tasks & Follow-up
  const pendingTasks = [];
  const pendingPats = [
    [/\b([a-zA-Z\s]+?\s+is\s+planned\s+for\s+[^.,;]+)/gi, "Scheduled Investigation / Procedure", "Medium"],
    [/\b(?:is\s+planned\s+for|planned\s+for)\s+([^.,;]+)/gi, "Scheduled Investigation / Procedure", "Medium"],
    [/\b(?:needs\s+another|rescheduled|needs|waiting\s+for)\s+([^.,;]+)/gi, "Diagnostic Scheduling Pending", "High"],
    [/\b(?:still\s+for\s+referral\s+to|referral\s+to)\s+([^.,;]+)/gi, "Specialist Referral Pending", "Medium"],
    [/\b(?:still\s+need\s+(?:the\s+)?team\s+to\s+review|still\s+for\s+review)\b/gi, "Medical Team Review Pending", "High"],
    [/\b(?:just\s+ask\s+the\s+doctor\s+for\s+the\s+next\s+dose|ask\s+doctor)\b/gi, "Medication Dosing Clarification", "High"],
    [/\b(?:still\s+under\s+monitoring)\b/gi, "Ongoing Active Monitoring Required", "Medium"]
  ];
  for (const [pat, type, prio] of pendingPats) {
    let m;
    while ((m = pat.exec(clean)) !== null) {
      const src = findSentence(m.index, sList);
      pendingTasks.push({
        task: m[0].charAt(0).toUpperCase() + m[0].slice(1),
        type,
        priority: prio,
        source_sentence: src,
        start_char: m.index,
        end_char: m.index + m[0].length
      });
    }
  }

  const followUp = [];
  for (const pt of pendingTasks) {
    if (pt.task.toLowerCase().includes('referral') || pt.task.toLowerCase().includes('review') || pt.task.toLowerCase().includes('appointment')) {
      followUp.push({
        action: pt.task,
        type: "Specialist / Multidisciplinary Follow-Up",
        source_sentence: pt.source_sentence,
        start_char: pt.start_char,
        end_char: pt.end_char
      });
    }
  }

  // 12. Clinical Safety & Risk Alerts
  const clinicalRisks = [];
  const lower = clean.toLowerCase();

  // 1. Fall Risk: requires affirmative mobility or balance concern (not negated)
  const hasFallConcern = symptoms.some(s => ["Gait Unsteadiness / Ataxia", "Severe Visual Impairment"].includes(s.normalized) && !s.is_negated) ||
                         treatments.some(t => t.text.toLowerCase().includes("assistance") && !t.is_negated);
  if (hasFallConcern) {
    clinicalRisks.push({
      risk_type: "Fall Risk Alert",
      severity: "High",
      rationale: "Documented affirmative gait unsteadiness, sensory deficit, or mobility assistance required.",
      care_directive: "Ensure call bell within reach; assistance with all ward transfers; non-slip footwear."
    });
  }

  // 2. Cardiovascular Alert: MUST BE CURRENT AND AFFIRMATIVE! (not negated, not historical)
  const hasCurrentChestPain = symptoms.some(s => s.normalized === "Chest Pain / Angina Symptoms" && !s.is_negated && !s.is_historical);
  const hasCardiacCondition = conditions.some(c => ["Angina Pectoris", "Cerebrovascular Accident / Stroke"].includes(c.normalized) && !c.is_negated);
  const hasRefractoryNitro = medications.some(m => m.normalized.toLowerCase().includes("nitro")) && lower.includes("no effect");
  if (hasCurrentChestPain || hasCardiacCondition || hasRefractoryNitro) {
    clinicalRisks.push({
      risk_type: "Cardiovascular / Ischemic Alert",
      severity: "High",
      rationale: hasCurrentChestPain ? "Active current chest pain or angina symptoms documented." : "Cardiac condition or refractory medication response documented.",
      care_directive: "Continuous telemetry / observation; immediate doctor review if pain recurs; repeat 12-lead ECG."
    });
  }

  // 3. Glycemic Alert
  if (medications.some(m => m.normalized.toLowerCase().includes("insulin")) || lower.includes("sliding scale") || lower.includes("bgl trend")) {
    clinicalRisks.push({
      risk_type: "Glycemic Management Alert",
      severity: "Medium",
      rationale: "Sliding scale insulin protocol with documented morning blood glucose fluctuations.",
      care_directive: "Pre-prandial BGL monitoring; verify insulin dose with medical team."
    });
  }

  // 4. Neurological Alert
  const hasNeuroSymptom = symptoms.some(s => ["Headache (Cephalgia)", "Vertigo (Vestibular)", "Photophobia (Light Sensitivity)"].includes(s.normalized) && !s.is_negated && !s.is_historical);
  const hasNeuroCondition = conditions.some(c => c.normalized.toLowerCase().includes("bell's palsy") && !c.is_negated);
  if (hasNeuroSymptom || hasNeuroCondition || lower.includes("gcs")) {
    clinicalRisks.push({
      risk_type: "Neurological Monitoring Alert",
      severity: "Medium",
      rationale: "Cranial nerve / neurological symptoms under active investigation.",
      care_directive: "Routine neuro observations; monitor pupil equality and limb symmetry."
    });
  }

  // 13. Partition findings and Acuity Check
  const activeConditions = conditions.filter(c => !c.is_negated && !c.is_historical && !c.is_uncertain);
  const activeSymptoms = symptoms.filter(s => !s.is_negated && !s.is_historical && !s.is_uncertain);
  const uncertainFindings = [...conditions, ...symptoms].filter(x => x.is_uncertain);
  const negatedFindings = [...symptoms, ...conditions].filter(x => x.is_negated);
  const historicalFindings = [...symptoms, ...conditions].filter(x => x.is_historical);

  let primaryReason = "clinical evaluation";
  if (activeConditions.length > 0) {
    primaryReason = activeConditions[0].normalized;
  } else if (activeSymptoms.length > 0) {
    primaryReason = activeSymptoms[0].normalized;
  } else if (uncertainFindings.length > 0) {
    primaryReason = `suspected ${uncertainFindings[0].normalized}`;
  } else if (negatedFindings.length > 0) {
    primaryReason = `clinical observation (denies ${negatedFindings[0].text})`;
  } else if (historicalFindings.length > 0) {
    primaryReason = `ward observation following resolved ${historicalFindings[0].normalized}`;
  }

  const criticalCues = ["may die", "critical", "arrest", "deteriorat", "unstable", "emergency", "code blue", "in extremis", "life-threatening"];
  const hasCriticalCue = criticalCues.some(cue => lower.includes(cue));

  const ptDict = {};
  for (const p of patientInfo) ptDict[p.field] = p.value;
  const pName = ptDict["Patient Name"] || "Patient";
  const pBed = ptDict["Bed / Room"] || "Ward Bed";
  const pAge = ptDict["Age"] || "";
  const pDoc = ptDict["Attending Consultant"] || "Medical Team";

  let obsStatus = measurements.find(m => m.type.includes("GCS"))?.text ? `GCS recorded as ${measurements.find(m => m.type.includes("GCS"))?.text}` : (hasCriticalCue ? "Acuity and clinical stability require urgent senior evaluation" : "Routine ward vital sign monitoring ongoing");

  let keyTask = "";
  if (hasCriticalCue) {
    keyTask = "CRITICAL ALERT: Urgent medical team review required; note indicates acute deterioration concern.";
  } else if (pendingTasks.length > 0) {
    keyTask = `Key priority is to follow up on ${pendingTasks[0].task.toLowerCase()}.`;
  } else {
    keyTask = "Patient remains under routine nursing surveillance with no acute deterioration noted.";
  }

  const execSummary = `${pName} (${pBed}, ${pAge}${pDoc !== "Medical Team" ? ', under ' + pDoc : ''}) admitted for management of ${primaryReason}. ${obsStatus}. ${keyTask}`;

  // 14. ISBAR Framework
  const isbarSituation = [];
  if (activeSymptoms.length > 0) {
    isbarSituation.push(`Current Clinical Presentation: Acute ${activeSymptoms.slice(0, 3).map(s => s.normalized).join(", ")}`);
  } else if (uncertainFindings.length > 0) {
    isbarSituation.push(`Current Clinical Presentation: Suspected / Query ${uncertainFindings.slice(0, 2).map(x => x.normalized).join(", ")}`);
  } else if (activeConditions.length > 0) {
    isbarSituation.push(`Current Admission Reason: Management of ${activeConditions[0].normalized}`);
  } else if (historicalFindings.length > 0) {
    isbarSituation.push(`Current Ward Presentation: Observation following resolved ${historicalFindings[0].normalized} ('${historicalFindings[0].text}')`);
  } else {
    isbarSituation.push("Admitted to ward for clinical observation and symptomatic management.");
  }

  if (negatedFindings.length > 0) {
    isbarSituation.push(`Pertinent Negatives (Explicitly Denied / Absent): ${negatedFindings.slice(0, 3).map(n => n.text).join(", ")}`);
  }
  if (hasCriticalCue) {
    isbarSituation.push("CRITICAL ACUITY ALERT: Immediate clinical deterioration concern noted in handover narrative.");
  }
  for (const ev of events) {
    if (ev.type.toLowerCase().includes("admission") || ev.type.toLowerCase().includes("presentation")) {
      isbarSituation.push(`Context: ${ev.event}`);
      break;
    }
  }

  const isbarAssessment = [
    ...(measurements.map(m => `${m.type}: ${m.text}`)),
    ...(treatments.map(t => `Care Status: ${t.normalized} (${t.text})`)),
    ...(investigations.map(i => `Diagnostic Finding: ${i.normalized}${i.is_planned ? ' [Planned]' : ''}`))
  ];
  if (hasCriticalCue) {
    isbarAssessment.push("CRITICAL: Patient status requires immediate clinical review; note indicates acute instability risk.");
  } else if (isbarAssessment.length === 0) {
    isbarAssessment.push("Routine vital sign monitoring ongoing; acute assessment findings not explicitly documented.");
  }

  const isbarRecommendation = [];
  if (hasCriticalCue) {
    isbarRecommendation.push("[Urgent Priority] Immediate medical team bedside review and acute resuscitation assessment.");
  }
  isbarRecommendation.push(...pendingTasks.map(t => `[${t.priority} Priority] ${t.task}`));
  isbarRecommendation.push(...followUp.map(f => `Follow-Up: ${f.action}`));
  if (isbarRecommendation.length === 0) {
    isbarRecommendation.push("Continue routine vital observations and supportive nursing care.");
  }

  const isbar = {
    identify: [
      `Patient: ${pName}`,
      `Location: ${pBed}`,
      `Demographics: ${pAge} | ${ptDict["Gender / Sex"] || "Sex not documented"}`,
      `Consultant: ${pDoc}`
    ],
    situation: isbarSituation,
    background: [
      ...(activeConditions.length > 0 ? activeConditions.map(c => `Documented Condition: ${c.normalized}`) : []),
      ...historicalFindings.map(h => `Past Shift Episode (Resolved): ${h.normalized} ('${h.text}')`),
      ...(activeConditions.length === 0 && historicalFindings.length === 0 ? ["No prior chronic conditions documented in shift handover."] : [])
    ],
    assessment: isbarAssessment,
    recommendation: isbarRecommendation
  };

  // 15. Standard 9 Categories
  const currentCondList = [];
  for (const s of symptoms) {
    if (s.is_negated) {
      currentCondList.push(`Pertinent Negative (Explicitly Denied / Absent): ${s.normalized} ('${s.text}')`);
    } else if (s.is_historical) {
      currentCondList.push(`Past Shift Episode (Resolved): ${s.normalized} ('${s.text}')`);
    } else if (s.is_uncertain) {
      currentCondList.push(`Suspected / Query Symptom: ${s.normalized}`);
    } else {
      currentCondList.push(`Acute Symptom: ${s.normalized}`);
    }
  }
  for (const m of measurements) {
    currentCondList.push(`Vital Assessment: ${m.type} — ${m.text}`);
  }
  if (currentCondList.length === 0) {
    currentCondList.push("Current condition stable; no acute distressing symptoms documented.");
  }

  const structuredHandover = {
    patient_information: patientInfo.map(p => `${p.field}: ${p.value}`),
    current_condition: currentCondList,
    medical_history: conditions.map(c => {
      if (c.is_negated) return `Ruled Out / Denied: ${c.normalized} ('${c.text}')`;
      if (c.is_uncertain) return `Suspected / Differential: ${c.normalized}`;
      return `Documented History: ${c.normalized}`;
    }),
    medications_treatment: [
      ...medications.map(m => m.is_negated ? `${m.normalized} — Not administered / Ceased` : `${m.normalized} — Dose: ${m.dosage}, Route: ${m.route}, Freq: ${m.frequency}`),
      ...treatments.map(t => `Care Level: ${t.normalized} (${t.text})`)
    ],
    investigations: investigations.map(i => `Investigation${i.is_planned ? ' (Planned / Scheduled)' : ''}: ${i.normalized}`),
    clinical_events: events.map(e => `${e.event} (${e.type})`),
    temporal_information: temporal.map(t => `Time: '${t.expression}' (${t.type}) → ${t.associated_event}`),
    pending_tasks: pendingTasks.map(p => `[${p.priority} Priority] ${p.task} (${p.type})`),
    follow_up: followUp.map(f => `${f.action} (${f.type})`),
    executive_summary: execSummary,
    isbar
  };

  // 16. Evidence Mapping
  const evidence = [
    ...patientInfo.map(p => ({ category: "Patient Info", entity: `${p.field}: ${p.value}`, source_sentence: p.source_sentence })),
    ...conditions.map(c => ({ category: "Condition", entity: c.text, source_sentence: c.source_sentence })),
    ...symptoms.map(s => ({ category: "Symptom", entity: s.text, source_sentence: s.source_sentence })),
    ...medications.map(m => ({ category: "Medication", entity: m.text, source_sentence: m.source_sentence })),
    ...investigations.map(i => ({ category: "Investigation", entity: i.text, source_sentence: i.source_sentence })),
    ...measurements.map(ms => ({ category: "Measurement", entity: ms.text, source_sentence: ms.source_sentence })),
    ...events.map(ev => ({ category: "Clinical Event", entity: ev.event, source_sentence: ev.source_sentence })),
    ...pendingTasks.map(pt => ({ category: "Pending Task", entity: pt.task, source_sentence: pt.source_sentence }))
  ];

  return {
    report_id: reportId || "Custom",
    raw_text: text,
    preprocessed_text: clean,
    changes_made: prep.changes_made,
    word_count: clean.split(/\s+/).filter(Boolean).length,
    char_count: clean.length,
    entities: {
      patient_information: patientInfo,
      conditions,
      symptoms,
      medications,
      investigations,
      treatments,
      measurements,
      abbreviations,
      clinical_risks: clinicalRisks
    },
    events,
    temporal_information: temporal,
    pending_tasks: pendingTasks,
    follow_up: followUp,
    structured_handover: structuredHandover,
    executive_summary: execSummary,
    isbar,
    clinical_risks: clinicalRisks,
    evidence,
    model_metadata: {
      pipeline: (engine === 'rule') ? "PULSE Deterministic Rule Baseline (Client Engine)" : "PULSE Hybrid Clinical Engine (Client Fallback)",
      nlp_paradigm: (engine === 'rule') ? "Deterministic Regex and Lexical Rules" : "Contextual Assertion Scoping & Clinical Rules",
      candidate_backbone: "Bio_ClinicalBERT (Trained in Phase C)",
      evaluation_reference: "Synthetic Nursing Handover Reference Corpus (101 Documents)"
    }
  };
}

export function getLocalStats() {
  return datasetData.stats;
}

export function getLocalReports() {
  return {
    total_count: datasetData.reports.length,
    reports: datasetData.reports.map(r => ({
      report_id: r.report_id,
      filename: r.filename,
      word_count: r.word_count,
      char_count: r.char_count,
      preview: r.raw_text.length > 140 ? r.raw_text.substring(0, 140) + "..." : r.raw_text,
      status: r.status
    }))
  };
}

export function getLocalReport(reportId) {
  const r = datasetData.reports.find(item => String(item.report_id) === String(reportId));
  if (!r) throw new Error(`Report #${reportId} not found`);
  const prep = preprocessTextLocal(r.raw_text);
  return {
    report_id: r.report_id,
    filename: r.filename,
    word_count: r.word_count,
    char_count: r.char_count,
    raw_text: r.raw_text,
    preprocessed_text: prep.preprocessed_text,
    changes_made: prep.changes_made,
    preserved_clinical_elements: prep.preserved_clinical_elements,
    sentences: prep.sentences,
    token_count: prep.token_count,
    philosophy_note: prep.philosophy_note
  };
}

// ==========================================
// CLIENT-SIDE PATIENT & NOTE WORKFLOW ENGINE
// (Enables complete standalone demo on Vercel)
// ==========================================

export const INITIAL_DEMO_PATIENTS = [
  {
    id: 1,
    display_id: "PULSE-DEMO-001",
    name: "Michael I Wu",
    age: "48 years",
    gender: "Male",
    ward: "Neurology (Demo Ward A)",
    bed_number: "Bed 8",
    consultant: "Dr. Hanlen",
    admitting_diagnosis: "Headache and vertigo (Synthetic demonstration narrative from Report 0)",
    vitals: { hr: 78, spo2: 98, bp_sys: 124, bp_dia: 82, rr: 16, temperature: 36.8, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 2,
    display_id: "PULSE-DEMO-002",
    name: "Vera Abbott",
    age: "93 years",
    gender: "Female",
    ward: "Cardiology (Demo Ward B)",
    bed_number: "Bed 4",
    consultant: "Dr. Liu",
    admitting_diagnosis: "Chest pain evaluation (Synthetic demonstration narrative from Report 1)",
    vitals: { hr: 84, spo2: 96, bp_sys: 138, bp_dia: 86, rr: 18, temperature: 37.0, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 3,
    display_id: "PULSE-DEMO-003",
    name: "Leila Sonya Da Silva",
    age: "34 years",
    gender: "Female",
    ward: "Endocrinology (Demo Ward C)",
    bed_number: "Bed 5",
    consultant: "Dr. Liu",
    admitting_diagnosis: "Diabetes management (Synthetic demonstration narrative from Report 12)",
    vitals: { hr: 76, spo2: 99, bp_sys: 118, bp_dia: 76, rr: 14, temperature: 36.6, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 4,
    display_id: "PULSE-DEMO-004",
    name: "Pierre Cox",
    age: "77 years",
    gender: "Male",
    ward: "Vascular Surgery (Demo Ward A)",
    bed_number: "Bed 2",
    consultant: "Dr. Gregor",
    admitting_diagnosis: "Right leg pain and swelling query embolism (Synthetic demonstration narrative from Report 15)",
    vitals: { hr: 88, spo2: 95, bp_sys: 142, bp_dia: 88, rr: 20, temperature: 37.2, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 5,
    display_id: "PULSE-DEMO-005",
    name: "Frank Morgan Montgomery",
    age: "78 years",
    gender: "Male",
    ward: "Cardiothoracic (Demo Ward B)",
    bed_number: "Bed 5",
    consultant: "Dr. Sanchez",
    admitting_diagnosis: "Shortness of breath and post-op tiredness (Synthetic demonstration narrative from Report 22)",
    vitals: { hr: 92, spo2: 94, bp_sys: 130, bp_dia: 80, rr: 22, temperature: 36.9, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 6,
    display_id: "PULSE-DEMO-006",
    name: "Nina Maria Carey",
    age: "67 years",
    gender: "Female",
    ward: "Respiratory (Demo Ward C)",
    bed_number: "Bed 1",
    consultant: "Dr. Jaime",
    admitting_diagnosis: "Bronchitis, fever and cough (Synthetic demonstration narrative from Report 35)",
    vitals: { hr: 96, spo2: 93, bp_sys: 126, bp_dia: 78, rr: 24, temperature: 38.4, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 7,
    display_id: "PULSE-DEMO-007",
    name: "Matt Owen",
    age: "43 years",
    gender: "Male",
    ward: "Transplant Unit (Demo Ward A)",
    bed_number: "Bed 3",
    consultant: "Dr. Kenzie",
    admitting_diagnosis: "Post lung transplant recovery (Synthetic demonstration narrative from Report 48)",
    vitals: { hr: 82, spo2: 97, bp_sys: 122, bp_dia: 78, rr: 16, temperature: 37.1, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 8,
    display_id: "PULSE-DEMO-008",
    name: "Dave McKenzie",
    age: "72 years",
    gender: "Male",
    ward: "Psychogeriatric (Demo Ward D)",
    bed_number: "Bed 3",
    consultant: "Dr. Jorge De Silva",
    admitting_diagnosis: "Acute confusion and dementia monitoring (Synthetic demonstration narrative from Report 56)",
    vitals: { hr: 74, spo2: 98, bp_sys: 132, bp_dia: 82, rr: 15, temperature: 36.7, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 9,
    display_id: "PULSE-DEMO-009",
    name: "Lisa Kerr",
    age: "62 years",
    gender: "Female",
    ward: "Neurology (Demo Ward A)",
    bed_number: "Bed 6",
    consultant: "Dr. Laine",
    admitting_diagnosis: "Cerebral haemorrhage evaluation (Synthetic demonstration narrative from Report 75)",
    vitals: { hr: 70, spo2: 98, bp_sys: 148, bp_dia: 92, rr: 14, temperature: 36.9, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 10,
    display_id: "PULSE-DEMO-010",
    name: "Evan Stephenson",
    age: "22 years",
    gender: "Male",
    ward: "Renal & Trauma (Demo Ward B)",
    bed_number: "Bed 3",
    consultant: "Dr. Medical Officer",
    admitting_diagnosis: "Post-fall rhabdomyolysis and renal monitoring (Synthetic demonstration narrative from Report 90)",
    vitals: { hr: 80, spo2: 99, bp_sys: 116, bp_dia: 74, rr: 16, temperature: 36.8, recorded_at: new Date().toISOString(), data_source: "Simulated Demonstration Data" },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
];

const memoryStorage = {};

function storageGet(key) {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(key);
    }
  } catch (e) {
    // ignore
  }
  return memoryStorage[key] || null;
}

function storageSet(key, value) {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(key, value);
      return;
    }
  } catch (e) {
    // ignore
  }
  memoryStorage[key] = value;
}

export function getLocalPatients(search = '') {
  let stored = storageGet('pulse_demo_patients');
  let patients = [];
  if (!stored) {
    patients = [...INITIAL_DEMO_PATIENTS];
    storageSet('pulse_demo_patients', JSON.stringify(patients));
  } else {
    try {
      patients = JSON.parse(stored);
      if (!Array.isArray(patients) || patients.length === 0) {
        patients = [...INITIAL_DEMO_PATIENTS];
        storageSet('pulse_demo_patients', JSON.stringify(patients));
      }
    } catch (e) {
      patients = [...INITIAL_DEMO_PATIENTS];
      storageSet('pulse_demo_patients', JSON.stringify(patients));
    }
  }

  if (search && search.trim()) {
    const q = search.trim().toLowerCase();
    patients = patients.filter(p =>
      (p.name && p.name.toLowerCase().includes(q)) ||
      (p.display_id && p.display_id.toLowerCase().includes(q)) ||
      (p.ward && p.ward.toLowerCase().includes(q)) ||
      (p.bed_number && p.bed_number.toLowerCase().includes(q)) ||
      (p.consultant && p.consultant.toLowerCase().includes(q)) ||
      (p.admitting_diagnosis && p.admitting_diagnosis.toLowerCase().includes(q))
    );
  }

  return {
    total_count: patients.length,
    total_patients: patients.length,
    patients
  };
}

export function getLocalPatient(patientId) {
  const { patients } = getLocalPatients();
  const p = patients.find(item =>
    String(item.id) === String(patientId) ||
    String(item.display_id).toLowerCase() === String(patientId).toLowerCase()
  );
  return p || null;
}

export function createLocalPatient(patientData) {
  const currentList = getLocalPatients().patients;
  const nextId = currentList.length > 0 ? Math.max(...currentList.map(p => Number(p.id) || 0)) + 1 : 1;
  const displayId = patientData.display_id || `PULSE-DEMO-${String(nextId).padStart(3, '0')}`;

  const newPatient = {
    id: nextId,
    display_id: displayId,
    name: patientData.name,
    age: patientData.age || "Unspecified",
    gender: patientData.gender || "Unspecified",
    ward: patientData.ward || "General Ward",
    bed_number: patientData.bed_number || "Unassigned",
    consultant: patientData.consultant || "Attending Medical Officer",
    admitting_diagnosis: patientData.admitting_diagnosis || "Observation",
    vitals: patientData.vitals || {
      hr: 76,
      spo2: 98,
      bp_sys: 120,
      bp_dia: 80,
      rr: 16,
      temperature: 36.8,
      recorded_at: new Date().toISOString(),
      data_source: "Simulated Demonstration Data"
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  currentList.push(newPatient);
  storageSet('pulse_demo_patients', JSON.stringify(currentList));
  return newPatient;
}

export function getLocalPatientNotes(patientId) {
  const key = `pulse_notes_${patientId}`;
  const stored = storageGet(key);
  let notes = [];
  if (stored) {
    try {
      notes = JSON.parse(stored);
      if (Array.isArray(notes)) {
        notes = notes.map(n => {
          // Normalize extraction for UI components
          if (!n.extraction) {
            const ext = n.latest_extraction || (n.extractions && n.extractions[0]);
            if (ext) {
              n.extraction = {
                id: ext.id,
                engine_used: ext.engine_used,
                extracted_at: ext.created_at || ext.extracted_at,
                data: ext.data || ext.extracted_data
              };
            }
          }
          if (n.extraction?.data && !n.extracted_data) {
            n.extracted_data = n.extraction.data;
          }
          // Normalize review for UI components
          if (!n.review) {
            const rev = n.latest_review || (n.reviews && n.reviews[0]);
            if (rev) {
              n.review = {
                id: rev.id,
                reviewer_identifier: rev.reviewer_identifier,
                reviewed_data: rev.reviewed_data || rev.data,
                review_notes: rev.review_notes,
                reviewed_at: rev.created_at || rev.reviewed_at
              };
              n.reviewer_identifier = rev.reviewer_identifier;
              n.reviewed_at = rev.created_at || rev.reviewed_at;
            }
          }
          if (!n.review_history && n.reviews) {
            n.review_history = n.reviews;
          }
          return n;
        });
      }
    } catch (e) {
      notes = [];
    }
  }
  return {
    total_notes: notes.length,
    notes
  };
}

export function createLocalPatientNote(patientId, rawText, authorIdentifier) {
  const key = `pulse_notes_${patientId}`;
  const { notes } = getLocalPatientNotes(patientId);
  const nextId = notes.length > 0 ? Math.max(...notes.map(n => Number(n.id) || 0)) + 1 : 1;
  const newNote = {
    id: nextId,
    patient_id: patientId,
    raw_text: rawText,
    status: 'Draft',
    author_identifier: authorIdentifier || 'Staff Nurse / Clinician (Demo)',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    extractions: [],
    reviews: [],
    latest_extraction: null,
    latest_review: null,
    extraction: null,
    review: null,
    review_history: []
  };
  notes.unshift(newNote);
  storageSet(key, JSON.stringify(notes));
  return newNote;
}

export function processLocalPatientNote(patientId, noteId) {
  const key = `pulse_notes_${patientId}`;
  const { notes } = getLocalPatientNotes(patientId);
  const noteIndex = notes.findIndex(n => String(n.id) === String(noteId));
  if (noteIndex === -1) {
    throw new Error(`Note #${noteId} not found`);
  }
  const note = notes[noteIndex];
  const analysis = analyzeLocalEngine({ rawText: note.raw_text });
  const extractedData = {
    isbar: analysis.isbar,
    entities: analysis.entities,
    events: analysis.events,
    temporal_information: analysis.temporal_information,
    pending_tasks: analysis.pending_tasks,
    follow_up: analysis.follow_up,
    structured_handover: analysis.structured_handover,
    executive_summary: analysis.executive_summary,
    evidence: analysis.evidence,
    model_metadata: {
      pipeline: "PULSE Hybrid Clinical Engine (Client Cloud)",
      nlp_paradigm: "Client-side Contextual Clinical Extraction & ISBAR Structuring",
      model_active: false,
      disclaimer: "Client-side static execution for clinical demonstration"
    }
  };
  const extraction = {
    id: Date.now(),
    note_id: note.id,
    engine_used: "PULSE Hybrid Clinical Engine (Client Cloud)",
    created_at: new Date().toISOString(),
    extracted_data: extractedData
  };
  const formattedExtraction = {
    id: extraction.id,
    engine_used: extraction.engine_used,
    extracted_at: extraction.created_at,
    data: extractedData
  };

  note.status = 'Processed';
  note.updated_at = new Date().toISOString();
  if (!note.extractions) note.extractions = [];
  note.extractions.unshift(extraction);
  note.latest_extraction = extraction;
  note.extraction = formattedExtraction;
  note.extracted_data = extractedData;
  notes[noteIndex] = note;
  storageSet(key, JSON.stringify(notes));
  return note;
}

export function reviewLocalPatientNote(patientId, noteId, reviewedData, reviewerIdentifier, reviewNotes) {
  const key = `pulse_notes_${patientId}`;
  const { notes } = getLocalPatientNotes(patientId);
  const noteIndex = notes.findIndex(n => String(n.id) === String(noteId));
  if (noteIndex === -1) {
    throw new Error(`Note #${noteId} not found`);
  }
  const note = notes[noteIndex];
  const review = {
    id: Date.now(),
    note_id: note.id,
    reviewer_identifier: reviewerIdentifier || "Staff Clinician (Review)",
    review_notes: reviewNotes,
    created_at: new Date().toISOString(),
    reviewed_data: reviewedData
  };
  note.status = 'Reviewed';
  note.updated_at = new Date().toISOString();
  if (!note.reviews) note.reviews = [];
  note.reviews.unshift(review);
  note.latest_review = review;
  note.review = review;
  note.reviewer_identifier = review.reviewer_identifier;
  note.reviewed_at = review.created_at;
  note.review_history = note.reviews;
  notes[noteIndex] = note;
  storageSet(key, JSON.stringify(notes));
  return {
    message: "Clinician review recorded successfully",
    note_id: note.id,
    review_id: review.id,
    reviewer_identifier: review.reviewer_identifier,
    review_notes: review.review_notes,
    reviewed_at: review.created_at,
    status: "Reviewed",
    review,
    note
  };
}


