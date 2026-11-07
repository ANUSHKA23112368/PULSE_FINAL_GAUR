import React from 'react';
import { calculateNews2 } from '../utils/news2';

function cleanFragment(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function bundleResources(bundle, type) {
  return (bundle?.entry || [])
    .map((entry) => entry.resource)
    .filter((resource) => resource?.resourceType === type);
}

export function ClinicalPrintSheet({ patient, isbar, bundle, analysisResult, title = 'Clinical Shift Handover' }) {
  const patientInfo = analysisResult?.entities?.patient_information;
  const field = (name) => patientInfo?.find((item) => item.field === name)?.value;

  const patientResource = bundleResources(bundle, 'Patient')[0];
  const composition = bundleResources(bundle, 'Composition')[0];
  const name = patient?.name || patientResource?.name?.[0]?.text || field('Patient Name') || 'Unnamed patient';
  const mrn = patient?.display_id || patient?.id || field('MRN') || field('Patient ID') || '—';
  const ward = patient?.ward || field('Ward') || '—';
  const bed = patient?.bed_number || field('Bed') || '—';
  const age = patient?.age || field('Age') || '—';
  const gender = patient?.gender || field('Gender / Sex') || '—';
  const consultant = patient?.consultant || field('Attending Consultant') || '—';
  const vitals = patient?.vitals || analysisResult?.vitals;
  const news2 = vitals ? calculateNews2(vitals) : null;

  const sectionText = (sectionTitle) => {
    const section = composition?.section?.find((item) => item.title === sectionTitle);
    return cleanFragment(section?.text?.div);
  };
  const isbarValue = (key, fallbackTitle) => {
    const direct = isbar?.[key];
    if (Array.isArray(direct)) return direct.join(' ');
    if (direct) return direct;
    const analysed = analysisResult?.isbar?.[key];
    if (Array.isArray(analysed)) return analysed.join(' ');
    if (analysed) return analysed;
    return sectionText(fallbackTitle) || 'Not recorded';
  };

  const conditions =
    analysisResult?.entities?.conditions?.map((item) => item.normalized || item.text) ||
    bundleResources(bundle, 'Condition').map((item) => item.code?.text).filter(Boolean);

  const medications =
    analysisResult?.entities?.medications?.map((item) =>
      [item.normalized || item.text, item.dosage, item.route, item.frequency].filter(Boolean).join(' · ')
    ) ||
    bundleResources(bundle, 'MedicationStatement')
      .map((item) => [item.medicationCodeableConcept?.text, item.dosage?.[0]?.text].filter(Boolean).join(' · '))
      .filter(Boolean);

  const tasks =
    analysisResult?.structured_handover?.pending_tasks?.map((item) => (typeof item === 'string' ? item : item.task)) ||
    bundleResources(bundle, 'Task').map((item) => item.description).filter(Boolean);

  const isbarRows = [
    ['Identify', isbarValue('identify', 'Identify')],
    ['Situation', isbarValue('situation', 'Situation')],
    ['Background', isbarValue('background', 'Background')],
    ['Assessment', isbarValue('assessment', 'Assessment')],
    ['Recommendation', isbarValue('recommendation', 'Recommendation')],
  ];

  return (
    <article id="pulse-print-sheet" className="print-sheet">
      <header className="print-sheet-header">
        <div>
          <div className="print-sheet-brand">PULSE</div>
          <h1>{title}</h1>
          <p>Structured clinical handover · hospital clipboard record</p>
        </div>
        <div className="print-sheet-stamp">
          <span>Printed</span>
          <strong>{new Date().toLocaleString('en-GB')}</strong>
          <span>MRN {mrn}</span>
        </div>
      </header>

      <section className="print-sheet-patient">
        <div><span>Patient</span><strong>{name}</strong></div>
        <div><span>MRN</span><strong>{mrn}</strong></div>
        <div><span>Age / Sex</span><strong>{age} / {gender}</strong></div>
        <div><span>Ward / Bed</span><strong>{ward} / {bed}</strong></div>
        <div><span>Attending</span><strong>{consultant}</strong></div>
        {news2 && (
          <div className={`print-sheet-news2 is-${news2.color}`}>
            <span>NEWS2</span>
            <strong>{news2.score} · {news2.shortLevel} risk</strong>
          </div>
        )}
      </section>

      {news2 && (
        <section className="print-sheet-observations">
          <h2>Physiological observations</h2>
          <table>
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Value</th>
                <th>Points</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {news2.parameters.map((parameter) => (
                <tr key={parameter.key}>
                  <td>{parameter.label}</td>
                  <td>{parameter.valueText}</td>
                  <td>{parameter.points}</td>
                  <td>{parameter.target}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="print-sheet-isbar">
        <h2>ISBAR handover</h2>
        {isbarRows.map(([label, value]) => (
          <div className="print-sheet-row" key={label}>
            <span className="print-sheet-row-label">{label}</span>
            <p>{value}</p>
          </div>
        ))}
      </section>

      <div className="print-sheet-columns">
        <section>
          <h2>Active conditions</h2>
          {conditions?.length ? (
            <ul>{conditions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
          ) : <p className="print-sheet-empty">None recorded.</p>}
        </section>
        <section>
          <h2>Medications</h2>
          {medications?.length ? (
            <ul>{medications.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
          ) : <p className="print-sheet-empty">None recorded.</p>}
        </section>
      </div>

      <section className="print-sheet-tasks">
        <h2>Pending actions for the receiving nurse</h2>
        {tasks?.length ? (
          <ol>{tasks.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol>
        ) : <p className="print-sheet-empty">No pending tasks recorded.</p>}
      </section>

      <footer className="print-sheet-footer">
        <div className="print-sheet-signatures">
          <span>Handing over nurse: ______________________</span>
          <span>Time: __________</span>
          <span>Receiving nurse: ______________________</span>
          <span>Time: __________</span>
        </div>
        <p>
          PULSE is an AI-assisted clinical information-organisation prototype. It does not diagnose, prescribe, or replace
          professional clinical judgement. Verify every field against the source record before handover.
        </p>
      </footer>
    </article>
  );
}

export default ClinicalPrintSheet;
