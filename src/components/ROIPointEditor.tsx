'use client';

import React, { useRef, useEffect, useState } from 'react';
import { Button, Alert } from 'react-bootstrap';
import { useRoiStore } from '@/store/useRoiStore';
import { Point } from '@/types/roi';
import { ShapeUtils } from '@/utils/roiShape';

interface ROIPointEditorProps {
  videoWidth: number;
  videoHeight: number;
  className?: string;
}

export const ROIPointEditor: React.FC<ROIPointEditorProps> = ({
  videoWidth,
  videoHeight,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [draggedPointIndex, setDraggedPointIndex] = useState<number | null>(null);
  const [hoveredPointIndex, setHoveredPointIndex] = useState<number | null>(null);
  const [editedPoints, setEditedPoints] = useState<Point[]>([]);

  // Get state from store
  const rois = useRoiStore((state) => state.rois);
  const selectedRoiId = useRoiStore((state) => state.selectedRoiId);
  const updateRoi = useRoiStore((state) => state.updateRoi);

  // Get selected ROI
  const selectedRoi = rois.find((r) => r.id === selectedRoiId);

  // Initialize edited points when selection changes
  useEffect(() => {
    if (selectedRoi && isEditing) {
      setEditedPoints([...selectedRoi.coordinates]);
    }
  }, [selectedRoi?.id, isEditing]);

  // Render editing overlay
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isEditing || !selectedRoi) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, videoWidth, videoHeight);

    // Render ROI shape
    renderEditableRoi(ctx, editedPoints, selectedRoi.shape);

    // Render draggable points
    editedPoints.forEach((point, index) => {
      renderEditPoint(ctx, point, index === hoveredPointIndex, index === draggedPointIndex);
    });
  }, [isEditing, editedPoints, hoveredPointIndex, draggedPointIndex, videoWidth, videoHeight]);

  // Render editable ROI shape
  const renderEditableRoi = (
    ctx: CanvasRenderingContext2D,
    points: Point[],
    shape: 'polygon' | 'line' | 'rectangle'
  ) => {
    if (points.length === 0) return;

    ctx.strokeStyle = '#FFFF00'; // Yellow for editing
    ctx.lineWidth = 3;
    ctx.globalAlpha = 0.8;
    ctx.setLineDash([5, 5]); // Dashed line

    if (shape === 'polygon') {
      if (points.length < 3) return;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      points.forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.closePath();
      ctx.stroke();
    } else if (shape === 'line') {
      if (points.length !== 2) return;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      ctx.lineTo(points[1].x, points[1].y);
      ctx.stroke();
    } else if (shape === 'rectangle') {
      if (points.length !== 2) return;
      const rect4Points = ShapeUtils.rectangleTo4Points(points[0], points[1]);
      ctx.beginPath();
      ctx.moveTo(rect4Points[0].x, rect4Points[0].y);
      rect4Points.forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.closePath();
      ctx.stroke();
    }

    ctx.setLineDash([]); // Reset dash
    ctx.globalAlpha = 1.0;
  };

  // Render individual edit point
  const renderEditPoint = (
    ctx: CanvasRenderingContext2D,
    point: Point,
    isHovered: boolean,
    isDragged: boolean
  ) => {
    const radius = isDragged ? 10 : isHovered ? 8 : 6;

    // Outer circle (white)
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
    ctx.fill();

    // Inner circle (blue or yellow)
    ctx.fillStyle = isDragged ? '#FFFF00' : isHovered ? '#00AAFF' : '#0066FF';
    ctx.beginPath();
    ctx.arc(point.x, point.y, radius - 2, 0, Math.PI * 2);
    ctx.fill();

    // Point index label
    if (isHovered || isDragged) {
      ctx.font = '12px Arial';
      ctx.fillStyle = '#FFFFFF';
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 2;
      const index = editedPoints.findIndex((p) => p.x === point.x && p.y === point.y);
      const text = `P${index}`;
      ctx.strokeText(text, point.x - 8, point.y - 12);
      ctx.fillText(text, point.x - 8, point.y - 12);
    }
  };

  // Check if mouse is near a point
  const getNearestPoint = (mousePos: Point): number | null => {
    const threshold = 15; // pixels
    for (let i = 0; i < editedPoints.length; i++) {
      const point = editedPoints[i];
      const dist = Math.sqrt(
        Math.pow(mousePos.x - point.x, 2) + Math.pow(mousePos.y - point.y, 2)
      );
      if (dist <= threshold) {
        return i;
      }
    }
    return null;
  };

  // Handle mouse move
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isEditing || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const mousePos: Point = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    // If dragging, update point position
    if (draggedPointIndex !== null) {
      const newPoints = [...editedPoints];
      newPoints[draggedPointIndex] = mousePos;
      setEditedPoints(newPoints);
    } else {
      // Check for hover
      const nearestIndex = getNearestPoint(mousePos);
      setHoveredPointIndex(nearestIndex);
    }
  };

  // Handle mouse down (start drag)
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isEditing || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const mousePos: Point = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    const nearestIndex = getNearestPoint(mousePos);
    if (nearestIndex !== null) {
      setDraggedPointIndex(nearestIndex);
    }
  };

  // Handle mouse up (stop drag)
  const handleMouseUp = () => {
    if (draggedPointIndex !== null) {
      setDraggedPointIndex(null);
    }
  };

  // Handle start editing
  const handleStartEditing = () => {
    if (!selectedRoi) {
      alert('Please select a ROI first');
      return;
    }
    setIsEditing(true);
    setEditedPoints([...selectedRoi.coordinates]);
  };

  // Handle save changes
  const handleSaveChanges = () => {
    if (!selectedRoi) return;

    // Validate points
    if (selectedRoi.shape === 'line' && editedPoints.length !== 2) {
      alert('Line must have exactly 2 points');
      return;
    }

    if (selectedRoi.shape === 'rectangle' && editedPoints.length !== 2) {
      alert('Rectangle must have exactly 2 points');
      return;
    }

    if (selectedRoi.shape === 'polygon' && editedPoints.length < 3) {
      alert('Polygon must have at least 3 points');
      return;
    }

    // Update ROI
    updateRoi(selectedRoi.id, {
      coordinates: editedPoints,
    });

    setIsEditing(false);
    setEditedPoints([]);
    alert('ROI updated successfully!');
  };

  // Handle cancel editing
  const handleCancelEditing = () => {
    setIsEditing(false);
    setEditedPoints([]);
    setDraggedPointIndex(null);
    setHoveredPointIndex(null);
  };

  // Handle delete point
  const handleDeletePoint = () => {
    if (hoveredPointIndex === null || !selectedRoi) return;

    // Check minimum points
    if (selectedRoi.shape === 'polygon' && editedPoints.length <= 3) {
      alert('Polygon must have at least 3 points');
      return;
    }

    if (selectedRoi.shape === 'line' || selectedRoi.shape === 'rectangle') {
      alert('Cannot delete points from line or rectangle');
      return;
    }

    // Remove point
    const newPoints = editedPoints.filter((_, index) => index !== hoveredPointIndex);
    setEditedPoints(newPoints);
    setHoveredPointIndex(null);
  };

  // Handle add point (insert between two points)
  const handleAddPoint = () => {
    if (hoveredPointIndex === null || !selectedRoi) return;

    if (selectedRoi.shape === 'line' || selectedRoi.shape === 'rectangle') {
      alert('Cannot add points to line or rectangle');
      return;
    }

    // Insert point between current and next point
    const nextIndex = (hoveredPointIndex + 1) % editedPoints.length;
    const currentPoint = editedPoints[hoveredPointIndex];
    const nextPoint = editedPoints[nextIndex];

    // Calculate midpoint
    const newPoint: Point = {
      x: (currentPoint.x + nextPoint.x) / 2,
      y: (currentPoint.y + nextPoint.y) / 2,
    };

    // Insert new point
    const newPoints = [...editedPoints];
    newPoints.splice(nextIndex, 0, newPoint);
    setEditedPoints(newPoints);
  };

  // Keyboard shortcuts
  useEffect(() => {
    if (!isEditing) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleCancelEditing();
      } else if (e.key === 'Enter') {
        handleSaveChanges();
      } else if (e.key === 'Delete' && hoveredPointIndex !== null) {
        handleDeletePoint();
      } else if (e.key === '+' && hoveredPointIndex !== null) {
        handleAddPoint();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isEditing, hoveredPointIndex, editedPoints]);

  if (!selectedRoi) {
    return (
      <Alert variant="info" className="m-3">
        Please select a ROI from the list to enable point editing
      </Alert>
    );
  }

  return (
    <div className="roi-point-editor">
      {!isEditing ? (
        <Button variant="warning" className="w-100 mb-3" onClick={handleStartEditing}>
          ✏️ Edit Points
        </Button>
      ) : (
        <>
          <Alert variant="warning" className="mb-2 py-2">
            <small>
              <strong>Point Editing Mode Active</strong>
              <br />
              • Drag points to move them
              <br />
              • Hover over point and press Delete to remove
              <br />
              • Hover over point and press + to add point after
              <br />
              Points: {editedPoints.length}
            </small>
          </Alert>

          <div className="d-flex gap-2 mb-3">
            <Button variant="success" size="sm" onClick={handleSaveChanges}>
              ✓ Save
            </Button>
            <Button variant="danger" size="sm" onClick={handleCancelEditing}>
              ✕ Cancel
            </Button>
          </div>

          <canvas
            ref={canvasRef}
            width={videoWidth}
            height={videoHeight}
            className={className}
            onMouseMove={handleMouseMove}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              cursor: draggedPointIndex !== null ? 'grabbing' : hoveredPointIndex !== null ? 'grab' : 'default',
              pointerEvents: 'auto',
              zIndex: 1000, // Above ROIOverlay
            }}
          />
        </>
      )}
    </div>
  );
};
