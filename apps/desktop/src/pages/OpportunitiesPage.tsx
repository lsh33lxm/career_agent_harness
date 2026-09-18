import {
  AlertCircle,
  BriefcaseBusiness,
  Check,
  Inbox,
  Plus,
  RefreshCw,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  admitOpportunityManually,
  admitOpportunityProposal,
  getOpportunity,
  listOpportunities,
  setOpportunityUserPriority,
  type OpportunitySummary,
  type PriorityLevel,
} from "../api/client";

const priorityLevels: PriorityLevel[] = ["low", "medium", "high", "urgent"];

type LoadState = "loading" | "ready" | "error";
type AdmissionPath = "manual" | "proposal";

function requestId(prefix: string): string {
  const suffix = globalThis.crypto.randomUUID?.().replaceAll("-", "_")
    ?? `${Date.now()}_${Math.random().toString(36).slice(2)}`;
  return `${prefix}_${suffix}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The Local API request failed";
}

function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export function OpportunitiesPage() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [items, setItems] = useState<OpportunitySummary[]>([]);
  const [loadError, setLoadError] = useState("");
  const [admissionOpen, setAdmissionOpen] = useState(false);
  const [admissionPath, setAdmissionPath] = useState<AdmissionPath>("manual");
  const [admissionPending, setAdmissionPending] = useState(false);
  const [admissionError, setAdmissionError] = useState("");
  const [priorityDrafts, setPriorityDrafts] = useState<Record<string, PriorityLevel | "">>({});
  const [priorityReasons, setPriorityReasons] = useState<Record<string, string>>({});
  const [priorityPending, setPriorityPending] = useState<string | null>(null);
  const [priorityErrors, setPriorityErrors] = useState<Record<string, string>>({});

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadState("loading");
    setLoadError("");
    try {
      const opportunities = await listOpportunities(signal);
      setItems(opportunities);
      setLoadState("ready");
    } catch (error) {
      if (!signal?.aborted) {
        setLoadError(errorMessage(error));
        setLoadState("error");
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function handleAdmission(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const jobId = String(data.get("jobId"));
    const jobRevision = Number(data.get("jobRevision"));
    const reason = String(data.get("reason") ?? "").trim();
    const opportunityId = requestId("opportunity");
    const baseRequest = {
      command_id: requestId("command"),
      opportunity_id: opportunityId,
      decision_id: requestId("decision"),
      job_id: jobId,
      job_revision: jobRevision,
      ...(reason ? { reason } : {}),
    };

    setAdmissionPending(true);
    setAdmissionError("");
    try {
      if (admissionPath === "proposal") {
        await admitOpportunityProposal(
          {
            ...baseRequest,
            proposal_id: String(data.get("proposalId")),
            proposal_reason: String(data.get("proposalReason")),
            proposed_by: "agent",
          },
          requestId("proposal_admission"),
        );
      } else {
        await admitOpportunityManually(baseRequest, requestId("manual_admission"));
      }
      const opportunities = await listOpportunities();
      setItems(opportunities);
      setLoadState("ready");
      setAdmissionOpen(false);
      form.reset();
    } catch (error) {
      setAdmissionError(errorMessage(error));
    } finally {
      setAdmissionPending(false);
    }
  }

  async function handlePriority(event: FormEvent<HTMLFormElement>, item: OpportunitySummary) {
    event.preventDefault();
    const opportunityId = item.opportunity.entity_id;
    const level = priorityDrafts[opportunityId] ?? item.user_priority?.level ?? "";
    if (!level) {
      return;
    }

    const reason = priorityReasons[opportunityId]?.trim();
    setPriorityPending(opportunityId);
    setPriorityErrors((current) => ({ ...current, [opportunityId]: "" }));
    try {
      await setOpportunityUserPriority(
        opportunityId,
        {
          command_id: requestId("command"),
          expected_revision: item.opportunity.revision,
          level,
          ...(reason ? { reason } : {}),
        },
        requestId("user_priority"),
      );
      const updated = await getOpportunity(opportunityId);
      setItems((current) =>
        current.map((opportunity) =>
          opportunity.opportunity.entity_id === opportunityId ? updated : opportunity,
        ),
      );
      setPriorityDrafts((current) => ({ ...current, [opportunityId]: updated.user_priority?.level ?? "" }));
      setPriorityReasons((current) => ({ ...current, [opportunityId]: "" }));
    } catch (error) {
      setPriorityErrors((current) => ({ ...current, [opportunityId]: errorMessage(error) }));
    } finally {
      setPriorityPending(null);
    }
  }

  return (
    <main className="page opportunities-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Opportunities</h1>
        </div>
        <button
          className="primary-command"
          type="button"
          onClick={() => {
            setAdmissionOpen((open) => !open);
            setAdmissionError("");
          }}
        >
          {admissionOpen ? <X size={17} aria-hidden="true" /> : <Plus size={17} aria-hidden="true" />}
          <span>{admissionOpen ? "Close" : "Add opportunity"}</span>
        </button>
      </div>

      {admissionOpen && (
        <section className="admission-panel" aria-labelledby="admission-title">
          <div className="section-heading">
            <h2 id="admission-title">Opportunity admission</h2>
          </div>
          <form className="admission-form" onSubmit={handleAdmission}>
            <fieldset className="admission-path">
              <legend>Admission path</legend>
              <div className="segmented-control">
                <button
                  type="button"
                  aria-pressed={admissionPath === "manual"}
                  onClick={() => setAdmissionPath("manual")}
                >
                  Manual
                </button>
                <button
                  type="button"
                  aria-pressed={admissionPath === "proposal"}
                  onClick={() => setAdmissionPath("proposal")}
                >
                  Confirm proposal
                </button>
              </div>
            </fieldset>

            <label>
              <span>Job ID</span>
              <input
                name="jobId"
                required
                minLength={3}
                maxLength={128}
                pattern="[a-z][a-z0-9_-]+"
                placeholder="job_..."
              />
            </label>
            <label>
              <span>Job revision</span>
              <input name="jobRevision" type="number" required min={1} step={1} defaultValue={1} />
            </label>

            {admissionPath === "proposal" && (
              <>
                <label>
                  <span>Proposal ID</span>
                  <input
                    name="proposalId"
                    required
                    minLength={3}
                    maxLength={128}
                    pattern="[a-z][a-z0-9_-]+"
                    placeholder="proposal_..."
                  />
                </label>
                <label className="form-field-wide">
                  <span>Proposal reason</span>
                  <textarea name="proposalReason" required maxLength={2048} rows={2} />
                </label>
              </>
            )}

            <label className="form-field-wide">
              <span>Decision note <small>Optional</small></span>
              <textarea name="reason" maxLength={2048} rows={2} />
            </label>

            {admissionError && (
              <p className="inline-error form-field-wide" role="alert">
                <AlertCircle size={16} aria-hidden="true" />
                {admissionError}
              </p>
            )}

            <div className="form-actions form-field-wide">
              <button className="primary-command" type="submit" disabled={admissionPending}>
                <Check size={17} aria-hidden="true" />
                <span>{admissionPending ? "Adding..." : admissionPath === "manual" ? "Add opportunity" : "Confirm and add"}</span>
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="opportunity-list" aria-labelledby="opportunity-list-title">
        <div className="section-heading">
          <h2 id="opportunity-list-title">Active records</h2>
          {loadState === "ready" && <span>{items.length} {items.length === 1 ? "item" : "items"}</span>}
        </div>

        {loadState === "loading" && (
          <div className="opportunity-state" aria-live="polite">
            <span className="status-spinner" aria-hidden="true" />
            <p>Loading opportunities</p>
          </div>
        )}

        {loadState === "error" && (
          <div className="opportunity-state" role="alert">
            <AlertCircle size={24} aria-hidden="true" />
            <h3>Could not load opportunities</h3>
            <p>{loadError}</p>
            <button className="secondary-command" type="button" onClick={() => void load()}>
              <RefreshCw size={16} aria-hidden="true" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {loadState === "ready" && items.length === 0 && (
          <div className="opportunity-state">
            <Inbox size={24} aria-hidden="true" />
            <h3>No opportunities yet</h3>
          </div>
        )}

        {loadState === "ready" && items.length > 0 && (
          <div className="opportunity-records">
            {items.map((item) => {
              const opportunityId = item.opportunity.entity_id;
              const selectedPriority = priorityDrafts[opportunityId] ?? item.user_priority?.level ?? "";
              const priorityError = priorityErrors[opportunityId];
              return (
                <article className="opportunity-record" key={opportunityId}>
                  <header className="record-header">
                    <div className="record-identity">
                      <BriefcaseBusiness size={18} aria-hidden="true" />
                      <div>
                        <h3>{item.job.job_id}</h3>
                        <p>{opportunityId}</p>
                      </div>
                    </div>
                    <div className="record-meta">
                      <span>{titleCase(item.opportunity.state)}</span>
                      <span>Revision {item.opportunity.revision}</span>
                      <span>Job revision {item.job.revision}</span>
                    </div>
                  </header>

                  <div className="priority-columns">
                    <section aria-label={`Suggested priority for ${item.job.job_id}`}>
                      <div className="priority-heading">
                        <h4>Suggested priority</h4>
                        {item.suggested_priority ? (
                          <span className={`priority-badge priority-badge--${item.suggested_priority.level}`}>
                            {titleCase(item.suggested_priority.level)}
                          </span>
                        ) : (
                          <span className="priority-empty">Not suggested</span>
                        )}
                      </div>
                      {item.suggested_priority && (
                        <ul>
                          {item.suggested_priority.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                        </ul>
                      )}
                    </section>

                    <section aria-label={`User priority for ${item.job.job_id}`}>
                      <div className="priority-heading">
                        <h4>User priority</h4>
                        {item.user_priority ? (
                          <span className={`priority-badge priority-badge--${item.user_priority.level}`}>
                            {titleCase(item.user_priority.level)}
                          </span>
                        ) : (
                          <span className="priority-empty">Not set</span>
                        )}
                      </div>
                      {item.user_priority?.reason && <p className="priority-reason">{item.user_priority.reason}</p>}
                      <form className="priority-form" onSubmit={(event) => void handlePriority(event, item)}>
                        <label>
                          <span className="sr-only">Set user priority for {item.job.job_id}</span>
                          <select
                            aria-label={`Set user priority for ${item.job.job_id}`}
                            value={selectedPriority}
                            onChange={(event) =>
                              setPriorityDrafts((current) => ({
                                ...current,
                                [opportunityId]: event.target.value as PriorityLevel | "",
                              }))
                            }
                          >
                            <option value="">Select priority</option>
                            {priorityLevels.map((level) => <option key={level} value={level}>{titleCase(level)}</option>)}
                          </select>
                        </label>
                        <label className="priority-note">
                          <span className="sr-only">Priority reason for {item.job.job_id}</span>
                          <input
                            aria-label={`Priority reason for ${item.job.job_id}`}
                            value={priorityReasons[opportunityId] ?? ""}
                            onChange={(event) =>
                              setPriorityReasons((current) => ({
                                ...current,
                                [opportunityId]: event.target.value,
                              }))
                            }
                            maxLength={2048}
                            placeholder="Reason (optional)"
                          />
                        </label>
                        <button
                          className="secondary-command"
                          type="submit"
                          disabled={!selectedPriority || priorityPending === opportunityId}
                        >
                          <Check size={16} aria-hidden="true" />
                          <span>{priorityPending === opportunityId ? "Saving..." : "Save"}</span>
                        </button>
                      </form>
                      {priorityError && <p className="inline-error" role="alert">{priorityError}</p>}
                    </section>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
