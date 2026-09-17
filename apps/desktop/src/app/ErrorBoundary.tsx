import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  failed: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // The foundation intentionally avoids logging potentially sensitive UI state.
  }

  render(): ReactNode {
    if (this.state.failed) {
      return (
        <main className="fatal-state">
          <h1>Workspace unavailable</h1>
          <p>The current view could not be rendered.</p>
          <button type="button" onClick={() => window.location.reload()}>
            Reload workspace
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
