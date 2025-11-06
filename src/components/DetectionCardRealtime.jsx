'use client';
import React, { useState, useRef, useEffect } from 'react';
import { Card, Badge, Button } from 'react-bootstrap';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace('http', 'ws'); // Convert HTTP to WebSocket URL

// Color mapping for vehicle classes
// Model classes: 0=bus, 1=car, 2=bike, 3=truck
const CLASS_COLORS = {
  bus: '#e67e22',        // 🟠 Orange
  car: '#3498db',        // 🔵 Blue
  bike: '#2ecc71',       // 🟢 Green
  truck: '#e74c3c',      // 🔴 Red
  default: '#95a5a6'     // Gray (fallback)
};

export function DetectionCardRealtime({ video }) {
  const router = useRouter();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const cardRef = useRef(null);
  const wsRef = useRef(null);
  
  const [isHovered, setIsHovered] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [videoLoading, setVideoLoading] = useState(true);
  const [detectionActive, setDetectionActive] = useState(false);
  const [detections, setDetections] = useState([]);
  const [fps, setFps] = useState(0);
  const [frameNumber, setFrameNumber] = useState(0);

  // IntersectionObserver để lazy load video
  useEffect(() => {
    if (!cardRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
          } else {
            setIsVisible(false);
            // Disconnect WebSocket khi card không còn visible
            if (wsRef.current) {
              wsRef.current.close();
              wsRef.current = null;
              setDetectionActive(false);
            }
          }
        });
      },
      {
        threshold: 0.1,
        rootMargin: '50px'
      }
    );

    observer.observe(cardRef.current);

    return () => {
      if (cardRef.current) {
        observer.unobserve(cardRef.current);
      }
    };
  }, []);

  // Get status badge color
  const getStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'secondary', text: 'Chờ xử lý' },
      processing: { bg: 'warning', text: 'Đang xử lý' },
      done: { bg: 'success', text: 'Hoàn thành' },
      completed: { bg: 'success', text: 'Hoàn thành' },
      failed: { bg: 'danger', text: 'Thất bại' }
    };
    return statusMap[status] || statusMap.pending;
  };

  // Handle video error
  const handleVideoError = (e) => {
    console.error(`❌ Video error for ${video.file_name || video.filename}:`, e);
    setVideoError(true);
    setVideoLoading(false);
  };

  // Handle video loaded
  const handleVideoLoaded = () => {
    setVideoLoading(false);
    setVideoError(false);
    
    // Sync canvas size with video
    if (canvasRef.current && videoRef.current) {
      canvasRef.current.width = videoRef.current.videoWidth;
      canvasRef.current.height = videoRef.current.videoHeight;
    }
  };

  // Get video URL
  const getVideoUrl = () => {
    const pathToTry = video.output_path || video.file_path;
    let finalUrl = null;
    
    if (pathToTry) {
      if (pathToTry.startsWith('/videos/')) {
        finalUrl = `${API_URL}${pathToTry}`;
      } else if (!pathToTry.startsWith('/')) {
        finalUrl = `${API_URL}/videos/${pathToTry}`;
      } else {
        finalUrl = `${API_URL}${pathToTry}`;
      }
    } else {
      const fileName = video.filename || video.file_name;
      if (fileName) {
        finalUrl = `${API_URL}/videos/${fileName}`;
      }
    }
    
    return finalUrl;
  };

  // Connect to WebSocket for realtime detection
  const connectWebSocket = () => {
    if (wsRef.current) {
      console.log('⚠️ WebSocket already connected');
      return;
    }

    const videoId = video.id || video.video_job_id;
    if (!videoId) {
      console.error('❌ No video ID available');
      return;
    }

    // WebSocket URL: ws://localhost:8000/api/realtime/ws/detect/{video_id}?fps=30
    // Optimized for >30 FPS with ONNX/TensorRT
    const wsUrl = `${WS_URL}/api/realtime/ws/detect/${videoId}?fps=30`;
    console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setDetectionActive(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'detection') {
            setDetections(data.objects || []);
            setFps(data.fps || 0);
            setFrameNumber(data.frame || 0);
            
            // Draw bounding boxes on canvas (optimized with requestAnimationFrame)
            requestAnimationFrame(() => {
              drawDetections(data.objects || [], data.video_size || [1920, 1080]);
            });
          } else if (data.type === 'error') {
            console.error('❌ WebSocket error:', data.message);
            setDetectionActive(false);
          }
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setDetectionActive(false);
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket closed');
        setDetectionActive(false);
        wsRef.current = null;
      };
    } catch (error) {
      console.error('❌ Failed to connect WebSocket:', error);
      setDetectionActive(false);
    }
  };

  // Disconnect WebSocket
  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setDetectionActive(false);
      setDetections([]);
      
      // Clear canvas
      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext('2d');
        ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
      }
    }
  };

  // Draw detections on canvas
  const drawDetections = (objects, videoSize) => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Get scale factors (canvas size vs video original size)
    const scaleX = canvas.width / videoSize[0];
    const scaleY = canvas.height / videoSize[1];

    // Draw each detection
    objects.forEach((obj) => {
      const [x1, y1, x2, y2] = obj.bbox;
      const label = obj.label || 'vehicle';
      const conf = obj.conf || 0;
      const trackId = obj.track_id || -1;

      // Scale bbox to canvas size
      const sx1 = x1 * scaleX;
      const sy1 = y1 * scaleY;
      const sx2 = x2 * scaleX;
      const sy2 = y2 * scaleY;
      const width = sx2 - sx1;
      const height = sy2 - sy1;

      // Get color for class
      const color = CLASS_COLORS[label.toLowerCase()] || CLASS_COLORS.default;

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(sx1, sy1, width, height);

      // Draw label background
      const labelText = `${label} ${(conf * 100).toFixed(0)}% [${trackId}]`;
      ctx.font = 'bold 14px Arial';
      const textMetrics = ctx.measureText(labelText);
      const textWidth = textMetrics.width;
      const textHeight = 20;

      ctx.fillStyle = color;
      ctx.fillRect(sx1, sy1 - textHeight - 4, textWidth + 8, textHeight + 4);

      // Draw label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(labelText, sx1 + 4, sy1 - 8);
    });
  };

  // Toggle detection on/off
  const toggleDetection = () => {
    if (detectionActive) {
      disconnectWebSocket();
    } else {
      connectWebSocket();
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const statusBadge = getStatusBadge(video.status);
  const videoUrl = getVideoUrl();

  const handleCardClick = () => {
    const videoId = video.id || video.video_job_id;
    const videoPath = video.file_path || video.output_path || video.filename || video.file_name;
    router.push(`/detection/live?video=${encodeURIComponent(videoPath)}&id=${videoId}`);
  };

  return (
    <Card
      ref={cardRef}
      className="h-100 shadow-sm border-0"
      style={{
        transition: 'all 0.3s ease',
        transform: isHovered ? 'scale(1.02)' : 'scale(1)',
        cursor: 'pointer'
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Video Preview with Canvas Overlay */}
      <div 
        style={{ 
          position: 'relative', 
          width: '100%', 
          paddingTop: '56.25%', 
          backgroundColor: '#000', 
          overflow: 'hidden' 
        }}
        onClick={handleCardClick}
      >
        {videoError || !videoUrl ? (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '14px',
              gap: '8px'
            }}
          >
            <div>❌ Video không khả dụng</div>
            <div style={{ fontSize: '12px', opacity: 0.7 }}>
              {video.file_name || video.filename || 'Unknown'}
            </div>
          </div>
        ) : (
          <>
            {videoLoading && (
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: '#000',
                  zIndex: 1
                }}
              >
                <div style={{ color: '#fff', fontSize: '12px' }}>Loading...</div>
              </div>
            )}
            {isVisible && (
              <>
                {/* Video Element */}
                <video
                  ref={videoRef}
                  src={videoUrl}
                  className="position-absolute top-0 start-0 w-100 h-100"
                  style={{ 
                    objectFit: 'cover',
                    display: videoLoading ? 'none' : 'block'
                  }}
                  autoPlay
                  muted
                  loop
                  playsInline
                  preload="auto"
                  crossOrigin="anonymous"
                  onError={handleVideoError}
                  onLoadedData={handleVideoLoaded}
                  onLoadStart={() => setVideoLoading(true)}
                  onCanPlay={() => setVideoLoading(false)}
                />
                
                {/* Canvas Overlay for BBox */}
                <canvas
                  ref={canvasRef}
                  className="position-absolute top-0 start-0 w-100 h-100"
                  style={{
                    objectFit: 'cover',
                    pointerEvents: 'none',
                    zIndex: 2
                  }}
                />
              </>
            )}
          </>
        )}
        
        {/* Status Badge Overlay */}
        <div className="position-absolute top-0 end-0 m-2" style={{ zIndex: 3 }}>
          <Badge bg={statusBadge.bg} className="px-2 py-1">
            {statusBadge.text}
          </Badge>
        </div>

        {/* Detection Active Badge */}
        {detectionActive && (
          <div className="position-absolute top-0 start-0 m-2" style={{ zIndex: 3 }}>
            <Badge bg="danger" className="px-2 py-1">
              🔴 LIVE {fps.toFixed(0)} FPS
            </Badge>
          </div>
        )}

        {/* Frame Counter */}
        {detectionActive && frameNumber > 0 && (
          <div className="position-absolute bottom-0 start-0 m-2" style={{ zIndex: 3 }}>
            <Badge bg="dark" className="px-2 py-1" style={{ opacity: 0.8 }}>
              Frame {frameNumber} | {detections.length} objects
            </Badge>
          </div>
        )}
      </div>

      {/* Card Body */}
      <Card.Body className="d-flex flex-column">
        <div className="mb-2">
          <h6 className="mb-1 fw-semibold" style={{ fontSize: '16px', lineHeight: '1.3' }}>
            {video.filename || video.file_name || 'Video không tên'}
          </h6>
          <p className="text-muted small mb-0" style={{ fontSize: '12px' }}>
            ID: {video.id || video.video_job_id} • {video.created_at || video.upload_time ? new Date(video.created_at || video.upload_time).toLocaleDateString('vi-VN') : 'N/A'}
          </p>
        </div>

        {/* Stats Row */}
        <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top">
          <div className="d-flex gap-2 flex-wrap">
            {video.fps && (
              <Badge bg="info" className="px-2 py-1" style={{ fontSize: '11px' }}>
                ⚡ {video.fps.toFixed(1)} FPS
              </Badge>
            )}
            {video.duration && (
              <Badge bg="secondary" className="px-2 py-1" style={{ fontSize: '11px' }}>
                ⏱️ {video.duration.toFixed(1)}s
              </Badge>
            )}
            {video.violations_count !== undefined && (
              <Badge bg={video.violations_count > 0 ? 'danger' : 'success'} className="px-2 py-1" style={{ fontSize: '11px' }}>
                🚨 {video.violations_count} vi phạm
              </Badge>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="d-flex gap-2 mt-2">
          <Button
            variant={detectionActive ? 'danger' : 'success'}
            size="sm"
            className="rounded-pill flex-grow-1"
            onClick={(e) => {
              e.stopPropagation();
              toggleDetection();
            }}
          >
            {detectionActive ? '⏹️ Stop Detection' : '▶️ Start Detection'}
          </Button>
          <Button
            variant="primary"
            size="sm"
            className="rounded-pill"
            onClick={(e) => {
              e.stopPropagation();
              handleCardClick();
            }}
          >
            📊 Chi Tiết
          </Button>
        </div>
      </Card.Body>
    </Card>
  );
}

