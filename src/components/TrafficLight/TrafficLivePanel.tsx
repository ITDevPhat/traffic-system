'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card, Row, Col } from 'react-bootstrap';
import { TrafficLiveROI, TrafficLightROI } from './TrafficLiveROI';

interface TrafficLivePanelProps {
  videoRef: React.RefObject<HTMLVideoElement>;
  canvasRef: React.RefObject<HTMLCanvasElement>;
  videoWidth: number;
  videoHeight: number;
  isPlaying: boolean;
  className?: string;
}

export const TrafficLivePanel: React.FC<TrafficLivePanelProps> = ({
  videoRef,
  canvasRef,
  videoWidth,
  videoHeight,
  isPlaying,
  className = '',
}) => {
  const [rois, setRois] = useState<TrafficLightROI[]>([]);
  const [croppedImages, setCroppedImages] = useState<Map<string, string>>(new Map());
  const animationFrameRef = useRef<number>();

  // Extract ROI regions from video and update realtime
  const extractROIImages = () => {
    if (!videoRef.current || !canvasRef.current || rois.length === 0) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const newCroppedImages = new Map<string, string>();

    rois.forEach((roi) => {
      // Calculate bounding box from polygon points
      const xs = roi.points.map((p) => p.x);
      const ys = roi.points.map((p) => p.y);
      const minX = Math.min(...xs);
      const minY = Math.min(...ys);
      const maxX = Math.max(...xs);
      const maxY = Math.max(...ys);

      const cropX = minX * videoWidth;
      const cropY = minY * videoHeight;
      const cropWidth = (maxX - minX) * videoWidth;
      const cropHeight = (maxY - minY) * videoHeight;

      // Create temporary canvas for cropping
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = cropWidth;
      tempCanvas.height = cropHeight;
      const tempCtx = tempCanvas.getContext('2d');

      if (tempCtx) {
        // Draw cropped region
        tempCtx.drawImage(
          video,
          cropX,
          cropY,
          cropWidth,
          cropHeight,
          0,
          0,
          cropWidth,
          cropHeight
        );

        // Convert to data URL
        const dataUrl = tempCanvas.toDataURL('image/jpeg', 0.8);
        newCroppedImages.set(roi.id, dataUrl);
      }
    });

    setCroppedImages(newCroppedImages);
  };

  // Update ROI images continuously when playing
  useEffect(() => {
    if (!isPlaying || rois.length === 0) {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    const updateLoop = () => {
      extractROIImages();
      animationFrameRef.current = requestAnimationFrame(updateLoop);
    };

    animationFrameRef.current = requestAnimationFrame(updateLoop);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, rois, videoWidth, videoHeight]);

  // Handle ROI updates
  const handleROIUpdate = (updatedRois: TrafficLightROI[]) => {
    setRois(updatedRois);
    // Clear cropped images when ROIs change
    if (updatedRois.length === 0) {
      setCroppedImages(new Map());
    }
  };

  return (
    <>
      <Row>
        {/* Left: ROI Drawing Controls */}
        <Col lg={4}>
          <TrafficLiveROI
            videoWidth={videoWidth}
            videoHeight={videoHeight}
            onROIUpdate={handleROIUpdate}
            canvasRef={canvasRef}
          />
        </Col>

        {/* Right: Cropped ROI Previews */}
        <Col lg={8}>
          <Card>
            <Card.Body>
              <h5 className="mb-3">🎥 Vùng Đèn Realtime</h5>
              {rois.length === 0 ? (
                <div className="text-center text-muted py-5">
                  <p>Chưa có vùng ROI nào được vẽ</p>
                  <small>Nhấn "Vẽ Vùng ROI" để bắt đầu</small>
                </div>
              ) : (
                <Row className="g-3">
                  {rois.map((roi) => {
                    const croppedImage = croppedImages.get(roi.id);
                    return (
                      <Col key={roi.id} md={6} lg={4}>
                        <Card className="h-100">
                          <Card.Header
                            className="py-2"
                            style={{
                              backgroundColor: roi.color.stroke,
                              color: '#ffffff',
                              fontWeight: 'bold',
                            }}
                          >
                            {roi.label}
                          </Card.Header>
                          <Card.Body className="p-2">
                            <div
                              style={{
                                width: '100%',
                                minHeight: '120px',
                                backgroundColor: '#f3f4f6',
                                borderRadius: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                overflow: 'hidden',
                              }}
                            >
                              {croppedImage ? (
                                <img
                                  src={croppedImage}
                                  alt={roi.label}
                                  style={{
                                    maxWidth: '100%',
                                    maxHeight: '200px',
                                    objectFit: 'contain',
                                  }}
                                />
                              ) : (
                                <div className="text-muted text-center p-3">
                                  <small>Đang chờ video...</small>
                                </div>
                              )}
                            </div>
                            <div className="mt-2 text-center">
                              <span
                                className="badge"
                                style={{
                                  backgroundColor:
                                    roi.signalState === 'RED'
                                      ? '#ef4444'
                                      : roi.signalState === 'YELLOW'
                                      ? '#f59e0b'
                                      : roi.signalState === 'GREEN'
                                      ? '#10b981'
                                      : '#6b7280',
                                }}
                              >
                                {roi.signalState || 'UNKNOWN'}
                              </span>
                            </div>
                          </Card.Body>
                        </Card>
                      </Col>
                    );
                  })}
                </Row>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );
};
