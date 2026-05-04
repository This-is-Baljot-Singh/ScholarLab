import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { toast } from 'sonner';

interface WebSocketMessage {
  type: string;
  payload: any;
}

export const useStudentWebSocket = () => {
  const { token, isAuthenticated } = useAuth();
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/student?token=${token}`;

    const connect = () => {
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        console.log('Real-time curriculum sync established.');
      };

      ws.current.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          
          if (data.type === 'curriculum:unlocked') {
            toast.success(data.payload.message, {
              description: `Unlocked: ${data.payload.curriculumItem.title}`,
              duration: 5000,
            });
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message', error);
        }
      };

      ws.current.onclose = (event) => {
        setIsConnected(false);
        if (event.code !== 1008) {
          setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [isAuthenticated, token]);

  return { isConnected };
};