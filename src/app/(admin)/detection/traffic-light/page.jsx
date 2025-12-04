'use client';
import React, { useRef, useEffect, useState, Suspense, useMemo, useCallback } from 'react';
import { Button, Form, Row, Col, Card, Badge } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { useSearchParams } from 'next/navigation';
import PageTitle from '@/components/PageTitle';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const ROI_COLORS = [
  { stroke: '#34d399', fill: 'rgba(52, 211, 153, 0.2)' },
  { stroke: '#60a5fa', fill: 'rgba(96, 165, 250, 0.2)' },
  { stroke: '#fbbf24', fill: 'rgba(251, 191, 36, 0.2)' },
  { stroke: '#f472b6', fill: 'rgba(244, 114, 182, 0.2)' },
  { stroke: '#f87171', fill: 'rgba(248, 113, 113, 0.2)' },
  { stroke: '#a855f7', fill: 'rgba(168, 85, 247, 0.2)' },
];

const RoiOverlay = React.forwardRef(({ frameDimensions, rois, draftPoints, isDrawing, onPointerDown, mousePos, onMouseMove }, ref) => {
  const width = frameDimensions?.width || 1;
  const height = frameDimensions?.height || 1;
  const hasFrame = width > 0 && height > 0;

  const toSvgPoints = (points = []) => {
    if (!hasFrame) return '';
    return points
      .map((pt) => {
        const nx = Math.min(Math.max(pt?.x ?? 0, 0), 1);
        const ny = Math.min(Math.max(pt?.y ?? 0, 0), 1);
        return `${nx * width},${ny * height}`;
      })
      .join(' ');
  };

  // Check if mouse is near the start point for snapping
  const getSnapDistance = (mouseX, mouseY, startPoint) => {
    if (!startPoint || !hasFrame) return Infinity;
    const startX = startPoint.x * width;
    const startY = startPoint.y * height;
    return Math.sqrt((mouseX - startX) ** 2 + (mouseY - startY) ** 2);
  };

  const shouldShowSnapCircle = () => {
    if (!isDrawing || draftPoints.length < 3 || !mousePos || !hasFrame) return false;
    const snapDistance = getSnapDistance(mousePos.x, mousePos.y, draftPoints[0]);
    return snapDistance <= 15; // 15px snap radius
  };

  const renderLabel = (roi) => {
    if (!roi?.points || roi.points.length === 0 || !hasFrame) return null;
    const sum = roi.points.reduce(
      (acc, pt) => {
        const nx = Math.min(Math.max(pt?.x ?? 0, 0), 1);
        const ny = Math.min(Math.max(pt?.y ?? 0, 0), 1);
        return { x: acc.x + nx, y: acc.y + ny };
      },
      { x: 0, y: 0 }
    );
    const cx = (sum.x / roi.points.length) * width;
    const cy = (sum.y / roi.points.length) * height;

    return (
      <text
        key={`${roi.id}-label`}
        x={cx}
        y={cy}
        fill="#111827"
        fontSize={14}
        fontWeight={600}
        textAnchor="middle"
        alignmentBaseline="middle"
        style={{ paintOrder: 'stroke', stroke: 'rgba(255,255,255,0.85)', strokeWidth: 3 }}
      >
        {roi.label || 'ROI'}
      </text>
    );
  };

  return (
    <svg
      ref={ref}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      onPointerDown={isDrawing ? onPointerDown : undefined}
      onMouseMove={isDrawing ? onMouseMove : undefined}
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 6,
        pointerEvents: isDrawing ? 'auto' : 'none',
        cursor: isDrawing ? 'crosshair' : 'default'
      }}
    >
      {rois.map((roi) => (
        <React.Fragment key={roi.id}>
          <polygon
            points={toSvgPoints(roi.points)}
            fill={roi.color?.fill || 'rgba(59, 130, 246, 0.2)'}
            stroke={roi.color?.stroke || '#2563eb'}
            strokeWidth={2}
            strokeLinejoin="round"
          />
          {renderLabel(roi)}
        </React.Fragment>
      ))}
      {draftPoints.length > 0 && (
        <>
          <polyline
            points={toSvgPoints(draftPoints)}
            fill="none"
            stroke="#f97316"
            strokeWidth={2}
            strokeDasharray="6 4"
          />
          {draftPoints.map((pt, idx) => {
            const nx = Math.min(Math.max(pt?.x ?? 0, 0), 1);
            const ny = Math.min(Math.max(pt?.y ?? 0, 0), 1);
            return (
              <circle
                key={`draft-${idx}`}
                cx={nx * width}
                cy={ny * height}
                r={5}
                fill="#f97316"
                stroke="#ffffff"
                strokeWidth={2}
              />
            );
          })}
          {/* Snapping circle at start point when mouse is near */}
          {shouldShowSnapCircle() && draftPoints[0] && (
            <circle
              cx={draftPoints[0].x * width}
              cy={draftPoints[0].y * height}
              r={12}
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
  );
});

RoiOverlay.displayName = 'RoiOverlay';

function DetectionPageBinaryContent() {
  const searchParams = useSearchParams();
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);
  const isMountedRef = useRef(true);
  const overlayRef = useRef(null);
  const lastRoiSignatureRef = useRef('');
  
  // Safe toast wrapper - only show toast if component is mounted
  // Use try-catch to prevent errors if toast is unavailable
  const safeToast = useMemo(() => ({
    success: (msg, opts) => {
      if (!isMountedRef.current) return;
      try {
        if (toast && typeof toast.success === 'function') {
          toast.success(msg, opts);
        }
      } catch (e) {
        console.warn('Toast error:', e);
      }
    },
    error: (msg, opts) => {
      if (!isMountedRef.current) return;
      try {
        if (toast && typeof toast.error === 'function') {
          toast.error(msg, opts);
        }
      } catch (e) {
        console.warn('Toast error:', e);
      }
    },
    info: (msg, opts) => {
      if (!isMountedRef.current) return;
      try {
        if (toast && typeof toast.info === 'function') {
          toast.info(msg, opts);
        }
      } catch (e) {
        console.warn('Toast error:', e);
      }
    },
    warning: (msg, opts) => {
      if (!isMountedRef.current) return;
      try {
        if (toast && typeof toast.warning === 'function') {
          toast.warning(msg, opts);
        }
      } catch (e) {
        console.warn('Toast error:', e);
      }
    },
    dismiss: () => {
      // BỎ ID - chỉ dismiss all để tránh lỗi
      if (!isMountedRef.current) return;
      try {
        if (toast && typeof toast.dismiss === 'function') {
          toast.dismiss(); // Dismiss all toasts
        }
      } catch (e) {
        // Silently ignore - toast might be unmounted
      }
    },
  }), []);
  
  // Rendering pipeline refs
  const lastBufferRef = useRef(null);
  const decodingRef = useRef(false);
  const nextBitmapRef = useRef(null);
  const displayBitmapRef = useRef(null);
  const rafIdRef = useRef(0);
  // Throttled UI refs
  const fpsRef = useRef(0);
  const frameIdxRef = useRef(0);

  const [connected, setConnected] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [fps, setFps] = useState(0);
  const [frameIdx, setFrameIdx] = useState(0);
  const [source, setSource] = useState(''); // video file only
  const [sourceType, setSourceType] = useState('upload'); // only 'upload'
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [modelLoaded, setModelLoaded] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isUploadingVideo, setIsUploadingVideo] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('models/vehicle/11s/yolo_vehicle_11s.onnx'); // Default: 11s ONNX
  const [autoStart, setAutoStart] = useState(false); // Flag to auto-start detection
  const [warmupProgress, setWarmupProgress] = useState(0); // Warmup progress 0-100
  const [isWarmingUp, setIsWarmingUp] = useState(false); // Warmup phase
  
  // Model version management
  const [modelVersions, setModelVersions] = useState({});
  const [currentVersion, setCurrentVersion] = useState('11s');
  const [currentFormat, setCurrentFormat] = useState('onnx');
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  
  // Optimized settings defaults
  const [settings, setSettings] = useState({
    conf: 0.5,           // Increased from 0.35
    target_fps: 45,
    jpeg_quality: 60,    // Increased from 55
    inference_size: 640, // Optimized for RTX 3050 performance
    encode_width: 960,
    veh_detect_hz: 25,
    force_gpu: true
  });
  
  const [frameDimensions, setFrameDimensions] = useState({ width: 1280, height: 720 });
  const [expectBinary, setExpectBinary] = useState(false);
  
  // Module toggles
  const [modules, setModules] = useState({
    yolo: true,
    tracking: true,
    bboxDrawing: true,
    roi: true,
    roiDrawing: true
  });

  const [roiPolygons, setRoiPolygons] = useState([]);
  const [isDrawingRoi, setIsDrawingRoi] = useState(false);
  const [draftRoiPoints, setDraftRoiPoints] = useState([]);
  const [draftRoiName, setDraftRoiName] = useState('');
  const [activeRoiId, setActiveRoiId] = useState(null);
  const [mousePos, setMousePos] = useState(null);
  const [showDebugOverlay, setShowDebugOverlay] = useState(false);

  // Keyboard event handler for debug overlay (D key)
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'D' || event.key === 'd') {
        setShowDebugOverlay(prev => !prev);
        console.log('🔧 Debug overlay toggled:', !showDebugOverlay);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showDebugOverlay]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      // Dismiss all toasts when component unmounts (with safe check)
      try {
        if (typeof toast !== 'undefined' && toast && typeof toast.dismiss === 'function') {
          toast.dismiss();
        }
      } catch (error) {
        console.warn('⚠️ Toast cleanup error (safe to ignore):', error);
      }
    };
  }, []);

  // Load model versions on mount
  useEffect(() => {
    fetchModelVersions();
  }, []);

  // Auto-load video from query params
  useEffect(() => {
    const videoParam = searchParams?.get('video');
    const videoId = searchParams?.get('id');
    
    if (videoParam && !videoLoaded) {
      console.log(`🎬 Auto-loading video from URL: ${videoParam} (ID: ${videoId})`);
      
      // Decode video path from URL
      const videoPath = decodeURIComponent(videoParam);
      
      // Set video source - use the path directly
      // If it's a full path like "/videos/video.mp4", use it directly
      // If it's just filename, prepend /videos/
      let finalPath = videoPath;
      if (videoPath && !videoPath.startsWith('/')) {
        finalPath = `/videos/${videoPath}`;
      }
      
      setSource(finalPath);
      setVideoLoaded(true);
      setAutoStart(true); // Flag to auto-start after models load and warmup
      
      safeToast.info(`📹 Video loaded: ${videoPath.split('/').pop()}`, { autoClose: 2000 });
    }
  }, [searchParams, videoLoaded, safeToast]);

  const loadModels = useCallback(async () => {
    // Skip if already loaded
    if (modelLoaded || isLoadingModels) return;

    setIsLoadingModels(true);
    
    // Longer timeout for model loading (GPU initialization can take time)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout for GPU init
    
    const videoParam = searchParams?.get('video');
    if (!videoParam) {
      safeToast.info('Loading models (GPU)...', { autoClose: 2000 });
    }
    
    try {
      const res = await fetch(`${API_URL}/api/detection/models/load`, { 
          method: 'POST',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        // Try to parse JSON error response
        let errorMessage = 'Failed to load models';
        try {
          const errorData = await res.json();
          errorMessage = errorData?.detail?.error || errorData?.error || errorData?.detail || errorMessage;
        } catch {
          // If not JSON, try text
          try {
            const text = await res.text();
            errorMessage = text || errorMessage;
          } catch {
            errorMessage = `HTTP ${res.status}: ${res.statusText}`;
          }
        }
        throw new Error(errorMessage);
      }
      
      const data = await res.json();
      if ((data?.device || '').toLowerCase() !== 'cuda') {
        safeToast.error('GPU required. CUDA not detected.');
        return;
      }
      setModelLoaded(true);
      
      const videoParam = searchParams?.get('video');
      if (videoParam) {
        console.log('✅ Models loaded - ready for auto-start');
        // Don't show toast if auto-starting (to avoid spam)
      } else {
        safeToast.success('Models ready on GPU (CUDA)', { autoClose: 2000 });
      }
    } catch (e) {
      console.error('Model loading error:', e);
      clearTimeout(timeoutId);
      
      if (e.name === 'AbortError') {
        safeToast.error('Model loading timeout! Check backend.');
      } else {
        const errorMsg = e.message || 'Unknown error';
        safeToast.error(`Cannot load models: ${errorMsg}`);
      }
    } finally {
      setIsLoadingModels(false);
    }
  }, [modelLoaded, isLoadingModels, searchParams, safeToast]);

  // Auto-load models on mount (non-blocking) - ưu tiên nếu có video param
  useEffect(() => {
    const videoParam = searchParams?.get('video');

    // If video param exists, load models immediately (no delay)
    // Otherwise, small delay for better UX
    const delay = videoParam ? 100 : 500;

    if (!modelLoaded && !isLoadingModels) {
      const timer = setTimeout(() => {
        if (videoParam) {
          console.log('🚀 Auto-loading models (video detected from URL)...');
          safeToast.info('Loading AI models...', { autoClose: 3000 });
        }
        loadModels();
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [searchParams, modelLoaded, isLoadingModels, loadModels, safeToast]);

  const scheduleDecode = useCallback(() => {
    if (decodingRef.current) return;
    const buf = lastBufferRef.current;
    if (!buf) return;
    // claim buffer
    lastBufferRef.current = null;
    decodingRef.current = true;
    const blob = new Blob([buf], { type: 'image/jpeg' });
    createImageBitmap(blob)
      .then((bitmap) => {
        // Replace any pending next bitmap
        if (nextBitmapRef.current) {
          try { nextBitmapRef.current.close(); } catch {}
        }
        nextBitmapRef.current = bitmap;
      })
      .catch(() => {})
      .finally(() => {
        decodingRef.current = false;
        // If a newer buffer arrived while decoding, process it now
        if (lastBufferRef.current) scheduleDecode();
      });
  }, []);

  const connectWebSocket = useCallback((src) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Build WebSocket URL with all optimization parameters
    const params = new URLSearchParams();
    params.append('source', src || '0');
    params.append('conf', settings.conf);
    params.append('fps', settings.target_fps);
    params.append('imgsz', settings.inference_size);
    params.append('quality', settings.jpeg_quality);
    params.append('encode_width', settings.encode_width);
    params.append('model_path', selectedModel || 'models/yolov8n.pt');
    params.append('veh_detect_hz', settings.veh_detect_hz);
    params.append('enable_yolo', modules.yolo);
    params.append('enable_tracking', modules.tracking);
    params.append('enable_bbox_drawing', modules.bboxDrawing);
    params.append('enable_roi', modules.roi);
    params.append('enable_roi_drawing', modules.roiDrawing);
    params.append('force_gpu', settings.force_gpu);

    const wsUrl = `${API_URL.replace('http', 'ws')}/api/detection/realtime?${params.toString()}`;
    console.log('?? Connecting to:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';  // Critical for binary frames
    
    ws.onopen = () => {
      if (!isMountedRef.current) return;
      console.log('? Binary WebSocket connected!');
      lastRoiSignatureRef.current = '';
      setConnected(true);
      setExpectBinary(false);
      safeToast.success('Connected! Waiting for frames...');
    };
    
    ws.onclose = () => {
      if (!isMountedRef.current) return;
      console.log('? WebSocket closed');
      setConnected(false);
      setDetecting(false);
      lastRoiSignatureRef.current = '';
      safeToast.info('WebSocket disconnected');
    };
    
    ws.onerror = (error) => {
      if (!isMountedRef.current) return;
      console.error('? WebSocket error:', error);
      setConnected(false);
      setDetecting(false);
      lastRoiSignatureRef.current = '';
      safeToast.error('WebSocket error! Check backend.');
    };

    // Handle messages: text (header) and binary (JPEG) alternate
    ws.onmessage = async (event) => {
      // Text message (JSON header)
      if (typeof event.data === 'string') {
        try {
          const pkt = JSON.parse(event.data);
          
        if (pkt.type === 'info') {
            // Set canvas size once
            const c = canvasRef.current;
            if (c) {
              const newWidth = pkt.frame_width || 1280;
              const newHeight = pkt.frame_height || 720;
              c.width = newWidth;
              c.height = newHeight;
              setFrameDimensions({ width: newWidth, height: newHeight });
              const ctx = c.getContext('2d');
              if (ctx && ctx.imageSmoothingEnabled) ctx.imageSmoothingEnabled = false;
                console.log(`?? Canvas: ${newWidth}x${newHeight}`);
                console.log('?? Info:', pkt);
                if (pkt.rois && typeof pkt.rois === 'object') {
                  const entries = Object.entries(pkt.rois);
                  if (entries.length > 0) {
                    const width = newWidth || frameDimensions.width || 1;
                    const height = newHeight || frameDimensions.height || 1;
                    const imported = entries
                      .map(([name, raw], idx) => {
                        const coords = Array.isArray(raw)
                          ? raw
                          : (raw?.coordinates || raw?.points || []);
                        if (!Array.isArray(coords)) return null;
                        const points = coords
                          .map((pt) => {
                            if (!Array.isArray(pt) || pt.length < 2) return null;
                            return {
                              x: clamp01(pt[0] / width),
                              y: clamp01(pt[1] / height)
                            };
                          })
                          .filter(Boolean);
                        if (points.length < 3) return null;
                        return {
                          id: `roi-server-${idx}`,
                          label: String(name),
                          color: ROI_COLORS[idx % ROI_COLORS.length],
                          points,
                        };
                      })
                      .filter(Boolean);
                    if (imported.length > 0) {
                      setRoiPolygons((prev) => (prev.length > 0 ? prev : imported));
                    }
                  }
                }
            }
          } else if (pkt.type === 'frame') {
            // Update FPS and frame index
            if (typeof pkt.fps === 'number') fpsRef.current = pkt.fps;
            if (typeof pkt.frame_idx === 'number') frameIdxRef.current = pkt.frame_idx;
            
            // Store detections metadata (for future violations rendering)
            if (pkt.detections && Array.isArray(pkt.detections)) {
              // TODO: Store in state/ref for violations overlay rendering
              // For now, just log occasionally
              if (pkt.frame_idx % 30 === 0 && pkt.detections.length > 0) {
                console.log(`?? Frame ${pkt.frame_idx}: ${pkt.detections.length} detections`, pkt.detections[0]);
              }
            }
            
            // Next message should be binary JPEG
            setExpectBinary(true);
          } else if (pkt.type === 'error') {
            safeToast.error(`Server Error: ${pkt.message}`);
            stopDetection();
          } else if (pkt.type === 'roi_ack') {
            const count = typeof pkt.count === 'number' ? pkt.count : 0;
            safeToast.success(`ROI synced (${count})`, { autoClose: 1500 });
          } else if (pkt.type === 'roi_cleared') {
            lastRoiSignatureRef.current = '';
            safeToast.info('ROI cleared on detector', { autoClose: 1500 });
          } else if (pkt.type === 'roi_error') {
            safeToast.error(pkt.message || 'ROI update failed');
          } else if (pkt.type === 'settings_updated') {
            safeToast.success(`✅ ${pkt.message}`, { autoClose: 2000 });
          }
        } catch (e) {
          console.error('Failed to parse text message:', e);
        }
      return;
    }
    
      // Binary message (JPEG ArrayBuffer)
      if (event.data instanceof ArrayBuffer) {
        // Latest-wins: keep only the newest buffer, decode off-main-thread
        lastBufferRef.current = event.data;
        scheduleDecode();
        setExpectBinary(false);
      }
    };

    wsRef.current = ws;
  }, [
    settings,
    modules,
    selectedModel,
    safeToast,
    frameDimensions.height,
    frameDimensions.width,
    scheduleDecode,
  ]);

  // Warmup phase: 5 seconds before starting detection
  const warmupIntervalRef = useRef(null);
  
  const startWarmup = useCallback(() => {
    setIsWarmingUp(true);
    setWarmupProgress(0);

    const warmupDuration = 5000; // 5 seconds
    const updateInterval = 50; // Update every 50ms for smooth progress (100 updates total)
    const progressStep = (100 / warmupDuration) * updateInterval;
    
    let currentProgress = 0;
    
    warmupIntervalRef.current = setInterval(() => {
      currentProgress += progressStep;
      if (currentProgress >= 100) {
        currentProgress = 100;
        if (warmupIntervalRef.current) {
          clearInterval(warmupIntervalRef.current);
          warmupIntervalRef.current = null;
        }
        setIsWarmingUp(false);
        setWarmupProgress(100);
        
        // Start detection after warmup
        if (source && isMountedRef.current) {
          console.log('🚀 Auto-starting detection after warmup');
          setDetecting(true);
          connectWebSocket(source);
          safeToast.success('🎯 Detection started!', { autoClose: 2000 });
        }
      } else {
        setWarmupProgress(currentProgress);
      }
    }, updateInterval);
  }, [connectWebSocket, safeToast, source]);
  
  // Cleanup warmup on unmount
  useEffect(() => {
    return () => {
      if (warmupIntervalRef.current) {
        clearInterval(warmupIntervalRef.current);
        warmupIntervalRef.current = null;
      }
    };
  }, []);

  // Auto-start detection when video and models are ready
  useEffect(() => {
    if (autoStart && videoLoaded && modelLoaded && !detecting && !isLoadingModels && !isWarmingUp) {
      // Small delay to ensure everything is ready, then start warmup
      const timer = setTimeout(() => {
        console.log('⚡ Starting warmup phase (5s)...');
        setAutoStart(false);
        startWarmup(); // Call warmup function directly
        safeToast.info('🔥 Warming up models (5s)...', { autoClose: 5000 });
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, [autoStart, videoLoaded, modelLoaded, detecting, isLoadingModels, isWarmingUp, source, safeToast, startWarmup]);

  // Start RAF render loop once (draw latest decoded frame to avoid stutter)
  useEffect(() => {
    const loop = () => {
      const c = canvasRef.current;
      if (!c) { rafIdRef.current = requestAnimationFrame(loop); return; }
      const ctx = c.getContext('2d');
      if (ctx && ctx.imageSmoothingEnabled) ctx.imageSmoothingEnabled = false;

      const next = nextBitmapRef.current;
      if (next) {
        // Swap buffers
        nextBitmapRef.current = null;
        const prev = displayBitmapRef.current;
        displayBitmapRef.current = next;
        try {
          // Always draw the image (server sends annotated frames)
          // BBox visibility is controlled by server settings
          ctx.drawImage(displayBitmapRef.current, 0, 0, c.width, c.height);
        } catch {}
        if (prev) {
          try { prev.close(); } catch {}
        }
      }
      rafIdRef.current = requestAnimationFrame(loop);
    };
    rafIdRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafIdRef.current);
  }, []);

  // Throttle UI state updates (reduce React re-render jank)
  useEffect(() => {
    const id = setInterval(() => {
      setFps(fpsRef.current);
      setFrameIdx(frameIdxRef.current);
    }, 200);
    return () => clearInterval(id);
  }, []);

  // Fetch available vehicle models for selection (.onnx/.pt only)
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/detection/models/available`);
        if (!res.ok) return;
        const data = await res.json();
        
        // Get vehicle models with format info
        const vehModels = Array.isArray(data?.models?.vehicle) ? data.models.vehicle : [];
        const modelOptions = vehModels.map((model) => ({
          name: `${model.name} (${model.format.toUpperCase()})`,
          path: `models/${model.path}`,
          format: model.format
        }));
        
        setAvailableModels(modelOptions);
        
        if (modelOptions.length > 0) {
          // Prefer ONNX models, then 11s models, then first available
          const preferOnnx = modelOptions.find(m => m.format === 'onnx' && /11s/i.test(m.name));
          const prefer11s = modelOptions.find(m => /11s/i.test(m.name));
          const selected = preferOnnx || prefer11s || modelOptions[0];
          setSelectedModel(selected.path);
        }
      } catch (error) {
        console.error('Failed to fetch models:', error);
      }
    })();
  }, []);

  const startDetection = async () => {
    // If models not loaded yet, try to load them first
      if (!modelLoaded) {
      if (!isLoadingModels) {
        safeToast.info('Loading models first...', { autoClose: 1500 });
        await loadModels();
      } else {
        safeToast.warning('Models still loading, please wait...');
        return;
      }
      
      // Check again after loading
      if (!modelLoaded) {
        safeToast.error('Failed to load models. Check GPU.');
          return;
        }
    }
    
    let currentSource = source;
    if (!videoLoaded) {
      safeToast.warning('Please upload a video first.');
        return;
      }
      
      setDetecting(true);
    connectWebSocket(currentSource);
    safeToast.info('Detection started!');
  };

  const stopDetection = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    safeToast.info('Detection stopped.');
    // Clear decode/display buffers
    lastBufferRef.current = null;
    decodingRef.current = false;
    if (nextBitmapRef.current) { try { nextBitmapRef.current.close(); } catch {} nextBitmapRef.current = null; }
    if (displayBitmapRef.current) { try { displayBitmapRef.current.close(); } catch {} displayBitmapRef.current = null; }
    const c = canvasRef.current;
    if (c) {
      const ctx = c.getContext('2d');
      try { ctx.clearRect(0, 0, c.width, c.height); } catch {}
    }
    setDetecting(false);
    setConnected(false);
    lastRoiSignatureRef.current = '';
  };

  const handleVideoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (limit 500MB)
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
      safeToast.error('Video too large! Max 500MB.');
      return;
    }

    setIsUploadingVideo(true);

    // Show progress only for large files
    if (file.size > 10 * 1024 * 1024) { // > 10MB
      safeToast.info(`Uploading ${file.name}... (${(file.size / 1024 / 1024).toFixed(1)}MB)`, {
        autoClose: false,
        closeButton: false
      });
    }

    // Add timeout only for very large files
    const controller = new AbortController();
    const timeoutMs = file.size > 100 * 1024 * 1024 ? 60000 : 30000; // 60s for >100MB, 30s otherwise
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_URL}/api/detection/upload-temp-video`, {
        method: 'POST',
        body: formData,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      safeToast.dismiss(); // Dismiss all toasts
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      if (data.ok) {
        setSource(data.temp_path);
        setVideoLoaded(true);
        safeToast.success(`Video ready: ${file.name}`, { autoClose: 2000 });
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      clearTimeout(timeoutId);
      safeToast.dismiss(); // Dismiss all toasts
      
      console.error('Upload error:', error);
      
      if (error.name === 'AbortError') {
        safeToast.error('Upload timeout! Try smaller video.');
      } else {
        safeToast.error(`Upload error: ${error.message}`);
      }
    } finally {
      setIsUploadingVideo(false);
    }
  };

  const updateSettings = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    
    // Send live settings update if detection is running
    if (detecting && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const cmd = {
        command: 'update_settings',
        settings: { [key]: value }
      };
      console.log('📤 Sending live settings update:', cmd);
      wsRef.current.send(JSON.stringify(cmd));
      
      // Show immediate feedback
      safeToast.info(`⚙️ ${key} updated to ${value}`, { autoClose: 1500 });
    }
  };

  const updateModule = (module, enabled) => {
    const newModules = { ...modules, [module]: enabled };
    setModules(newModules);

    // Module toggle validation and confirmation
    const moduleNames = {
      yolo: 'YOLO Detection',
      tracking: 'Object Tracking', 
      bboxDrawing: 'Bounding Box Drawing',
      roi: 'ROI Processing',
      roiDrawing: 'ROI Drawing'
    };

    const moduleName = moduleNames[module] || module;
    
    // If detecting and BBox toggle changed, send command to server
    if (detecting && module === 'bboxDrawing' && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send command to toggle bbox drawing
      const cmd = { command: 'toggle_bbox', enabled: enabled };
      console.log('📤 Sending command:', cmd);
      wsRef.current.send(JSON.stringify(cmd));
      safeToast.success(`🎨 ${moduleName} ${enabled ? 'enabled' : 'disabled'}`, { autoClose: 1500 });
    } else if (detecting && (module === 'yolo' || module === 'tracking')) {
      // YOLO and Tracking require full restart
      safeToast.info(`🔄 ${moduleName} will apply on next detection start`, {
        autoClose: 2000
      });
    } else if (detecting && module === 'roi') {
      // ROI processing toggle
      safeToast.success(`🎯 ${moduleName} ${enabled ? 'enabled' : 'disabled'}`, { autoClose: 1500 });
    } else if (module === 'roiDrawing') {
      // ROI drawing toggle
      if (!enabled && isDrawingRoi) {
        cancelRoiDrawing();
      }
      safeToast.success(`✏️ ${moduleName} ${enabled ? 'enabled' : 'disabled'}`, { autoClose: 1500 });
    } else {
      // General toggle confirmation
      safeToast.success(`⚙️ ${moduleName} ${enabled ? 'enabled' : 'disabled'}`, { autoClose: 1500 });
    }

    // Log module state for debugging
    console.log(`🔧 Module ${module}: ${enabled ? 'ON' : 'OFF'}`);
  };

  const fetchModelVersions = async () => {
    try {
      setIsLoadingVersions(true);
      const response = await fetch(`${API_URL}/api/detection/models/versions`);
      const result = await response.json();
      
      if (result.ok) {
        setModelVersions(result.versions);
        setCurrentVersion(result.current_version);
        console.log('📋 Model versions loaded:', result.versions);
      } else {
        throw new Error(result.error || 'Failed to fetch model versions');
      }
    } catch (error) {
      console.error('Error fetching model versions:', error);
      safeToast.error(`❌ Failed to load model versions: ${error.message}`);
    } finally {
      setIsLoadingVersions(false);
    }
  };

  const handleSwitchModelVersion = async (version, format) => {
    try {
      safeToast.info(`🔄 Switching to ${version.toUpperCase()} (${format.toUpperCase()})...`, { autoClose: 2000 });
      
      const response = await fetch(`${API_URL}/api/detection/models/switch-version`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          version: version,
          format: format
        })
      });

      const result = await response.json();
      
      if (result.ok) {
        setCurrentVersion(version);
        setCurrentFormat(format);
        setSelectedModel(result.model_path);
        
        safeToast.success(
          `✅ Switched to ${version.toUpperCase()} (${format.toUpperCase()})!`, 
          { autoClose: 3000 }
        );
        
        console.log(`✅ Model switch successful: ${result.model_path}`);
        console.log(`🎯 Optimization: ${result.optimizations}`);
      } else {
        throw new Error(result.error || 'Model switch failed');
      }
    } catch (error) {
      console.error('Model switch error:', error);
      safeToast.error(`❌ Model switch failed: ${error.message}`);
    }
  };

  const handleHotSwapModel = async () => {
    if (!selectedModel) {
      safeToast.error('No model selected for hot-swap');
      return;
    }

    try {
      safeToast.info('♻️ Hot-swapping model...', { autoClose: 2000 });
      
      const response = await fetch(`${API_URL}/api/detection/models/hot-swap`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_path: selectedModel,
          device: 'cuda:0'
        })
      });

      const result = await response.json();
      
      if (result.ok) {
        const modelType = result.model_type === 'onnx' ? 'ONNX' : 'PyTorch';
        safeToast.success(`♻️ Model hot-swapped to ${modelType}!`, { autoClose: 3000 });
        console.log(`✅ Hot-swap successful: ${selectedModel} (${modelType})`);
      } else {
        throw new Error(result.error || 'Hot-swap failed');
      }
    } catch (error) {
      console.error('Hot-swap error:', error);
      safeToast.error(`❌ Hot-swap failed: ${error.message}`);
    }
  };

  const clamp01 = (value) => Math.min(Math.max(value ?? 0, 0), 1);

  const startDrawingRoi = () => {
    if (isDrawingRoi) {
      safeToast.info('Finish the current ROI before starting a new one.');
      return;
    }
    const id = `roi-${Date.now()}`;
    setActiveRoiId(id);
    setDraftRoiName(`ROI ${roiPolygons.length + 1}`);
    setDraftRoiPoints([]);
    setIsDrawingRoi(true);
  };

  const cancelRoiDrawing = () => {
    setIsDrawingRoi(false);
    setDraftRoiPoints([]);
    setDraftRoiName('');
    setActiveRoiId(null);
  };

  const undoLastRoiPoint = () => {
    setDraftRoiPoints((prev) => prev.slice(0, -1));
  };

  const completeRoi = () => {
    if (draftRoiPoints.length < 3) {
      safeToast.error('ROI polygon needs at least 3 points.');
      return;
    }
    const idx = roiPolygons.length;
    const color = ROI_COLORS[idx % ROI_COLORS.length];
    const sanitizedPoints = draftRoiPoints.map((pt) => ({
      x: clamp01(pt?.x),
      y: clamp01(pt?.y),
    }));
    const label = (draftRoiName || '').trim() || `ROI ${idx + 1}`;
    const newRoi = {
      id: activeRoiId || `roi-${Date.now()}`,
      label,
      color,
      points: sanitizedPoints,
    };
    setRoiPolygons((prev) => [...prev, newRoi]);
    cancelRoiDrawing();
    safeToast.success(`Added ${label}`);
  };

  const removeRoi = (id) => {
    setRoiPolygons((prev) => prev.filter((roi) => roi.id !== id));
  };

  const updateRoiLabel = (id, label) => {
    setRoiPolygons((prev) => prev.map((roi) => (roi.id === id ? { ...roi, label } : roi)));
  };

  const handleRoiOverlayPointer = (event) => {
    if (!isDrawingRoi) return;
    const rect = overlayRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return;
    
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    const nx = clamp01(mouseX / rect.width);
    const ny = clamp01(mouseY / rect.height);
    
    event.preventDefault();
    event.stopPropagation();
    
    // Check for snapping to start point (close polygon)
    if (draftRoiPoints.length >= 3) {
      const startPoint = draftRoiPoints[0];
      const startX = startPoint.x * rect.width;
      const startY = startPoint.y * rect.height;
      const snapDistance = Math.sqrt((mouseX - startX) ** 2 + (mouseY - startY) ** 2);
      
      if (snapDistance <= 15) {
        // Snap to start point and complete polygon
        completeRoi();
        return;
      }
    }
    
    setDraftRoiPoints((prev) => [...prev, { x: nx, y: ny }]);
  };

  // Handle mouse move for snapping preview
  const handleRoiOverlayMouseMove = (event) => {
    if (!isDrawingRoi) return;
    const rect = overlayRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return;
    
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    setMousePos({ x: mouseX, y: mouseY });
  };

  const clearAllRois = (notify = true) => {
    setRoiPolygons([]);
    cancelRoiDrawing();
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      clearRoiOnServer(false);
    }
    lastRoiSignatureRef.current = '';
    if (notify) {
      safeToast.info('ROI list cleared.');
    }
  };

  const roiPayload = useMemo(() => {
    if (!roiPolygons || roiPolygons.length === 0) return {};
    const width = frameDimensions.width || 1;
    const height = frameDimensions.height || 1;
    const payload = {};
    roiPolygons.forEach((roi, idx) => {
      if (!roi.points || roi.points.length < 3) return;
      const key = (roi.label || '').trim() || `roi_${idx + 1}`;
      payload[key] = roi.points.map((pt) => [
        Math.round(clamp01(pt?.x) * width * 100) / 100,
        Math.round(clamp01(pt?.y) * height * 100) / 100,
      ]);
    });
    return payload;
  }, [roiPolygons, frameDimensions.width, frameDimensions.height]);

  const roiPayloadSignature = useMemo(() => JSON.stringify(roiPayload), [roiPayload]);

  const sendRoisToServer = (notify = true) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      if (notify) safeToast.warning('Start detection to send ROI polygons.');
      return false;
    }
    if (!roiPayload || Object.keys(roiPayload).length === 0) {
      if (notify) safeToast.info('No ROI polygons to send.');
      clearRoiOnServer(false);
      return false;
    }
    wsRef.current.send(JSON.stringify({ command: 'set_roi', rois: roiPayload }));
    lastRoiSignatureRef.current = roiPayloadSignature;
    if (notify) {
      const count = Object.keys(roiPayload).length;
      safeToast.success(`Applied ${count} ROI polygon${count > 1 ? 's' : ''}`);
    }
    return true;
  };

  const clearRoiOnServer = useCallback((notify = true) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      if (notify) safeToast.warning('Detector not connected.');
      return false;
    }
    wsRef.current.send(JSON.stringify({ command: 'clear_roi' }));
    lastRoiSignatureRef.current = '';
    if (notify) safeToast.info('ROI cleared on detector.');
    return true;
  }, [safeToast]);

  useEffect(() => {
    if (!connected) return;
    if (!modules.roi) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    if (isDrawingRoi) return;

    if (!roiPayload || Object.keys(roiPayload).length === 0) {
      if (lastRoiSignatureRef.current !== '') {
        clearRoiOnServer(false);
      }
      return;
    }

    if (roiPayloadSignature === lastRoiSignatureRef.current) return;

    wsRef.current.send(JSON.stringify({ command: 'set_roi', rois: roiPayload }));
    lastRoiSignatureRef.current = roiPayloadSignature;
  }, [connected, modules.roi, roiPayload, roiPayloadSignature, isDrawingRoi, clearRoiOnServer]);

  return (
    <>
      <PageTitle title="Realtime Detection (Binary Turbo Stream)" />
      <div className="container-fluid mt-3">
        <Card className="mb-3 shadow-sm">
          <Card.Body>
                <Row className="align-items-center g-2">
                    <Col xs="auto">
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="video/*"
                        onChange={handleVideoUpload}
                        style={{ display: 'none' }}
                      />
                      <Button 
                      variant={videoLoaded ? 'success' : 'outline-primary'}
                        onClick={() => fileInputRef.current?.click()}
                      disabled={detecting || isUploadingVideo}
                        className="rounded-pill"
                      >
                      {isUploadingVideo ? (
                        <>⏳ Uploading...</>
                      ) : (
                        <>📁 {videoLoaded ? '✅ Video Ready' : 'Choose Video'}</>
                      )}
                      </Button>
                    </Col>
                  
                  <Col xs="auto">
                    <Button 
                      size="sm"
                      onClick={loadModels}
                      disabled={modelLoaded || detecting || isLoadingModels}
                      className="rounded-pill"
                      style={{
                        background: modelLoaded ? '#6c757d' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        border: 'none',
                        color: '#fff',
                        fontWeight: 500
                      }}
                    >
                      {isLoadingModels ? (
                        <>⏳ Loading...</>
                      ) : (
                        <>⚙️ {modelLoaded ? 'Models Ready' : 'Load Models'}</>
                      )}
                    </Button>
                  </Col>

              <Col xs="auto">
                <Form.Group className="mb-0">
                  <Form.Label className="mb-1">
                    <strong>🧠 Model Version</strong>
                  </Form.Label>
                  <div className="d-flex gap-2">
                    <Form.Select
                      value={currentVersion}
                      onChange={(e) => {
                        const newVersion = e.target.value;
                        handleSwitchModelVersion(newVersion, currentFormat);
                      }}
                      disabled={detecting || isLoadingVersions}
                      style={{ minWidth: 120, fontSize: '0.9rem' }}
                    >
                      {Object.keys(modelVersions).map((version) => (
                        <option key={version} value={version}>
                          {modelVersions[version]?.name || version.toUpperCase()}
                        </option>
                      ))}
                    </Form.Select>
                    
                    <Form.Select
                      value={currentFormat}
                      onChange={(e) => {
                        const newFormat = e.target.value;
                        handleSwitchModelVersion(currentVersion, newFormat);
                      }}
                      disabled={detecting || isLoadingVersions}
                      style={{ minWidth: 100, fontSize: '0.9rem' }}
                    >
                      {modelVersions[currentVersion]?.models?.map((model) => (
                        <option key={model.format} value={model.format}>
                          {model.format.toUpperCase()} ({model.size_mb}MB)
                        </option>
                      )) || []}
                    </Form.Select>
                    
                    {detecting && (
                      <Button
                        size="sm"
                        variant="outline-primary"
                        onClick={handleHotSwapModel}
                        disabled={!selectedModel}
                        title="Hot-swap current model"
                      >
                        ♻️
                      </Button>
                    )}
                  </div>
                  <Form.Text className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {currentVersion === '11s' && '⚡ Speed & Efficiency (RTX 3050 Optimized)'}
                    {currentVersion === 'v10m' && '🎯 Accuracy & Precision'}
                    {' • '}{currentFormat.toUpperCase()} format
                    {detecting && ' • Use ♻️ for live switching'}
                  </Form.Text>
                </Form.Group>
                  </Col>
                  
                  <Col xs="auto">
                    {!detecting ? (
                      <Button 
                        size="sm"
                        onClick={startDetection}
                        disabled={!modelLoaded || !videoLoaded}
                        className="rounded-pill"
                        style={{
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          border: 'none',
                          color: '#fff',
                          fontWeight: 500,
                          boxShadow: '0 4px 15px 0 rgba(102, 126, 234, 0.4)'
                        }}
                      >
                        Start Detection
                      </Button>
                    ) : (
                      <Button 
                        size="sm"
                        onClick={stopDetection}
                        className="rounded-pill"
                        style={{
                          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                          border: 'none',
                          color: '#fff',
                          fontWeight: 500
                        }}
                      >
                        Stop
                      </Button>
                    )}
                  </Col>
                  
                  <Col xs="auto">
                    <Badge 
                      bg={detecting ? 'success' : 'secondary'}
                      className="px-3 py-2"
                      style={{
                        fontSize: '0.85rem',
                        fontWeight: 500,
                        animation: detecting ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
                      }}
                    >
                  {detecting ? '● LIVE (BINARY)' : '○ Offline'}
                    </Badge>
                  </Col>
                  
              <Col className="ms-auto">
                <div className="d-flex align-items-center gap-2 justify-content-end">
                      <Badge
                    bg={fps >= 30 ? 'success' : fps >= 20 ? 'warning' : 'danger'}
                        className="px-2 py-1"
                        style={{fontSize: '0.85rem', fontWeight: 600}}
                      >
                    ⚡ {fps.toFixed(1)} FPS
                  </Badge>
                  <Badge bg="info" className="px-2 py-1" style={{fontSize: '0.85rem', fontWeight: 600}}>
                    Frame: {frameIdx}
                      </Badge>
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>

        <Card className="mb-3 shadow-sm">
                <Card.Body>
        <Row>
          <Col md={12}>
            <h6 className="mb-3">🔧 Detection Modules {detecting && <small className="text-success">(live updates enabled)</small>}</h6>
            <div className="d-flex gap-3 flex-wrap">
              <Form.Check
                type="switch"
                id="yolo-toggle"
                label="YOLO Detection"
                checked={modules.yolo}
                onChange={(e) => updateModule('yolo', e.target.checked)}
                disabled={false}
              />
              <Form.Check
                type="switch"
                id="tracking-toggle"
                label="ByteTrack Tracking"
                checked={modules.tracking}
                onChange={(e) => updateModule('tracking', e.target.checked)}
                disabled={false}
              />
              <Form.Check
                type="switch"
                id="bbox-toggle"
                label="BBox Drawing"
                checked={modules.bboxDrawing}
                onChange={(e) => updateModule('bboxDrawing', e.target.checked)}
                disabled={false}
              />
              <Form.Check
                type="switch"
                id="roi-toggle"
                label="ROI Module"
                checked={modules.roi}
                onChange={(e) => updateModule('roi', e.target.checked)}
                disabled={false}
              />
              <Form.Check
                type="switch"
                id="roi-drawing-toggle"
                label="ROI Drawing"
                checked={modules.roiDrawing}
                onChange={(e) => updateModule('roiDrawing', e.target.checked)}
                disabled={false}
              />
              <Form.Check
                type="switch"
                id="force-gpu-toggle"
                label="Force GPU (CUDA)"
                checked={settings.force_gpu}
                onChange={(e) => updateSettings('force_gpu', e.target.checked)}
                disabled={detecting}
              />
            </div>
            {detecting && (
              <small className="text-info d-block mt-2">
                💡 Tip: Most settings update live! Only YOLO/Tracking modules need restart
              </small>
            )}
          </Col>
        </Row>
        <hr />
        <Row>
              <Col md={3}>
                <Form.Group className="mb-2">
                  <Form.Label>
                    Confidence: {settings.conf.toFixed(2)} 
                    {detecting && <small className="text-success"> (live)</small>}
                  </Form.Label>
                    <Form.Range
                      value={settings.conf}
                      min={0.1}
                      max={0.9}
                      step={0.05}
                    onChange={(e) => updateSettings('conf', parseFloat(e.target.value))}
                    disabled={false}
                  />
                      </Form.Group>
                    </Col>
              <Col md={2}>
                <Form.Group className="mb-2">
                  <Form.Label>
                    Target FPS: {settings.target_fps}
                    {detecting && <small className="text-success"> (live)</small>}
                  </Form.Label>
                  <Form.Range
                    value={settings.target_fps}
                    min={15}
                    max={60}
                    step={5}
                    onChange={(e) => updateSettings('target_fps', parseInt(e.target.value))}
                    disabled={false}
                  />
                      </Form.Group>
                    </Col>
              <Col md={2}>
                <Form.Group className="mb-2">
                  <Form.Label>
                    JPEG Quality: {settings.jpeg_quality}
                    {detecting && <small className="text-success"> (live)</small>}
                  </Form.Label>
                  <Form.Range
                    value={settings.jpeg_quality}
                    min={50}
                    max={85}
                    step={5}
                    onChange={(e) => updateSettings('jpeg_quality', parseInt(e.target.value))}
                    disabled={false}
                  />
                </Form.Group>
                  </Col>
              <Col md={2}>
                <Form.Group className="mb-2">
                  <Form.Label>
                    Inference Size: {settings.inference_size}
                    {detecting && <small className="text-warning"> (restart)</small>}
                  </Form.Label>
                        <Form.Select 
                    value={settings.inference_size}
                    onChange={(e) => updateSettings('inference_size', parseInt(e.target.value))}
                    disabled={false}
                  >
                    <option value="480">480 (Faster)</option>
                    <option value="640">640 (Balanced)</option>
                    <option value="832">832 (YOLO11s Native)</option>
                    <option value="960">960 (Better)</option>
                        </Form.Select>
                      </Form.Group>
                    </Col>
              <Col md={3}>
                <Form.Group className="mb-2">
                  <Form.Label>
                    Encode Width: {settings.encode_width}
                    {detecting && <small className="text-success"> (live)</small>}
                  </Form.Label>
                        <Form.Select 
                    value={settings.encode_width}
                    onChange={(e) => updateSettings('encode_width', parseInt(e.target.value))}
                    disabled={false}
                  >
                    <option value="800">800 (Fastest)</option>
                    <option value="960">960 (Fast)</option>
                    <option value="1280">1280 (Quality)</option>
                        </Form.Select>
                      </Form.Group>
                    </Col>
                  </Row>
                </Card.Body>
              </Card>

              <div style={{
              position:'relative',
              width:'100%',
              maxWidth: '1280px',
              aspectRatio:'16/9',
              border:'2px solid #667eea',
              background:'#000',
              borderRadius: '8px',
              overflow: 'hidden'
            }}>
                  <canvas
                    ref={canvasRef}
                style={{width:'100%', height:'100%', background:'#000'}}
                width={frameDimensions.width}
                height={frameDimensions.height}
              />
              <RoiOverlay
                ref={overlayRef}
                frameDimensions={frameDimensions}
                rois={roiPolygons}
                draftPoints={draftRoiPoints}
                isDrawing={isDrawingRoi}
                onPointerDown={handleRoiOverlayPointer}
                mousePos={mousePos}
                onMouseMove={handleRoiOverlayMouseMove}
              />
              
              {/* Debug Overlay (Press 'D' to toggle) */}
              {showDebugOverlay && (
                <div style={{
                  position: 'absolute',
                  top: '10px',
                  left: '10px',
                  background: 'rgba(0, 0, 0, 0.8)',
                  color: '#fff',
                  padding: '12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  zIndex: 10,
                  minWidth: '200px'
                }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#00ff00' }}>
                    🔧 Debug Info (Press D to hide)
                  </div>
                  <div>FPS: {fps.toFixed(1)} | Frame: {frameIdx}</div>
                  <div>Model: {selectedModel.split('/').pop()}</div>
                  <div>Format: {selectedModel.includes('.onnx') ? 'ONNX' : 'PyTorch'}</div>
                  <div>Resolution: {frameDimensions.width}x{frameDimensions.height}</div>
                  <div style={{ marginTop: '6px', fontWeight: 'bold' }}>Modules:</div>
                  <div style={{ marginLeft: '10px' }}>
                    <div>YOLO: {modules.yolo ? '✅' : '❌'}</div>
                    <div>Tracking: {modules.tracking ? '✅' : '❌'}</div>
                    <div>BBox: {modules.bboxDrawing ? '✅' : '❌'}</div>
                    <div>ROI: {modules.roi ? '✅' : '❌'} ({roiPolygons.length})</div>
                    <div>ROI Draw: {modules.roiDrawing ? '✅' : '❌'}</div>
                  </div>
                  <div style={{ marginTop: '6px' }}>
                    Status: {connected ? '🟢 Connected' : '🔴 Disconnected'}
                  </div>
                </div>
              )}

              {!detecting && !isWarmingUp && (
                  <div style={{
                    position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  color: '#fff',
                  fontSize: '1.5rem',
                  textAlign: 'center'
                }}>
                  🎥 Ready for Video Detection<br/>
                  <small style={{fontSize: '0.8rem', opacity: 0.7}}>
                    {videoLoaded ? 'Click Start Detection' : 'Upload video to start detection'}
                    <br/>Press 'D' for debug overlay
                                      </small>
                  </div>
                      )}
              
              {/* Warmup Progress Overlay */}
              {isWarmingUp && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  color: '#fff',
                  textAlign: 'center',
                  zIndex: 10,
                  background: 'rgba(0, 0, 0, 0.85)',
                  padding: '2rem 3rem',
                  borderRadius: '16px',
                  minWidth: '350px',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                  border: '2px solid rgba(102, 126, 234, 0.3)'
                }}>
                  <div style={{ fontSize: '3rem', marginBottom: '1rem', animation: 'pulse 2s infinite' }}>
                    🔥
                  </div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                    Warming Up Models
                  </div>
                  <div style={{ fontSize: '0.95rem', opacity: 0.8, marginBottom: '1.5rem' }}>
                    Preparing for optimal performance...
                  </div>
                  {/* Progress Bar */}
                  <div style={{
                    width: '100%',
                    height: '10px',
                    background: 'rgba(255, 255, 255, 0.2)',
                    borderRadius: '5px',
                    overflow: 'hidden',
                    marginBottom: '0.8rem'
                  }}>
                    <div style={{
                      width: `${warmupProgress}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                      transition: 'width 0.1s ease',
                      borderRadius: '5px',
                      boxShadow: '0 0 10px rgba(102, 126, 234, 0.5)'
                    }} />
                  </div>
                  <div style={{ fontSize: '0.9rem', opacity: 0.7, fontWeight: 500 }}>
                    {Math.round(warmupProgress)}% • {Math.max(0, Math.ceil((100 - warmupProgress) / 20))}s remaining
                  </div>
                </div>
              )}
                    </div>

            


                                  </div>
    </>
  );
}

// Wrap in Suspense for useSearchParams
export default function DetectionPageBinary() {
  return (
    <Suspense fallback={
      <div className="container-fluid mt-3">
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-3">Loading detection page...</p>
        </div>
      </div>
    }>
      <DetectionPageBinaryContent />
    </Suspense>
  );
}