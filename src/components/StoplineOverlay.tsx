'use client';

import React, { useRef, useEffect } from 'react';

export interface StoplineConfig {
  name: string;
  points: [number, number][];  // [[x1, y1], [x2, y2]]
  color?: string;
  thickness?: number;
}

interface StoplineOverlayProps {
  stoplines: StoplineConfig[];
  videoWidth: number;
  videoHeight: number;
  enabled?: boolean;
  className?: string;
}

export const StoplineOverlay: React.FC<StoplineOverlayProps> = ({
  stoplines,
  videoWidth,
  videoHeight,
  enabled = true,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!enabled) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, videoWidth, videoHeight);

    // Draw each stopline
    stoplines.forEach((stopline) => {
      if (stopline.points.length < 2) return;

      const [p1, p2] = stopline.points;
      const color = stopline.color || '#FF0000';
      const thickness = stopline.thickness || 3;

      // Draw line
      ctx.beginPath();
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
      ctx.strokeStyle = color;
      ctx.lineWidth = thickness;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Draw dashed pattern for visibility
      ctx.setLineDash([10, 5]);
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw label
      const midX = (p1[0] + p2[0]) / 2;
      const midY = (p1[1] + p2[1]) / 2;

      ctx.font = 'bold 12px Arial';
      ctx.fillStyle = '#FFFFFF';
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 3;

      // Draw text with outline
      ctx.strokeText(stopline.name, midX - 30, midY - 10);
      ctx.fillText(stopline.name, midX - 30, midY - 10);

      // Draw "STOP" text
      ctx.font = 'bold 14px Arial';
      ctx.fillStyle = color;
      ctx.strokeText('STOP', midX - 20, midY + 20);
      ctx.fillText('STOP', midX - 20, midY + 20);
    });
  }, [stoplines, videoWidth, videoHeight, enabled]);

  if (!enabled || stoplines.length === 0) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      width={videoWidth}
      height={videoHeight}
      className={className}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',
      }}
    />
  );
};

export default StoplineOverlay;
