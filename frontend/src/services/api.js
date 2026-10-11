/**
 * PULSE API Service
 * Handles communication with the FastAPI backend with seamless, automatic
 * client-side fallback (using bundled dataset and local engine) when deployed on
 * static hosts like Vercel, Netlify, or GitHub Pages.
 */

import { 
  getLocalStats, 
  getLocalReports, 
  getLocalReport, 
  preprocessTextLocal, 
  analyzeLocalEngine,
  getLocalPatients,
  getLocalPatient,
  createLocalPatient,
  getLocalPatientNotes,
  createLocalPatientNote,
  processLocalPatientNote,
  reviewLocalPatientNote
} from './localEngine';

const API_BASE = '/api';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    if (!res.ok) throw new Error("Backend not responding");
    return await res.json();
  } catch (err) {
    // Return healthy client-side engine response on Vercel
    const stats = getLocalStats();
    const patientsData = getLocalPatients();
    return {
      status: "healthy (Cloud Client Engine)",
      system: "PULSE (Patient Update & Log Structuring Engine)",
      version: "1.0.0-prototype",
      dataset_loaded: true,
      total_reports: stats.total_reports,
      total_patients: patientsData.total_count,
      model_status: {
        current_engine: "PULSE Hybrid Clinical Engine (Client Cloud)",
        candidate_backbone: "Bio_ClinicalBERT",
        candidate_status: "Active (Client-side assertion scoping & ISBAR generator)"
      },
      disclaimer: "PULSE is an AI-assisted clinical information-organization prototype. It does not diagnose, prescribe treatment, or replace professional clinical judgment."
    };
  }
}

export async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error("Backend stats offline");
    return await res.json();
  } catch (err) {
    // Cloud / Vercel fallback: load dynamic statistics computed from the 101 reports
    return getLocalStats();
  }
}

export async function fetchReports() {
  try {
    const res = await fetch(`${API_BASE}/reports`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error("Backend reports offline");
    return await res.json();
  } catch (err) {
    // Cloud / Vercel fallback: return all 101 reports from bundled dataset
    return getLocalReports();
  }
}

export async function fetchReport(reportId) {
  try {
    const res = await fetch(`${API_BASE}/reports/${reportId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error("Backend report fetch offline");
    return await res.json();
  } catch (err) {
    // Cloud / Vercel fallback: return exact report by ID
    return getLocalReport(reportId);
  }
}

export async function preprocessText(rawText) {
  try {
    const res = await fetch(`${API_BASE}/preprocess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text: rawText }),
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error("Backend preprocessor offline");
    return await res.json();
  } catch (err) {
    return preprocessTextLocal(rawText);
  }
}

export async function analyzeHandover({ reportId, rawText, engine }) {
  try {
    const payload = {};
    if (reportId !== undefined && reportId !== null && reportId !== '') {
      payload.report_id = String(reportId);
    }
    if (rawText !== undefined && rawText !== null) {
      payload.raw_text = rawText;
    }
    if (engine) {
      payload.engine = engine;
    }

    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(15000)
    });
    if (!res.ok) throw new Error("Backend analyzer offline");
    return await res.json();
  } catch (err) {
    // Cloud / Vercel fallback: execute complete clinical analysis pipeline client-side
    return analyzeLocalEngine({ reportId, rawText });
  }
}

export async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/history`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error("Backend history offline");
    return await res.json();
  } catch (err) {
    return { history: [] };
  }
}

export async function fetchPatients(search = '') {
  try {
    const url = search ? `${API_BASE}/patients?search=${encodeURIComponent(search)}` : `${API_BASE}/patients`;
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error("Failed to fetch patients list");
    return await res.json();
  } catch (err) {
    return getLocalPatients(search);
  }
}

export async function fetchPatient(patientId) {
  try {
    const res = await fetch(`${API_BASE}/patients/${patientId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`Patient ${patientId} not found`);
    return await res.json();
  } catch (err) {
    return getLocalPatient(patientId);
  }
}

export async function createPatient(patientData) {
  try {
    const res = await fetch(`${API_BASE}/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patientData),
      signal: AbortSignal.timeout(4000)
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Failed to create synthetic demo patient" }));
      throw new Error(errorData.detail || "Failed to create synthetic demo patient");
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend patient creation unavailable, saving to client storage:", err);
    return createLocalPatient(patientData);
  }
}

export async function fetchPatientNotes(patientId) {
  try {
    const res = await fetch(`${API_BASE}/patients/${patientId}/notes`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`Failed to fetch notes for patient ${patientId}`);
    return await res.json();
  } catch (err) {
    return getLocalPatientNotes(patientId);
  }
}

export async function createPatientNote(patientId, rawText, authorIdentifier = "Staff Clinician (Demo)") {
  try {
    const res = await fetch(`${API_BASE}/patients/${patientId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text: rawText, author_identifier: authorIdentifier }),
      signal: AbortSignal.timeout(4000)
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Failed to save note" }));
      throw new Error(errorData.detail || "Failed to save note");
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend note creation unavailable, saving to client storage:", err);
    return createLocalPatientNote(patientId, rawText, authorIdentifier);
  }
}

export async function processPatientNote(patientId, noteId) {
  try {
    const res = await fetch(`${API_BASE}/patients/${patientId}/notes/${noteId}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(15000)
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Failed to process note" }));
      throw new Error(errorData.detail || "Failed to process note");
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend note processor unavailable, processing via client clinical NLP engine:", err);
    return processLocalPatientNote(patientId, noteId);
  }
}

export async function fetchPatientNote(patientId, noteId) {
  try {
    const res = await fetch(`${API_BASE}/patients/${patientId}/notes/${noteId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`Note ${noteId} not found`);
    return await res.json();
  } catch (err) {
    const { notes } = getLocalPatientNotes(patientId);
    return notes.find(n => String(n.id) === String(noteId)) || null;
  }
}

export async function reviewPatientNote(patientId, noteId, reviewedData, reviewerIdentifier = "Staff Clinician (Demo)", reviewNotes = null) {
  try {
    const res = await fetch(`${API_BASE}/patients/${patientId}/notes/${noteId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reviewed_data: reviewedData,
        reviewer_identifier: reviewerIdentifier,
        review_notes: reviewNotes
      }),
      signal: AbortSignal.timeout(6000)
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Failed to persist clinician review" }));
      throw new Error(errorData.detail || "Failed to persist clinician review");
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend review endpoint unavailable, saving to client storage:", err);
    return reviewLocalPatientNote(patientId, noteId, reviewedData, reviewerIdentifier, reviewNotes);
  }
}



