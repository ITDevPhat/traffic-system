'use client';
import React, { useState, useRef, useCallback } from 'react';
import { Button, Form, Row, Col, Card, Badge, Alert, Spinner, Table } from 'react-bootstrap';
import { toast } from 'react-toastify';
import PageTitle from '@/components/PageTitle';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function OCRPage() {
  const fileInputRef = useRef(null);
  const canvasRef = useRef(null);
  
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ocrResults, setOcrResults] = useState(null);
  const [ocrHealth, setOcrHealth] = useState(null);
  const [settings, setSettings] = useState({
    confidence_threshold: 0.60,
    draw_bbox: true
  });

  // Check OCR health on mount
  React.useEffect(() => {
    checkOCRHealth();
  }, []);

  const checkOCRHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/api/ocr/health`);
      const data = await response.json();
      setOcrHealth(data);
      
      if (!data.ocr_available) {
        toast.error('OCR service not available!');
      }
    } catch (error) {
      console.error('OCR health check failed:', error);
      setOcrHealth({ status: 'error', ocr_available: false, error: error.message });
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file (JPG, PNG, etc.)');
      return;
    }

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      toast.error('Image too large! Max 10MB allowed.');
      return;
    }

    setSelectedFile(file);
    
    // Create preview URL
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    
    // Clear previous results
    setOcrResults(null);
    
    toast.success(`Image selected: ${file.name}`);
  };

  const processImage = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    if (!ocrHealth?.ocr_available) {
      toast.error('OCR service is not available');
      return;
    }

    setIsProcessing(true);
    
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('confidence_threshold', settings.confidence_threshold);
      formData.append('draw_bbox', settings.draw_bbox);

      const response = await fetch(`${API_URL}/api/ocr/image`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      setOcrResults(result);

      if (result.success && result.plates.length > 0) {
        const plateTexts = result.plates.map(p => p.text).join(', ');
        toast.success(`Found ${result.plates.length} license plate(s): ${plateTexts}`);
      } else {
        toast.warning('No license plates detected in the image');
      }

      // Draw results on canvas if bbox enabled
      if (settings.draw_bbox && result.plates.length > 0) {
        drawBoundingBoxes(result);
      }

    } catch (error) {
      console.error('OCR processing error:', error);
      toast.error(`OCR failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const drawBoundingBoxes = useCallback((result) => {
    const canvas = canvasRef.current;
    const img = new Image();
    
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      
      // Draw bounding boxes
      result.plates.forEach((plate, index) => {
        const { bbox, text, confidence } = plate;
        
        // Box color based on confidence
        const color = confidence >= 0.8 ? '#00ff00' : confidence >= 0.6 ? '#ffff00' : '#ff8800';
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(bbox.x1, bbox.y1, bbox.width, bbox.height);
        
        // Label background
        const label = `${text} (${(confidence * 100).toFixed(1)}%)`;
        const labelWidth = ctx.measureText(label).width + 10;
        
        ctx.fillStyle = color;
        ctx.fillRect(bbox.x1, bbox.y1 - 25, labelWidth, 20);
        
        // Label text
        ctx.fillStyle = '#000';
        ctx.font = '14px Arial';
        ctx.fillText(label, bbox.x1 + 5, bbox.y1 - 8);
      });
    };
    
    img.src = previewUrl;
  }, [previewUrl]);

  const clearImage = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setOcrResults(null);
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    
    toast.info('Image cleared');
  };

  const downloadResults = () => {
    if (!ocrResults) return;
    
    const dataStr = JSON.stringify(ocrResults, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `ocr_results_${Date.now()}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
    toast.success('Results downloaded!');
  };

  return (
    <>
      <PageTitle title="License Plate OCR" />
      
      <div className="container-fluid mt-3">
        {/* OCR Health Status */}
        <Card className="mb-3">
          <Card.Body>
            <Row className="align-items-center">
              <Col>
                <h6 className="mb-0">🔍 OCR Service Status</h6>
              </Col>
              <Col xs="auto">
                <Badge 
                  bg={ocrHealth?.ocr_available ? 'success' : 'danger'}
                  className="px-3 py-2"
                >
                  {ocrHealth?.ocr_available ? '✅ Available' : '❌ Unavailable'}
                </Badge>
              </Col>
              <Col xs="auto">
                <Button 
                  size="sm" 
                  variant="outline-secondary"
                  onClick={checkOCRHealth}
                >
                  🔄 Refresh
                </Button>
              </Col>
            </Row>
            
            {ocrHealth && (
              <Row className="mt-2">
                <Col>
                  <small className="text-muted">
                    Device: {ocrHealth.device || 'unknown'} | 
                    Model: {ocrHealth.model_type || 'unknown'} | 
                    Status: {ocrHealth.status}
                  </small>
                </Col>
              </Row>
            )}
          </Card.Body>
        </Card>

        {/* Upload and Settings */}
        <Card className="mb-3">
          <Card.Body>
            <Row className="align-items-center g-3">
              <Col md={4}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
                <Button 
                  variant={selectedFile ? 'success' : 'primary'}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isProcessing}
                  className="w-100"
                >
                  📁 {selectedFile ? '✅ Image Selected' : 'Choose Image'}
                </Button>
              </Col>
              
              <Col md={3}>
                <Form.Group>
                  <Form.Label className="mb-1">
                    <strong>Confidence: {settings.confidence_threshold}</strong>
                  </Form.Label>
                  <Form.Range
                    value={settings.confidence_threshold}
                    min={0.1}
                    max={0.95}
                    step={0.05}
                    onChange={(e) => setSettings(prev => ({ 
                      ...prev, 
                      confidence_threshold: parseFloat(e.target.value) 
                    }))}
                    disabled={isProcessing}
                  />
                </Form.Group>
              </Col>
              
              <Col md={2}>
                <Form.Check
                  type="switch"
                  id="draw-bbox-toggle"
                  label="Draw BBox"
                  checked={settings.draw_bbox}
                  onChange={(e) => setSettings(prev => ({ 
                    ...prev, 
                    draw_bbox: e.target.checked 
                  }))}
                  disabled={isProcessing}
                />
              </Col>
              
              <Col md={2}>
                <Button 
                  variant="primary"
                  onClick={processImage}
                  disabled={!selectedFile || isProcessing || !ocrHealth?.ocr_available}
                  className="w-100"
                >
                  {isProcessing ? (
                    <>
                      <Spinner size="sm" className="me-2" />
                      Processing...
                    </>
                  ) : (
                    '🔍 Detect Plates'
                  )}
                </Button>
              </Col>
              
              <Col md={1}>
                <Button 
                  variant="outline-danger"
                  onClick={clearImage}
                  disabled={!selectedFile || isProcessing}
                  className="w-100"
                >
                  🗑️
                </Button>
              </Col>
            </Row>
          </Card.Body>
        </Card>

        <Row>
          {/* Image Preview */}
          <Col lg={8}>
            <Card>
              <Card.Header>
                <h6 className="mb-0">📸 Image Preview</h6>
              </Card.Header>
              <Card.Body>
                {previewUrl ? (
                  <div style={{ position: 'relative', textAlign: 'center' }}>
                    <img 
                      src={previewUrl} 
                      alt="Preview" 
                      style={{ 
                        maxWidth: '100%', 
                        maxHeight: '600px',
                        display: settings.draw_bbox && ocrResults ? 'none' : 'block'
                      }} 
                    />
                    <canvas 
                      ref={canvasRef}
                      style={{ 
                        maxWidth: '100%', 
                        maxHeight: '600px',
                        display: settings.draw_bbox && ocrResults ? 'block' : 'none',
                        border: '1px solid #ddd'
                      }}
                    />
                  </div>
                ) : (
                  <div 
                    className="d-flex align-items-center justify-content-center"
                    style={{ height: '300px', backgroundColor: '#f8f9fa', border: '2px dashed #dee2e6' }}
                  >
                    <div className="text-center text-muted">
                      <div style={{ fontSize: '3rem' }}>📷</div>
                      <p className="mb-0">Select an image to preview</p>
                      <small>Supported: JPG, PNG, BMP, TIFF (max 10MB)</small>
                    </div>
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>

          {/* Results Panel */}
          <Col lg={4}>
            <Card>
              <Card.Header className="d-flex justify-content-between align-items-center">
                <h6 className="mb-0">🎯 Detection Results</h6>
                {ocrResults && (
                  <Button 
                    size="sm" 
                    variant="outline-primary"
                    onClick={downloadResults}
                  >
                    💾 Download
                  </Button>
                )}
              </Card.Header>
              <Card.Body>
                {!ocrResults ? (
                  <div className="text-center text-muted py-4">
                    <div style={{ fontSize: '2rem' }}>🔍</div>
                    <p className="mb-0">No results yet</p>
                    <small>Upload and process an image</small>
                  </div>
                ) : (
                  <>
                    {/* Summary */}
                    <div className="mb-3">
                      <Badge bg="info" className="me-2">
                        📊 {ocrResults.detection_results.plates_detected} detected
                      </Badge>
                      <Badge bg="success">
                        ✅ {ocrResults.detection_results.plates_recognized} recognized
                      </Badge>
                    </div>

                    {/* Processing Info */}
                    <div className="mb-3 p-2 bg-light rounded">
                      <small>
                        <strong>Processing Time:</strong> {(ocrResults.processing_time * 1000).toFixed(1)}ms<br/>
                        <strong>Total Time:</strong> {(ocrResults.total_time * 1000).toFixed(1)}ms<br/>
                        <strong>Image Size:</strong> {ocrResults.image_info.processed_size.width}x{ocrResults.image_info.processed_size.height}
                      </small>
                    </div>

                    {/* License Plates */}
                    {ocrResults.plates.length > 0 ? (
                      <div>
                        <h6>🚗 License Plates:</h6>
                        {ocrResults.plates.map((plate, index) => (
                          <Card key={index} className="mb-2" size="sm">
                            <Card.Body className="p-2">
                              <div className="d-flex justify-content-between align-items-center">
                                <div>
                                  <strong style={{ fontSize: '1.1rem', color: '#0066cc' }}>
                                    {plate.text}
                                  </strong>
                                  <br/>
                                  <Badge 
                                    bg={plate.confidence >= 0.8 ? 'success' : 
                                        plate.confidence >= 0.6 ? 'warning' : 'danger'}
                                    className="mt-1"
                                  >
                                    {(plate.confidence * 100).toFixed(1)}%
                                  </Badge>
                                </div>
                                <div className="text-end">
                                  <small className="text-muted">
                                    Size: {Math.round(plate.bbox.width)}x{Math.round(plate.bbox.height)}<br/>
                                    Pos: ({Math.round(plate.bbox.x1)}, {Math.round(plate.bbox.y1)})
                                  </small>
                                </div>
                              </div>
                            </Card.Body>
                          </Card>
                        ))}
                      </div>
                    ) : (
                      <Alert variant="warning" className="mb-0">
                        <small>
                          <strong>No license plates found</strong><br/>
                          Try adjusting the confidence threshold or use a clearer image.
                        </small>
                      </Alert>
                    )}
                  </>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>
    </>
  );
}