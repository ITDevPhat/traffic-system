'use client';

import React, { useEffect } from 'react';
import { Button, Alert } from 'react-bootstrap';
import { useRoiStore } from '@/store/useRoiStore';
import { ROI_SHAPES, RoiType } from '@/types/roi';

interface ROIDrawingControlsProps {
  roiType: RoiType;
  roiName: string;
  onDrawingComplete: () => void;
}

export const ROIDrawingControls: React.FC<ROIDrawingControlsProps> = ({
  roiType,
  roiName,
  onDrawingComplete,
}) => {
  const drawingMode = useRoiStore((state) => state.drawingMode);
  const currentPoints = useRoiStore((state) => state.currentPoints);
  const setDrawingMode = useRoiStore((state) => state.setDrawingMode);
  const clearPoints = useRoiStore((state) => state.clearPoints);

  const shape = ROI_SHAPES[roiType];

  // Auto-finish for line and rectangle after 2 points
  useEffect(() => {
    if (drawingMode && currentPoints.length === 2 && (shape === 'line' || shape === 'rectangle')) {
      // Auto-finish after a short delay to allow the point to be rendered
      const timer = setTimeout(() => {
        handleFinishDrawing();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [currentPoints.length, drawingMode, shape]);

  // Keyboard shortcuts
  useEffect(() => {
    if (!drawingMode) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Cancel drawing
        handleCancelDrawing();
      } else if (e.key === 'Enter') {
        // Finish drawing (if valid)
        if (
          (shape === 'line' && currentPoints.length === 2) ||
          (shape === 'rectangle' && currentPoints.length === 2) ||
          (shape === 'polygon' && currentPoints.length >= 3)
        ) {
          handleFinishDrawing();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [drawingMode, currentPoints.length, shape]);

  // Get instruction text based on shape
  const getInstructionText = () => {
    if (shape === 'line') {
      return 'Click 2 points to create line';
    } else if (shape === 'rectangle') {
      return 'Click 2 corners to create rectangle';
    } else {
      return 'Click to add points, double-click or click first point to close polygon';
    }
  };

  // Handle start drawing
  const handleStartDrawing = () => {
    if (!roiName || roiName.trim().length < 3) {
      alert('Please enter a valid ROI name (at least 3 characters) before drawing');
      return;
    }
    setDrawingMode(true);
    clearPoints();
  };

  // Handle cancel drawing
  const handleCancelDrawing = () => {
    setDrawingMode(false);
    clearPoints();
  };

  // Handle finish drawing
  const handleFinishDrawing = () => {
    // Validate points based on shape
    if (shape === 'line' && currentPoints.length !== 2) {
      alert('Line must have exactly 2 points');
      return;
    }

    if (shape === 'rectangle' && currentPoints.length !== 2) {
      alert('Rectangle must have exactly 2 points');
      return;
    }

    if (shape === 'polygon' && currentPoints.length < 3) {
      alert('Polygon must have at least 3 points');
      return;
    }

    // Notify parent component
    onDrawingComplete();
  };

  return (
    <div className="drawing-controls mb-3">
      {!drawingMode ? (
        <Button variant="primary" className="w-100" onClick={handleStartDrawing}>
          🖊️ Start Drawing
        </Button>
      ) : (
        <>
          <Alert variant="info" className="mb-2 py-2">
            <small>
              <strong>Drawing Mode Active</strong>
              <br />
              {getInstructionText()}
              <br />
              Points: {currentPoints.length}
              {shape === 'polygon' && currentPoints.length >= 3 && (
                <span className="text-success"> (Can close)</span>
              )}
            </small>
          </Alert>

          <div className="d-flex gap-2">
            <Button
              variant="success"
              size="sm"
              onClick={handleFinishDrawing}
              disabled={
                (shape === 'line' && currentPoints.length !== 2) ||
                (shape === 'rectangle' && currentPoints.length !== 2) ||
                (shape === 'polygon' && currentPoints.length < 3)
              }
            >
              ✓ Finish
            </Button>
            <Button variant="danger" size="sm" onClick={handleCancelDrawing}>
              ✕ Cancel
            </Button>
          </div>
        </>
      )}
    </div>
  );
};
