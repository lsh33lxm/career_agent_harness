import { useCallback, useEffect, useState } from "react";

import { localizedApiError } from "./client";
import { getToday, type TodayQueue } from "./today";

export type TodayState =
  | { status: "loading" }
  | { status: "ready"; data: TodayQueue }
  | { status: "error"; message: string };

export function useToday(): [TodayState, () => void] {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<TodayState>({ status: "loading" });

  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    getToday(controller.signal)
      .then((data) => setState({ status: "ready", data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ status: "error", message: localizedApiError(error) });
        }
      });
    return () => controller.abort();
  }, [attempt]);

  return [state, retry];
}
