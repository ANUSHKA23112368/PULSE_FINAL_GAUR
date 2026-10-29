import React, { useEffect, useState } from 'react';
import { 
  Heart, 
  Wind, 
  Gauge, 
  Thermometer, 
  Activity, 
  AlertTriangle, 
  Clock,
  ArrowRight,
  ShieldAlert,
  Plus,
  CheckCircle2
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import { fetchPatient } from '../services/api';

// NEWS2 Calculator according to Royal College of Physicians UK guidelines
function calculateNews2(vitals) {
  if (!vitals) return { score: 0, level: 'Low', color: 'emerald', action: 'Routine observation every 12h' };

  let score = 0;
  const breakdown = [];

  // 1. Respiration Rate
  const rr = vitals.rr;
  if (rr !== undefined && rr !== null) {
    let p = 0;
    if (rr <= 8) p = 3;
    else if (rr >= 9 && rr <= 11) p = 1;
    else if (rr >= 12 && rr <= 20) p = 0;
    else if (rr >= 21 && rr <= 24) p = 2;
    else if (rr >= 25) p = 3;
    score += p;
    if (p > 0) breakdown.push({ param: 'Respiration Rate', value: `${rr}/min`, points: p });
  }

  // 2. Oxygen Saturation (SpO2 Scale 1)
  const spo2 = vitals.spo2;
  if (spo2 !== undefined && spo2 !== null) {
    let p = 0;
    if (spo2 <= 91) p = 3;
    else if (spo2 >= 92 && spo2 <= 93) p = 2;
    else if (spo2 >= 94 && spo2 <= 95) p = 1;
    else if (spo2 >= 96) p = 0;
    score += p;
    if (p > 0) breakdown.push({ param: 'SpO2 Saturation', value: `${spo2}%`, points: p });
  }

  // 3. Systolic BP
  const sys = vitals.bp_sys;
  if (sys !== undefined && sys !== null) {
    let p = 0;
    if (sys <= 90) p = 3;
    else if (sys >= 91 && sys <= 100) p = 2;
    else if (sys >= 101 && sys <= 110) p = 1;
    else if (sys >= 111 && sys <= 219) p = 0;
    else if (sys >= 220) p = 3;
    score += p;
    if (p > 0) breakdown.push({ param: 'Systolic BP', value: `${sys} mmHg`, points: p });
  }

  // 4. Heart Rate
  const hr = vitals.hr;
  if (hr !== undefined && hr !== null) {
    let p = 0;
    if (hr <= 40) p = 3;
    else if (hr >= 41 && hr <= 50) p = 1;
    else if (hr >= 51 && hr <= 90) p = 0;
    else if (hr >= 91 && hr <= 110) p = 1;
    else if (hr >= 111 && hr <= 130) p = 2;
    else if (hr >= 131) p = 3;
    score += p;
    if (p > 0) breakdown.push({ param: 'Heart Rate', value: `${hr} bpm`, points: p });
  }

  // 5. Temperature
  const temp = vitals.temperature;
  if (temp !== undefined && temp !== null) {
    let p = 0;
    if (temp <= 35.0) p = 3;
    else if (temp >= 35.1 && temp <= 36.0) p = 1;
    else if (temp >= 36.1 && temp <= 38.0) p = 0;
    else if (temp >= 38.1 && temp <= 39.0) p = 1;
    else if (temp >= 39.1) p = 2;
    score += p;
    if (p > 0) breakdown.push({ param: 'Temperature', value: `${temp}°C`, points: p });
  }

  let level = 'Low';
  let color = 'emerald';
  let action = 'Routine ward-level monitoring (4–12 hourly). Minimum clinical risk.';

  const hasScore3Param = breakdown.some(b => b.points >= 3);

  if (score >= 7) {
    level = 'High (Emergency Alert)';
    color = 'rose';
    action = 'Emergency escalation: Immediate assessment by Medical Emergency Team (MET) or Critical Care Outreach.';
  } else if (score >= 5 || hasScore3Param) {
    level = 'Medium (Urgent Clinical Review)';
    color = 'amber';
    action = 'Urgent review: Notify attending registrar or team doctor. Increase observation frequency to hourly.';
  }

  return { score, level, color, action, breakdown };
}

export function VitalsPage({ selectedPatient, onSwitchPatient, onNavigate, allPatients, onSelectPatient }) {
  const [patientDetails, setPatientDetails] = useState(selectedPatient);
  const [loading, setLoading] = useState(false);
  const [customVitals, setCustomVitals] = useState(null);
  const [showRecordModal, setShowRecordModal] = useState(false);

  // Form State for Recording New Vitals
  const [formVitals, setFormVitals] = useState({
    hr: 78,
    bp_sys: 124,
    bp_dia: 82,
    spo2: 98,
    rr: 16,
    temperature: 37.0
  });

  // Simulated Telemetry Waveform Phase
  const [waveOffset, setWaveOffset] = useState(0);

  useEffect(() => {
    async function loadFresh() {
      if (!selectedPatient) return;
      setLoading(true);
      try {
        const fresh = await fetchPatient(selectedPatient.display_id || selectedPatient.id);
        if (fresh) {
          setPatientDetails(fresh);
          if (fresh.vitals) {
            setFormVitals({
              hr: fresh.vitals.hr ?? 78,
              bp_sys: fresh.vitals.bp_sys ?? 120,
              bp_dia: fresh.vitals.bp_dia ?? 80,
              spo2: fresh.vitals.spo2 ?? 98,
              rr: fresh.vitals.rr ?? 16,
              temperature: fresh.vitals.temperature ?? 37.0
            });
          }
        }
      } catch (err) {
        console.warn("Could not reload patient vitals:", err);
      } finally {
        setLoading(false);
      }
    }
    loadFresh();
  }, [selectedPatient]);

  // Telemetry waveform animation loop
  useEffect(() => {
    const anim = setInterval(() => {
      setWaveOffset(prev => (prev + 4) % 600);
    }, 40);
    return () => clearInterval(anim);
  }, []);

  const currentVitals = customVitals || patientDetails?.vitals || formVitals;
  const news2 = calculateNews2(currentVitals);

  function handleScenarioSelect(scenario) {
    if (scenario === 'normal') {
      setFormVitals({ hr: 72, bp_sys: 120, bp_dia: 80, spo2: 98, rr: 16, temperature: 36.8 });
    } else if (scenario === 'tachy') {
      setFormVitals({ hr: 118, bp_sys: 135, bp_dia: 85, spo2: 96, rr: 22, temperature: 38.6 });
    } else if (scenario === 'sepsis') {
      setFormVitals({ hr: 130, bp_sys: 86, bp_dia: 52, spo2: 91, rr: 28, temperature: 39.4 });
    } else if (scenario === 'hypoxia') {
      setFormVitals({ hr: 104, bp_sys: 142, bp_dia: 90, spo2: 89, rr: 24, temperature: 37.2 });
    }
  }

  function handleSaveObservation(e) {
    e.preventDefault();
    const updated = {
      ...formVitals,
      hr: Number(formVitals.hr),
      bp_sys: Number(formVitals.bp_sys),
      bp_dia: Number(formVitals.bp_dia),
      spo2: Number(formVitals.spo2),
      rr: Number(formVitals.rr),
      temperature: Number(formVitals.temperature),
      recorded_at: new Date().toISOString(),
      data_source: 'Nurse Station Telemetry Input'
    };
    setCustomVitals(updated);
    setShowRecordModal(false);
  }

  // Generate SVG ECG Path Points
  const ecgPoints = [];
  const width = 600;
  for (let x = 0; x < width; x += 4) {
    const relX = (x + waveOffset) % 150;
    let y = 30; // baseline
    if (relX >= 30 && relX <= 38) {
      y = 26; // P wave
    } else if (relX >= 50 && relX <= 54) {
      y = 35; // Q
    } else if (relX >= 55 && relX <= 62) {
      y = 6; // R peak
    } else if (relX >= 63 && relX <= 67) {
      y = 44; // S dip
    } else if (relX >= 80 && relX <= 95) {
      y = 24; // T wave
    }
    ecgPoints.push(`${x},${y}`);
  }

  return (
    <div className="page-container">
      {/* Patient Banner */}
      <PatientBanner 
        patient={patientDetails || selectedPatient} 
        onSwitchPatient={onSwitchPatient}
        allPatients={allPatients}
        onSelectPatient={onSelectPatient}
        onNavigate={onNavigate}
      />

      {/* Clinical Safety & Simulation Disclosure */}
      <div className="scope-alert-card">
        <AlertTriangle size={18} className="scope-alert-icon" />
        <div className="scope-alert-content">
          <strong>Simulated Clinical Telemetry Demonstration Data:</strong>
          <span>Parameters reflect synthetic physiological observations for nursing shift evaluation. Not connected to physical patient monitors.</span>
        </div>
      </div>

      {/* Top Header & Observation Controls */}
      <div className="vitals-page-header">
        <div>
          <h2 className="page-heading">
            Bedside Physiological Telemetry & Observations
          </h2>
          <div className="page-subheading">
            <Clock size={14} />
            <span>Last recorded: {currentVitals?.recorded_at ? new Date(currentVitals.recorded_at).toLocaleTimeString() : 'Current Shift'}</span>
            <span>•</span>
            <span>Lead: Lead II ECG & Peripheral SpO2 Pleth</span>
          </div>
        </div>

        <div className="vitals-header-actions">
          <button 
            className="btn btn-primary"
            onClick={() => setShowRecordModal(true)}
          >
            <Plus size={15} /> Record New Observations
          </button>
        </div>
      </div>

      {/* Bedside Oscilloscope Telemetry Monitor (Philips/GE Style HUD) */}
      <div className="bedside-telemetry-panel">
        <div className="telemetry-screen-header">
          <div className="screen-title">
            <Activity size={16} className="text-emerald animate-pulse" />
            <span>BEDSIDE MONITOR • BED {patientDetails?.bed_number || '4'} • CONTINUOUS LEAD II</span>
          </div>
          <div className="telemetry-indicators">
            <span className="telemetry-badge text-emerald">SYNC 1mV</span>
            <span className="telemetry-badge">FILTER: DIAG</span>
            <span className="telemetry-badge">ALARM: ARMED</span>
          </div>
        </div>

        {/* Live Animated Canvas Waveforms */}
        <div className="telemetry-wave-grid">
          {/* ECG Wave Channel */}
          <div className="telemetry-wave-channel">
            <div className="channel-legend">
              <span className="channel-name text-emerald">ECG II (1.0x)</span>
              <span className="channel-rate text-emerald">
                {currentVitals?.hr || 78} <small>BPM</small>
              </span>
            </div>
            <div className="wave-svg-container">
              <svg className="telemetry-svg" viewBox="0 0 600 60" preserveAspectRatio="none">
                <polyline
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={ecgPoints.join(' ')}
                />
              </svg>
              <div className="telemetry-sweep-bar" style={{ left: `${(waveOffset % 600) / 6}%` }} />
            </div>
          </div>

          {/* Plethysmogram Wave Channel */}
          <div className="telemetry-wave-channel pleth-channel">
            <div className="channel-legend">
              <span className="channel-name text-sky">PLETH SpO2</span>
              <span className="channel-rate text-sky">
                {currentVitals?.spo2 || 98}% <small>PI 4.2</small>
              </span>
            </div>
            <div className="wave-svg-container">
              <svg className="telemetry-svg" viewBox="0 0 600 60" preserveAspectRatio="none">
                <polyline
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={ecgPoints.map(pt => {
                    const [x, y] = pt.split(',');
                    return `${x},${30 + Math.sin((Number(x) + waveOffset) * 0.08) * 16}`;
                  }).join(' ')}
                />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Vital Metric Stat Tiles */}
      <div className="vitals-cards-grid">
        {/* Heart Rate Tile */}
        <div className={`hospital-card vital-tile ${currentVitals.hr > 100 || currentVitals.hr < 50 ? 'vital-tile-alert' : ''}`}>
          <div className="vital-tile-header">
            <span>Heart Rate</span>
            <Heart size={18} className="text-rose animate-pulse" />
          </div>
          <div className="vital-tile-value-row">
            <span className="vital-main-val text-rose">{currentVitals.hr ?? '--'}</span>
            <span className="vital-unit">bpm</span>
          </div>
          <div className="vital-tile-footer">
            <span className="target-range">Normal: 60–100</span>
            {currentVitals.hr > 100 ? (
              <span className="badge-alert-tachy">Tachycardia</span>
            ) : currentVitals.hr < 50 ? (
              <span className="badge-alert-tachy">Bradycardia</span>
            ) : (
              <span className="badge-normal">Sinus Normal</span>
            )}
          </div>
        </div>

        {/* SpO2 Saturation Tile */}
        <div className={`hospital-card vital-tile ${currentVitals.spo2 < 95 ? 'vital-tile-alert' : ''}`}>
          <div className="vital-tile-header">
            <span>Oxygen (SpO2)</span>
            <Activity size={18} className="text-sky" />
          </div>
          <div className="vital-tile-value-row">
            <span className="vital-main-val text-sky">{currentVitals.spo2 ?? '--'}</span>
            <span className="vital-unit">%</span>
          </div>
          <div className="vital-tile-footer">
            <span className="target-range">Normal: 95–100%</span>
            {currentVitals.spo2 < 92 ? (
              <span className="badge-alert-hypoxia">Severe Hypoxia</span>
            ) : currentVitals.spo2 < 95 ? (
              <span className="badge-alert-tachy">Low SpO2</span>
            ) : (
              <span className="badge-normal">Adequate</span>
            )}
          </div>
        </div>

        {/* Blood Pressure Tile */}
        <div className={`hospital-card vital-tile ${(currentVitals.bp_sys > 140 || currentVitals.bp_sys < 90) ? 'vital-tile-alert' : ''}`}>
          <div className="vital-tile-header">
            <span>Blood Pressure</span>
            <Gauge size={18} className="text-violet" />
          </div>
          <div className="vital-tile-value-row">
            <span className="vital-main-val text-violet">
              {currentVitals.bp_sys ?? '--'}/{currentVitals.bp_dia ?? '--'}
            </span>
            <span className="vital-unit">mmHg</span>
          </div>
          <div className="vital-tile-footer">
            <span className="target-range">MAP ~{Math.round(((currentVitals.bp_dia || 80) * 2 + (currentVitals.bp_sys || 120)) / 3)} mmHg</span>
            {currentVitals.bp_sys > 140 ? (
              <span className="badge-alert-tachy">Hypertensive</span>
            ) : currentVitals.bp_sys < 90 ? (
              <span className="badge-alert-hypoxia">Hypotensive</span>
            ) : (
              <span className="badge-normal">Normotensive</span>
            )}
          </div>
        </div>

        {/* Respiration Rate Tile */}
        <div className={`hospital-card vital-tile ${currentVitals.rr > 22 || currentVitals.rr < 10 ? 'vital-tile-alert' : ''}`}>
          <div className="vital-tile-header">
            <span>Respiratory Rate</span>
            <Wind size={18} className="text-teal" />
          </div>
          <div className="vital-tile-value-row">
            <span className="vital-main-val text-teal">{currentVitals.rr ?? '--'}</span>
            <span className="vital-unit">/min</span>
          </div>
          <div className="vital-tile-footer">
            <span className="target-range">Normal: 12–20</span>
            {currentVitals.rr > 24 ? (
              <span className="badge-alert-tachy">Tachypnea</span>
            ) : (
              <span className="badge-normal">Spontaneous</span>
            )}
          </div>
        </div>

        {/* Temperature Tile */}
        <div className={`hospital-card vital-tile ${currentVitals.temperature > 38.0 ? 'vital-tile-alert' : ''}`}>
          <div className="vital-tile-header">
            <span>Core Temperature</span>
            <Thermometer size={18} className="text-amber" />
          </div>
          <div className="vital-tile-value-row">
            <span className="vital-main-val text-amber">{currentVitals.temperature ?? '--'}</span>
            <span className="vital-unit">°C</span>
          </div>
          <div className="vital-tile-footer">
            <span className="target-range">Normal: 36.5–37.5°C</span>
            {currentVitals.temperature >= 38.0 ? (
              <span className="badge-alert-tachy">Febrile / Pyrexia</span>
            ) : (
              <span className="badge-normal">Afebrile</span>
            )}
          </div>
        </div>
      </div>

      {/* Real-time National Early Warning Score (NEWS2) Card */}
      <div className={`hospital-card news2-score-card news2-risk-${news2.color}`}>
        <div className="news2-header">
          <div className="news2-title-group">
            <ShieldAlert size={22} className={`news2-icon text-${news2.color}`} />
            <div>
              <div className="news2-title">
                National Early Warning Score (NEWS2): <strong>{news2.score}</strong>
                <span className={`news2-badge news2-badge-${news2.color}`}>{news2.level}</span>
              </div>
              <div className="news2-action-guidance">{news2.action}</div>
            </div>
          </div>

          <div className="news2-score-dial">
            <span className="score-num">{news2.score}</span>
            <span className="score-label">Points</span>
          </div>
        </div>

        {/* Breakdown of Trigger Parameters if any */}
        {news2.breakdown.length > 0 && (
          <div className="news2-triggers">
            <span className="triggers-label">Parameters contributing to clinical risk:</span>
            <div className="triggers-chips">
              {news2.breakdown.map((b, idx) => (
                <span key={idx} className="trigger-chip">
                  <strong>{b.param}</strong>: {b.value} (+{b.points} pts)
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Clinical Notes Action Banner */}
      <div className="hospital-card next-step-cta">
        <div className="cta-text">
          <div className="cta-title">Proceed to Clinical Notes Authoring</div>
          <div className="cta-sub">
            Incorporate these vital observations directly into the shift handover note or synthesize into ISBAR.
          </div>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => onNavigate('notes')}
        >
          Clinical Notes <ArrowRight size={16} />
        </button>
      </div>

      {/* Record New Observations Modal */}
      {showRecordModal && (
        <div className="modal-backdrop" onClick={() => setShowRecordModal(false)}>
          <div className="record-vitals-dialog" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Activity size={20} className="modal-icon" />
                <h3>Record Patient Physiological Observations</h3>
              </div>
              <button className="modal-close-btn" onClick={() => setShowRecordModal(false)}>×</button>
            </div>

            <form onSubmit={handleSaveObservation}>
              <div className="modal-body">
                {/* Clinical Test Scenarios */}
                <div className="scenarios-row">
                  <span className="scenarios-label">Quick Test Scenarios:</span>
                  <div className="scenario-buttons">
                    <button 
                      type="button" 
                      className="scenario-btn" 
                      onClick={() => handleScenarioSelect('normal')}
                    >
                      Stable Normal
                    </button>
                    <button 
                      type="button" 
                      className="scenario-btn btn-tachy" 
                      onClick={() => handleScenarioSelect('tachy')}
                    >
                      Post-Op Fever & Tachycardia
                    </button>
                    <button 
                      type="button" 
                      className="scenario-btn btn-hypoxia" 
                      onClick={() => handleScenarioSelect('hypoxia')}
                    >
                      Respiratory Hypoxia (SpO2 89%)
                    </button>
                    <button 
                      type="button" 
                      className="scenario-btn btn-sepsis" 
                      onClick={() => handleScenarioSelect('sepsis')}
                    >
                      High Sepsis Risk (NEWS2 11)
                    </button>
                  </div>
                </div>

                <div className="vitals-form-grid">
                  <div className="form-group">
                    <label className="form-label">Heart Rate (bpm)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={formVitals.hr} 
                      onChange={e => setFormVitals({ ...formVitals, hr: e.target.value })} 
                      min="30" 
                      max="220" 
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">SpO2 Oxygen (%)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={formVitals.spo2} 
                      onChange={e => setFormVitals({ ...formVitals, spo2: e.target.value })} 
                      min="60" 
                      max="100" 
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Systolic BP (mmHg)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={formVitals.bp_sys} 
                      onChange={e => setFormVitals({ ...formVitals, bp_sys: e.target.value })} 
                      min="50" 
                      max="260" 
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Diastolic BP (mmHg)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={formVitals.bp_dia} 
                      onChange={e => setFormVitals({ ...formVitals, bp_dia: e.target.value })} 
                      min="30" 
                      max="160" 
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Respiratory Rate (/min)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={formVitals.rr} 
                      onChange={e => setFormVitals({ ...formVitals, rr: e.target.value })} 
                      min="6" 
                      max="60" 
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Temperature (°C)</label>
                    <input 
                      type="number" 
                      step="0.1" 
                      className="form-input" 
                      value={formVitals.temperature} 
                      onChange={e => setFormVitals({ ...formVitals, temperature: e.target.value })} 
                      min="30.0" 
                      max="44.0" 
                      required 
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button 
                  type="button" 
                  className="modal-action-btn secondary"
                  onClick={() => setShowRecordModal(false)}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="modal-action-btn primary"
                >
                  <CheckCircle2 size={15} /> Update Observations & Compute NEWS2
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default VitalsPage;
