/**
 * NEWS2 (National Early Warning Score 2) scoring engine.
 * Royal College of Physicians (UK) 2017 thresholds, SpO2 Scale 1.
 */

export const NEWS2_BANDS = [
  {
    key: 'low',
    label: 'Low clinical risk',
    short: 'Low',
    range: '0–4',
    action: 'Routine ward-level monitoring (4–12 hourly). Minimum clinical risk.',
  },
  {
    key: 'medium',
    label: 'Medium clinical risk',
    short: 'Medium',
    range: '5–6',
    action: 'Urgent review: notify the attending registrar or team doctor and increase observations to hourly.',
  },
  {
    key: 'high',
    label: 'High clinical risk',
    short: 'High',
    range: '7+',
    action: 'Emergency escalation: immediate assessment by the Medical Emergency Team or Critical Care Outreach.',
  },
];

function numeric(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function scoreRespiratoryRate(rr) {
  if (rr === null) return 0;
  if (rr <= 8) return 3;
  if (rr <= 11) return 1;
  if (rr <= 20) return 0;
  if (rr <= 24) return 2;
  return 3;
}

function scoreSpo2(spo2) {
  if (spo2 === null) return 0;
  if (spo2 <= 91) return 3;
  if (spo2 <= 93) return 2;
  if (spo2 <= 95) return 1;
  return 0;
}

function scoreSystolic(systolic) {
  if (systolic === null) return 0;
  if (systolic <= 90) return 3;
  if (systolic <= 100) return 2;
  if (systolic <= 110) return 1;
  if (systolic <= 219) return 0;
  return 3;
}

function scoreHeartRate(hr) {
  if (hr === null) return 0;
  if (hr <= 40) return 3;
  if (hr <= 50) return 1;
  if (hr <= 90) return 0;
  if (hr <= 110) return 1;
  if (hr <= 130) return 2;
  return 3;
}

function scoreTemperature(temp) {
  if (temp === null) return 0;
  if (temp <= 35.0) return 3;
  if (temp <= 36.0) return 1;
  if (temp <= 38.0) return 0;
  if (temp <= 39.0) return 1;
  return 2;
}

function scoreConsciousness(vitals) {
  const explicit = vitals?.acvpu || vitals?.acvpu_level || vitals?.consciousness;
  if (explicit) {
    const value = String(explicit).trim().toUpperCase();
    const points = value === 'A' || value === 'ALERT' ? 0 : 3;
    const labels = {
      A: 'Alert',
      ALERT: 'Alert',
      C: 'New confusion',
      CONFUSION: 'New confusion',
      V: 'Voice',
      VOICE: 'Voice',
      P: 'Pain',
      PAIN: 'Pain',
      U: 'Unresponsive',
      UNRESPONSIVE: 'Unresponsive',
    };
    return { points, label: labels[value] || String(explicit) };
  }

  const gcs = numeric(vitals?.gcs);
  if (gcs !== null) {
    return { points: gcs >= 15 ? 0 : 3, label: `GCS ${gcs}` };
  }

  return { points: 0, label: 'Alert (assumed)' };
}

export function calculateNews2(vitals) {
  if (!vitals) {
    return {
      score: 0,
      level: NEWS2_BANDS[0].label,
      shortLevel: NEWS2_BANDS[0].short,
      color: 'emerald',
      band: NEWS2_BANDS[0],
      action: NEWS2_BANDS[0].action,
      hasCriticalParameter: false,
      parameters: [],
      breakdown: [],
    };
  }

  const rr = numeric(vitals.rr);
  const spo2 = numeric(vitals.spo2);
  const systolic = numeric(vitals.bp_sys ?? vitals.systolic_bp);
  const hr = numeric(vitals.hr ?? vitals.heart_rate);
  const temp = numeric(vitals.temperature ?? vitals.temp);
  const consciousness = scoreConsciousness(vitals);

  const parameters = [
    {
      key: 'rr',
      label: 'Respiratory rate',
      value: rr,
      valueText: rr === null ? 'Not recorded' : `${rr} /min`,
      unit: '/min',
      target: '12–20',
      points: rr === null ? 0 : scoreRespiratoryRate(rr),
      recorded: rr !== null,
    },
    {
      key: 'spo2',
      label: 'Oxygen saturation',
      value: spo2,
      valueText: spo2 === null ? 'Not recorded' : `${spo2}%`,
      unit: '%',
      target: '96–100%',
      points: spo2 === null ? 0 : scoreSpo2(spo2),
      recorded: spo2 !== null,
    },
    {
      key: 'bp_sys',
      label: 'Systolic blood pressure',
      value: systolic,
      valueText: systolic === null ? 'Not recorded' : `${systolic} mmHg`,
      unit: 'mmHg',
      target: '111–219',
      points: systolic === null ? 0 : scoreSystolic(systolic),
      recorded: systolic !== null,
    },
    {
      key: 'hr',
      label: 'Heart rate',
      value: hr,
      valueText: hr === null ? 'Not recorded' : `${hr} bpm`,
      unit: 'bpm',
      target: '51–90',
      points: hr === null ? 0 : scoreHeartRate(hr),
      recorded: hr !== null,
    },
    {
      key: 'acvpu',
      label: 'Consciousness (ACVPU)',
      value: consciousness.label,
      valueText: consciousness.label,
      unit: '',
      target: 'Alert',
      points: consciousness.points,
      recorded: true,
    },
    {
      key: 'temperature',
      label: 'Temperature',
      value: temp,
      valueText: temp === null ? 'Not recorded' : `${temp} °C`,
      unit: '°C',
      target: '36.1–38.0',
      points: temp === null ? 0 : scoreTemperature(temp),
      recorded: temp !== null,
    },
  ];

  const score = parameters.reduce((total, parameter) => total + parameter.points, 0);
  const hasCriticalParameter = parameters.some((parameter) => parameter.points >= 3);
  const bandKey = score >= 7 ? 'high' : score >= 5 || hasCriticalParameter ? 'medium' : 'low';
  const band = NEWS2_BANDS.find((item) => item.key === bandKey) || NEWS2_BANDS[0];
  const color = bandKey === 'high' ? 'rose' : bandKey === 'medium' ? 'amber' : 'emerald';
  const level = band.key === 'high' ? 'High (Emergency Alert)' : band.key === 'medium' ? 'Medium (Urgent Clinical Review)' : 'Low';

  return {
    score,
    level,
    shortLevel: band.short,
    color,
    band,
    action: band.action,
    hasCriticalParameter,
    parameters,
    breakdown: parameters.filter((parameter) => parameter.points > 0),
  };
}

const TREND_CONFIG = {
  hr: { min: 40, max: 160, amplitude: 18, decimals: 0, label: 'Heart rate', unit: 'bpm', higherIsWorse: true },
  bp_sys: { min: 78, max: 195, amplitude: 16, decimals: 0, label: 'Systolic BP', unit: 'mmHg', higherIsWorse: true },
  spo2: { min: 86, max: 100, amplitude: 4, decimals: 0, label: 'SpO2', unit: '%', higherIsWorse: false },
  rr: { min: 8, max: 38, amplitude: 5, decimals: 0, label: 'Respiratory rate', unit: '/min', higherIsWorse: true },
  temperature: { min: 34.8, max: 40.5, amplitude: 0.8, decimals: 1, label: 'Temperature', unit: '°C', higherIsWorse: true },
  gcs: { min: 3, max: 15, amplitude: 1, decimals: 0, label: 'GCS', unit: '', higherIsWorse: false },
};

/**
 * Deterministic 24-hour series ending at the current value. Stable across
 * renders while still showing a plausible trajectory.
 */
export function buildVitalsTrend(vitals, key, count = 8) {
  const config = TREND_CONFIG[key];
  const current = numeric(vitals?.[key]);
  if (!config || current === null) return null;

  const total = Math.max(4, count);
  let seed = Math.abs(Math.round(current * 17)) + key.length * 37 + total;
  const random = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };

  const values = [];
  for (let index = 0; index < total - 1; index += 1) {
    const factor = (total - 1 - index) / (total - 1);
    const offset = (random() - 0.5) * config.amplitude * factor;
    values.push(current + offset);
  }
  values.push(current);

  const rounded = values.map((value) => {
    const clamped = Math.min(config.max, Math.max(config.min, value));
    return Number(clamped.toFixed(config.decimals));
  });
  const first = rounded[0];
  const delta = Number((current - first).toFixed(config.decimals));
  const threshold = config.decimals === 0 ? 1 : 0.1;
  const trend = Math.abs(delta) < threshold ? 'stable' : delta > 0 ? 'up' : 'down';
  const worsening =
    trend === 'stable' ? false : config.higherIsWorse ? trend === 'up' : trend === 'down';
  const sign = delta > 0 ? '+' : '';

  return {
    key,
    label: config.label,
    unit: config.unit,
    series: rounded,
    current,
    delta,
    trend,
    worsening,
    summary:
      trend === 'stable'
        ? 'Stable over 24h'
        : `${sign}${delta} ${config.unit}`.trim() + ' over 24h',
  };
}

function hashString(value) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash) % 233280;
}

/**
 * Synthetic bedside baseline for demo patients that have no observation record.
 * Deterministic per patient, and explicitly labelled as synthetic telemetry.
 */
export function getPatientVitals(patient = {}) {
  if (patient?.vitals) return patient.vitals;

  let seed = hashString(String(patient.display_id || patient.id || patient.name || 'PULSE-DEMO'));
  const random = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
  const diagnosis = String(patient.admitting_diagnosis || '').toLowerCase();
  const highAttention = ['sepsis', 'chest pain', 'embolism', 'vertigo', 'icu'].some((term) => diagnosis.includes(term));

  const hr = highAttention ? 96 + Math.round(random() * 34) : 66 + Math.round(random() * 28);
  const bpSys = highAttention ? 96 + Math.round(random() * 30) : 110 + Math.round(random() * 28);
  const bpDia = Math.round(bpSys * 0.64 + random() * 6);
  const spo2 = highAttention ? 91 + Math.round(random() * 5) : 95 + Math.round(random() * 4);
  const rr = highAttention ? 20 + Math.round(random() * 7) : 13 + Math.round(random() * 6);
  const temperature = Number((highAttention ? 37.6 + random() * 1.2 : 36.4 + random() * 0.9).toFixed(1));

  return {
    hr,
    bp_sys: bpSys,
    bp_dia: bpDia,
    spo2,
    rr,
    temperature,
    acvpu: 'A',
    recorded_at: patient.updated_at || null,
    data_source: 'Synthetic demo telemetry',
  };
}

export function buildVitalsTrendSet(vitals) {
  return Object.keys(TREND_CONFIG).reduce((accumulator, key) => {
    accumulator[key] = buildVitalsTrend(vitals, key);
    return accumulator;
  }, {});
}
