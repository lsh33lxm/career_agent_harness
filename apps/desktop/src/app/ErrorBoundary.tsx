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
          <h1>工作台暂时无法显示</h1>
          <p>当前页面渲染失败。你的本地数据不会因此被修改。</p>
          <button type="button" onClick={() => window.location.reload()}>
            重新加载工作台
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
