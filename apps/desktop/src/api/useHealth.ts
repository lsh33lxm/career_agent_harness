import { useCallback, useEffect, useState } from "react";

import { getHealth, localizedApiError, type HealthResponse } from "./client";

type HealthState =
  | { status: "loading" }
  | { status: "online"; data: HealthResponse }
  | { status: "offline"; message: string };

export function useHealth(): [HealthState, () => void] {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<HealthState>({ status: "loading" });

  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    getHealth(controller.signal)
      .then((data) => setState({ status: "online", data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ status: "offline", message: localizedApiError(error) });
        }
      });
    return () => controller.abort();
  }, [attempt]);

  return [state, retry];
}
