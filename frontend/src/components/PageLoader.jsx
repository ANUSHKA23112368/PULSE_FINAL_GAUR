import React from 'react';
import { Activity } from 'lucide-react';

export function PageLoader({ label = 'Loading clinical workspace' }) {
  return (
    <div className="route-loader" role="status" aria-live="polite">
      <div className="route-loader-mark">
        <Activity size={20} />
      </div>
      <div className="route-loader-copy">
        <strong>{label}</strong>
        <span>Synchronising handover data…</span>
      </div>
      <div className="route-loader-bar" aria-hidden="true">
        <span />
      </div>
    </div>
  );
}

export default PageLoader;
