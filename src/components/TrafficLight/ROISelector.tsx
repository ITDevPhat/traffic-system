'use client';

import React, { useState, useRef, useCallback } from 'react';

// Normalized ROI coordinates [0, 1]
export interface NormalizedROI {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Point {
  x: number;
  y: number;
}

interface ROISelectorProps {
  videoWidth: number;
  videoHeight: number;
  onROISelected: (roi: NormalizedROI) => void;
  className?: string;
}

export const ROISelector: React.FC<ROISelectorProps> = ({
  videoWidth,
  videoHeight,
  onROISelected,
  className = '',
}) => {
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<Point | null>(null);
  const [endPoint, setEndPoint] = useState<Point | null>(null);
  const [selectedROI, setSelectedROI] = useState<NormalizedROI | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Normalize pixel coordinates to [0, 1] range
  const normalizeCoordinates = useCallback(
    (x: number, y: number, width: number, height: number): NormalizedROI => {
      return {
        x: Math.max(0, Math.min(1, x / videoWidth)),
        y: Math.max(0, Math.min(1, y / videoHeight)),
        width: Math.max(0, Math.min(1, width / videoWidth)),
        height: Math.max(0, Math.min(1, height / videoHeight)),
      };
    },
    [videoWidth, videoHeight]
  );

  // Handle mouse down - start drawing
  const handleMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!svgRef.current) return;

      const rect = svgRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      setIsDrawing(true);
      setStartPoint({ x, y });
      setEndPoint({ x, y });
    },
    []
  );

  // Handle mouse move - update preview
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!isDrawing || !startPoint || !svgRef.current) return;

      const rect = svgRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      setEndPoint({ x, y });
    },
    [isDrawing, startPoint]
  );

  // Handle mouse up - finalize ROI
  const handleMouseUp = useCallback(() => {
    if (!isDrawing || !startPoint || !endPoint) return;

    // Calculate rectangle bounds
    const x = Math.min(startPoint.x, endPoint.x);
    const y = Math.min(startPoint.y, endPoint.y);
    const width = Math.abs(endPoint.x - startPoint.x);
    const height = Math.abs(endPoint.y - startPoint.y);

    // Normalize coordinates
    const normalizedROI = normalizeCoordinates(x, y, width, height);

    // Update state
    setSelectedROI(normalizedROI);
    setIsDrawing(false);

    // Notify parent
    onROISelected(normalizedROI);
  }, [isDrawing, startPoint, endPoint, normalizeCoordinates, onROISelected]);

  // Clear ROI
  const clearROI = useCallback(() => {
    setSelectedROI(null);
    setStartPoint(null);
    setEndPoint(null);
    setIsDrawing(false);
  }, []);

  // Calculate rectangle for rendering
  const getRectangle = (start: Point, end: Point) => {
    const x = Math.min(start.x, end.x);
    const y = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    return { x, y, width, height };
  };

  return (
    <svg
      ref={svgRef}
      width={videoWidth}
      height={videoHeight}
      className={className}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        cursor: isDrawing ? 'crosshair' : 'default',
        pointerEvents: 'auto',
        zIndex: 10,
      }}
    >
      {/* Preview rectangle while drawing */}
      {isDrawing && startPoint && endPoint && (
        <>
          {(() => {
            const rect = getRectangle(startPoint, endPoint);
            return (
              <rect
                x={rect.x}
                y={rect.y}
                width={rect.width}
                height={rect.height}
                fill="rgba(16, 185, 129, 0.2)"
                stroke="#10b981"
                strokeWidth={2}
                strokeDasharray="5,5"
              />
            );
          })()}
          {/* Snap circle at start point */}
          <circle
            cx={startPoint.x}
            cy={startPoint.y}
            r={8}
            fill="none"
            stroke="#10b981"
            strokeWidth={2}
          />
        </>
      )}

      {/* Selected ROI overlay */}
      {selectedROI && !isDrawing && (
        <rect
          x={selectedROI.x * videoWidth}
          y={selectedROI.y * videoHeight}
          width={selectedROI.width * videoWidth}
          height={selectedROI.height * videoHeight}
          fill="rgba(16, 185, 129, 0.15)"
          stroke="#10b981"
          strokeWidth={3}
        />
      )}

      {/* Label for selected ROI */}
      {selectedROI && !isDrawing && (
        <text
          x={selectedROI.x * videoWidth + 5}
          y={selectedROI.y * videoHeight - 5}
          fill="#ffffff"
          fontSize={14}
          fontWeight="bold"
          style={{
            paintOrder: 'stroke',
            stroke: '#000000',
            strokeWidth: 3,
          }}
        >
          Traffic Light ROI
        </text>
      )}
    </svg>
  );
};
