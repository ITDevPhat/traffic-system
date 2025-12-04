'use client';

import React, { useEffect, useState } from 'react';
import { Alert, Badge } from 'react-bootstrap';

export interface ViolationEvent {
  type: string;
  track_id: number;
  timestamp: number;
  details?: {
    light_state?: string;
    [key: string]: any;
  };
}

interface ViolationOverlayProps {
  violations: ViolationEvent[];
  maxDisplay?: number;
  autoHideDelay?: number;
  className?: string;
}

export const ViolationOverlay: React.FC<ViolationOverlayProps> = ({
  violations,
  maxDisplay = 5,
  autoHideDelay = 5000,
  className = '',
}) => {
  const [visibleViolations, setVisibleViolations] = useState<ViolationEvent[]>([]);

  useEffect(() => {
    // Add new violations
    if (violations.length > 0) {
      setVisibleViolations((prev) => {
        const newViolations = violations.filter(
          (v) => !prev.some((pv) => pv.track_id === v.track_id && pv.type === v.type)
        );
        return [...newViolations, ...prev].slice(0, maxDisplay);
      });
    }
  }, [violations, maxDisplay]);

  // Auto-hide violations after delay
  useEffect(() => {
    if (visibleViolations.length === 0) return;

    const timer = setTimeout(() => {
      setVisibleViolations((prev) => prev.slice(0, -1));
    }, autoHideDelay);

    return () => clearTimeout(timer);
  }, [visibleViolations, autoHideDelay]);

  const getViolationColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'red_light':
        return 'danger';
      case 'late_yellow':
        return 'warning';
      case 'stopline_crossing':
        return 'danger';
      case 'speeding':
        return 'warning';
      default:
        return 'danger';
    }
  };

  const getViolationIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'red_light':
        return '🚨';
      case 'late_yellow':
        return '⚠️';
      case 'stopline_crossing':
        return '🚫';
      case 'speeding':
        return '💨';
      default:
        return '⚠️';
    }
  };

  const formatViolationType = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (visibleViolations.length === 0) {
    return null;
  }

  return (
    <div
      className={`violation-overlay ${className}`}
      style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        zIndex: 1000,
        maxWidth: '350px',
      }}
    >
      {visibleViolations.map((violation, index) => (
        <Alert
          key={`${violation.track_id}-${violation.type}-${index}`}
          variant={getViolationColor(violation.type)}
          className="mb-2 py-2 px-3"
          style={{
            animation: 'slideIn 0.3s ease-out',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          <div className="d-flex align-items-center gap-2">
            <span style={{ fontSize: '1.5rem' }}>{getViolationIcon(violation.type)}</span>
            <div>
              <div className="fw-bold">
                {formatViolationType(violation.type)}
              </div>
              <small>
                Vehicle ID: <Badge bg="dark">#{violation.track_id}</Badge>
              </small>
              {violation.details?.light_state && (
                <small className="d-block">
                  Light: {violation.details.light_state.toUpperCase()}
                </small>
              )}
            </div>
          </div>
        </Alert>
      ))}

      <style jsx global>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
};

export default ViolationOverlay;
