'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Badge, Button, Form, Alert, Spinner } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'react-toastify';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ViolationDetail {
  violation_id: number;
  video_job_id: number;
  vehicle_id?: number;
  violation_type_code?: string;
  frame?: number;
  timestamp?: string;
  roi_type?: string;
  evidence_img?: string;
  plate?: string;
  confidence?: number;
  verification_status: string;
  verified_by?: number;
  verified_at?: string;
  created_at: string;
  
  // Joined data
  violation_type?: {
    description: string;
    fine_amount?: number;
    severity?: string;
  };
  camera?: {
    name: string;
    model?: string;
  };
  location?: {
    name: string;
    address?: string;
  };
  bboxes?: Array<{
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    label?: string;
    confidence?: number;
  }>;
}

interface ViolationType {
  violation_type_code: string;
  description: string;
  fine_amount?: number;
  severity?: string;
}

export default function ViolationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const violationId = params.id as string;
  
  const [violation, setViolation] = useState<ViolationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState<Partial<ViolationDetail>>({});
  const [saving, setSaving] = useState(false);
  
  // Image upload states
  const [plateImage, setPlateImage] = useState<string | null>(null);
  const [locationImage, setLocationImage] = useState<string | null>(null);
  const [evidenceImage, setEvidenceImage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  
  // Violation types
  const [violationTypes, setViolationTypes] = useState<ViolationType[]>([]);
  const [loadingTypes, setLoadingTypes] = useState(false);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const plateFileRef = useRef<HTMLInputElement>(null);
  const locationFileRef = useRef<HTMLInputElement>(null);
  const evidenceFileRef = useRef<HTMLInputElement>(null);

  // Load violation details
  const loadViolationDetail = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/violations/${violationId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setViolation(data);
      setEditedData(data);
    } catch (err: any) {
      console.error('Error loading violation:', err);
      setError(err.message || 'Không thể tải thông tin vi phạm');
      toast.error('Không thể tải thông tin vi phạm');
    } finally {
      setLoading(false);
    }
  };

  // Load violation types
  const loadViolationTypes = async () => {
    setLoadingTypes(true);
    try {
      const response = await fetch(`${API_URL}/api/violation-types`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setViolationTypes(data);
    } catch (err: any) {
      console.error('Error loading violation types:', err);
      toast.error('Không thể tải danh sách loại vi phạm');
    } finally {
      setLoadingTypes(false);
    }
  };

  useEffect(() => {
    if (violationId) {
      loadViolationDetail();
      loadViolationTypes();
    }
  }, [violationId]);

  // Draw bounding boxes on canvas
  const drawBoundingBoxes = () => {
    if (!canvasRef.current || !imageRef.current || !violation?.bboxes) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = imageRef.current;

    if (!ctx) return;

    // Set canvas size to match image
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw bounding boxes
    violation.bboxes.forEach((bbox) => {
      const { x1, y1, x2, y2, label, confidence } = bbox;
      
      // Choose color based on label
      let color = '#00ff00'; // Default green
      if (label?.includes('vehicle')) color = '#0066ff'; // Blue for vehicles
      if (label?.includes('plate')) color = '#ff6600'; // Orange for plates
      if (label?.includes('violation')) color = '#ff0000'; // Red for violations
      
      // Draw rectangle
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      // Draw label background
      const labelText = `${label || 'Object'} ${confidence ? `(${(confidence * 100).toFixed(1)}%)` : ''}`;
      ctx.font = 'bold 16px Arial';
      const textMetrics = ctx.measureText(labelText);
      const textWidth = textMetrics.width;
      const textHeight = 20;

      ctx.fillStyle = color;
      ctx.fillRect(x1, y1 - textHeight - 4, textWidth + 8, textHeight + 4);

      // Draw label text
      ctx.fillStyle = '#fff';
      ctx.fillText(labelText, x1 + 4, y1 - 8);
    });
  };

  // Handle image load
  const handleImageLoad = () => {
    setTimeout(() => drawBoundingBoxes(), 100);
  };

  // Handle save changes
  const handleSave = async () => {
    setSaving(true);
    
    try {
      const response = await fetch(`${API_URL}/api/violations/${violationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editedData),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const updatedViolation = await response.json();
      setViolation(updatedViolation);
      setIsEditing(false);
      toast.success('Đã cập nhật thông tin vi phạm');
    } catch (err: any) {
      console.error('Error saving violation:', err);
      toast.error('Không thể lưu thay đổi');
    } finally {
      setSaving(false);
    }
  };

  // Handle cancel edit
  const handleCancel = () => {
    setEditedData(violation || {});
    setIsEditing(false);
    setPlateImage(null);
    setLocationImage(null);
    setEvidenceImage(null);
  };

  // Handle image upload
  const handleImageUpload = async (file: File, type: 'plate' | 'location' | 'evidence') => {
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Vui lòng chọn file hình ảnh');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Kích thước file không được vượt quá 5MB');
      return;
    }

    setUploading(true);

    try {
      // Create FormData for upload
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', type);
      formData.append('violation_id', violationId);

      const response = await fetch(`${API_URL}/api/violations/${violationId}/upload-image`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Update the appropriate image state
      switch (type) {
        case 'plate':
          setPlateImage(result.url);
          break;
        case 'location':
          setLocationImage(result.url);
          break;
        case 'evidence':
          setEvidenceImage(result.url);
          setEditedData(prev => ({ ...prev, evidence_img: result.url }));
          break;
      }

      toast.success(`Đã upload ${type === 'plate' ? 'ảnh biển số' : type === 'location' ? 'ảnh địa điểm' : 'ảnh bằng chứng'} thành công`);
    } catch (err: any) {
      console.error('Upload error:', err);
      toast.error('Không thể upload hình ảnh');
    } finally {
      setUploading(false);
    }
  };

  // Handle file input change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: 'plate' | 'location' | 'evidence') => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file, type);
    }
  };

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'UNKNOWN';
    return new Date(dateString).toLocaleString('vi-VN');
  };

  // Get status badge variant
  const getStatusVariant = (status: string) => {
    const variants: Record<string, string> = {
      unverified: 'warning',
      verified: 'success',
      rejected: 'danger',
    };
    return variants[status] || 'secondary';
  };

  // Get status label
  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      unverified: 'Chưa xác minh',
      verified: 'Đã xác minh',
      rejected: 'Từ chối',
    };
    return labels[status] || status;
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="text-center">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2">Đang tải thông tin vi phạm...</p>
        </div>
      </div>
    );
  }

  if (error || !violation) {
    return (
      <>
        <PageTitle title="Lỗi" subName="Không thể tải" />
        <Alert variant="danger">
          <h5>Không thể tải thông tin vi phạm</h5>
          <p>{error}</p>
          <Button variant="outline-danger" onClick={() => router.back()}>
            Quay lại
          </Button>
        </Alert>
      </>
    );
  }

  return (
    <>
      <PageTitle title={`Chi tiết vi phạm #${violation.violation_id}`} subName="Xem chi tiết" />
      
      <div className="container-fluid">
        {/* Header Actions */}
        <Row className="mb-3">
          <Col>
            <div className="d-flex justify-content-between align-items-center">
              <Button variant="outline-secondary" onClick={() => router.back()}>
                ← Quay lại danh sách
              </Button>
              <div className="d-flex gap-2">
                {!isEditing ? (
                  <Button variant="primary" onClick={() => setIsEditing(true)}>
                    ✏️ Chỉnh sửa
                  </Button>
                ) : (
                  <>
                    <Button 
                      variant="success" 
                      onClick={handleSave}
                      disabled={saving}
                    >
                      {saving ? <Spinner animation="border" size="sm" /> : '💾'} Lưu
                    </Button>
                    <Button variant="outline-secondary" onClick={handleCancel}>
                      ❌ Hủy
                    </Button>
                  </>
                )}
              </div>
            </div>
          </Col>
        </Row>

        {/* Official Report Card - Full Width */}
        <Row className="mb-4">
          <Col>
            <Card className="shadow-lg border-danger">
              <Card.Header className="bg-danger text-white text-center py-4">
                <h2 className="mb-1 fw-bold">🚨 HỆ THỐNG GIÁM SÁT TRẬT TỰ GIAO THÔNG</h2>
                <h3 className="mb-0 fw-bold">ĐƯỜNG BỘ BẰNG HÌNH ẢNH</h3>
              </Card.Header>
              <Card.Body className="p-4">
                <Row>
                  <Col md={6}>
                    {/* Violation Type */}
                    <div className="mb-4">
                      <label className="form-label fw-bold fs-5 text-danger">Hành vi vi phạm:</label>
                      {isEditing ? (
                        <div>
                          <Form.Select
                            value={editedData.violation_type_code || ''}
                            onChange={(e) => {
                              const selectedType = violationTypes.find(vt => vt.violation_type_code === e.target.value);
                              setEditedData({
                                ...editedData, 
                                violation_type_code: e.target.value,
                                violation_type: selectedType ? {
                                  description: selectedType.description,
                                  fine_amount: selectedType.fine_amount,
                                  severity: selectedType.severity
                                } : undefined
                              });
                            }}
                            className="fs-5 mb-2"
                            disabled={loadingTypes}
                          >
                            <option value="">-- Chọn loại vi phạm --</option>
                            {violationTypes.map((vt) => (
                              <option key={vt.violation_type_code} value={vt.violation_type_code}>
                                {vt.violation_type_code} - {vt.description}
                              </option>
                            ))}
                          </Form.Select>
                          
                          {/* Show selected violation type info */}
                          {editedData.violation_type_code && (
                            <div className="fs-6 text-dark p-3 bg-light rounded">
                              {(() => {
                                const selectedType = violationTypes.find(vt => vt.violation_type_code === editedData.violation_type_code);
                                if (!selectedType) return null;
                                
                                return (
                                  <>
                                    <strong>Mức Phạt {selectedType.description}:</strong>
                                    <br />
                                    Hiện Nay Theo Nghị định 168/2024/NĐ-CP có hiệu lực từ 1/1/2025, mức phạt vượt đèn đỏ (không chấp hành hiệu lệnh đèn tín hiệu giao thông) phụ thuộc vào loại phương tiện và có gây tai nạn hay không.
                                    <br /><br />
                                    <strong>Phạt Ô Tô:</strong>
                                    <br />• Không gây tai nạn: 18.000.000 - 20.000.000 đồng, trừ 4 điểm giấy phép lái xe.
                                    <br />• Gây tai nạn: 20.000.000 - 22.000.000 đồng, trừ 10 điểm.
                                    {selectedType.fine_amount && (
                                      <>
                                        <br /><br />
                                        <strong>Mức phạt cơ bản:</strong> {selectedType.fine_amount.toLocaleString('vi-VN')} VNĐ
                                      </>
                                    )}
                                  </>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div>
                          <Badge bg="danger" className="fs-4 px-3 py-2 mb-2">
                            {violation.violation_type_code || 'UNKNOWN'}
                          </Badge>
                          {violation.violation_type?.description && (
                            <div className="fs-6 text-dark mt-2 p-3 bg-light rounded">
                              <strong>Mức Phạt {violation.violation_type.description}:</strong>
                              <br />
                              Hiện Nay Theo Nghị định 168/2024/NĐ-CP có hiệu lực từ 1/1/2025, mức phạt vượt đèn đỏ (không chấp hành hiệu lệnh đèn tín hiệu giao thông) phụ thuộc vào loại phương tiện và có gây tai nạn hay không.
                              <br /><br />
                              <strong>Phạt Ô Tô:</strong>
                              <br />• Không gây tai nạn: 18.000.000 - 20.000.000 đồng, trừ 4 điểm giấy phép lái xe.
                              <br />• Gây tai nạn: 20.000.000 - 22.000.000 đồng, trừ 10 điểm.
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Timestamp */}
                    <div className="mb-4">
                      <label className="form-label fw-bold fs-5 text-primary">Thời gian vi phạm:</label>
                      {isEditing ? (
                        <Form.Control
                          type="datetime-local"
                          value={editedData.timestamp ? new Date(editedData.timestamp).toISOString().slice(0, 16) : ''}
                          onChange={(e) => setEditedData({...editedData, timestamp: e.target.value})}
                          className="fs-5"
                        />
                      ) : (
                        <div className="fw-bold text-primary fs-4">
                          {formatDate(violation.timestamp)}
                        </div>
                      )}
                    </div>

                    {/* Location */}
                    <div className="mb-4">
                      <label className="form-label fw-bold fs-5 text-info">Địa điểm vi phạm:</label>
                      <div className="d-flex align-items-start gap-3">
                        <div className="flex-grow-1">
                          <div className="fw-bold text-info fs-4">
                            {violation.location?.name || 'UNKNOWN'}
                          </div>
                          {violation.location?.address && (
                            <div className="text-muted fs-6 mt-1">
                              {violation.location.address}
                            </div>
                          )}
                        </div>
                        
                        {/* Location Image */}
                        <div className="text-center">
                          <div 
                            className="border rounded p-2 mb-2 bg-light"
                            style={{ width: '120px', height: '80px', cursor: 'pointer' }}
                            onClick={() => locationFileRef.current?.click()}
                          >
                            {locationImage ? (
                              <img 
                                src={locationImage} 
                                alt="Location" 
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                className="rounded"
                              />
                            ) : (
                              <div className="d-flex align-items-center justify-content-center h-100">
                                <div className="text-center">
                                  <i className="ri-map-pin-add-line fs-4 text-muted"></i>
                                  <div className="small text-muted">Ảnh địa điểm</div>
                                </div>
                              </div>
                            )}
                          </div>
                          {isEditing && (
                            <Button 
                              size="sm" 
                              variant="outline-info"
                              onClick={() => locationFileRef.current?.click()}
                              disabled={uploading}
                            >
                              {uploading ? <Spinner size="sm" /> : '📍'} Upload
                            </Button>
                          )}
                          <input
                            ref={locationFileRef}
                            type="file"
                            accept="image/*"
                            style={{ display: 'none' }}
                            onChange={(e) => handleFileChange(e, 'location')}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Direction */}
                    <div className="mb-4">
                      <label className="form-label fw-bold fs-5 text-warning">Hướng/ Chiều:</label>
                      {isEditing ? (
                        <Form.Control
                          type="text"
                          value={editedData.roi_type || ''}
                          onChange={(e) => setEditedData({...editedData, roi_type: e.target.value})}
                          placeholder="Nhập hướng/chiều..."
                          className="fs-5"
                        />
                      ) : (
                        <div className="fw-bold fs-4 text-warning">
                          {violation.roi_type || 'Mặc định Ngã Tư'}
                        </div>
                      )}
                    </div>
                  </Col>

                  <Col md={6}>
                    {/* License Plate */}
                    <div className="mb-4">
                      <label className="form-label fw-bold fs-5 text-dark">Biển số xe vi phạm:</label>
                      <div className="d-flex align-items-start gap-3">
                        <div className="flex-grow-1">
                          {isEditing ? (
                            <Form.Control
                              type="text"
                              value={editedData.plate || ''}
                              onChange={(e) => setEditedData({...editedData, plate: e.target.value})}
                              placeholder="Nhập biển số xe..."
                              className="text-uppercase fs-5"
                            />
                          ) : (
                            <div>
                              <Badge bg="dark" className="fs-3 px-4 py-3 mb-2">
                                {violation.plate || 'UNKNOWN'}
                              </Badge>
                              {violation.confidence && (
                                <div className="text-muted fs-6 mt-2">
                                  <strong>Độ tin cậy OCR:</strong> {(violation.confidence * 100).toFixed(1)}%
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                        
                        {/* Plate Image */}
                        <div className="text-center">
                          <div 
                            className="border rounded p-2 mb-2 bg-light"
                            style={{ width: '120px', height: '60px', cursor: 'pointer' }}
                            onClick={() => plateFileRef.current?.click()}
                          >
                            {plateImage ? (
                              <img 
                                src={plateImage} 
                                alt="Plate" 
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                className="rounded"
                              />
                            ) : (
                              <div className="d-flex align-items-center justify-content-center h-100">
                                <div className="text-center">
                                  <i className="ri-image-add-line fs-4 text-muted"></i>
                                  <div className="small text-muted">Ảnh biển số</div>
                                </div>
                              </div>
                            )}
                          </div>
                          {isEditing && (
                            <Button 
                              size="sm" 
                              variant="outline-primary"
                              onClick={() => plateFileRef.current?.click()}
                              disabled={uploading}
                            >
                              {uploading ? <Spinner size="sm" /> : '📷'} Upload
                            </Button>
                          )}
                          <input
                            ref={plateFileRef}
                            type="file"
                            accept="image/*"
                            style={{ display: 'none' }}
                            onChange={(e) => handleFileChange(e, 'plate')}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Operating Unit */}
                    <div className="mb-4">
                      <label className="form-label fw-bold fs-5 text-success">Đơn vị vận hành:</label>
                      <div className="fw-bold text-success fs-4">
                        ADMIN (mặc định)
                      </div>
                    </div>

                    {/* Verification Status */}
                    <div className="mb-4">
                      <label className="form-label fw-bold fs-5">Trạng thái xác minh:</label>
                      {isEditing ? (
                        <Form.Select
                          value={editedData.verification_status || ''}
                          onChange={(e) => setEditedData({...editedData, verification_status: e.target.value})}
                          className="fs-5"
                        >
                          <option value="unverified">Chưa xác minh</option>
                          <option value="verified">Đã xác minh</option>
                          <option value="rejected">Từ chối</option>
                        </Form.Select>
                      ) : (
                        <Badge bg={getStatusVariant(violation.verification_status)} className="fs-4 px-3 py-2">
                          {getStatusLabel(violation.verification_status)}
                        </Badge>
                      )}
                    </div>

                    {/* Fine Amount */}
                    {violation.violation_type?.fine_amount && (
                      <div className="mb-4">
                        <label className="form-label fw-bold fs-5 text-danger">Mức phạt:</label>
                        <div className="fw-bold text-danger fs-2">
                          {violation.violation_type.fine_amount.toLocaleString('vi-VN')} VNĐ
                        </div>
                      </div>
                    )}
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Technical Details */}
        <Row className="mb-4">
          <Col>
            <Card className="shadow-sm">
              <Card.Header className="bg-info text-white">
                <h5 className="mb-0">📊 Thông tin kỹ thuật</h5>
              </Card.Header>
              <Card.Body>
                <Row className="g-3">
                  <Col md={2}>
                    <small className="text-muted">ID Vi phạm:</small>
                    <div className="fw-bold fs-6">#{violation.violation_id}</div>
                  </Col>
                  <Col md={2}>
                    <small className="text-muted">Video Job:</small>
                    <div className="fw-bold fs-6">#{violation.video_job_id}</div>
                  </Col>
                  <Col md={2}>
                    <small className="text-muted">Frame:</small>
                    <div className="fw-bold fs-6">{violation.frame || 'N/A'}</div>
                  </Col>
                  <Col md={2}>
                    <small className="text-muted">Camera:</small>
                    <div className="fw-bold fs-6">{violation.camera?.name || 'N/A'}</div>
                  </Col>
                  <Col md={2}>
                    <small className="text-muted">Tạo lúc:</small>
                    <div className="fw-bold fs-6">{formatDate(violation.created_at)}</div>
                  </Col>
                  {violation.verified_at && (
                    <Col md={2}>
                      <small className="text-muted">Xác minh lúc:</small>
                      <div className="fw-bold fs-6">{formatDate(violation.verified_at)}</div>
                    </Col>
                  )}
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Evidence Image - Bottom */}
        <Row>
          <Col>
            <Card className="shadow-lg">
              <Card.Header className="bg-danger text-white d-flex justify-content-between align-items-center">
                <h4 className="mb-0">📸 Các hình bằng chứng vi phạm</h4>
                {isEditing && (
                  <Button 
                    variant="light" 
                    size="sm"
                    onClick={() => evidenceFileRef.current?.click()}
                    disabled={uploading}
                  >
                    {uploading ? <Spinner size="sm" /> : '📤'} Upload Ảnh Mới
                  </Button>
                )}
              </Card.Header>
              <Card.Body className="p-0">
                <div 
                  style={{
                    position: 'relative',
                    backgroundColor: '#000',
                    minHeight: '500px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {(evidenceImage || violation.evidence_img) ? (
                    <div style={{ position: 'relative', width: '100%' }}>
                      <img
                        ref={imageRef}
                        src={evidenceImage || `${API_URL}${violation.evidence_img}`}
                        alt="Evidence"
                        style={{
                          maxWidth: '100%',
                          maxHeight: '700px',
                          width: '100%',
                          height: 'auto',
                          objectFit: 'contain',
                          display: 'block'
                        }}
                        onLoad={handleImageLoad}
                        onError={(e) => {
                          console.error('Image load error:', e);
                          toast.error('Không thể tải hình ảnh bằng chứng');
                        }}
                      />
                      
                      {/* Canvas overlay for bounding boxes */}
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
                    </div>
                  ) : (
                    <div 
                      className="text-center text-white p-5"
                      style={{ cursor: isEditing ? 'pointer' : 'default' }}
                      onClick={isEditing ? () => evidenceFileRef.current?.click() : undefined}
                    >
                      <div style={{ fontSize: '64px', marginBottom: '16px' }}>📷</div>
                      <h5>Không có hình ảnh bằng chứng</h5>
                      <p className="text-muted">
                        {isEditing ? 'Nhấn để upload hình ảnh bằng chứng' : 'Chưa có hình ảnh được lưu cho vi phạm này'}
                      </p>
                      {isEditing && (
                        <Button variant="outline-light" className="mt-3">
                          📤 Upload Hình Ảnh
                        </Button>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Hidden file input */}
                <input
                  ref={evidenceFileRef}
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={(e) => handleFileChange(e, 'evidence')}
                />
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>
    </>
  );
}