// ScholarLab/frontend/src/shared/hooks/useStudentWebSocket.ts
import { useEffect, useCallback, useState, useRef } from 'react';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/authStore';
import type { CurriculumItem } from '@/types/student';

interface CurriculumUnlockedEvent {
  curriculumItem: CurriculumItem;
  message: string;
}

export const useStudentWebSocket = (enabled: boolean = true) => {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [unlockedItems, setUnlockedItems] = useState<CurriculumItem[]>([]);
  
  // Grab the token to authenticate the WS connection
  const token = useAuthStore((state) => state.accessToken);

  useEffect(() => {
    if (!enabled || !token) return;

    const baseUrl = import.meta.env.VITE_API_URL?.replace('http', 'ws') || 'ws://localhost:8000/api';
    // Append the token as a query parameter for the FastAPI backend
    const wsUrl = `${baseUrl}/ws/student?token=${token}`;
    
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setIsConnected(true);
      // Removed the toast success here so it doesn't spam the user on silent reconnects
    };

    socket.onclose = () => setIsConnected(false);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'curriculum:unlocked') {
          const payload = data.payload as CurriculumUnlockedEvent;
          setUnlockedItems((prev) => [...prev, payload.curriculumItem]);
          toast.success(payload.message || 'New curriculum unlocked!', {
            description: payload.curriculumItem.title,
            duration: 5000,
          });
        }
      } catch (err) {
        console.error("Failed to parse websocket message", err);
      }
    };

    wsRef.current = socket;

    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [enabled, token]);

  const emitAttendanceMarked = useCallback((lectureId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'attendance:marked', payload: { lectureId } }));
    }
  }, []);

  return { isConnected, unlockedItems, emitAttendanceMarked };
};