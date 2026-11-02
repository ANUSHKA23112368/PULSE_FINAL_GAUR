import React from 'react';

/**
 * Enhanced Card component to standardize UI across the platform
 */
export function PulseCard({ title, subtitle, icon: Icon, children, className = "", headerActions }) {
  return (
    <div className={`pulse-card ${className}`}>
      {(title || subtitle || Icon) && (
        <div className="pulse-card-header">
          <div>
            {title && (
              <h3 className="card-title">
                {Icon && <Icon size={18} style={{ marginRight: '8px', color: '#06b6d4' }} />}
                {title}
              </h3>
            )}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {headerActions && <div className="card-header-actions">{headerActions}</div>}
        </div>
      )}
      <div className="pulse-card-body">{children}</div>
    </div>
  );
}
