/**
 * useFacultyWebSocket
 * ====================
 * Custom hook that manages a persistent WebSocket connection to the faculty
 * analytics channel at:
 *   ws(s)://HOST/ws/faculty/{sessionId}?token=<JWT>
 *
 * Features:
 *   • Exponential back-off reconnection (up to MAX_RETRIES, capped at MAX_BACKOFF_MS)
 *   • Discriminated-union event parsing with full TypeScript narrowing
 *   • React Query cache invalidation for attendance_verified and risk_score_updated
 *   • Zustand authStore for token retrieval (never stores WS in global state)
 *   • Automatic cleanup on component unmount
 *
 * Usage:
 *   const { connectionState, lastEvent } = useFacultyWebSocket({ sessionId });
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/authStore';
import { ACCESS_TOKEN_KEY } from '@/constants/auth';
import type { FacultyWSEvent, WSConnectionState } from '@/types/websocket';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_RETRIES = 5;
const BASE_BACKOFF_MS = 1_000;   // 1 second
const MAX_BACKOFF_MS = 30_000;   // 30 seconds

/** Derive ws:// or wss:// from the current page protocol */
function getWsBaseUrl(): string {
  const { protocol, hostname, port } = window.location;
  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
  // In development Vite proxies /api → :8000 but the WS lives directly on :8000
  const wsPort = port === '5173' || port === '5174' ? '8000' : port;
  return `${wsProtocol}//${hostname}:${wsPort}`;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UseFacultyWebSocketOptions {
  /** The active lecture session_id to subscribe to. Pass null/undefined to skip. */
  sessionId: string | null | undefined;
}

export interface UseFacultyWebSocketResult {
  connectionState: WSConnectionState;
  lastEvent: FacultyWSEvent | null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useFacultyWebSocket(
  { sessionId }: UseFacultyWebSocketOptions,
): UseFacultyWebSocketResult {
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const [connectionState, setConnectionState] = useState<WSConnectionState>('closed');
  const [lastEvent, setLastEvent] = useState<FacultyWSEvent | null>(null);

  // Stable refs so event handlers never capture stale closures
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);

  // ------------------------------------------------------------------
  // Event handler — runs for every WS message received
  // ------------------------------------------------------------------
  const handleMessage = useCallback(
    (raw: MessageEvent) => {
      let event: FacultyWSEvent;
      try {
        event = JSON.parse(raw.data as string) as FacultyWSEvent;
      } catch {
        return; // Ignore non-JSON frames (e.g. plain-text pings)
      }

      setLastEvent(event);

      switch (event.type) {
        case 'attendance_verified': {
          // Invalidate the trends chart and the overview stat cards
          void queryClient.invalidateQueries({ queryKey: ['attendance-trends'] });
          void queryClient.invalidateQueries({ queryKey: ['ml-analytics-overview'] });
          toast.success(`✓ ${event.student_name} verified`, {
            description: `Session attendance: ${event.attendance_count}`,
            duration: 4_000,
          });
          break;
        }

        case 'spoofing_attempt_detected': {
          toast.error('⚠ Spoofing attempt detected', {
            description: event.reason,
            duration: 8_000,
          });
          break;
        }

        case 'risk_score_updated': {
          // Surgically update the matching student in the React Query cache
          queryClient.setQueryData<
            Array<{
              id: string;
              riskScore: number;
              riskLabel: 'Safe' | 'At Risk' | 'Critical';
            }>
          >(['at-risk-students'], (prev) => {
            if (!prev) return prev;
            return prev.map((s) =>
              s.id === event.student_id
                ? {
                    ...s,
                    riskScore: event.new_risk_score,
                    riskLabel: event.risk_label,
                  }
                : s,
            );
          });
          break;
        }
      }
    },
    [queryClient],
  );

  // ------------------------------------------------------------------
  // connect() — open a new WebSocket, wire up handlers
  // ------------------------------------------------------------------
  const connect = useCallback(() => {
    if (!sessionId || !isAuthenticated) return;

    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token || token === 'undefined' || token === 'null') return;

    const url = `${getWsBaseUrl()}/ws/faculty/${sessionId}?token=${encodeURIComponent(token)}`;

    setConnectionState('connecting');
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;
      setConnectionState('connected');
    };

    ws.onmessage = handleMessage;

    ws.onclose = (evt) => {
      wsRef.current = null;

      if (!shouldReconnectRef.current) {
        setConnectionState('closed');
        return;
      }

      // Normal close codes (1000 = normal, 1008 = policy violation / auth fail)
      // — do not retry on auth failure
      if (evt.code === 1008) {
        setConnectionState('failed');
        return;
      }

      if (retryCountRef.current >= MAX_RETRIES) {
        setConnectionState('failed');
        return;
      }

      const backoff = Math.min(
        BASE_BACKOFF_MS * 2 ** retryCountRef.current,
        MAX_BACKOFF_MS,
      );
      retryCountRef.current += 1;
      setConnectionState('reconnecting');

      retryTimerRef.current = setTimeout(() => {
        connect();
      }, backoff);
    };

    ws.onerror = () => {
      // onerror is always followed by onclose — let onclose drive reconnection
    };
  }, [sessionId, isAuthenticated, handleMessage]);

  // ------------------------------------------------------------------
  // Effect — mount / sessionId change
  // ------------------------------------------------------------------
  useEffect(() => {
    shouldReconnectRef.current = true;
    retryCountRef.current = 0;
    connect();

    return () => {
      // Unmount — close cleanly, suppress reconnection
      shouldReconnectRef.current = false;
      if (retryTimerRef.current !== null) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
      setConnectionState('closed');
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, isAuthenticated]);

  return { connectionState, lastEvent };
}
