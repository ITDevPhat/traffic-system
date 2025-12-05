'use client';

import React, { useRef, useEffect, useState } from 'react';
import { Container, Row, Col, Card, Button, Alert, Badge } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';

// Simple ROI interface
interface Point {
  x: number;
  y: number;
}

interface TrafficLightROI {
  id: string;
  label: string;
  points: Point[];
  color: { stroke: string; fill: string };
}

const COLORS = [
  { stroke: '#ef4444', fill: 'rgba(239, 68, 68, 0.2)' },
  { stroke: '#f59e0b', fill: 'rgba(245, 158, 11, 0.2)' },
  { stroke: '#10b981', fill: 'rgba(16, 185, 129, 0.2)' },
  { stroke: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.2)' },
];

export default function TrafficLiveDemoPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [videoSrc, setVideoSrc] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 1280, height: 720 });

  // ROI drawing state
  const [rois, setRois] = useState<TrafficLightROI[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [draftPoints, setDraftPoints] = useState<Point[]>([]);
  const [mousePos, setMousePos] = useState<Point | null>(null);
  const [nextIndex, setNextIndex] = useState(1);

  // Cropped images
  const [croppedImages, setCroppedImages] = useState<Map<string, string>>(new Map());

  // Handle video upload
  const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setVideoSrc(url);
    setVideoLoaded(false);
  };

  // Handle video loaded
  const handleVideoLoadedMetadata = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const width = video.videoWidth;
    const height = video.videoHeight;
    setDimensions({ width, height });
    setVideoLoaded(true);
    if (canvasRef.current) {
      canvasRef.current.width = width;
      canvasRef.current.height = height;
    }
  };

  // Toggle play/pause
  const togglePlayPause = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  // Draw video to canvas
  useEffect(() => {
    if (!isPlaying || !videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    const drawFrame = () => {
      if (video.paused || video.ended) {
        setIsPlaying(false);
        return;
      }
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      animationId = requestAnimationFrame(drawFrame);
    };
    animationId = requestAnimationFrame(drawFrame);
    return () => cancelAnimationFrame(animationId);
  }, [isPlaying]);

  // Extract ROI images
  useEffect(() => {
    if (!isPlaying || !videoRef.current || !canvasRef.current || rois.length === 0) return;

    const video = videoRef.current;
    let animationId: number;

    const extractROIs = () => {
      const newCroppedImages = new Map<string, string>();
      rois.forEach((roi) => {
        const xs = roi.points.map((p) => p.x);
        const ys = roi.points.map((p) => p.y);
        const minX = Math.min(...xs) * dimensions.width;
        const minY = Math.min(...ys) * dimensions.height;
        const maxX = Math.max(...xs) * dimensions.width;
        const maxY = Math.max(...ys) * dimensions.height;
        const cropWidth = maxX - minX;
        const cropHeight = maxY - minY;

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = cropWidth;
        tempCanvas.height = cropHeight;
        const tempCtx = tempCanvas.getContext('2d');
        if (tempCtx) {
          tempCtx.drawImage(video, minX, minY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight);
          newCroppedImages.set(roi.id, tempCanvas.toDataURL('image/jpeg', 0.8));
        }
      });
      setCroppedImages(newCroppedImages);
      animationId = requestAnimationFrame(extractROIs);
    };

    animationId = requestAnimationFrame(extractROIs);
    return () => cancelAnimationFrame(animationId);
  }, [isPlaying, rois, dimensions]);

  // Normalize point
  const normalizePoint = (clientX: number, clientY: number): Point | null => {
    if (!svgRef.current) return null;
    const rect = svgRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
    return { x, y };
  };

  // Check if near start point
  const isNearStart = (point: Point): boolean => {
    if (draftPoints.length < 3) return false;
    const start = draftPoints[0];
    const dx = Math.abs(point.x - start.x) * dimensions.width;
    const dy = Math.abs(point.y - start.y) * dimensions.height;
    return Math.sqrt(dx * dx + dy * dy) < 15;
  };

  // Handle click
  const handleClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDrawing) return;
    e.preventDefault();
    const point = normalizePoint(e.clientX, e.clientY);
    if (!point) return;

    if (isNearStart(point) && draftPoints.length >= 3) {
      const newROI: TrafficLightROI = {
        id: `roi-${Date.now()}`,
        label: `Đèn ${nextIndex}`,
        points: [...draftPoints],
        color: COLORS[(nextIndex - 1) % COLORS.length],
      };
      setRois([...rois, newROI]);
      setNextIndex(nextIndex + 1);
      setIsDrawing(false);
      setDraftPoints([]);
      setMousePos(null);
    } else {
      setDraftPoints([...draftPoints, point]);
    }
  };

  // Handle mouse move
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDrawing) return;
    const point = normalizePoint(e.clientX, e.clientY);
    if (point) setMousePos(point);
  };

  // Points to SVG string
  const pointsToSvg = (points: Point[]): string => {
    return points.map((p) => `${p.x * dimensions.width},${p.y * dimensions.height}`).join(' ');
  };

  return (
    <>
      <PageTitle title="Traffic Live Demo" subName="Detection" />

      <Container fluid>
        <Row>
          <Col xs={12}>
            <Card>
              <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h4 className="mb-0">🚦 Demo Vẽ ROI Đèn Giao Thông</h4>
                  <div className="d-flex gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="video/*"
                      onChange={handleVideoUpload}
                      style={{ display: 'none' }}
                    />
                    <Button variant="outline-primary" size="sm" onClick={() => fileInputRef.current?.click()}>
                      📁 Chọn Video
                    </Button>
                    {videoLoaded && (
                      <Button variant={isPlaying ? 'danger' : 'success'} size="sm" onClick={togglePlayPause}>
                        {isPlaying ? '⏸️ Pause' : '▶️ Play'}
                      </Button>
                    )}
                  </div>
                </div>

                {!videoSrc && (
                  <Alert variant="info">
                    <i className="mdi mdi-information me-2"></i>
                    Chọn video để bắt đầu
                  </Alert>
                )}

                {videoSrc && (
                  <div className="position-relative">
                    <video
                      ref={videoRef}
                      src={videoSrc}
                      onLoadedMetadata={handleVideoLoadedMetadata}
                      style={{ display: 'none' }}
                      muted
                      loop
                    />
                    <div className="position-relative" style={{ width: '100%', maxWidth: '100%' }}>
                      <canvas
                        ref={canvasRef}
                        style={{
                          width: '100%',
                          height: 'auto',
                          backgroundColor: '#000',
                          borderRadius: '8px',
                        }}
                      />
                      {/* SVG Overlay */}
                      <svg
                        ref={svgRef}
                        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
                        preserveAspectRatio="none"
                        onClick={handleClick}
                        onMouseMove={handleMouseMove}
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: '100%',
                          cursor: isDrawing ? 'crosshair' : 'default',
                          pointerEvents: isDrawing ? 'auto' : 'none',
                          zIndex: 10,
                        }}
                      >
                        {/* Existing ROIs */}
                        {rois.map((roi) => (
                          <g key={roi.id}>
                            <polygon
                              points={pointsToSvg(roi.points)}
                              fill={roi.color.fill}
                              stroke={roi.color.stroke}
                              strokeWidth={3}
                            />
                            <text
                              x={roi.points[0].x * dimensions.width}
                              y={roi.points[0].y * dimensions.height - 10}
                              fill="#fff"
                              fontSize={14}
                              fontWeight="bold"
                              style={{ paintOrder: 'stroke', stroke: '#000', strokeWidth: 3 }}
                            >
                              {roi.label}
                            </text>
                          </g>
                        ))}
                        {/* Draft polygon */}
                        {isDrawing && draftPoints.length > 0 && (
                          <>
                            <polyline
                              points={pointsToSvg(draftPoints)}
                              fill="none"
                              stroke="#f59e0b"
                              strokeWidth={2}
                              strokeDasharray="6 4"
                            />
                            {mousePos && (
                              <line
                                x1={draftPoints[draftPoints.length - 1].x * dimensions.width}
                                y1={draftPoints[draftPoints.length - 1].y * dimensions.height}
                                x2={mousePos.x * dimensions.width}
                                y2={mousePos.y * dimensions.height}
                                stroke="#f59e0b"
                                strokeWidth={2}
                                strokeDasharray="6 4"
                              />
                            )}
                            {draftPoints.map((pt, idx) => (
                              <circle
                                key={idx}
                                cx={pt.x * dimensions.width}
                                cy={pt.y * dimensions.height}
                                r={6}
                                fill="#f59e0b"
                                stroke="#fff"
                                strokeWidth={2}
                              />
                            ))}
                            {mousePos && isNearStart(mousePos) && (
                              <circle
                                cx={draftPoints[0].x * dimensions.width}
                                cy={draftPoints[0].y * dimensions.height}
                                r={15}
                                fill="none"
                                stroke="#10b981"
                                strokeWidth={3}
                                strokeDasharray="4 2"
                              />
                            )}
                          </>
                        )}
                      </svg>
                    </div>
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Controls */}
        {videoLoaded && (
          <Row className="mt-3">
            <Col lg={4}>
              <Card>
                <Card.Body>
                  <h5 className="mb-3">
                    🎨 Điều Khiển <Badge bg="info">{rois.length}</Badge>
                  </h5>
                  <div className="d-flex flex-column gap-2">
                    {!isDrawing ? (
                      <>
                        <Button variant="primary" onClick={() => setIsDrawing(true)}>
                          ✏️ Vẽ Vùng ROI
                        </Button>
                        {rois.length > 0 && (
                          <Button
                            variant="outline-danger"
                            onClick={() => {
                              setRois([]);
                              setNextIndex(1);
                              setCroppedImages(new Map());
                            }}
                          >
                            🗑️ Xóa Tất Cả
                          </Button>
                        )}
                      </>
                    ) : (
                      <>
                        <Alert variant="success" className="mb-0 py-2">
                          Click để vẽ điểm. Click vào điểm đầu để hoàn thành.
                        </Alert>
                        <Button
                          variant="outline-secondary"
                          onClick={() => {
                            setIsDrawing(false);
                            setDraftPoints([]);
                            setMousePos(null);
                          }}
                        >
                          ✕ Hủy
                        </Button>
                      </>
                    )}
                  </div>

                  {rois.length > 0 && (
                    <div className="mt-3">
                      <small className="text-muted">Danh sách vùng:</small>
                      {rois.map((roi) => (
                        <div
                          key={roi.id}
                          className="d-flex align-items-center gap-2 mt-2 p-2 border rounded"
                        >
                          <div
                            style={{
                              width: '16px',
                              height: '16px',
                              backgroundColor: roi.color.stroke,
                              borderRadius: '3px',
                            }}
                          />
                          <span className="fw-medium">{roi.label}</span>
                          <Button
                            variant="outline-danger"
                            size="sm"
                            className="ms-auto"
                            onClick={() => setRois(rois.filter((r) => r.id !== roi.id))}
                          >
                            ✕
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>

            {/* Cropped ROI Views */}
            <Col lg={8}>
              <Card>
                <Card.Body>
                  <h5 className="mb-3">🎥 Vùng Đèn Realtime</h5>
                  {rois.length === 0 ? (
                    <div className="text-center text-muted py-5">
                      <p>Chưa có vùng ROI</p>
                      <small>Nhấn "Vẽ Vùng ROI" để bắt đầu</small>
                    </div>
                  ) : (
                    <Row className="g-3">
                      {rois.map((roi) => {
                        const img = croppedImages.get(roi.id);
                        return (
                          <Col key={roi.id} md={6} lg={4}>
                            <Card className="h-100">
                              <Card.Header
                                className="py-2"
                                style={{ backgroundColor: roi.color.stroke, color: '#fff' }}
                              >
                                <strong>{roi.label}</strong>
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
                                  }}
                                >
                                  {img ? (
                                    <img
                                      src={img}
                                      alt={roi.label}
                                      style={{ maxWidth: '100%', maxHeight: '200px', objectFit: 'contain' }}
                                    />
                                  ) : (
                                    <small className="text-muted">Đang chờ...</small>
                                  )}
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
        )}
      </Container>
    </>
  );
}
