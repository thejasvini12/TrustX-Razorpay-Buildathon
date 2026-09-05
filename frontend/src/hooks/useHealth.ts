import { useState, useEffect, useCallback } from 'react';
import { HealthResponse } from '../types/api';
import { riskApi } from '../services/api';

export interface HealthState {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
  lastChecked: Date | null;
  latencyMs: number | null;
  refresh: () => Promise<void>;
}

export function useHealth(pollIntervalMs: number = 10000): HealthState {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const check = useCallback(async () => {
    const startTime = performance.now();
    try {
      setLoading(true);
      const res = await riskApi.getHealth();
      const elapsed = Math.round(performance.now() - startTime);
      setHealth(res);
      setLatencyMs(elapsed);
      setError(null);
      setLastChecked(new Date());
    } catch (err: any) {
      setHealth(null);
      setLatencyMs(null);
      setError(err?.message || 'Backend unreachable');
      setLastChecked(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    check();
    if (pollIntervalMs > 0) {
      const interval = setInterval(check, pollIntervalMs);
      return () => clearInterval(interval);
    }
  }, [check, pollIntervalMs]);

  return { health, loading, error, lastChecked, latencyMs, refresh: check };
}
