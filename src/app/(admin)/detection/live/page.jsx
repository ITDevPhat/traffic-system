'use client';
import React, { useRef, useEffect, useState, Suspense } from 'react';
import { Button, Form, Row, Col, Card, Badge } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { useSearchParams } from 'next/navigation';
import PageTitle from '@/components/PageTitle';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function DetectionPageBinaryContent() {
  const searchParams = useSearchParams();
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);
  const isMountedRef = useRef(true);
  
  // Safe toast wrapper - only show toast if component is mounted
  // Use try-catch to prevent errors if toast is unavailable
  const safeToast = {
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
    dismiss: (id) => {
      if (!isMountedRef.current) return;
      try {
        if (toast && typeof toast.dismiss === 'function') {
          toast.dismiss(id);
        }
      } catch (e) {
        console.warn('Toast dismiss error:', e);
      }
    },
  };
  
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
  const [availableModels, setAvailableModels] = useState([]); // vehicle models full paths
  const [selectedModel, setSelectedModel] = useState('models/yolov8n.pt');
  const [autoStart, setAutoStart] = useState(false); // Flag to auto-start detection
  const [warmupProgress, setWarmupProgress] = useState(0); // Warmup progress 0-100
  const [isWarmingUp, setIsWarmingUp] = useState(false); // Warmup phase
  
  // Optimized settings defaults
  const [settings, setSettings] = useState({
    conf: 0.35,
    target_fps: 30,
    jpeg_quality: 55,
    inference_size: 480,
    encode_width: 960,
    veh_detect_hz: 25
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

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      // Dismiss all toasts when component unmounts
      toast.dismiss();
    };
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
  }, [searchParams, videoLoaded]);

  // Auto-load models on mount (non-blocking) - ưu tiên nếu có video param
  useEffect(() => {
    const videoParam = searchParams?.get('video');
    
    // If video param exists, load models immediately (no delay)
    // Otherwise, small delay for better UX
    const delay = videoParam ? 100 : 500;
    
    if (!modelLoaded && !isLoadingModels) {
      setTimeout(() => {
        if (videoParam) {
          console.log('🚀 Auto-loading models (video detected from URL)...');
          safeToast.info('Loading AI models...', { autoClose: 3000 });
        }
        loadModels();
      }, delay);
    }
  }, [searchParams]); // Run when searchParams change

  // Warmup phase: 5 seconds before starting detection
  const warmupIntervalRef = useRef(null);
  
  const startWarmup = () => {
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
  };
  
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
  }, [autoStart, videoLoaded, modelLoaded, detecting, isLoadingModels, isWarmingUp, source]);

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

  const scheduleDecode = () => {
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
  };

  // Fetch available vehicle models for selection
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/detection/models/available`);
        if (!res.ok) return;
        const data = await res.json();
        // Only get vehicle models, use simple "models/" prefix
        const vehFiles = Array.isArray(data?.models?.vehicle) ? data.models.vehicle : [];
        const full = vehFiles.map((name) => `models/${name}`);
        setAvailableModels(full);
        if (full.length > 0) {
          // Prefer vehicle_11s or first available
          const prefer = full.find(p => /vehicle.*11/i.test(p)) || full[0];
          setSelectedModel(prefer);
        }
      } catch {}
    })();
  }, []);

  const connectWebSocket = (src) => {
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

    const wsUrl = `${API_URL.replace('http', 'ws')}/api/detection/realtime?${params.toString()}`;
    console.log('🔗 Connecting to:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';  // Critical for binary frames
    
    ws.onopen = () => {
      if (!isMountedRef.current) return;
      console.log('✅ Binary WebSocket connected!');
      setConnected(true);
      setExpectBinary(false);
      safeToast.success('Connected! Waiting for frames...');
    };
    
    ws.onclose = () => {
      if (!isMountedRef.current) return;
      console.log('❌ WebSocket closed');
      setConnected(false);
      setDetecting(false);
      safeToast.info('WebSocket disconnected');
    };
    
    ws.onerror = (error) => {
      if (!isMountedRef.current) return;
      console.error('❌ WebSocket error:', error);
      setConnected(false);
      setDetecting(false);
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
              console.log(`📐 Canvas: ${newWidth}x${newHeight}`);
              console.log('📦 Info:', pkt);
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
                console.log(`🎯 Frame ${pkt.frame_idx}: ${pkt.detections.length} detections`, pkt.detections[0]);
              }
            }
            
            // Next message should be binary JPEG
            setExpectBinary(true);
          } else if (pkt.type === 'error') {
            toast.error(`Server Error: ${pkt.message}`);
            stopDetection();
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
  };

  const loadModels = async () => {
    // Skip if already loaded
    if (modelLoaded || isLoadingModels) return;
    
    setIsLoadingModels(true);
    
    // Longer timeout for model loading (GPU initialization can take time)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout for GPU init
    
    const videoParam = searchParams?.get('video');
    if (!videoParam) {
      toast.info('Loading models (GPU)...', { autoClose: 2000 });
    }
    
    try {
      const res = await fetch(`${API_URL}/api/detection/models/load`, { 
          method: 'POST',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to load models');
      }
      const data = await res.json();
      if ((data?.device || '').toLowerCase() !== 'cuda') {
        toast.error('GPU required. CUDA not detected.');
        return;
      }
      setModelLoaded(true);
      
      const videoParam = searchParams?.get('video');
      if (videoParam) {
        console.log('✅ Models loaded - ready for auto-start');
        // Don't show toast if auto-starting (to avoid spam)
      } else {
        toast.success('Models ready on GPU (CUDA)', { icon: '🚀', autoClose: 2000 });
      }
    } catch (e) {
      console.error(e);
      clearTimeout(timeoutId);
      
      if (e.name === 'AbortError') {
        toast.error('Model loading timeout! Check backend.');
      } else {
        toast.error(`Cannot load models: ${e.message}`);
      }
    } finally {
      setIsLoadingModels(false);
    }
  };

  const startDetection = async () => {
    // If models not loaded yet, try to load them first
      if (!modelLoaded) {
      if (!isLoadingModels) {
        toast.info('Loading models first...', { autoClose: 1500 });
        await loadModels();
      } else {
        toast.warning('Models still loading, please wait...');
        return;
      }
      
      // Check again after loading
      if (!modelLoaded) {
        toast.error('Failed to load models. Check GPU.');
          return;
        }
    }
    
    let currentSource = source;
    if (!videoLoaded) {
      toast.warning('Please upload a video first.');
        return;
      }
      
      setDetecting(true);
    connectWebSocket(currentSource);
    toast.info('Detection started!');
  };

  const stopDetection = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
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
    toast.info('Detection stopped.');
  };

  const handleVideoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (limit 500MB)
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
      toast.error('Video too large! Max 500MB.');
      return;
    }

    setIsUploadingVideo(true);

    // Show progress only for large files
    let toastId = null;
    if (file.size > 10 * 1024 * 1024) { // > 10MB
      toastId = toast.info(`Uploading ${file.name}... (${(file.size / 1024 / 1024).toFixed(1)}MB)`, {
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
      if (toastId) toast.dismiss(toastId);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      if (data.ok) {
        setSource(data.temp_path);
        setVideoLoaded(true);
        toast.success(`Video ready: ${file.name}`, { autoClose: 2000 });
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      clearTimeout(timeoutId);
      toast.dismiss(toastId);
      
      console.error('Upload error:', error);
      
      if (error.name === 'AbortError') {
        toast.error('Upload timeout! Try smaller video.');
      } else {
        toast.error(`Upload error: ${error.message}`);
      }
    } finally {
      setIsUploadingVideo(false);
    }
  };

  const updateSettings = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const updateModule = (module, enabled) => {
    const newModules = { ...modules, [module]: enabled };
    setModules(newModules);
    
    // If detecting and BBox toggle changed, send command to server
    if (detecting && module === 'bboxDrawing' && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send command to toggle bbox drawing
      const cmd = { command: 'toggle_bbox', enabled: enabled };
      console.log('📤 Sending command:', cmd);
      wsRef.current.send(JSON.stringify(cmd));
      toast.success(`BBox ${enabled ? 'enabled' : 'disabled'}`, { autoClose: 1000 });
    } else if (detecting && module !== 'bboxDrawing') {
      // YOLO and Tracking require full restart
      toast.info(`${module === 'yolo' ? 'YOLO' : 'Tracking'} will apply on next detection start`, {
        autoClose: 2000
      });
    }
  };

  return (
    <>
      <PageTitle title="Realtime Detection (Binary 30 FPS)" />
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
                  <Form.Label className="mb-1">Vehicle Model</Form.Label>
                  <Form.Select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={detecting}
                    style={{ minWidth: 260 }}
                  >
                    {availableModels.length === 0 && (
                      <option value={selectedModel}>Auto (yolov8n)</option>
                    )}
                    {availableModels.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </Form.Select>
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
                    bg={fps > 25 ? 'success' : fps > 15 ? 'warning' : 'danger'}
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
            <h6 className="mb-3">🔧 Detection Modules {detecting && <small className="text-muted">(restart to apply)</small>}</h6>
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
            </div>
            {detecting && (
              <small className="text-info d-block mt-2">
                💡 Tip: Stop and restart detection to apply YOLO/Tracking changes
              </small>
            )}
          </Col>
        </Row>
        <hr />
        <Row>
              <Col md={3}>
                <Form.Group className="mb-2">
                  <Form.Label>Confidence: {settings.conf.toFixed(2)}</Form.Label>
                    <Form.Range
                      value={settings.conf}
                      min={0.1}
                      max={0.9}
                      step={0.05}
                    onChange={(e) => updateSettings('conf', parseFloat(e.target.value))}
                    disabled={detecting}
                  />
                      </Form.Group>
                    </Col>
              <Col md={2}>
                <Form.Group className="mb-2">
                  <Form.Label>Target FPS: {settings.target_fps}</Form.Label>
                  <Form.Range
                    value={settings.target_fps}
                    min={15}
                    max={30}
                    step={5}
                    onChange={(e) => updateSettings('target_fps', parseInt(e.target.value))}
                    disabled={detecting}
                  />
                      </Form.Group>
                    </Col>
              <Col md={2}>
                <Form.Group className="mb-2">
                  <Form.Label>JPEG Quality: {settings.jpeg_quality}</Form.Label>
                  <Form.Range
                    value={settings.jpeg_quality}
                    min={50}
                    max={85}
                    step={5}
                    onChange={(e) => updateSettings('jpeg_quality', parseInt(e.target.value))}
                    disabled={detecting}
                  />
                </Form.Group>
                  </Col>
              <Col md={2}>
                <Form.Group className="mb-2">
                  <Form.Label>Inference Size: {settings.inference_size}</Form.Label>
                        <Form.Select 
                    value={settings.inference_size}
                    onChange={(e) => updateSettings('inference_size', parseInt(e.target.value))}
                    disabled={detecting}
                  >
                    <option value="480">480 (Faster)</option>
                    <option value="640">640 (Balanced)</option>
                    <option value="960">960 (Better)</option>
                        </Form.Select>
                      </Form.Group>
                    </Col>
              <Col md={3}>
                <Form.Group className="mb-2">
                  <Form.Label>Encode Width: {settings.encode_width}</Form.Label>
                        <Form.Select 
                    value={settings.encode_width}
                    onChange={(e) => updateSettings('encode_width', parseInt(e.target.value))}
                    disabled={detecting}
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
