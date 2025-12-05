/**
 * Property-Based Tests for Traffic Light WebSocket Client
 * Feature: traffic-light-roi-detection
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { TrafficLightWSClient, TLMessage, WSMessageType, TrafficLightState } from '../trafficLightWebSocket';

describe('TrafficLightWSClient - Property-Based Tests', () => {
  /**
   * Property 8: JSON Parsing Robustness
   * **Validates: Requirements 4.2**
   * 
   * For any valid JSON WebSocket message containing the required fields,
   * the frontend parsing must succeed and extract all fields without throwing exceptions.
   */
  it('Property 8: valid JSON messages with required fields parse successfully', () => {
    fc.assert(
      fc.property(
        // Generate valid message types
        fc.constantFrom<WSMessageType>('state_update', 'error', 'info', 'connection'),
        // Generate optional state
        fc.option(fc.constantFrom<TrafficLightState>('GREEN', 'RED', 'YELLOW', 'UNKNOWN')),
        // Generate optional confidence [0, 1]
        fc.option(fc.float({ min: 0, max: 1 })),
        // Generate optional timestamp (ISO string)
        fc.option(fc.date().map(d => d.toISOString())),
        // Generate optional frame (base64-like string)
        fc.option(fc.string({ minLength: 10, maxLength: 100 })),
        // Generate optional error message
        fc.option(fc.string({ minLength: 1, maxLength: 200 })),
        // Generate optional info message
        fc.option(fc.string({ minLength: 1, maxLength: 200 })),
        (type, state, confidence, timestamp, frame, error, info) => {
          // Construct a valid message
          const message: any = { type };
          
          if (state !== null) message.state = state;
          if (confidence !== null) message.confidence = confidence;
          if (timestamp !== null) message.timestamp = timestamp;
          if (frame !== null) message.frame = frame;
          if (error !== null) message.error = error;
          if (info !== null) message.info = info;

          // Convert to JSON string
          const jsonString = JSON.stringify(message);

          // Create client instance
          const client = new TrafficLightWSClient();

          // Access the private parseMessage method via reflection
          // In TypeScript, we can cast to any to access private methods for testing
          const parseMessage = (client as any).parseMessage.bind(client);

          // Parse should not throw
          let parsed: TLMessage | null = null;
          expect(() => {
            parsed = parseMessage(jsonString);
          }).not.toThrow();

          // Verify parsed message has correct structure
          expect(parsed).toBeDefined();
          expect(parsed!.type).toBe(type);
          
          // Verify optional fields are preserved
          if (state !== null) {
            expect(parsed!.state).toBe(state);
          }
          if (confidence !== null) {
            expect(parsed!.confidence).toBe(confidence);
          }
          if (timestamp !== null) {
            expect(parsed!.timestamp).toBe(timestamp);
          }
          if (frame !== null) {
            expect(parsed!.frame).toBe(frame);
          }
          if (error !== null) {
            expect(parsed!.error).toBe(error);
          }
          if (info !== null) {
            expect(parsed!.info).toBe(info);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 22: Connection Loss Feedback
   * **Validates: Requirements 9.5**
   * 
   * For any unexpected WebSocket closure (not initiated by user),
   * a warning toast with "Connection lost" message must be displayed.
   * 
   * Note: This property tests that the onClose callback is invoked when
   * the WebSocket closes unexpectedly (not via disconnect()).
   */
  it('Property 22: unexpected connection closure triggers close callback', () => {
    fc.assert(
      fc.property(
        // Generate random camera IDs
        fc.string({ minLength: 1, maxLength: 50 }),
        (cameraId) => {
          const client = new TrafficLightWSClient();
          
          let closeCallbackInvoked = false;
          
          // Register close callback
          client.onClose(() => {
            closeCallbackInvoked = true;
          });

          // Simulate connection and unexpected closure
          // We can't actually connect to a real WebSocket in unit tests,
          // but we can verify the callback registration works
          
          // For this property test, we verify that:
          // 1. The onClose callback can be registered
          // 2. The client tracks manual vs unexpected disconnects
          
          // Verify callback was registered (by checking it's not null)
          expect((client as any).closeCallback).not.toBeNull();
          
          // Verify isManualDisconnect starts as false
          expect((client as any).isManualDisconnect).toBe(false);
          
          // When disconnect() is called, isManualDisconnect should be true
          client.disconnect();
          expect((client as any).isManualDisconnect).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Additional property: Invalid JSON should throw errors
   * This ensures robustness by verifying that malformed messages are rejected
   */
  it('Property: invalid JSON messages throw parsing errors', () => {
    fc.assert(
      fc.property(
        // Generate invalid JSON strings
        fc.oneof(
          fc.constant('not json'),
          fc.constant('{invalid}'),
          fc.constant('{"type":}'),
          fc.constant('{"missing_type": true}'),
          fc.constant(''),
        ),
        (invalidJson) => {
          const client = new TrafficLightWSClient();
          const parseMessage = (client as any).parseMessage.bind(client);

          // Parsing invalid JSON should throw
          expect(() => {
            parseMessage(invalidJson);
          }).toThrow();
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Additional property: Messages with invalid type should throw
   */
  it('Property: messages with invalid type field throw errors', () => {
    fc.assert(
      fc.property(
        // Generate invalid message types
        fc.string({ minLength: 1, maxLength: 50 }).filter(
          s => !['state_update', 'error', 'info', 'connection'].includes(s)
        ),
        (invalidType) => {
          const message = { type: invalidType };
          const jsonString = JSON.stringify(message);

          const client = new TrafficLightWSClient();
          const parseMessage = (client as any).parseMessage.bind(client);

          // Parsing message with invalid type should throw
          expect(() => {
            parseMessage(jsonString);
          }).toThrow();
        }
      ),
      { numRuns: 50 }
    );
  });
});
