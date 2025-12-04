'use client';

import React, { useRef, useEffect } from 'react';
import { useRoiStore } from '@/store/useRoiStore';
import { Roi } from '@/types/roi';
import { ShapeUtils } from '@/utils/roiShape';

interface DetectionROIOverlayProps {
  width: number;
  height: number;
  cameraId: string;
  className?: string;
}

export const DetectionROIOverlay: React.FC<DetectionROIOverlayProps> = ({
  width,
  height,
  cameraId,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Get ROIs from store
  const rois = useRoiStore((state) => state.rois);
  const currentCamera = useRoiStore((state) => state.currentCamera);
  const loadFromBackend = useRoiStore((state) => state.loadFromBackend);

  // Load ROIs when camera changes
  useEffect(() => {
    if (cameraId && cameraId !== currentCamera) {
      loadFromBackend(cameraId).catch((err) => {
        console.error('Failed to load ROIs:', err);
      });
    }
  }, [cameraId, currentCamera, loadFromBackend]);

  // Render ROIs on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Render each ROI (read-only, no interaction)
    rois.forEach((roi) => {
      renderRoi(ctx, roi);
    });
  }, [rois, width, height]);

  // Render a single ROI
  const renderRoi = (ctx: CanvasRenderingContext2D, roi: Roi) => {
    const points = roi.coordinates;
    if (points.length === 0) return;

    // Set style
    ctx.strokeStyle = roi.color;
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.6;  // Semi-transparent

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
  const renderPolygon = (ctx: CanvasRenderingContext2D, points: any[], label: string) => {
    if (points.length < 3) return;

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.stroke();

    // Draw label
    drawLabel(ctx, label, points[0].x, points[0].y - 10);
  };

  // Render line
  const renderLine = (ctx: CanvasRenderingContext2D, points: any[], label: string) => {
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
  const renderRectangle = (ctx: CanvasRenderingContext2D, points: any[], label: string) => {
    if (points.length !== 2) return;

    // Convert 2 points to 4 points
    const rect4Points = ShapeUtils.rectangleTo4Points(points[0], points[1]);

    // Draw as polygon
    ctx.beginPath();
    ctx.moveTo(rect4Points[0].x, rect4Points[0].y);
    rect4Points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.stroke();

    // Draw label
    drawLabel(ctx, label, rect4Points[0].x, rect4Points[0].y - 10);
  };

  // Draw label text
  const drawLabel = (ctx: CanvasRenderingContext2D, text: string, x: number, y: number) => {
    ctx.font = '12px Arial';
    ctx.fillStyle = '#FFFFFF';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 2;

    // Draw text with outline
    ctx.strokeText(text, x, y);
    ctx.fillText(text, x, y);
  };

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className={className}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',  // No interaction
        zIndex: 1,  // Below bbox but above video
      }}
    />
  );
};
