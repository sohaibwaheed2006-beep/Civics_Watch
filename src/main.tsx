import React from 'react';
import ReactDOM from 'react-dom/client';
import App from '@/app/App';
import { AppErrorBoundary } from '@/components/error-boundary';
import { initObservability } from '@/lib/observability';
import '@/styles/index.css';

// Start error tracking before the app renders so startup errors are captured.
// No-op unless VITE_SENTRY_DSN is configured.
initObservability();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>
);
