'use client';
import React, { useRef, useEffect, useState, Suspense, useMemo, useCallback } from 'react';
import { Button, Form, Row, Col, Card, Badge, Modal, Alert } from 'react-bootstrap';
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
  const prevSourceRef = useRef('');
  // Throttled UI refs
  const fpsRef = useRef(0);
  const frameIdxRef = useRef(0);

  const [connected, setConnected] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
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

  // Traffic light + violation state
  const [lightState, setLightState] = useState('GREEN');
  const [lastLightChangeTs, setLastLightChangeTs] = useState(null);
  const [violations, setViolations] = useState([]);
  const vehicleStatesRef = useRef(new Map());
  const lightStateRef = useRef({ state: 'GREEN', changedAt: 0 });
  const redStartRef = useRef(null);
  const currentDetectionsRef = useRef([]);

  const [roiPolygons, setRoiPolygons] = useState([]);

  // === TRAFFIC LIGHT ROI (CANVAS OVERLAY WITH DRAG & RESIZE) ===
  const [tlRoi, setTlRoi] = useState(null); // {x, y, w, h} in video pixels
  const [isDrawingTL, setIsDrawingTL] = useState(false);
  const [isMovingTL, setIsMovingTL] = useState(false);
  const [resizeHandle, setResizeHandle] = useState(null); // 'tl', 'tr', 'bl', 'br'
  const [startPos, setStartPos] = useState(null); // mouse anchor
  const [tlRoiActive, setTlRoiActive] = useState(false);
  const [isSelectingTLMode, setIsSelectingTLMode] = useState(false); // UI mode
  const [trafficLightState, setTrafficLightState] = useState("UNKNOWN");
  const [trafficLightFrame, setTrafficLightFrame] = useState(null);
  const [trafficLightConfidence, setTrafficLightConfidence] = useState(null);
  const tlSocketRef = useRef(null);
  const tlCanvasRef = useRef(null); // Canvas for TL ROI drawing

  // === STOPLINE (2-POINT LINE) ===
  const [stopline, setStopline] = useState(null); // {x1, y1, x2, y2} in video pixels
  const [isDrawingStopline, setIsDrawingStopline] = useState(false);
  const [isMovingStopline, setIsMovingStopline] = useState(false);
  const [stoplineHandle, setStoplineHandle] = useState(null); // 'p1' or 'p2' for endpoints
  const [stoplineActive, setStoplineActive] = useState(false);
  const [isDrawingRoi, setIsDrawingRoi] = useState(false);
  const [draftRoiPoints, setDraftRoiPoints] = useState([]);
  const [draftRoiName, setDraftRoiName] = useState('');
  const [activeRoiId, setActiveRoiId] = useState(null);
  const [mousePos, setMousePos] = useState(null);
  const [showDebugOverlay, setShowDebugOverlay] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  const resolveCameraId = useCallback(
    (srcValue) => {
      const path = (srcValue || source || '').toLowerCase();
      return path.includes('viphamgiaothong') ? 'cam02' : 'cam01';
    },
    [source]
  );

  const resetTrafficLightState = useCallback(
    ({ clearGeometry = false, closeSocket = false } = {}) => {
      if (closeSocket && tlSocketRef.current) {
        tlSocketRef.current.close();
        tlSocketRef.current = null;
      }

      setTrafficLightState("UNKNOWN");
      setTrafficLightFrame(null);
      setTrafficLightConfidence(null);
      setTlRoiActive(false);
      setIsSelectingTLMode(false);
      setViolations([]);
      vehicleStatesRef.current.clear();

      if (clearGeometry) {
        setTlRoi(null);
        setStopline(null);
        setStoplineActive(false);
      }
    },
    []
  );

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

  useEffect(() => {
    if (!source || source === prevSourceRef.current) return;

    prevSourceRef.current = source;
    resetTrafficLightState({ clearGeometry: true, closeSocket: true });
  }, [source, resetTrafficLightState]);

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
          try { nextBitmapRef.current.close(); } catch { }
        }
        nextBitmapRef.current = bitmap;
      })
      .catch(() => { })
      .finally(() => {
        decodingRef.current = false;
        // If a newer buffer arrived while decoding, process it now
        if (lastBufferRef.current) scheduleDecode();
      });
  }, []);

  const clamp01 = (value) => Math.min(Math.max(value ?? 0, 0), 1);

  const stoplineBounds = useMemo(() => {
    // Use 2-point stopline if available
    if (stopline && stopline.x1 !== undefined) {
      return {
        label: 'Stopline',
        minX: Math.min(stopline.x1, stopline.x2),
        maxX: Math.max(stopline.x1, stopline.x2),
        minY: Math.min(stopline.y1, stopline.y2),
        maxY: Math.max(stopline.y1, stopline.y2),
      };
    }

    // Fallback to ROI polygon if no 2-point stopline
    if (!roiPolygons || roiPolygons.length === 0) return null;
    const stoplineRoi =
      roiPolygons.find((roi) => /stop/i.test(roi.label || '')) || roiPolygons[0];
    if (!stoplineRoi?.points || stoplineRoi.points.length === 0) return null;

    const width = frameDimensions.width || 1;
    const height = frameDimensions.height || 1;
    const xs = stoplineRoi.points.map((p) => clamp01(p.x) * width);
    const ys = stoplineRoi.points.map((p) => clamp01(p.y) * height);

    return {
      label: stoplineRoi.label || 'Stopline',
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    };
  }, [stopline, roiPolygons, frameDimensions.width, frameDimensions.height]);

  const classifyPosition = useCallback(
    (frontPoint) => {
      if (!stoplineBounds || !frontPoint) return 'UNKNOWN';
      const { minY, maxY } = stoplineBounds;
      const tolerance = 6; // pixels
      if (frontPoint.y < minY - tolerance) return 'AFTER_LINE';
      if (frontPoint.y > maxY + tolerance) return 'BEFORE_LINE';
      return 'ON_LINE';
    },
    [stoplineBounds]
  );

  // Check if bbox intersects with stopline
  const bboxIntersectsStopline = useCallback(
    (bbox) => {
      if (!stoplineBounds || !bbox || bbox.length < 4) return false;
      const [x1, y1, x2, y2] = bbox;
      const { minY, maxY } = stoplineBounds;

      // Add tolerance for line-based stopline (thicker detection zone)
      const tolerance = 20; // pixels - wider zone for better detection

      // Check if bbox overlaps with stopline Y range (with tolerance)
      return !(y2 < minY - tolerance || y1 > maxY + tolerance);
    },
    [stoplineBounds]
  );

  const handleLightState = useCallback((stateRaw) => {
    const state = (stateRaw || 'GREEN').toString().toUpperCase();
    if (state === lightStateRef.current.state) return;

    const ts = Date.now();
    lightStateRef.current = { state, changedAt: ts };
    setLightState(state);
    setLastLightChangeTs(ts);

    console.log(`🚦 Light state changed: ${state}`);

    if (state === 'RED') {
      redStartRef.current = ts;
      console.log('🔴 RED LIGHT - Violation detection ACTIVE');
    } else {
      redStartRef.current = null;
      // Reset all violations when light is not red
      vehicleStatesRef.current.forEach((v) => {
        v.violation = false;
      });
      console.log(`🟢 ${state} LIGHT - Violations reset`);
    }
  }, []);

  const processTrafficLightLogic = useCallback(
    (pkt) => {
      if (!pkt || !Array.isArray(pkt.detections)) return;

      // Store detections for overlay rendering
      currentDetectionsRef.current = pkt.detections;

      // Update light state from packet
      if (pkt.light_state) {
        handleLightState(pkt.light_state);
      }

      if (!stoplineBounds) return;

      const now = Date.now();
      const isRed = lightStateRef.current.state === 'RED';
      const updatedViolations = [];

      pkt.detections.forEach((det) => {
        const trackId = det?.track_id ?? det?.id ?? null;
        const bbox = det?.bbox;
        if (!trackId || !Array.isArray(bbox) || bbox.length < 4) return;

        const current = vehicleStatesRef.current.get(trackId) || {
          firstSeenAt: now,
          violation: false,
          lastFrame: pkt.frame_idx ?? 0,
        };

        // NEW LOGIC: Nếu đèn đỏ VÀ bbox đè lên stopline → vi phạm ngay
        const intersects = bboxIntersectsStopline(bbox);
        if (isRed && !current.violation && intersects) {
          current.violation = true;
          current.crossedAt = now;
          updatedViolations.push({
            trackId,
            frame: pkt.frame_idx ?? frameIdxRef.current,
            light: 'RED',
            stopline: stoplineBounds.label,
            time: new Date().toLocaleTimeString(),
          });
          console.log(`🚨 VIOLATION: Track ${trackId} crossed stopline on RED light`, {
            bbox,
            stoplineBounds,
            intersects
          });
        }

        // Reset violation khi đèn không đỏ
        if (!isRed) {
          current.violation = false;
        }

        current.lastFrame = pkt.frame_idx ?? current.lastFrame;
        vehicleStatesRef.current.set(trackId, current);
      });

      if (updatedViolations.length > 0) {
        setViolations((prev) => [...updatedViolations, ...prev].slice(0, 20));
      }
    },
    [bboxIntersectsStopline, handleLightState, stoplineBounds]
  );

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
    // Determine camera_id based on source video for correct config loading
    const cameraId = resolveCameraId(src);
    params.append('camera_id', cameraId);

    // Use dedicated traffic light WebSocket endpoint
    const wsUrl = `${API_URL.replace('http', 'ws')}/api/traffic-light/realtime?${params.toString()}`;
    console.log('🚦 Connecting to Traffic Light WS:', wsUrl);

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

              // Auto-load ROI for viphamgiaothong (cam02)
              if (source && source.toLowerCase().includes('viphamgiaothong')) {
                console.log('🎬 Video Viphamgiaothong detected - Loading cam02.json config...');

                // Values from cam02.json
                const cam02Roi = { x: 939, y: 113, w: 147, h: 75 };
                setTlRoi(cam02Roi);
                setTlRoiActive(true);

                const cam02Stopline = { x1: 143, y1: 927, x2: 1278, y2: 939 };
                setStopline(cam02Stopline);
                setStoplineActive(true);

                safeToast.success('✅ Loaded cam02 configuration', { autoClose: 2000 });
              }

              // Auto-load ROI for video3 after detection starts
              if (source && source.toLowerCase().includes('video3')) {
                // Set default TL ROI
                const defaultTlRoi = { x: 833, y: 14, w: 52, h: 101 };
                setTlRoi(defaultTlRoi);
                setTlRoiActive(true);

                // Set default Stopline
                const defaultStopline = { x1: 37, y1: 334, x2: 804, y2: 320 };
                setStopline(defaultStopline);
                setStoplineActive(true);

                // Auto-save TL ROI to backend
                const roi_pixel = {
                  x1: Math.round(defaultTlRoi.x),
                  y1: Math.round(defaultTlRoi.y),
                  x2: Math.round(defaultTlRoi.x + defaultTlRoi.w),
                  y2: Math.round(defaultTlRoi.y + defaultTlRoi.h)
                };

                const cameraId = resolveCameraId(source);

                fetch(`${API_URL}/api/traffic-light/roi`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    camera_id: cameraId,
                    roi_pixel,
                    frame_width: newWidth,
                    frame_height: newHeight
                  })
                }).then(res => {
                  if (res.ok) {
                    console.log('✅ TL ROI auto-saved for video3');
                    safeToast.success('✅ Auto-loaded ROI & Stopline', { autoClose: 2000 });
                  }
                }).catch(err => {
                  console.warn('Failed to auto-save TL ROI:', err);
                });

                console.log('🚦 Auto-loaded ROI & Stopline for video3');
              }
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
              processTrafficLightLogic(pkt);
            }

            // Handle traffic light data from realtime stream
            if (pkt.traffic_light) {
              const tl = pkt.traffic_light;
              if (tl.state) {
                setTrafficLightState(tl.state);
                // Sync with lightStateRef for violation logic
                handleLightState(tl.state);
              }
              if (tl.confidence !== undefined) {
                setTrafficLightConfidence(tl.confidence);
              }
              if (tl.roi_frame) {
                setTrafficLightFrame("data:image/jpeg;base64," + tl.roi_frame);
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
    processTrafficLightLogic,
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

      // Skip rendering if paused (keep last frame frozen)
      if (!isPaused) {
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

            // Draw violation overlay (red bbox + label)
            const detections = currentDetectionsRef.current;
            if (detections && detections.length > 0) {
              detections.forEach((det) => {
                const trackId = det?.track_id ?? det?.id ?? null;
                const bbox = det?.bbox;
                if (!trackId || !bbox || bbox.length < 4) return;

                const vehicleState = vehicleStatesRef.current.get(trackId);
                if (vehicleState && vehicleState.violation) {
                  const [x1, y1, x2, y2] = bbox;

                  // Draw red bbox
                  ctx.strokeStyle = '#FF0000';
                  ctx.lineWidth = 4;
                  ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

                  // Draw "VI PHẠM" label
                  ctx.fillStyle = '#FF0000';
                  ctx.fillRect(x1, y1 - 25, 100, 25);
                  ctx.fillStyle = '#FFFFFF';
                  ctx.font = 'bold 16px Arial';
                  ctx.fillText('VI PHẠM', x1 + 5, y1 - 7);
                }
              });
            }
          } catch { }
          if (prev) {
            try { prev.close(); } catch { }
          }
        }
      }
      // Continue loop even when paused (to resume smoothly)
      rafIdRef.current = requestAnimationFrame(loop);
    };
    rafIdRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafIdRef.current);
  }, [isPaused]);

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
    if (nextBitmapRef.current) { try { nextBitmapRef.current.close(); } catch { } nextBitmapRef.current = null; }
    if (displayBitmapRef.current) { try { displayBitmapRef.current.close(); } catch { } displayBitmapRef.current = null; }
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

        resetTrafficLightState({ clearGeometry: true, closeSocket: true });

        // Probe video to get dimensions
        try {
          const probeResponse = await fetch(`${API_URL}/api/detection/probe-video?path=${encodeURIComponent(data.temp_path)}`);
          if (probeResponse.ok) {
            const probeData = await probeResponse.json();
            if (probeData.width && probeData.height) {
              console.log('📹 Video dimensions:', probeData.width, 'x', probeData.height);
              setFrameDimensions({ width: probeData.width, height: probeData.height });
            }
          }
        } catch (probeError) {
          console.warn('Failed to probe video dimensions:', probeError);
        }

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

  // === TRAFFIC LIGHT ROI FUNCTIONS ===
  // === SAVE TRAFFIC LIGHT ROI (PIXEL-BASED) ===
  const saveTrafficLightROI = async () => {
    try {
      if (!tlRoi) {
        safeToast.error('No Traffic Light ROI defined. Please draw ROI first.');
        return;
      }

      // Convert {x, y, w, h} format to {x1, y1, x2, y2}
      const roi_pixel = {
        x1: parseInt(tlRoi.x) || 0,
        y1: parseInt(tlRoi.y) || 0,
        x2: parseInt(tlRoi.x + tlRoi.w) || 0,
        y2: parseInt(tlRoi.y + tlRoi.h) || 0,
      };

      console.log('🚦 Saving TL ROI:', { tlRoi, roi_pixel });

      // Validation
      if (roi_pixel.x2 <= roi_pixel.x1 || roi_pixel.y2 <= roi_pixel.y1) {
        safeToast.error('Invalid ROI: width and height must be positive');
        return;
      }

      const response = await fetch(`${API_URL}/api/traffic-light/roi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camera_id: resolveCameraId(),
          roi_pixel,
          frame_width: frameDimensions.width || 1920,
          frame_height: frameDimensions.height || 1080
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ TL ROI saved:', result);
        setTlRoiActive(true);
        safeToast.success('Traffic Light ROI saved!');
        startTrafficLightWS();
      } else {
        const error = await response.json();
        safeToast.error(`Failed to save ROI: ${error.detail || error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving TL ROI:', error);
      safeToast.error('Failed to save Traffic Light ROI');
    }
  };

  const startTrafficLightWS = () => {
    if (tlSocketRef.current) {
      tlSocketRef.current.close();
    }

    const wsUrl = `${API_URL.replace("http", "ws")}/api/traffic-light/ws/traffic-light?camera_id=${resolveCameraId()}`;

    tlSocketRef.current = new WebSocket(wsUrl);

    tlSocketRef.current.onopen = () => {
      console.log('🚦 Traffic Light WebSocket connected');
      safeToast.success('Traffic Light detection started!');
    };

    tlSocketRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.error) {
          safeToast.error(`TL Error: ${data.error}`);
          return;
        }

        if (data.state) {
          setTrafficLightState(data.state);
        }

        if (data.confidence !== undefined) {
          setTrafficLightConfidence(data.confidence);
        }

        if (data.roi_frame) {
          setTrafficLightFrame("data:image/jpeg;base64," + data.roi_frame);
        }
      } catch (error) {
        console.error('Error parsing TL message:', error);
      }
    };

    tlSocketRef.current.onerror = (error) => {
      console.warn("TL WebSocket error:", error);
      safeToast.warning('Traffic Light connection error');
    };

    tlSocketRef.current.onclose = () => {
      console.log("TL socket closed");
    };
  };

  const stopTrafficLightWS = () => {
    resetTrafficLightState({ closeSocket: true });
    safeToast.info('Traffic Light detection stopped');
  };

  // Cleanup TL WebSocket on unmount
  useEffect(() => {
    return () => {
      if (tlSocketRef.current) {
        tlSocketRef.current.close();
      }
    };
  }, []);

  // === TRAFFIC LIGHT ROI CANVAS DRAWING & INTERACTION ===

  // Sync canvas size with video resolution
  useEffect(() => {
    const canvas = tlCanvasRef.current;
    const mainCanvas = canvasRef.current;

    if (canvas && mainCanvas && frameDimensions.width > 0 && frameDimensions.height > 0) {
      console.log('📐 Syncing canvas dimensions:', frameDimensions);
      canvas.width = frameDimensions.width;
      canvas.height = frameDimensions.height;

      // Set default TL ROI if not already set
      if (!tlRoi && frameDimensions.width > 833 && frameDimensions.height > 115) {
        const defaultRoi = { x: 833, y: 14, w: 52, h: 101 };
        setTlRoi(defaultRoi);
        console.log('🚦 Default TL ROI set:', defaultRoi);
      }
    }
  }, [frameDimensions, tlRoi]);

  // Draw TL ROI on canvas
  const drawTLROI = useCallback(() => {
    const canvas = tlCanvasRef.current;
    if (!canvas) {
      console.warn('⚠️ TL Canvas not available');
      return;
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!tlRoi || (!tlRoiActive && !isSelectingTLMode)) {
      if (canvas.width > 0 && tlRoi && Math.random() < 0.02) {
        console.log('ℹ️ TL ROI hidden until active/drawing');
      }
      return;
    }

    // Log only when actually drawing
    if (Math.random() < 0.01) { // 1% chance to log
      console.log('🎨 Drawing TL ROI:', tlRoi, 'on canvas:', canvas.width, 'x', canvas.height);
    }

    // Draw rectangle
    ctx.strokeStyle = '#FFD700'; // Gold
    ctx.lineWidth = 3;
    ctx.strokeRect(tlRoi.x, tlRoi.y, tlRoi.w, tlRoi.h);

    ctx.fillStyle = 'rgba(255, 215, 0, 0.25)';
    ctx.fillRect(tlRoi.x, tlRoi.y, tlRoi.w, tlRoi.h);

    // Draw resize handles (corners)
    const handleSize = 10;
    ctx.fillStyle = '#FFD700';

    // Top-left
    ctx.fillRect(tlRoi.x - handleSize / 2, tlRoi.y - handleSize / 2, handleSize, handleSize);
    // Top-right
    ctx.fillRect(tlRoi.x + tlRoi.w - handleSize / 2, tlRoi.y - handleSize / 2, handleSize, handleSize);
    // Bottom-left
    ctx.fillRect(tlRoi.x - handleSize / 2, tlRoi.y + tlRoi.h - handleSize / 2, handleSize, handleSize);
    // Bottom-right
    ctx.fillRect(tlRoi.x + tlRoi.w - handleSize / 2, tlRoi.y + tlRoi.h - handleSize / 2, handleSize, handleSize);

    // Label
    ctx.fillStyle = '#FFD700';
    ctx.fillRect(tlRoi.x, tlRoi.y - 28, 200, 28);
    ctx.fillStyle = '#000';
    ctx.font = 'bold 14px sans-serif';
    ctx.fillText(`🚦 TL ROI (${Math.round(tlRoi.w)}×${Math.round(tlRoi.h)})`, tlRoi.x + 5, tlRoi.y - 8);
  }, [isSelectingTLMode, tlRoi, tlRoiActive]);

  // === STOPLINE DRAWING FUNCTIONS ===
  const drawStopline = useCallback(() => {
    const canvas = tlCanvasRef.current;
    if (!canvas || !stopline) return;

    const ctx = canvas.getContext('2d');

    // Draw line with shadow for visibility
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
    ctx.shadowBlur = 4;
    ctx.strokeStyle = '#FF4444'; // Bright red
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(stopline.x1, stopline.y1);
    ctx.lineTo(stopline.x2, stopline.y2);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Draw endpoints (larger for easier grabbing)
    const handleSize = 12;
    ctx.fillStyle = '#FF4444';
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;

    // Endpoint 1
    ctx.beginPath();
    ctx.arc(stopline.x1, stopline.y1, handleSize / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Endpoint 2
    ctx.beginPath();
    ctx.arc(stopline.x2, stopline.y2, handleSize / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Label
    const midX = (stopline.x1 + stopline.x2) / 2;
    const midY = (stopline.y1 + stopline.y2) / 2;
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
    ctx.shadowBlur = 4;
    ctx.fillStyle = '#FF4444';
    ctx.fillRect(midX - 60, midY - 28, 120, 28);
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 14px sans-serif';
    ctx.fillText('🛑 Stopline', midX - 50, midY - 8);
  }, [stopline]);

  // Redraw when ROI or stopline changes
  useEffect(() => {
    drawTLROI();
    drawStopline();
  }, [drawTLROI, drawStopline]);

  // Check if point is on stopline endpoint
  const hitStoplineHandle = (x, y) => {
    if (!stopline) return null;

    const handleSize = 20; // Larger hit area for easier grabbing
    const dist1 = Math.sqrt((x - stopline.x1) ** 2 + (y - stopline.y1) ** 2);
    const dist2 = Math.sqrt((x - stopline.x2) ** 2 + (y - stopline.y2) ** 2);

    if (dist1 < handleSize) return 'p1';
    if (dist2 < handleSize) return 'p2';
    return null;
  };

  // Check if point is near stopline (for moving entire line)
  const hitStopline = (x, y) => {
    if (!stopline) return false;

    // Distance from point to line segment
    const A = x - stopline.x1;
    const B = y - stopline.y1;
    const C = stopline.x2 - stopline.x1;
    const D = stopline.y2 - stopline.y1;

    const dot = A * C + B * D;
    const lenSq = C * C + D * D;
    const param = lenSq !== 0 ? dot / lenSq : -1;

    let xx, yy;
    if (param < 0) {
      xx = stopline.x1;
      yy = stopline.y1;
    } else if (param > 1) {
      xx = stopline.x2;
      yy = stopline.y2;
    } else {
      xx = stopline.x1 + param * C;
      yy = stopline.y1 + param * D;
    }

    const dx = x - xx;
    const dy = y - yy;
    const distance = Math.sqrt(dx * dx + dy * dy);

    return distance < 15; // 15px threshold for easier selection
  };

  // Convert mouse position to video pixel coordinates
  const getVideoCoords = (e, element) => {
    const rect = element.getBoundingClientRect();
    const scaleX = frameDimensions.width / rect.width;
    const scaleY = frameDimensions.height / rect.height;

    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  // Check if point is inside ROI
  const hitTestROI = (x, y) => {
    if (!tlRoi) return false;
    return x >= tlRoi.x && x <= tlRoi.x + tlRoi.w &&
      y >= tlRoi.y && y <= tlRoi.y + tlRoi.h;
  };

  // Check if point is on resize handle
  const hitResizeHandle = (x, y) => {
    if (!tlRoi) return null;

    const handleSize = 15; // Hit area
    const corners = {
      tl: { x: tlRoi.x, y: tlRoi.y },
      tr: { x: tlRoi.x + tlRoi.w, y: tlRoi.y },
      bl: { x: tlRoi.x, y: tlRoi.y + tlRoi.h },
      br: { x: tlRoi.x + tlRoi.w, y: tlRoi.y + tlRoi.h }
    };

    for (const [handle, pos] of Object.entries(corners)) {
      if (Math.abs(x - pos.x) < handleSize && Math.abs(y - pos.y) < handleSize) {
        return handle;
      }
    }
    return null;
  };

  // Mouse down handler
  const handleTLMouseDown = (e) => {
    const canvas = tlCanvasRef.current;
    if (!canvas) return;

    const { x, y } = getVideoCoords(e, canvas);

    // Stopline mode
    if (isDrawingStopline) {
      if (stopline) {
        // Check if clicking on endpoint
        const handle = hitStoplineHandle(x, y);
        if (handle) {
          setStoplineHandle(handle);
          setStartPos({ x, y });
          return;
        }

        // Check if clicking on line
        if (hitStopline(x, y)) {
          setIsMovingStopline(true);
          setStartPos({ x, y });
          return;
        }
      }

      // Start drawing new stopline
      if (!stopline) {
        setStopline({ x1: x, y1: y, x2: x, y2: y });
        setStartPos({ x, y });
      }
      return;
    }

    // TL ROI mode
    if (!isSelectingTLMode) return;

    // Check if clicking on existing ROI
    if (tlRoi) {
      const handle = hitResizeHandle(x, y);
      if (handle) {
        setResizeHandle(handle);
        setStartPos({ x, y });
        return;
      }

      if (hitTestROI(x, y)) {
        setIsMovingTL(true);
        setStartPos({ x, y });
        return;
      }
    }

    // Start drawing new ROI
    setTlRoi({ x, y, w: 0, h: 0 });
    setStartPos({ x, y });
    setIsDrawingTL(true);
  };

  // Mouse move handler
  const handleTLMouseMove = (e) => {
    if (!startPos) return;

    const canvas = tlCanvasRef.current;
    if (!canvas) return;

    const { x, y } = getVideoCoords(e, canvas);

    // Stopline mode
    if (isDrawingStopline && stopline) {
      if (stoplineHandle) {
        // Moving endpoint
        const newStopline = { ...stopline };
        if (stoplineHandle === 'p1') {
          newStopline.x1 = x;
          newStopline.y1 = y;
        } else {
          newStopline.x2 = x;
          newStopline.y2 = y;
        }
        setStopline(newStopline);
      } else if (isMovingStopline) {
        // Moving entire line
        const dx = x - startPos.x;
        const dy = y - startPos.y;
        setStopline({
          x1: stopline.x1 + dx,
          y1: stopline.y1 + dy,
          x2: stopline.x2 + dx,
          y2: stopline.y2 + dy
        });
        setStartPos({ x, y });
      } else {
        // Drawing new line
        setStopline(prev => ({ ...prev, x2: x, y2: y }));
      }
      return;
    }

    // TL ROI mode
    if (!isSelectingTLMode) return;

    if (isDrawingTL) {
      // Drawing new ROI
      const newRoi = {
        x: Math.min(startPos.x, x),
        y: Math.min(startPos.y, y),
        w: Math.abs(x - startPos.x),
        h: Math.abs(y - startPos.y)
      };
      setTlRoi(newRoi);
    } else if (isMovingTL && tlRoi) {
      // Moving ROI
      const dx = x - startPos.x;
      const dy = y - startPos.y;
      const moved = {
        ...tlRoi,
        x: Math.max(0, Math.min(tlRoi.x + dx, frameDimensions.width - tlRoi.w)),
        y: Math.max(0, Math.min(tlRoi.y + dy, frameDimensions.height - tlRoi.h))
      };
      setTlRoi(moved);
      setStartPos({ x, y });
    } else if (resizeHandle && tlRoi) {
      // Resizing ROI
      let newRoi = { ...tlRoi };

      switch (resizeHandle) {
        case 'tl': // Top-left
          newRoi.w = tlRoi.w + (tlRoi.x - x);
          newRoi.h = tlRoi.h + (tlRoi.y - y);
          newRoi.x = x;
          newRoi.y = y;
          break;
        case 'tr': // Top-right
          newRoi.w = x - tlRoi.x;
          newRoi.h = tlRoi.h + (tlRoi.y - y);
          newRoi.y = y;
          break;
        case 'bl': // Bottom-left
          newRoi.w = tlRoi.w + (tlRoi.x - x);
          newRoi.h = y - tlRoi.y;
          newRoi.x = x;
          break;
        case 'br': // Bottom-right
          newRoi.w = x - tlRoi.x;
          newRoi.h = y - tlRoi.y;
          break;
      }

      // Ensure minimum size
      if (newRoi.w > 20 && newRoi.h > 20) {
        setTlRoi(newRoi);
      }
    }
  };

  // Mouse up handler
  const handleTLMouseUp = () => {
    setIsDrawingTL(false);
    setIsMovingTL(false);
    setResizeHandle(null);
    setIsMovingStopline(false);
    setStoplineHandle(null);
    setStartPos(null);
  };

  // Save stopline to backend
  const saveStopline = async () => {
    if (!stopline) {
      safeToast.error('No stopline to save');
      return;
    }

    try {
      const stoplineData = {
        x1: Math.round(stopline.x1),
        y1: Math.round(stopline.y1),
        x2: Math.round(stopline.x2),
        y2: Math.round(stopline.y2)
      };

      console.log('📤 Saving stopline:', stoplineData);

      const response = await fetch(`${API_URL}/api/violations/stopline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camera_id: resolveCameraId(),
          stopline: stoplineData
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ Stopline saved:', result);
        setStoplineActive(true);
        setIsDrawingStopline(false);
        safeToast.success('Stopline saved!');
      } else {
        const error = await response.json();
        console.error('❌ Stopline save error:', error);
        safeToast.error(`Failed to save stopline: ${error.detail || error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving stopline:', error);
      safeToast.error('Failed to save stopline');
    }
  };

  // Delete stopline
  const deleteStopline = () => {
    setStopline(null);
    setStoplineActive(false);
    setIsDrawingStopline(false);
    safeToast.info('Stopline deleted');
  };

  // Save TL ROI and start detection
  const confirmTLROI = async () => {
    if (!tlRoi || tlRoi.w < 20 || tlRoi.h < 20) {
      safeToast.error('ROI too small! Minimum size is 20x20 pixels.');
      return;
    }

    try {
      // Send pixel coordinates (backend will convert to normalized)
      const roi_pixel = {
        x1: Math.round(tlRoi.x),
        y1: Math.round(tlRoi.y),
        x2: Math.round(tlRoi.x + tlRoi.w),
        y2: Math.round(tlRoi.y + tlRoi.h)
      };

      console.log('📤 Sending TL ROI (pixels):', roi_pixel);
      console.log('📐 Frame dimensions:', frameDimensions);

      const response = await fetch(`${API_URL}/api/traffic-light/roi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camera_id: resolveCameraId(),
          roi_pixel,
          frame_width: frameDimensions.width || 1920,
          frame_height: frameDimensions.height || 1080
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ TL ROI saved:', result);
        setTlRoiActive(true);
        setIsSelectingTLMode(false);
        safeToast.success('Traffic Light ROI saved!');
        startTrafficLightWS();
      } else {
        const error = await response.json();
        console.error('❌ Backend error:', error);
        safeToast.error(`Failed to save ROI: ${error.detail || error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving TL ROI:', error);
      safeToast.error('Failed to save Traffic Light ROI');
    }
  };

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

              {/* Pause/Resume Button */}
              {detecting && (
                <Col xs="auto">
                  <Button
                    size="sm"
                    onClick={() => setIsPaused(!isPaused)}
                    className="rounded-pill"
                    variant={isPaused ? 'success' : 'warning'}
                    style={{
                      fontWeight: 500,
                      minWidth: '80px'
                    }}
                  >
                    {isPaused ? '▶️ Resume' : '⏸️ Pause'}
                  </Button>
                </Col>
              )}

              <Col xs="auto">
                <Badge
                  bg={detecting ? (isPaused ? 'warning' : 'success') : 'secondary'}
                  className="px-3 py-2"
                  style={{
                    fontSize: '0.85rem',
                    fontWeight: 500,
                    animation: (detecting && !isPaused) ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
                  }}
                >
                  {detecting ? (isPaused ? '⏸️ PAUSED' : '● LIVE') : '○ Offline'}
                </Badge>
              </Col>

              <Col className="ms-auto">
                <div className="d-flex align-items-center gap-2 justify-content-end">
                  <Badge
                    bg={fps >= 30 ? 'success' : fps >= 20 ? 'warning' : 'danger'}
                    className="px-2 py-1"
                    style={{ fontSize: '0.85rem', fontWeight: 600 }}
                  >
                    ⚡ {fps.toFixed(1)} FPS
                  </Badge>
                  <Badge bg="info" className="px-2 py-1" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                    Frame: {frameIdx}
                  </Badge>
                </div>
              </Col>
            </Row>
          </Card.Body>
        </Card>

        {/* Settings Modal Button - Fixed bottom left */}
        <Button
          onClick={() => setShowSettingsModal(true)}
          style={{
            position: 'fixed',
            bottom: '20px',
            left: '80px',
            zIndex: 1000,
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
            boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px',
            transition: 'all 0.3s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.1)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
          }}
          title="Detection Settings"
        >
          ⚙️
        </Button>

        {/* Settings Modal */}
        <Modal
          show={showSettingsModal}
          onHide={() => setShowSettingsModal(false)}
          size="lg"
          centered
        >
          <Modal.Header closeButton>
            <Modal.Title>
              🔧 Detection Settings
              {detecting && <Badge bg="success" className="ms-2">Live Updates</Badge>}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <h6 className="mb-3">Detection Modules</h6>
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

            <hr className="my-3" />

            <h6 className="mb-3">Detection Parameters</h6>
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

            {detecting && (
              <Alert variant="info" className="mt-3 mb-0">
                <small>
                  💡 <strong>Tip:</strong> Most settings update live! Only YOLO/Tracking modules need restart.
                </small>
              </Alert>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowSettingsModal(false)}>
              Close
            </Button>
          </Modal.Footer>
        </Modal>

        {/* Light State + Violations Panel - Above video */}
        {(stoplineBounds || trafficLightState !== 'GREEN' || violations.length > 0 || tlRoiActive) && (
          <div className="mb-3" style={{
            background: 'rgba(17, 24, 39, 0.95)',
            color: '#fff',
            padding: '12px 16px',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.12)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
          }}>
            <div className="d-flex justify-content-between align-items-center flex-wrap gap-3">
              {/* Traffic Light State */}
              <div className="d-flex align-items-center gap-2">
                <span style={{ fontSize: '20px' }}>🚦</span>
                <span
                  style={{
                    display: 'inline-block',
                    padding: '6px 16px',
                    borderRadius: '6px',
                    background:
                      trafficLightState === 'RED'
                        ? '#ef4444'
                        : trafficLightState === 'GREEN'
                          ? '#22c55e'
                          : trafficLightState === 'YELLOW'
                            ? '#eab308'
                            : '#6b7280',
                    color: trafficLightState === 'YELLOW' ? '#000' : '#fff',
                    fontWeight: 700,
                    fontSize: '15px'
                  }}
                >
                  {trafficLightState}
                </span>
              </div>

              {/* TL ROI Info */}
              {tlRoiActive && tlRoi && (
                <div style={{ fontSize: '13px', color: '#d1d5db' }}>
                  <strong>TL ROI:</strong> {tlRoi.w}×{tlRoi.h}px at ({Math.round(tlRoi.x)}, {Math.round(tlRoi.y)})
                </div>
              )}

              {/* Stopline Info */}
              {stoplineBounds && (
                <div style={{ fontSize: '13px', color: '#d1d5db' }}>
                  <strong>Stopline:</strong> Y={Math.round(stoplineBounds.minY)}-{Math.round(stoplineBounds.maxY)}
                </div>
              )}

              {/* Violations */}
              <div className="d-flex align-items-center gap-2">
                <span style={{ fontSize: '18px' }}>🚨</span>
                <span style={{ fontSize: '13px', fontWeight: 600 }}>Vi Phạm:</span>
                <span
                  className="badge"
                  style={{
                    background: violations.length > 0 ? '#ef4444' : '#6b7280',
                    fontSize: '13px',
                    padding: '4px 10px'
                  }}
                >
                  {violations.length}
                </span>
              </div>
            </div>

            {/* Violations List */}
            {violations.length > 0 && (
              <div className="mt-2" style={{
                borderTop: '1px solid rgba(255,255,255,0.1)',
                paddingTop: '8px'
              }}>
                <div style={{
                  display: 'flex',
                  gap: '6px',
                  flexWrap: 'wrap',
                  maxHeight: '60px',
                  overflowY: 'auto'
                }}>
                  {violations.slice(0, 10).map((v, idx) => (
                    <span
                      key={`${v.trackId}-${v.frame}-${idx}`}
                      style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        background: 'rgba(239,68,68,0.2)',
                        border: '1px solid rgba(239,68,68,0.4)',
                        fontSize: '12px',
                        color: '#fca5a5',
                        fontWeight: 600
                      }}
                    >
                      #{v.trackId}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div style={{
          position: 'relative',
          width: '100%',
          maxWidth: '1280px',
          aspectRatio: '16/9',
          border: '2px solid #667eea',
          background: '#000',
          borderRadius: '8px',
          overflow: 'hidden'
        }}>
          {/* Main video canvas (z-index: 0) */}
          <canvas
            ref={canvasRef}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              background: '#000',
              zIndex: 0
            }}
            width={frameDimensions.width}
            height={frameDimensions.height}
          />

          {/* Traffic Light ROI Canvas (z-index: 10) */}
          <canvas
            ref={tlCanvasRef}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: (isSelectingTLMode || isDrawingStopline) ? 'auto' : 'none',
              cursor: (isSelectingTLMode || isDrawingStopline) ? 'crosshair' : 'default',
              zIndex: 10
            }}
            width={frameDimensions.width}
            height={frameDimensions.height}
            onMouseDown={handleTLMouseDown}
            onMouseMove={handleTLMouseMove}
            onMouseUp={handleTLMouseUp}
            onMouseLeave={handleTLMouseUp}
          />

          {/* Polygon ROI Overlay (z-index: 6) */}
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

          {/* TL ROI Selection Instructions */}
          {isSelectingTLMode && (
            <div
              style={{
                position: 'absolute',
                top: '10px',
                left: '50%',
                transform: 'translateX(-50%)',
                background: 'rgba(255, 215, 0, 0.95)',
                color: '#000',
                padding: '12px 24px',
                borderRadius: '8px',
                fontWeight: 'bold',
                fontSize: '14px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                zIndex: 15,
                textAlign: 'center'
              }}
            >
              {!tlRoi && '🖱️ Click & drag to draw Traffic Light ROI'}
              {tlRoi && !isDrawingTL && !isMovingTL && !resizeHandle && '✅ Drag to move • Corners to resize'}
              {isDrawingTL && '✏️ Drawing ROI...'}
              {isMovingTL && '🔄 Moving ROI...'}
              {resizeHandle && '↔️ Resizing ROI...'}
            </div>
          )}





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
              🎥 Ready for Video Detection<br />
              <small style={{ fontSize: '0.8rem', opacity: 0.7 }}>
                {videoLoaded ? 'Click Start Detection' : 'Upload video to start detection'}
                <br />Press 'D' for debug overlay
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

        {/* ==== TRAFFIC LIGHT ROI CONTROL & PREVIEW PANEL ==== */}
        <Card className="mt-4" style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          border: 'none',
          boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)'
        }}>
          <Card.Body>
            <Row className="align-items-center">
              <Col md={8}>
                <h5 className="text-white mb-3">
                  🚦 Traffic Light Detection (Separate ROI)
                </h5>

                <div className="d-flex gap-2 flex-wrap mb-3">
                  {!isSelectingTLMode && !tlRoiActive && (
                    <Button
                      onClick={() => {
                        setIsSelectingTLMode(true);
                        setTlRoi(null);
                      }}
                      variant="light"
                      size="sm"
                      className="fw-bold"
                      disabled={!videoLoaded}
                    >
                      🖱️ Draw Traffic Light ROI
                    </Button>
                  )}

                  {isSelectingTLMode && (
                    <>
                      <Button
                        onClick={confirmTLROI}
                        variant="success"
                        size="sm"
                        className="fw-bold"
                        disabled={!tlRoi || tlRoi.w < 20 || tlRoi.h < 20}
                      >
                        ✅ Confirm & Start Detection
                      </Button>

                      <Button
                        onClick={() => {
                          setIsSelectingTLMode(false);
                          setTlRoi(null);
                        }}
                        variant="danger"
                        size="sm"
                      >
                        ❌ Cancel
                      </Button>

                      {tlRoi && (
                        <Button
                          onClick={() => setTlRoi(null)}
                          variant="warning"
                          size="sm"
                        >
                          🔄 Clear ROI
                        </Button>
                      )}
                    </>
                  )}

                  {tlRoiActive && (
                    <>
                      <Button
                        onClick={() => {
                          setIsSelectingTLMode(true);
                          setTlRoiActive(false);
                          stopTrafficLightWS();
                        }}
                        variant="warning"
                        size="sm"
                      >
                        ✏️ Redraw ROI
                      </Button>

                      <Button
                        onClick={stopTrafficLightWS}
                        variant="danger"
                        size="sm"
                      >
                        ⏹️ Stop Detection
                      </Button>
                    </>
                  )}
                </div>

                {tlRoi && isSelectingTLMode && (
                  <>
                    <Alert variant="success" className="mb-2">
                      <small>
                        ✅ <strong>ROI Selected:</strong> {Math.round(tlRoi.w)}×{Math.round(tlRoi.h)} pixels
                        <br />�r Position: ({Math.round(tlRoi.x)}, {Math.round(tlRoi.y)})
                        <br />💡 Drag to move • Corners to resize • Edit values below
                      </small>
                    </Alert>

                    <div className="mb-3">
                      <Form.Label className="text-white fw-bold mb-2" style={{ fontSize: '0.9rem' }}>
                        Fine-tune ROI Coordinates (Pixels)
                      </Form.Label>
                      <Row className="g-2">
                        <Col xs={3}>
                          <Form.Control
                            type="number"
                            value={Math.round(tlRoi.x)}
                            onChange={(e) => {
                              const newX = parseInt(e.target.value) || 0;
                              setTlRoi(prev => ({ ...prev, x: Math.max(0, Math.min(newX, frameDimensions.width - prev.w)) }));
                            }}
                            size="sm"
                          />
                          <Form.Text className="text-white-50" style={{ fontSize: '0.75rem' }}>X</Form.Text>
                        </Col>
                        <Col xs={3}>
                          <Form.Control
                            type="number"
                            value={Math.round(tlRoi.y)}
                            onChange={(e) => {
                              const newY = parseInt(e.target.value) || 0;
                              setTlRoi(prev => ({ ...prev, y: Math.max(0, Math.min(newY, frameDimensions.height - prev.h)) }));
                            }}
                            size="sm"
                          />
                          <Form.Text className="text-white-50" style={{ fontSize: '0.75rem' }}>Y</Form.Text>
                        </Col>
                        <Col xs={3}>
                          <Form.Control
                            type="number"
                            value={Math.round(tlRoi.w)}
                            onChange={(e) => {
                              const newW = parseInt(e.target.value) || 20;
                              setTlRoi(prev => ({ ...prev, w: Math.max(20, Math.min(newW, frameDimensions.width - prev.x)) }));
                            }}
                            size="sm"
                          />
                          <Form.Text className="text-white-50" style={{ fontSize: '0.75rem' }}>Width</Form.Text>
                        </Col>
                        <Col xs={3}>
                          <Form.Control
                            type="number"
                            value={Math.round(tlRoi.h)}
                            onChange={(e) => {
                              const newH = parseInt(e.target.value) || 20;
                              setTlRoi(prev => ({ ...prev, h: Math.max(20, Math.min(newH, frameDimensions.height - prev.y)) }));
                            }}
                            size="sm"
                          />
                          <Form.Text className="text-white-50" style={{ fontSize: '0.75rem' }}>Height</Form.Text>
                        </Col>
                      </Row>
                    </div>
                  </>
                )}

                {!isSelectingTLMode && !tlRoiActive && (
                  <Alert variant="info" className="mb-0">
                    <small>
                      💡 <strong>How to use:</strong>
                      <br />1. Click "Draw Traffic Light ROI"
                      <br />2. Click & drag on video to draw rectangle
                      <br />3. Adjust position/size as needed
                      <br />4. Click "Confirm & Start Detection"
                    </small>
                  </Alert>
                )}
              </Col>

              <Col md={4}>
                <div className="bg-white rounded p-3">
                  <h6 className="mb-2 text-dark">Traffic Light Status</h6>

                  {trafficLightFrame ? (
                    <div className="mb-2">
                      <img
                        src={trafficLightFrame}
                        alt="Traffic Light ROI"
                        className="w-100 rounded border border-secondary"
                        style={{ maxHeight: '120px', objectFit: 'contain' }}
                      />
                    </div>
                  ) : (
                    <div
                      className="mb-2 d-flex align-items-center justify-content-center bg-secondary rounded"
                      style={{ height: '120px' }}
                    >
                      <span className="text-white">No ROI frame yet</span>
                    </div>
                  )}

                  <div className="d-flex justify-content-between align-items-center">
                    <span className="fw-bold text-dark">State:</span>
                    <span
                      className="px-3 py-1 rounded fw-bold"
                      style={{
                        background:
                          trafficLightState === "RED" ? '#ef4444' :
                            trafficLightState === "GREEN" ? '#22c55e' :
                              trafficLightState === "YELLOW" ? '#eab308' :
                                '#6b7280',
                        color: trafficLightState === "YELLOW" ? '#000' : '#fff'
                      }}
                    >
                      {trafficLightState}
                    </span>
                  </div>

                  {trafficLightConfidence !== null && (
                    <div className="mt-2 text-dark">
                      <small>
                        Confidence: <strong>{(trafficLightConfidence * 100).toFixed(1)}%</strong>
                      </small>
                    </div>
                  )}
                </div>
              </Col>
            </Row>
          </Card.Body>
        </Card>

        {/* ==== STOPLINE CONTROL PANEL ==== */}
        <Card className="mt-4" style={{
          background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
          border: 'none',
          boxShadow: '0 8px 32px rgba(239, 68, 68, 0.3)'
        }}>
          <Card.Body>
            <h5 className="text-white mb-3">
              🛑 Stopline Configuration
            </h5>

            <div className="d-flex gap-2 flex-wrap mb-3">
              {!isDrawingStopline && !stoplineActive && (
                <Button
                  onClick={() => {
                    setIsDrawingStopline(true);
                    setStopline(null);
                  }}
                  variant="light"
                  size="sm"
                  className="fw-bold"
                  disabled={!videoLoaded}
                >
                  ✏️ Draw Stopline
                </Button>
              )}

              {isDrawingStopline && (
                <>
                  <Button
                    onClick={saveStopline}
                    variant="success"
                    size="sm"
                    className="fw-bold"
                    disabled={!stopline}
                  >
                    ✅ Save Stopline
                  </Button>

                  <Button
                    onClick={() => {
                      setIsDrawingStopline(false);
                      setStopline(null);
                    }}
                    variant="danger"
                    size="sm"
                  >
                    ❌ Cancel
                  </Button>
                </>
              )}

              {stoplineActive && (
                <>
                  <Button
                    onClick={() => {
                      setIsDrawingStopline(true);
                      setStoplineActive(false);
                    }}
                    variant="warning"
                    size="sm"
                  >
                    ✏️ Edit Stopline
                  </Button>

                  <Button
                    onClick={deleteStopline}
                    variant="danger"
                    size="sm"
                  >
                    🗑️ Delete
                  </Button>
                </>
              )}
            </div>

            {stopline && isDrawingStopline && (
              <Alert variant="success" className="mb-0">
                <small>
                  ✅ <strong>Stopline:</strong> ({Math.round(stopline.x1)}, {Math.round(stopline.y1)}) → ({Math.round(stopline.x2)}, {Math.round(stopline.y2)})
                  <br />💡 Drag line to move • Drag endpoints to adjust • Click Save when ready
                </small>
              </Alert>
            )}

            {stoplineActive && stopline && !isDrawingStopline && (
              <Alert variant="success" className="mb-0">
                <small>
                  ✅ <strong>Stopline locked:</strong> ({Math.round(stopline.x1)}, {Math.round(stopline.y1)}) → ({Math.round(stopline.x2)}, {Math.round(stopline.y2)})
                  <br />📍 Midpoint: ({Math.round((stopline.x1 + stopline.x2) / 2)}, {Math.round((stopline.y1 + stopline.y2) / 2)})
                </small>
              </Alert>
            )}

            {!isDrawingStopline && !stoplineActive && (
              <Alert variant="info" className="mb-0">
                <small>
                  💡 <strong>How to use:</strong>
                  <br />1. Click "Draw Stopline"
                  <br />2. Click two points on video to draw line
                  <br />3. Adjust position as needed
                  <br />4. Click "Save Stopline"
                </small>
              </Alert>
            )}
          </Card.Body>
        </Card>


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