import { useCallback, useEffect, useState } from "react";

import { getCapabilities, type CapabilityWorkspace } from "./capabilities";
import { localizedApiError } from "./client";

export interface CapabilityQuery {
  candidateId: string;
  graphVersionId?: string;
}

export type CapabilitiesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: CapabilityWorkspace }
  | { status: "error"; message: string };

export function useCapabilities(
  query: CapabilityQuery | null,
): [CapabilitiesState, () => void] {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<CapabilitiesState>({ status: "idle" });
  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    if (query === null) {
      setState({ status: "idle" });
      return undefined;
    }
    const controller = new AbortController();
    setState({ status: "loading" });
    getCapabilities(query.candidateId, query.graphVersionId, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ status: "error", message: localizedApiError(error) });
        }
      });
    return () => controller.abort();
  }, [attempt, query]);

  return [state, retry];
}
