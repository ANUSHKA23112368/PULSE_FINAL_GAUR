import React, { useEffect, useRef } from 'react';
import { X, Moon, Sun, ShieldAlert } from 'lucide-react';

export function MobileNav({
  open,
  onClose,
  groups = [],
  activeTab,
  onNavigate,
  theme,
  onToggleTheme,
}) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose();
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleKeyDown);
    const focusTimer = window.setTimeout(() => closeRef.current?.focus(), 50);

    return () => {
      window.clearTimeout(focusTimer);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="mobile-nav-backdrop" onClick={onClose} role="presentation">
      <aside
        id="mobile-navigation"
        className="mobile-nav-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Clinical workspace navigation"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mobile-nav-header">
          <div>
            <strong>Workspace</strong>
            <span>Clinical handover navigation</span>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="mobile-nav-close"
            onClick={onClose}
            aria-label="Close navigation menu"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mobile-nav-scroll">
          {groups.map((group) => (
            <div className="mobile-nav-group" key={group.label}>
              <div className="mobile-nav-group-label">{group.label}</div>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`mobile-nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      onNavigate(item.id);
                      onClose();
                    }}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className="mobile-nav-item-icon">
                      <Icon size={16} />
                    </span>
                    <span className="mobile-nav-item-copy">
                      <strong>{item.label}</strong>
                      {item.sub && <small>{item.sub}</small>}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        <div className="mobile-nav-footer">
          <button
            type="button"
            className="mobile-nav-theme"
            onClick={() => {
              onToggleTheme();
            }}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            <span>Switch to {theme === 'dark' ? 'light' : 'dark'} theme</span>
          </button>

          <div className="mobile-nav-scope">
            <ShieldAlert size={14} />
            <span>Research prototype — not a diagnostic device.</span>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default MobileNav;
