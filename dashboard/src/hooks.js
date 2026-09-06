import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Polls `fn` on an interval. Keeps the last good value on a transient failure
 * so a single dropped request doesn't blank the dashboard.
 */
export function usePoll(fn, intervalMs, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const alive = useRef(true);
  const cb = useCallback(fn, deps); // eslint-disable-line react-hooks/exhaustive-deps

  const refresh = useCallback(async () => {
    try {
      const next = await cb();
      if (!alive.current) return;
      setData(next);
      setError(null);
    } catch (e) {
      if (alive.current) setError(e);
    } finally {
      if (alive.current) setLoaded(true);
    }
  }, [cb]);

  useEffect(() => {
    alive.current = true;
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => {
      alive.current = false;
      clearInterval(id);
    };
  }, [refresh, intervalMs]);

  return { data, error, loaded, refresh };
}

/** Re-renders on a timer so relative timestamps ("42s ago") stay honest. */
export function useTicker(intervalMs = 1000) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}
