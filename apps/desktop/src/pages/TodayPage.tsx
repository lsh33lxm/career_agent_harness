import { AlertCircle, CheckCircle2, RefreshCw } from "lucide-react";

import { useHealth } from "../api/useHealth";

export function TodayPage() {
  const [health, retry] = useHealth();

  return (
    <main className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Friday, September 18</p>
          <h1>Today</h1>
        </div>
        <div className={`service-status service-status--${health.status}`} aria-live="polite">
          {health.status === "loading" && <span className="status-spinner" aria-hidden="true" />}
          {health.status === "online" && <CheckCircle2 size={16} aria-hidden="true" />}
          {health.status === "offline" && <AlertCircle size={16} aria-hidden="true" />}
          <span>
            {health.status === "loading" && "Connecting"}
            {health.status === "online" && `Core ${health.data.version}`}
            {health.status === "offline" && "Core offline"}
          </span>
          {health.status === "offline" && (
            <button type="button" onClick={retry} title="Retry connection" aria-label="Retry connection">
              <RefreshCw size={15} />
            </button>
          )}
        </div>
      </div>

      <section className="metrics-band" aria-label="Workspace summary">
        <div>
          <span>Needs review</span>
          <strong>0</strong>
        </div>
        <div>
          <span>Next actions</span>
          <strong>0</strong>
        </div>
        <div>
          <span>Active opportunities</span>
          <strong>0</strong>
        </div>
        <div>
          <span>Upcoming interviews</span>
          <strong>0</strong>
        </div>
      </section>

      <section className="work-queue">
        <div className="section-heading">
          <h2>Work queue</h2>
          <span>0 items</span>
        </div>
        <div className="empty-state">
          <div className="empty-state-mark" aria-hidden="true">
            <CheckCircle2 size={22} />
          </div>
          <h3>Nothing needs attention</h3>
          <p>New evidence, reviews, follow-ups, and blocked runs will appear here.</p>
        </div>
      </section>
    </main>
  );
}
