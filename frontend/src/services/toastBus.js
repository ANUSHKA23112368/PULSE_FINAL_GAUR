export const TOAST_EVENT = 'pulse:toast';

let lastMessage = '';
let lastAt = 0;

/**
 * Emits a toast from service code. Identical messages are collapsed for a few
 * seconds so a backend outage does not produce a wall of notifications.
 */
export function notify(message, type = 'info') {
  if (typeof window === 'undefined' || !message) return;
  const now = Date.now();
  if (message === lastMessage && now - lastAt < 8000) return;
  lastMessage = message;
  lastAt = now;
  window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: { message, type } }));
}

export function subscribeToasts(handler) {
  if (typeof window === 'undefined') return () => {};
  const listener = (event) => handler(event.detail);
  window.addEventListener(TOAST_EVENT, listener);
  return () => window.removeEventListener(TOAST_EVENT, listener);
}
