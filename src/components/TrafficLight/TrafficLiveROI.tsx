'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Button, Card, Badge } from 'react-bootstrap';

// ROI point interface
interface Point {
  x: number; // normalized [0, 1]
  y: number; // normalized [0, 1]
}

// Traffic light ROI interface
export interface TrafficLightROI {
  id: string;
  label: string;
  points: Point[];
  color: {
    stroke: string;
    fill: string;
  };
  signalState?: 'RED' | 'YELLOW' | 'GREEN' | 'UNKNOWN';
}

interface TrafficLiveROIProps {
  videoWidth: number;
  videoHeight: number;
  onROIUpdate?: (rois: TrafficLightROI[]) => void;
  canvasRef?: React.RefObject<HTMLCanvasElement>;
  className?: string;
}

const SIGNAL_COLORS = [
  { stroke: '#ef4444', fill: 'rgba(239, 68, 68, 0.2)' },
  { stroke: '#f59e0b', fill: 'rgba(245, 158, 11, 0.2)' },
  { stroke: '#10b981', fill: 'rgba(16, 185, 129, 0.2)' },
  { stroke: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.2)' },
  { stroke: '#06b6d4', fill: 'rgba(6, 182, 212, 0.2)' },
];

export const TrafficLiveROI: React.FC<TrafficLiveROIProps> = ({
  videoWidth,
  videoHeight,
  onROIUpdate,
  canvasRef,
  className = '',
}) => {
  const [rois, setRois] = useState<TrafficLightROI[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [draftPoints, setDraftPoints] = useState<Point[]>([]);
  const [mousePos, setMousePos] = useState<Point | null>(null);
  const [nextRoiIndex, setNextRoiIndex] = useState(1);
  const svgRef = useRef<SVGSVGElement>(null);

  // Normalize pixel coordinates to [0, 1]
  const normalizePoint = useCallback(
    (clientX: number, clientY: number): Point | null => {
      const element = canvasRef?.current || svgRef.current;
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      const x = (clientX - rect.left) / rect.width;
      const y = (clientY - rect.top) / rect.height;
      return {
        x: Math.max(0, Math.min(1, x)),
        y: Math.max(0, Math.min(1, y)),
      };
    },
    [canvasRef]
  );

  // Check if mouse is near start point for closing polygon
  const isNearStartPoint = useCallback(
    (point: Point): boolean => {
      if (draftPoints.length < 3) return false;
      const start = draftPoints[0];
      const dx = Math.abs(point.x - start.x) * videoWidth;
      const dy = Math.abs(point.y - start.y) * videoHeight;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < 15;
    },
    [draftPoints, videoWidth, videoHeight]
  );

  // Start drawing mode
  const handleStartDrawing = useCallback(() => {
    setIsDrawing(true);
    setDraftPoints([]);
    setMousePos(null);
  }, []);

  // Cancel drawing
  const handleCancelDrawing = useCallback(() => {
    setIsDrawing(false);
    setDraftPoints([]);
    setMousePos(null);
  }, []);

  // Handle mouse move
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!isDrawing) return;
      const point = normalizePoint(e.clientX, e.clientY);
      if (point) {
        setMousePos(point);
      }
    },
    [isDrawing, normalizePoint]
  );

  // Handle click to add point
  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!isDrawing) return;
      e.preventDefault();
      e.stopPropagation();

      const point = normalizePoint(e.clientX, e.clientY);
      if (!point) return;

      // Check if clicking near start point to close polygon
      if (isNearStartPoint(point)) {
        if (draftPoints.length >= 3) {
          const newROI: TrafficLightROI = {
            id: `traffic-light-${Date.now()}`,
            label: `Đèn ${nextRoiIndex}`,
            points: [...draftPoints],
            color: SIGNAL_COLORS[(nextRoiIndex - 1) % SIGNAL_COLORS.length],
            signalState: 'UNKNOWN',
          };

          const updatedRois = [...rois, newROI];
          setRois(updatedRois);
          setNextRoiIndex(nextRoiIndex + 1);
          setIsDrawing(false);
          setDraftPoints([]);
          setMousePos(null);

          if (onROIUpdate) {
            onROIUpdate(updatedRois);
          }
        }
      } else {
        setDraftPoints([...draftPoints, point]);
      }
    },
    [isDrawing, normalizePoint, isNearStartPoint, draftPoints, rois, nextRoiIndex, onROIUpdate]
  );

  // Delete ROI
  const handleDeleteROI = useCallback(
    (roiId: string) => {
      const updatedRois = rois.filter((roi) => roi.id !== roiId);
      setRois(updatedRois);
      if (onROIUpdate) {
        onROIUpdate(updatedRois);
      }
    },
    [rois, onROIUpdate]
  );

  // Clear all ROIs
  const handleClearAll = useCallback(() => {
    setRois([]);
    setNextRoiIndex(1);
    if (onROIUpdate) {
      onROIUpdate([]);
    }
  }, [onROIUpdate]);

  // Convert points to SVG polygon string
  const pointsToSvgString = (points: Point[]): string => {
    return points.map((p) => `${p.x * videoWidth},${p.y * videoHeight}`).join(' ');
  };

  // Get signal state badge color
  const getSignalBadgeColor = (state?: string): string => {
    switch (state) {
      case 'RED':
        return 'danger';
      case 'YELLOW':
        return 'warning';
      case 'GREEN':
        return 'success';
      default:
        return 'secondary';
    }
  };

  return (
    <div className={`traffic-live-roi ${className}`}>
      {/* Control Panel */}
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex align-items-center justify-content-between mb-3">
            <h5 className="mb-0">🚦 Vùng Đèn Giao Thông</h5>
            <Badge bg="info">{rois.length} vùng</Badge>
          </div>

          <div className="d-flex gap-2 flex-wrap">
            {!isDrawing ? (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleStartDrawing}
                  disabled={isDrawing}
                >
                  ✏️ Vẽ Vùng ROI
                </Button>
                {rois.length > 0 && (
                  <Button variant="outline-danger" size="sm" onClick={handleClearAll}>
                    🗑️ Xóa Tất Cả
                  </Button>
                )}
              </>
            ) : (
              <>
                <Button variant="success" size="sm" disabled>
                  ✓ Click để vẽ điểm (click vào điểm đầu để hoàn thành)
                </Button>
                <Button variant="outline-secondary" size="sm" onClick={handleCancelDrawing}>
                  ✕ Hủy
                </Button>
              </>
            )}
          </div>

          {/* ROI List */}
          {rois.length > 0 && (
            <div className="mt-3">
              <small className="text-muted d-block mb-2">Danh sách vùng:</small>
              <div className="d-flex flex-column gap-2">
                {rois.map((roi) => (
                  <div
                    key={roi.id}
                    className="d-flex align-items-center justify-content-between p-2 border rounded"
                    style={{ backgroundColor: '#f8f9fa' }}
                  >
                    <div className="d-flex align-items-center gap-2">
                      <div
                        style={{
                          width: '16px',
                          height: '16px',
                          backgroundColor: roi.color.stroke,
                          borderRadius: '3px',
                        }}
                      />
                      <span className="fw-medium">{roi.label}</span>
                      <Badge bg={getSignalBadgeColor(roi.signalState)} className="ms-2">
                        {roi.signalState || 'UNKNOWN'}
                      </Badge>
                    </div>
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => handleDeleteROI(roi.id)}
                    >
                      ✕
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* SVG Overlay for Drawing - positioned over canvas */}
      {canvasRef?.current && (
        <svg
          ref={svgRef}
          viewBox={`0 0 ${videoWidth} ${videoHeight}`}
          preserveAspectRatio="none"
          onClick={handleClick}
          onMouseMove={handleMouseMove}
          style={{
            position: 'absolute',
            top: canvasRef.current.offsetTop,
            left: canvasRef.current.offsetLeft,
            width: canvasRef.current.offsetWidth,
            height: canvasRef.current.offsetHeight,
            cursor: isDrawing ? 'crosshair' : 'default',
            pointerEvents: isDrawing ? 'auto' : 'none',
            zIndex: 10,
          }}
        >
          {/* Render existing ROIs */}
          {rois.map((roi) => (
            <g key={roi.id}>
              <polygon
                points={pointsToSvgString(roi.points)}
                fill={roi.color.fill}
                stroke={roi.color.stroke}
                strokeWidth={3}
              />
              <text
                x={roi.points[0].x * videoWidth}
                y={roi.points[0].y * videoHeight - 10}
                fill="#ffffff"
                fontSize={14}
                fontWeight="bold"
                style={{
                  paintOrder: 'stroke',
                  stroke: '#000000',
                  strokeWidth: 3,
                }}
              >
                {roi.label}
              </text>
            </g>
          ))}

          {/* Draft polygon while drawing */}
          {isDrawing && draftPoints.length > 0 && (
            <>
              <polyline
                points={pointsToSvgString(draftPoints)}
                fill="none"
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="6 4"
              />

              {mousePos && (
                <line
                  x1={draftPoints[draftPoints.length - 1].x * videoWidth}
                  y1={draftPoints[draftPoints.length - 1].y * videoHeight}
                  x2={mousePos.x * videoWidth}
                  y2={mousePos.y * videoHeight}
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                />
              )}

              {draftPoints.map((point, idx) => (
                <circle
                  key={`draft-${idx}`}
                  cx={point.x * videoWidth}
                  cy={point.y * videoHeight}
                  r={6}
                  fill="#f59e0b"
                  stroke="#ffffff"
                  strokeWidth={2}
                />
              ))}

              {draftPoints.length >= 3 && mousePos && isNearStartPoint(mousePos) && (
                <circle
                  cx={draftPoints[0].x * videoWidth}
                  cy={draftPoints[0].y * videoHeight}
                  r={15}
                  fill="none"
                  stroke="#10b981"
                  strokeWidth={3}
                  strokeDasharray="4 2"
                  opacity={0.8}
                />
              )}
            </>
          )}
        </svg>
      )}
    </div>
  );
};
