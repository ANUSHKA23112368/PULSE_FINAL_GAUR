/**
 * PULSE static hosting entry point.
 *
 * The prototype is a client-side React application: when /api is unreachable it
 * falls back to the bundled deterministic engine in frontend/src/services/localEngine.js.
 * This Worker only serves the built assets, so no Python service is required.
 */
export default {
  async fetch(request, env) {
    return env.ASSETS.fetch(request);
  },
};
