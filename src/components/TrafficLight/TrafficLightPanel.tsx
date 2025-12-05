'use client';

import React from 'react';

// Traffic light state types
export type TrafficLightState = 'GREEN' | 'RED' | 'YELLOW' | 'UNKNOWN';

// Component state interface
export interface TrafficLightPanelState {
  currentState: TrafficLightState;
  confidence: number;
  lastUpdate: string;
  framePreview: string | null;
  isDetecting: boolean;
}

interface TrafficLightPanelProps {
  state: TrafficLightPanelState;
  onStartDetection: () => void;
  onStopDetection: () => void;
  disabled?: boolean;
  className?: string;
}

// State to color mapping
const STATE_COLORS: Record<TrafficLightState, string> = {
  GREEN: '#10b981',
  RED: '#ef4444',
  YELLOW: '#f59e0b',
  UNKNOWN: '#6b7280',
};

export const TrafficLightPanel: React.FC<TrafficLightPanelProps> = ({
  state,
  onStartDetection,
  onStopDetection,
  disabled = false,
  className = '',
}) => {
  const stateColor = STATE_COLORS[state.currentState];

  return (
    <div
      className={`traffic-light-panel ${className}`}
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '16px',
        backgroundColor: '#ffffff',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          fontSize: '18px',
          fontWeight: 'bold',
          color: '#1f2937',
          borderBottom: '2px solid #e5e7eb',
          paddingBottom: '8px',
        }}
      >
        Traffic Light ROI
      </div>

      {/* ROI Preview Image */}
      <div
        style={{
          width: '100%',
          minHeight: '200px',
          backgroundColor: '#f3f4f6',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {state.framePreview ? (
          <img
            src={state.framePreview}
            alt="Traffic Light ROI Preview"
            style={{
              maxWidth: '100%',
              maxHeight: '300px',
              objectFit: 'contain',
            }}
          />
        ) : (
          <div
            style={{
              color: '#9ca3af',
              fontSize: '14px',
              textAlign: 'center',
              padding: '20px',
            }}
          >
            No ROI selected
          </div>
        )}
      </div>

      {/* State Display */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span
            style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#4b5563',
            }}
          >
            Status:
          </span>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '16px',
              fontWeight: 'bold',
              color: stateColor,
            }}
          >
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: stateColor,
                display: 'inline-block',
              }}
            />
            {state.currentState}
            {state.confidence > 0 && (
              <span
                style={{
                  fontSize: '14px',
                  fontWeight: 'normal',
                  color: '#6b7280',
                }}
              >
                ({Math.round(state.confidence * 100)}%)
              </span>
            )}
          </span>
        </div>

        {state.lastUpdate && (
          <div
            style={{
              fontSize: '12px',
              color: '#6b7280',
            }}
          >
            Last Update: {state.lastUpdate}
          </div>
        )}
      </div>

      {/* Control Buttons */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          flexWrap: 'wrap',
        }}
      >
        <button
          onClick={onStartDetection}
          disabled={disabled || state.isDetecting}
          style={{
            flex: 1,
            minWidth: '120px',
            padding: '10px 16px',
            backgroundColor: state.isDetecting ? '#9ca3af' : '#10b981',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '600',
            cursor: state.isDetecting || disabled ? 'not-allowed' : 'pointer',
            opacity: state.isDetecting || disabled ? 0.6 : 1,
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            if (!state.isDetecting && !disabled) {
              e.currentTarget.style.backgroundColor = '#059669';
            }
          }}
          onMouseLeave={(e) => {
            if (!state.isDetecting && !disabled) {
              e.currentTarget.style.backgroundColor = '#10b981';
            }
          }}
        >
          Start Detection
        </button>

        <button
          onClick={onStopDetection}
          disabled={disabled || !state.isDetecting}
          style={{
            flex: 1,
            minWidth: '120px',
            padding: '10px 16px',
            backgroundColor: !state.isDetecting ? '#9ca3af' : '#ef4444',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '600',
            cursor: !state.isDetecting || disabled ? 'not-allowed' : 'pointer',
            opacity: !state.isDetecting || disabled ? 0.6 : 1,
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            if (state.isDetecting && !disabled) {
              e.currentTarget.style.backgroundColor = '#dc2626';
            }
          }}
          onMouseLeave={(e) => {
            if (state.isDetecting && !disabled) {
              e.currentTarget.style.backgroundColor = '#ef4444';
            }
          }}
        >
          Stop Detection
        </button>
      </div>
    </div>
  );
};
