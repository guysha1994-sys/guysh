// frontend/src/hooks/usePolling.ts
import { useCallback, useEffect, useRef, useState } from "react";

export function usePolling(fetcher: () => Promise<void>, intervalMs = 60000) {
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    await fetcherRef.current();
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

  return { lastUpdated, refresh };
}
