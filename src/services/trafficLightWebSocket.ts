/**
 * Traffic Light WebSocket Client Manager
 * Feature: traffic-light-roi-detection
 * Requirements: 4.1, 4.2, 9.5
 */

export type TrafficLightState = 'GREEN' | 'RED' | 'YELLOW' | 'UNKNOWN';

export type WSMessageType = 'state_update' | 'error' | 'info' | 'connection';

export interface TLMessage {
  type: WSMessageType;
  state?: TrafficLightState;
  confidence?: number;
  timestamp?: string;
  frame?: string; // base64 JPEG
  error?: string;
  info?: string;
}

type MessageCallback = (data: TLMessage) => void;
type ErrorCallback = (error: Error) => void;
type CloseCallback = () => void;

/**
 * TrafficLightWSClient manages WebSocket connection for traffic light detection
 * with auto-reconnect and error handling capabilities.
 */
export class TrafficLightWSClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts: number = 0;
  private readonly maxReconnectAttempts: number = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private cameraId: string | null = null;
  private isManualDisconnect: boolean = false;

  // Callbacks
  private messageCallback: MessageCallback | null = null;
  private errorCallback: ErrorCallback | null = null;
  private closeCallback: CloseCallback | null = null;

  /**
   * Connect to the traffic light WebSocket endpoint
   * @param cameraId - The camera ID to connect to
   * @returns Promise that resolves when connection is established
   */
  async connect(cameraId: string): Promise<void> {
    this.cameraId = cameraId;
    this.isManualDisconnect = false;

    // Close existing connection if any
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    return new Promise((resolve, reject) => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const wsUrl = apiUrl.replace('http', 'ws');
        const url = `${wsUrl}/ws/traffic-light?camera_id=${encodeURIComponent(cameraId)}`;

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          console.log(`✅ Traffic Light WebSocket connected: ${cameraId}`);
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = this.parseMessage(event.data);
            if (this.messageCallback) {
              this.messageCallback(message);
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
            if (this.errorCallback) {
              this.errorCallback(error as Error);
            }
          }
        };

        this.ws.onerror = (event) => {
          console.error('WebSocket error:', event);
          const error = new Error('WebSocket connection error');
          if (this.errorCallback) {
            this.errorCallback(error);
          }
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('🔌 Traffic Light WebSocket closed');
          this.ws = null;

          if (this.closeCallback) {
            this.closeCallback();
          }

          // Auto-reconnect if not manually disconnected
          if (!this.isManualDisconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.handleReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket
   */
  disconnect(): void {
    this.isManualDisconnect = true;
    this.reconnectAttempts = 0;

    // Clear any pending reconnect timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.cameraId = null;
  }

  /**
   * Register callback for incoming messages
   * @param callback - Function to call when message is received
   */
  onMessage(callback: MessageCallback): void {
    this.messageCallback = callback;
  }

  /**
   * Register callback for errors
   * @param callback - Function to call when error occurs
   */
  onError(callback: ErrorCallback): void {
    this.errorCallback = callback;
  }

  /**
   * Register callback for connection close
   * @param callback - Function to call when connection closes
   */
  onClose(callback: CloseCallback): void {
    this.closeCallback = callback;
  }

  /**
   * Check if WebSocket is currently connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Handle reconnection with exponential backoff
   * @private
   */
  private handleReconnect(): void {
    if (!this.cameraId || this.isManualDisconnect) {
      return;
    }

    this.reconnectAttempts++;
    
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 16000);

    console.log(
      `🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
    );

    this.reconnectTimeout = setTimeout(() => {
      if (this.cameraId && !this.isManualDisconnect) {
        this.connect(this.cameraId).catch((error) => {
          console.error('Reconnection failed:', error);
          if (this.errorCallback) {
            this.errorCallback(new Error('Reconnection failed'));
          }
        });
      }
    }, delay);
  }

  /**
   * Parse incoming WebSocket message
   * @param data - Raw message data (string or JSON)
   * @returns Parsed TLMessage object
   * @private
   */
  private parseMessage(data: string): TLMessage {
    try {
      const parsed = JSON.parse(data);
      
      // Validate message structure
      if (!parsed.type) {
        throw new Error('Message missing required "type" field');
      }

      // Ensure type is valid
      const validTypes: WSMessageType[] = ['state_update', 'error', 'info', 'connection'];
      if (!validTypes.includes(parsed.type)) {
        throw new Error(`Invalid message type: ${parsed.type}`);
      }

      return parsed as TLMessage;
    } catch (error) {
      console.error('Failed to parse message:', error);
      throw error;
    }
  }
}
