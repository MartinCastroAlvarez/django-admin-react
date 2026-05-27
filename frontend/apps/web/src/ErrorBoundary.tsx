// App-shell error boundary (#415). A render-time throw anywhere in the
// routed content used to white-screen the whole admin; this catches it
// and shows a recoverable fallback instead, leaving the sidebar/layout
// intact. React error boundaries must be class components.

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // No telemetry pipeline in v1 — surface to the console for diagnosis.
    console.error('Unhandled render error in the admin SPA:', error, info);
  }

  override render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div role="alert" className="m-6 rounded border border-red-300 bg-red-50 p-4 text-sm">
        <p className="font-medium text-red-700">Something went wrong rendering this page.</p>
        <p className="mt-1 break-words text-red-600">{error.message}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-3 rounded border border-gray-300 px-3 py-1 text-gray-700 hover:bg-gray-100"
        >
          Reload
        </button>
      </div>
    );
  }
}
