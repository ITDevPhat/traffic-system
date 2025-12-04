'use client';

import React, { useRef, useEffect, useState } from 'react';
import { useRoiStore } from '@/store/useRoiStore';
import { Roi, Point } from '@/types/roi';
import { ShapeUtils } from '@/utils/roiShape';

interface ROIOverlayProps {
  videoWidth: number;
  videoHeight: number;
  className?: string;
}

export const ROIOverlay: React.FC<ROIOverlayProps> = ({
  videoWidth,
  videoHeight,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredRoiId, setHoveredRoiId] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState<Point | null>(null);

  // Get state from store
  const rois = useRoiStore((state) => state.rois);
  const selectedRoiId = useRoiStore((state) => state.selectedRoiId);
  const selectRoi = useRoiStore((state) => state.selectRoi);
  const drawingMode = useRoiStore((state) => state.drawingMode);
  const currentPoints = useRoiStore((state) => state.currentPoints);
  const filterType = useRoiStore((state) => state.filterType);
  const hoveredType = useRoiStore((state) => state.hoveredType);

  // Render ROIs on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, videoWidth, videoHeight);

    // Render each ROI (with filter)
    rois.forEach((roi) => {
      // Apply filter if set
      if (filterType && roi.roi_type !== filterType) {
        return; // Skip this ROI
      }

      const isHovered = hoveredRoiId === roi.id;
      const isSelected = selectedRoiId === roi.id;
      const isTypeHovered = hoveredType === roi.roi_type;

      renderRoi(ctx, roi, isHovered, isSelected, isTypeHovered);
    });

    // Render current drawing points
    if (drawingMode && currentPoints.length > 0) {
      renderDrawingPoints(ctx, currentPoints);

      // Show snap circle if near first point (for polygon closing)
      if (
        currentPoints.length >= 3 &&
        mousePos &&
        ShapeUtils.isNear(mousePos, currentPoints[0], 12)
      ) {
        renderSnapCircle(ctx, currentPoints[0]);
      }
    }
  }, [
    rois,
    hoveredRoiId,
    selectedRoiId,
    drawingMode,
    currentPoints,
    mousePos,
    filterType,
    hoveredType,
    videoWidth,
    videoHeight,
  ]);

  // Render a single ROI
  const renderRoi = (
    ctx: CanvasRenderingContext2D,
    roi: Roi,
    isHovered: boolean,
    isSelected: boolean,
    isTypeHovered: boolean
  ) => {
    const points = roi.coordinates;
    if (points.length === 0) return;

    // Set style based on state
    ctx.strokeStyle = isSelected ? '#FFFF00' : roi.color;
    ctx.lineWidth = isSelected ? 4 : isHovered || isTypeHovered ? 3 : 2;
    ctx.globalAlpha = isHovered || isTypeHovered ? 0.9 : 0.7;

    // Render based on shape
    if (roi.shape === 'polygon') {
      renderPolygon(ctx, points, roi.name);
    } else if (roi.shape === 'line') {
      renderLine(ctx, points, roi.name);
    } else if (roi.shape === 'rectangle') {
      renderRectangle(ctx, points, roi.name);
    }

    // Reset alpha
    ctx.globalAlpha = 1.0;
  };

  // Render polygon
  const renderPolygon = (ctx: CanvasRenderingContext2D, points: Point[], label: string) => {
    if (points.length < 3) return;

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.stroke();

    // Draw label at top-left
    drawLabel(ctx, label, points[0].x, points[0].y - 10);
  };

  // Render line
  const renderLine = (ctx: CanvasRenderingContext2D, points: Point[], label: string) => {
    if (points.length !== 2) return;

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    ctx.lineTo(points[1].x, points[1].y);
    ctx.stroke();

    // Draw label at midpoint
    const midX = (points[0].x + points[1].x) / 2;
    const midY = (points[0].y + points[1].y) / 2;
    drawLabel(ctx, label, midX, midY - 10);
  };

  // Render rectangle
  const renderRectangle = (ctx: CanvasRenderingContext2D, points: Point[], label: string) => {
    if (points.length !== 2) return;

    // Convert 2 points to 4 points
    const rect4Points = ShapeUtils.rectangleTo4Points(points[0], points[1]);

    // Draw as polygon
    ctx.beginPath();
    ctx.moveTo(rect4Points[0].x, rect4Points[0].y);
    rect4Points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.stroke();

    // Draw label at top-left
    drawLabel(ctx, label, rect4Points[0].x, rect4Points[0].y - 10);
  };

  // Draw label text
  const drawLabel = (ctx: CanvasRenderingContext2D, text: string, x: number, y: number) => {
    ctx.font = '14px Arial';
    ctx.fillStyle = '#FFFFFF';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 3;

    // Draw text with outline
    ctx.strokeText(text, x, y);
    ctx.fillText(text, x, y);
  };

  // Render current drawing points
  const renderDrawingPoints = (ctx: CanvasRenderingContext2D, points: Point[]) => {
    if (points.length === 0) return;

    ctx.strokeStyle = '#00FF00';
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.8;

    // Draw lines between points
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.stroke();

    // Draw points as circles
    ctx.fillStyle = '#00FF00';
    points.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.globalAlpha = 1.0;
  };

  // Render snap circle when near first point
  const renderSnapCircle = (ctx: CanvasRenderingContext2D, point: Point) => {
    ctx.strokeStyle = '#00FF00';
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.6;

    ctx.beginPath();
    ctx.arc(point.x, point.y, 12, 0, Math.PI * 2);
    ctx.stroke();

    ctx.globalAlpha = 1.0;
  };

  // Handle mouse move for hover detection
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const currentMousePos = { x, y };

    // Update mouse position
    setMousePos(currentMousePos);

    // Check if drawing mode and near first point (for visual feedback only)
    // The snap circle is rendered in the useEffect based on mousePos

    // Check if mouse is over any ROI (only when not in drawing mode)
    if (!drawingMode) {
      let foundRoi: string | null = null;

      for (const roi of rois) {
        if (roi.shape === 'polygon' && isPointInPolygon(currentMousePos, roi.coordinates)) {
          foundRoi = roi.id;
          break;
        }
        // TODO: Add hit detection for line and rectangle
      }

      setHoveredRoiId(foundRoi);
    }
  };

  // Handle click to select ROI or add drawing point
  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const clickPoint = { x, y };

    // If in drawing mode, add point
    if (drawingMode) {
      const addPoint = useRoiStore.getState().addPoint;
      const finishDrawing = useRoiStore.getState().finishDrawing;
      const points = useRoiStore.getState().currentPoints;

      // Check if clicking near first point to close polygon (only for polygons with 3+ points)
      if (points.length >= 3 && ShapeUtils.isNear(clickPoint, points[0], 12)) {
        // Close polygon automatically
        finishDrawing();
        return;
      }

      // Add point
      addPoint(clickPoint);

      // Auto-finish for line and rectangle after 2 points
      const newPointCount = points.length + 1;
      if (newPointCount === 2) {
        // Check if we need to auto-finish (this will be handled by the drawing controls)
        // For now, just add the point and let the user click finish
        // Or we can auto-finish here
        setTimeout(() => {
          const currentPoints = useRoiStore.getState().currentPoints;
          if (currentPoints.length === 2) {
            // Auto-finish will be triggered by the drawing controls
          }
        }, 100);
      }

      return;
    }

    // Otherwise, select ROI if hovering over one
    if (hoveredRoiId) {
      selectRoi(hoveredRoiId);
    }
  };

  // Simple point-in-polygon check
  const isPointInPolygon = (point: Point, polygon: Point[]): boolean => {
    return ShapeUtils.isPointInPolygon(point, polygon);
  };

  return (
    <canvas
      ref={canvasRef}
      width={videoWidth}
      height={videoHeight}
      className={className}
      onMouseMove={handleMouseMove}
      onClick={handleClick}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        cursor: drawingMode ? 'crosshair' : hoveredRoiId ? 'pointer' : 'default',
      }}
    />
  );
};
