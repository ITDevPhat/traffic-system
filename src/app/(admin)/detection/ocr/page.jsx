'use client';
import React, { useState, useRef, useEffect } from 'react';
import { Button, Card, Form, Alert, Badge, Spinner, Row, Col } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import { ocrImage, validateImageFile, checkOCRHealth } from '@/services/ocrService';
import { toast } from 'react-toastify';

export default function OCRImagePage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [error, setError] = useState(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [ocrHealth, setOcrHealth] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const fileInputRef = useRef(null);
  const fullscreenContainerRef = useRef(null);

  // Check OCR health on mount
  useEffect(() => {
    checkOCRHealth()
      .then(health => {
        setOcrHealth(health);
        if (!health.ocr_available) {
          toast.warning('OCR service không khả dụng');
        }
      })
      .catch(err => {
        console.error('Failed to check OCR health:', err);
        toast.error('Không thể kết nối OCR service');
      });
  }, []);

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    processFile(file);
  };

  // Process file (used by both file input and drag-drop)
  const processFile = (file) => {
    const validation = validateImageFile(file);
    if (!validation.valid) {
      toast.error(validation.error);
      return;
    }

    setSelectedFile(file);
    setError(null);
    setOcrResult(null);

    // Create preview
    const reader = new FileReader();
    reader.onload = (event) => {
      setPreviewUrl(event.target.result);
    };
    reader.readAsDataURL(file);
  };

  // Drag and drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  // Click to select file
  const handleClickToUpload = () => {
    fileInputRef.current?.click();
  };

  // Process OCR
  const handleProcessOCR = async () => {
    if (!selectedFile) {
      toast.error('Vui lòng chọn ảnh');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const result = await ocrImage(selectedFile, {
        confidenceThreshold,
        drawBbox: false,
        returnPaddedImage: true  // Request padded image for small images
      });

      setOcrResult(result);
      
      // If padded image is returned, use it as preview
      if (result.padded_image?.data) {
        setPreviewUrl(result.padded_image.data);
        toast.info('Ảnh nhỏ đã được thêm padding đen để dễ nhìn hơn', { autoClose: 3000 });
      }
      
      toast.success(`Phát hiện ${result.detection_results.plates_recognized} biển số`);

      // Draw bounding boxes on canvas
      drawBoundingBoxes(result);
    } catch (err) {
      console.error('OCR error:', err);
      setError(err.message || 'Lỗi xử lý OCR');
      toast.error('Lỗi xử lý OCR');
    } finally {
      setIsProcessing(false);
    }
  };

  // Draw bounding boxes on canvas
  const drawBoundingBoxes = (result) => {
    if (!canvasRef.current || !imageRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = imageRef.current;

    // Set canvas size to match displayed image size
    const rect = img.getBoundingClientRect();
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw bounding boxes
    result.plates.forEach((plate, index) => {
      const { bbox, text, confidence } = plate;
      
      // Draw rectangle
      ctx.strokeStyle = confidence >= confidenceThreshold ? '#00ff00' : '#ff9800';
      ctx.lineWidth = 4;
      ctx.strokeRect(bbox.x1, bbox.y1, bbox.width, bbox.height);

      // Draw label background
      const label = `${text} (${(confidence * 100).toFixed(1)}%)`;
      ctx.font = 'bold 20px Arial';
      const textMetrics = ctx.measureText(label);
      const textWidth = textMetrics.width;
      const textHeight = 24;

      ctx.fillStyle = confidence >= confidenceThreshold ? '#00ff00' : '#ff9800';
      ctx.fillRect(bbox.x1, bbox.y1 - textHeight - 6, textWidth + 12, textHeight + 6);

      // Draw label text
      ctx.fillStyle = '#000';
      ctx.fillText(label, bbox.x1 + 6, bbox.y1 - 10);
    });
  };

  // Redraw when confidence threshold changes or fullscreen toggles
  useEffect(() => {
    if (ocrResult && imageRef.current) {
      // Wait for image to render at new size
      setTimeout(() => drawBoundingBoxes(ocrResult), 100);
    }
  }, [confidenceThreshold, ocrResult, isFullscreen]);

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!isFullscreen) {
      if (fullscreenContainerRef.current?.requestFullscreen) {
        fullscreenContainerRef.current.requestFullscreen();
      } else if (fullscreenContainerRef.current?.webkitRequestFullscreen) {
        fullscreenContainerRef.current.webkitRequestFullscreen();
      } else if (fullscreenContainerRef.current?.msRequestFullscreen) {
        fullscreenContainerRef.current.msRequestFullscreen();
      }
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
      }
      setIsFullscreen(false);
    }
  };

  // Listen for fullscreen changes and window resize
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isNowFullscreen = !!document.fullscreenElement;
      setIsFullscreen(isNowFullscreen);
      
      // Redraw bbox after fullscreen change
      if (ocrResult && imageRef.current) {
        setTimeout(() => drawBoundingBoxes(ocrResult), 200);
      }
    };

    const handleResize = () => {
      if (ocrResult && imageRef.current) {
        drawBoundingBoxes(ocrResult);
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);
    window.addEventListener('resize', handleResize);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('msfullscreenchange', handleFullscreenChange);
      window.removeEventListener('resize', handleResize);
    };
  }, [ocrResult]);

  // Reset
  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setOcrResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <>
      <PageTitle title="OCR - Nhận Diện Biển Số Từ Ảnh" />
      <div className="container-fluid mt-3">
        <Row>
          {/* Left Column - Upload & Controls */}
          <Col lg={4}>
            <Card className="shadow-sm mb-3">
              <Card.Header className="bg-primary text-white">
                <h5 className="mb-0">📤 Upload Ảnh</h5>
              </Card.Header>
              <Card.Body>
                {/* OCR Health Status */}
                {ocrHealth && (
                  <Alert variant={ocrHealth.ocr_available ? 'success' : 'warning'} className="py-2 mb-3">
                    <div className="d-flex align-items-center gap-2">
                      <span>{ocrHealth.ocr_available ? '✅' : '⚠️'}</span>
                      <div className="small">
                        <strong>OCR Status:</strong> {ocrHealth.status}
                        {ocrHealth.device && <div>Device: {ocrHealth.device}</div>}
                      </div>
                    </div>
                  </Alert>
                )}

                {/* Drag & Drop File Input */}
                <div
                  className={`border rounded p-4 text-center mb-3 ${isDragging ? 'border-primary bg-light' : 'border-secondary'}`}
                  style={{
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    borderStyle: 'dashed',
                    borderWidth: '2px'
                  }}
                  onDragEnter={handleDragEnter}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={handleClickToUpload}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/jpg,image/png,image/bmp,image/tiff"
                    onChange={handleFileSelect}
                    disabled={isProcessing}
                    style={{ display: 'none' }}
                  />
                  
                  {selectedFile ? (
                    <div>
                      <div style={{ fontSize: '48px', marginBottom: '8px' }}>✅</div>
                      <h6 className="text-success mb-2">{selectedFile.name}</h6>
                      <small className="text-muted">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </small>
                      <div className="mt-2">
                        <small className="text-primary">Click để chọn ảnh khác</small>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div style={{ fontSize: '48px', marginBottom: '8px' }}>📁</div>
                      <h6 className="mb-2">Kéo thả ảnh vào đây</h6>
                      <p className="text-muted mb-2">hoặc</p>
                      <Button variant="outline-primary" size="sm">
                        Chọn ảnh từ máy
                      </Button>
                      <div className="mt-2">
                        <small className="text-muted">
                          Hỗ trợ: JPG, PNG, BMP, TIFF (tối đa 10MB)
                        </small>
                      </div>
                    </div>
                  )}
                </div>

                {/* Confidence Threshold */}
                <Form.Group className="mb-3">
                  <Form.Label>
                    Ngưỡng tin cậy: <Badge bg="info">{(confidenceThreshold * 100).toFixed(0)}%</Badge>
                  </Form.Label>
                  <Form.Range
                    min={0}
                    max={1}
                    step={0.05}
                    value={confidenceThreshold}
                    onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                    disabled={isProcessing}
                  />
                  <Form.Text className="text-muted">
                    Chỉ hiển thị kết quả có độ tin cậy {'≥'} ngưỡng này
                  </Form.Text>
                </Form.Group>

                {/* Action Buttons */}
                <div className="d-grid gap-2">
                  <Button
                    variant="success"
                    size="lg"
                    onClick={handleProcessOCR}
                    disabled={!selectedFile || isProcessing}
                  >
                    {isProcessing ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        Đang xử lý...
                      </>
                    ) : (
                      <>🔍 Nhận Diện Biển Số</>
                    )}
                  </Button>
                  <Button
                    variant="outline-secondary"
                    onClick={handleReset}
                    disabled={isProcessing}
                  >
                    🔄 Reset
                  </Button>
                </div>

                {/* Error Display */}
                {error && (
                  <Alert variant="danger" className="mt-3 mb-0">
                    <strong>Lỗi:</strong> {error}
                  </Alert>
                )}
              </Card.Body>
            </Card>

            {/* Results Summary */}
            {ocrResult && (
              <Card className="shadow-sm">
                <Card.Header className="bg-success text-white">
                  <h5 className="mb-0">📊 Kết Quả</h5>
                </Card.Header>
                <Card.Body>
                  <div className="mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Biển số phát hiện:</span>
                      <Badge bg="primary">{ocrResult.detection_results.plates_detected}</Badge>
                    </div>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Biển số nhận dạng:</span>
                      <Badge bg="success">{ocrResult.detection_results.plates_recognized}</Badge>
                    </div>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Thời gian xử lý:</span>
                      <Badge bg="info">{ocrResult.processing_time.toFixed(2)}s</Badge>
                    </div>
                  </div>

                  {/* Plate List */}
                  {ocrResult.plates.length > 0 && (
                    <div>
                      <h6 className="mb-2">Danh sách biển số:</h6>
                      {ocrResult.plates
                        .filter(p => p.confidence >= confidenceThreshold)
                        .map((plate, index) => (
                          <div key={index} className="border rounded p-2 mb-2">
                            <div className="d-flex justify-content-between align-items-center">
                              <strong className="text-primary">{plate.text}</strong>
                              <Badge bg={plate.confidence >= 0.8 ? 'success' : 'warning'}>
                                {(plate.confidence * 100).toFixed(1)}%
                              </Badge>
                            </div>
                            <small className="text-muted">
                              Position: ({plate.bbox.x1}, {plate.bbox.y1}) - ({plate.bbox.x2}, {plate.bbox.y2})
                            </small>
                          </div>
                        ))}
                    </div>
                  )}
                </Card.Body>
              </Card>
            )}
          </Col>

          {/* Right Column - Image Preview */}
          <Col lg={8}>
            <Card className="shadow-sm">
              <Card.Header className="bg-info text-white d-flex justify-content-between align-items-center">
                <h5 className="mb-0">🖼️ Xem Trước Kết Quả</h5>
                {previewUrl && (
                  <Button
                    size="sm"
                    variant="light"
                    onClick={toggleFullscreen}
                    className="d-flex align-items-center gap-1"
                  >
                    {isFullscreen ? (
                      <>🗙 Thoát Fullscreen</>
                    ) : (
                      <>⛶ Fullscreen</>
                    )}
                  </Button>
                )}
              </Card.Header>
              <Card.Body className="p-0">
                <div
                  ref={fullscreenContainerRef}
                  style={{
                    position: 'relative',
                    minHeight: '400px',
                    backgroundColor: '#000',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden'
                  }}
                >
                  {!previewUrl ? (
                    <div className="text-center text-white p-5">
                      <div style={{ fontSize: '64px', marginBottom: '16px' }}>📷</div>
                      <h5>Chưa có ảnh</h5>
                      <p className="text-muted">Chọn ảnh để bắt đầu nhận diện biển số</p>
                    </div>
                  ) : (
                    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                      {/* Original Image */}
                      <img
                        ref={imageRef}
                        src={previewUrl}
                        alt="Preview"
                        style={{
                          maxWidth: '100%',
                          maxHeight: isFullscreen ? '100vh' : '600px',
                          width: '100%',
                          height: 'auto',
                          objectFit: 'contain',
                          display: 'block'
                        }}
                        onLoad={() => {
                          if (ocrResult) {
                            // Redraw bbox when image loads
                            setTimeout(() => drawBoundingBoxes(ocrResult), 100);
                          }
                        }}
                      />
                      
                      {/* Canvas Overlay for BBox */}
                      {ocrResult && (
                        <canvas
                          ref={canvasRef}
                          style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: '100%',
                            objectFit: 'contain',
                            pointerEvents: 'none'
                          }}
                        />
                      )}
                    </div>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>
    </>
  );
}
