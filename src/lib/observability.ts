import * as Sentry from '@sentry/react';

/**
 * Initialise client-side error tracking.
 *
 * Optional by design: with no `VITE_SENTRY_DSN` set, Sentry is never
 * initialised, so there is zero overhead and nothing is sent. When the DSN is
 * present (set as a Vercel env var), uncaught errors and unhandled promise
 * rejections are reported automatically. Returns whether it was enabled.
 */
export function initObservability(): boolean {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return false;

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    // Errors are always captured; only performance tracing is sampled, to keep
    // within the free-tier quota.
    tracesSampleRate: 0.1,
    integrations: [Sentry.browserTracingIntegration()],
  });
  return true;
}
