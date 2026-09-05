import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { RiskEvent, CaseStatus } from '../types/riskFeed';
import { riskApi } from '../services/api';

const SESSION_STORAGE_KEY = 'ai_risk_canonical_session_feed';
const SESSION_CLEARED_AT_KEY = 'ai_risk_canonical_session_cleared_at';
const SESSION_CLEARED_IDS_KEY = 'ai_risk_canonical_session_cleared_ids';

interface RiskFeedContextType {
  events: RiskEvent[];
  addEvent: (event: Omit<RiskEvent, 'id' | 'timestamp'> & { id?: string }) => void;
  mergeEvents: (incomingEvents: RiskEvent[]) => void;
  updateEventStatus: (id: string, status: CaseStatus, operatorAction?: string, operatorNotes?: string) => void;
  clearFeed: () => void;
  selectedEvent: RiskEvent | null;
  setSelectedEvent: (event: RiskEvent | null) => void;
  clearedAt: number | null;
}

const RiskFeedContext = createContext<RiskFeedContextType | undefined>(undefined);

function getEventTimestamp(timestamp: any): number {
  if (!timestamp) return 0;
  if (timestamp instanceof Date) {
    const t = timestamp.getTime();
    return isNaN(t) ? 0 : t;
  }
  const t = new Date(timestamp).getTime();
  return isNaN(t) ? 0 : t;
}

function loadSessionClearedAt(): number | null {
  try {
    const raw = sessionStorage.getItem(SESSION_CLEARED_AT_KEY);
    if (raw) {
      const parsed = parseInt(raw, 10);
      if (!isNaN(parsed) && parsed > 0) {
        return parsed;
      }
    }
  } catch {
    // Non-blocking fallback
  }
  return null;
}

function loadSessionClearedIds(): Set<string> {
  try {
    const raw = sessionStorage.getItem(SESSION_CLEARED_IDS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return new Set(parsed);
      }
    }
  } catch {
    // Non-blocking fallback
  }
  return new Set();
}

function loadSessionEvents(clearedAt: number | null, clearedIds: Set<string>): RiskEvent[] {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed
          .map((e) => ({
            ...e,
            timestamp: new Date(e.timestamp),
          }))
          .filter((e) => {
            // 1. Exclude if event was explicitly cleared by ID
            if (clearedIds.has(e.id)) return false;

            // 2. Exclude ancient events (>60s prior to cleared boundary)
            if (clearedAt !== null) {
              const t = getEventTimestamp(e.timestamp);
              if (t > 0 && t < (clearedAt - 60000)) return false;
            }
            return true;
          });
      }
    }
  } catch {
    // Non-blocking fallback
  }
  return [];
}

export const RiskFeedProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [clearedAt, setClearedAt] = useState<number | null>(loadSessionClearedAt);
  const [clearedIds, setClearedIds] = useState<Set<string>>(loadSessionClearedIds);
  const clearedAtRef = useRef<number | null>(clearedAt);
  const clearedIdsRef = useRef<Set<string>>(clearedIds);

  useEffect(() => {
    clearedAtRef.current = clearedAt;
  }, [clearedAt]);

  useEffect(() => {
    clearedIdsRef.current = clearedIds;
  }, [clearedIds]);

  const [events, setEvents] = useState<RiskEvent[]>(() => loadSessionEvents(clearedAt, clearedIds));
  const [selectedEvent, setSelectedEvent] = useState<RiskEvent | null>(null);

  // Synchronize state to sessionStorage so page navigation and reloads stay consistent
  useEffect(() => {
    try {
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(events));
    } catch {
      // Non-blocking
    }
  }, [events]);

  const addEvent = useCallback((eventData: Omit<RiskEvent, 'id' | 'timestamp'> & { id?: string }) => {
    const nowIso = new Date().toISOString();
    const eventId = eventData.id || `evt_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

    setEvents((prev) => {
      const existingIdx = prev.findIndex((e) => e.id === eventId);
      if (existingIdx >= 0) {
        // Update the existing case in-place rather than creating duplicates
        const updated = [...prev];
        updated[existingIdx] = {
          ...updated[existingIdx],
          ...eventData,
          id: eventId,
          timestamp: new Date(),
          updatedAt: nowIso,
        };
        return updated;
      }

      const newEvent: RiskEvent = {
        status: 'OPEN',
        updatedAt: nowIso,
        ...eventData,
        id: eventId,
        timestamp: new Date(),
      };

      return [newEvent, ...prev];
    });
  }, []);

  const mergeEvents = useCallback((incomingEvents: RiskEvent[]) => {
    if (!incomingEvents || incomingEvents.length === 0) return;
    setEvents((prev) => {
      const activeClearedAt = clearedAtRef.current;
      const activeClearedIds = clearedIdsRef.current;

      const existingIds = new Set(prev.map((e) => e.id));
      const nowIso = new Date().toISOString();

      const newItems = incomingEvents
        .filter((e) => {
          // 1. Avoid duplicate addition if already in active feed
          if (existingIds.has(e.id)) return false;

          // 2. Filter out if explicitly part of cleared event IDs
          if (activeClearedIds.has(e.id)) return false;

          // 3. Clock-skew-safe timestamp check:
          // Filter out ancient historical events that occurred well before clearedAt (>60s before clear),
          // while admitting legitimate new events created around or after the clear operation.
          if (activeClearedAt !== null) {
            const eventTime = getEventTimestamp(e.timestamp);
            if (eventTime > 0 && eventTime < (activeClearedAt - 60000)) {
              return false;
            }
          }

          return true;
        })
        .map((e) => ({
          status: e.status || 'OPEN',
          updatedAt: e.updatedAt || nowIso,
          ...e,
        }));

      if (newItems.length === 0) return prev;
      const combined = [...newItems, ...prev];
      return combined.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    });
  }, []);

  // Centralized polling for live Razorpay test webhook risk events
  useEffect(() => {
    let mounted = true;
    const pollWebhookEvents = async () => {
      try {
        const eventsRes = await riskApi.getRazorpayRecentEvents();
        if (mounted && Array.isArray(eventsRes) && eventsRes.length > 0) {
          const mappedEvents: RiskEvent[] = eventsRes.map((item) => ({
            id: item.id,
            timestamp: new Date(item.timestamp),
            engine: (item.engine as any) || 'FRAUD_SPIKE',
            source: (item.source as any) || 'LIVE_ASSESSMENT',
            title: item.title,
            entityId: item.entityId,
            entityType: (item.entityType as any) || 'MERCHANT',
            severity: item.severity,
            score: item.score,
            decision: item.decision,
            rawMl: item.rawMl || {},
            evidence: item.evidence || [],
            telemetry: item.telemetry || {},
            policy: item.policy,
            attribution: item.attribution,
            returnRisk: item.returnRisk,
          }));
          mergeEvents(mappedEvents);
        }
      } catch {
        // Non-blocking fallback
      }
    };

    pollWebhookEvents();
    const interval = setInterval(pollWebhookEvents, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [mergeEvents]);

  const updateEventStatus = useCallback((id: string, status: CaseStatus, operatorAction?: string, operatorNotes?: string) => {
    const nowIso = new Date().toISOString();
    setEvents((prev) =>
      prev.map((e) => {
        if (e.id === id) {
          return {
            ...e,
            status,
            operatorAction: operatorAction !== undefined ? operatorAction : e.operatorAction,
            operatorNotes: operatorNotes !== undefined ? operatorNotes : e.operatorNotes,
            updatedAt: nowIso,
          };
        }
        return e;
      })
    );

    setSelectedEvent((prev) => {
      if (prev && prev.id === id) {
        return {
          ...prev,
          status,
          operatorAction: operatorAction !== undefined ? operatorAction : prev.operatorAction,
          operatorNotes: operatorNotes !== undefined ? operatorNotes : prev.operatorNotes,
          updatedAt: nowIso,
        };
      }
      return prev;
    });
  }, []);

  const clearFeed = useCallback(() => {
    const now = Date.now();

    // 1. Immediately capture IDs of all events currently in React state
    const currentIds = events.map((e) => e.id);
    const initialClearedIds = new Set([...Array.from(clearedIdsRef.current), ...currentIds]);

    clearedAtRef.current = now;
    clearedIdsRef.current = initialClearedIds;

    setClearedAt(now);
    setClearedIds(initialClearedIds);

    setEvents([]);
    setSelectedEvent(null);

    try {
      sessionStorage.setItem(SESSION_CLEARED_AT_KEY, now.toString());
      sessionStorage.setItem(SESSION_CLEARED_IDS_KEY, JSON.stringify(Array.from(initialClearedIds)));
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      // Non-blocking
    }

    // 2. Also snapshot current backend events to ensure any pre-existing backend IDs are cleared
    riskApi
      .getRazorpayRecentEvents()
      .then((recent) => {
        if (Array.isArray(recent) && recent.length > 0) {
          const backendIds = recent.map((r) => r.id);
          const fullClearedIds = new Set([...Array.from(clearedIdsRef.current), ...backendIds]);
          clearedIdsRef.current = fullClearedIds;
          setClearedIds(fullClearedIds);
          try {
            sessionStorage.setItem(SESSION_CLEARED_IDS_KEY, JSON.stringify(Array.from(fullClearedIds)));
          } catch {
            // Non-blocking
          }
        }
      })
      .catch(() => {
        // Non-blocking
      });
  }, [events]);

  return (
    <RiskFeedContext.Provider
      value={{
        events,
        addEvent,
        mergeEvents,
        updateEventStatus,
        clearFeed,
        selectedEvent,
        setSelectedEvent,
        clearedAt,
      }}
    >
      {children}
    </RiskFeedContext.Provider>
  );
};

export function useRiskFeed(): RiskFeedContextType {
  const context = useContext(RiskFeedContext);
  if (!context) {
    throw new Error('useRiskFeed must be used within a RiskFeedProvider');
  }
  return context;
}
