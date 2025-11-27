import { useEffect, useRef, useState } from 'react';
import { getAccessToken } from '@/services/api';

interface UseWebSocketOptions {
  /**
   * Whether to automatically reconnect on disconnect
   * @default true
   */
  autoReconnect?: boolean;

  /**
   * Delay in milliseconds before attempting to reconnect
   * @default 3000
   */
  reconnectDelay?: number;

  /**
   * Maximum number of reconnection attempts
   * @default 5
   */
  maxReconnectAttempts?: number;

  /**
   * Callback fired when connection is established
   */
  onConnect?: () => void;

  /**
   * Callback fired when connection is closed
   */
  onDisconnect?: () => void;

  /**
   * Callback fired when an error occurs
   */
  onError?: (error: Event) => void;
}

/**
 * Custom hook for WebSocket connections with automatic reconnection
 * @param url - WebSocket URL (e.g., 'ws://localhost:8000/ws')
 * @param onMessage - Callback for handling incoming messages
 * @param options - Connection options
 * @returns Connection state and control functions
 */
export function useWebSocket<T = any>(
  url: string | null,
  onMessage: (data: T) => void,
  options: UseWebSocketOptions = {}
) {
  const {
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = () => {
    if (!url) return;

    try {
      // Get access token for authentication
      const token = getAccessToken();

      // Append token as query parameter
      const wsUrl = token ? `${url}?token=${token}` : url;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('[WebSocket] Connected to', url);
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        onConnect?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
          setError('Failed to parse message');
        }
      };

      ws.current.onerror = (event) => {
        console.error('[WebSocket] Error:', event);
        setError('WebSocket error occurred');
        onError?.(event);
      };

      ws.current.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        onDisconnect?.();

        // Attempt to reconnect if enabled
        if (autoReconnect && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          console.log(
            `[WebSocket] Reconnecting (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})...`
          );

          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError('Max reconnection attempts reached');
        }
      };
    } catch (err) {
      console.error('[WebSocket] Connection error:', err);
      setError(err instanceof Error ? err.message : 'Connection failed');
    }
  };

  const disconnect = () => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  };

  const send = (data: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send message: not connected');
    }
  };

  useEffect(() => {
    if (url) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url]); // Only reconnect if URL changes

  return {
    isConnected,
    error,
    send,
    disconnect,
    reconnect: connect,
  };
}

/**
 * Hook for subscribing to audit log events in real-time
 * @param onEvent - Callback for handling audit events
 * @param enabled - Whether to enable the WebSocket connection
 */
export function useAuditLogStream(
  onEvent: (event: any) => void,
  enabled: boolean = true
) {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const wsUrl = enabled ? `${apiBaseUrl.replace('http', 'ws')}/api/v1/audit/stream` : null;

  return useWebSocket(wsUrl, onEvent, {
    autoReconnect: true,
    reconnectDelay: 3000,
    maxReconnectAttempts: 5,
    onConnect: () => console.log('[Audit Stream] Connected'),
    onDisconnect: () => console.log('[Audit Stream] Disconnected'),
  });
}
