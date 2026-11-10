/**
 * PULSE hash router.
 *
 * The app is deployed as a static bundle (Vercel/Netlify/GitHub Pages), so hash
 * routing keeps deep links working without server rewrites and preserves
 * browser back/forward behaviour. Route state is descriptive:
 *
 *   #/ward/vitals?patient=PULSE-DEMO-001
 *   #/studio/analyze?report=0
 */

export const TAB_PATHS = {
  dashboard: 'ward/roster',
  vitals: 'ward/vitals',
  notes: 'ward/notes',
  prior: 'ward/prior-history',
  summary: 'ward/isbar',
  changes: 'ward/changes',
  tasks: 'ward/tasks',
  history: 'ward/history',
  analyze: 'studio/analyze',
  reports: 'studio/reports',
  overview: 'studio/overview',
  dataset: 'studio/dataset',
  training: 'studio/training',
  evaluation: 'studio/evaluation',
  about: 'studio/about',
  landing: 'home',
};

export const TAB_TITLES = {
  dashboard: 'Patient Roster',
  vitals: 'Vitals & NEWS2',
  notes: 'Clinical Notes',
  prior: 'Prior History',
  summary: 'ISBAR Handover',
  changes: 'Shift Delta',
  tasks: 'Pending Actions',
  history: 'Audit History',
  analyze: 'Handover Analysis',
  reports: 'Handover Reports',
  overview: 'Architecture & EDA',
  dataset: 'Dataset Explorer',
  training: 'BioClinicalBERT Studio',
  evaluation: 'Benchmark Evaluation',
  about: 'About PULSE',
  landing: 'Workspace Overview',
};

const PATH_TABS = Object.entries(TAB_PATHS).reduce((acc, [tab, path]) => {
  acc[path] = tab;
  return acc;
}, {});

const DEFAULT_TAB = 'dashboard';

export function parseRoute(hash = typeof window !== 'undefined' ? window.location.hash : '') {
  const raw = String(hash || '').replace(/^#\/?/, '');
  const [rawPath = '', rawQuery = ''] = raw.split('?');
  const path = rawPath.replace(/\/+$/, '');
  const params = new URLSearchParams(rawQuery);
  // An empty hash is the landing entry point, not a redirect to the roster.
  const tab = PATH_TABS[path] || (path === '' ? 'landing' : undefined);

  return {
    path: path || TAB_PATHS.landing,
    tab: tab || DEFAULT_TAB,
    known: Boolean(tab),
    patient: params.get('patient') || null,
    report: params.get('report') || null,
  };
}

export function buildHash(tab, { patient, report } = {}) {
  const path = TAB_PATHS[tab] || TAB_PATHS[DEFAULT_TAB];
  const params = new URLSearchParams();
  if (patient) params.set('patient', patient);
  if (report !== undefined && report !== null && report !== '') params.set('report', String(report));
  const query = params.toString();
  return `#/${path}${query ? `?${query}` : ''}`;
}

export function navigateToTab(tab, options = {}) {
  const next = buildHash(tab, options);
  if (window.location.hash === next) return;
  window.location.hash = next;
}

/**
 * Keep the URL in sync with in-page selections (patient/report) without
 * pushing a new history entry for every click.
 */
export function replaceQuery(updates = {}) {
  const current = parseRoute();
  const next = buildHash(current.tab, {
    patient: updates.patient !== undefined ? updates.patient : current.patient,
    report: updates.report !== undefined ? updates.report : current.report,
  });
  if (window.location.hash !== next) {
    window.history.replaceState(null, '', next);
  }
}

export function ensureInitialHash() {
  if (!window.location.hash) {
    window.history.replaceState(null, '', buildHash('landing'));
  }
}
