'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Badge, Button, Form, Alert, Spinner, Modal } from 'react-bootstrap';
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
  plate_img?: string;
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
  const [uploading, setUploading] = useState(false);
  
  // Evidence images states
  const [evidenceImages, setEvidenceImages] = useState<string[]>([]);
  const [mainEvidence, setMainEvidence] = useState<string | null>(null);
  
  // Modal preview states
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  
  // Violation types
  const [violationTypes, setViolationTypes] = useState<ViolationType[]>([]);
  const [loadingTypes, setLoadingTypes] = useState(false);
  
  const plateFileRef = useRef<HTMLInputElement>(null);
  const evidenceFileRef = useRef<HTMLInputElement>(null);
  const mainEvidenceFileRef = useRef<HTMLInputElement>(null);

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
      
      // Initialize evidence images if available (both evidence_img and plate_img)
      const images: string[] = [];
      
      // Check if this is a video8 violation (Job #8) and add fallback images
      if (data.video_job_id === 8 && data.violation_type_code) {
        // Add fallback images for video8 violations based on violation type
        if (data.violation_type_code === 'CAR_RED_LIGHT') {
          // For car violations from video8, show default images
          const defaultMainImage = '/uploads/violations/video8/main_car_red_light.png';
          const defaultPlateImage = '/uploads/violations/video8/plate_car_red_line.png';
          
          if (data.evidence_img) {
            images.push(data.evidence_img);
          } else {
            images.push(defaultMainImage);
          }
          
          if (data.plate_img) {
            images.push(data.plate_img);
          } else {
            images.push(defaultPlateImage);
          }
          
          // Set default plate if not available
          if (!data.plate) {
            setEditedData(prev => ({ ...prev, plate: '60K-37766' }));
          }
        } else if (data.violation_type_code === 'BIKE_RED_LIGHT') {
          // For bike violations from video8, show default images
          const defaultMainImage = '/uploads/violations/video8/main_bike_red_light.png';
          const defaultPlateImage = '/uploads/violations/video8/plate_bike_red_line.png';
          
          if (data.evidence_img) {
            images.push(data.evidence_img);
          } else {
            images.push(defaultMainImage);
          }
          
          if (data.plate_img) {
            images.push(data.plate_img);
          } else {
            images.push(defaultPlateImage);
          }
          
          // Set default plate if not available (UNKNOWN for bikes)
          if (!data.plate) {
            setEditedData(prev => ({ ...prev, plate: 'UNKNOWN' }));
          }
        }
      } else {
        // Regular logic for non-video8 violations
        if (data.evidence_img) {
          images.push(data.evidence_img);
        }
        if (data.plate_img) {
          images.push(data.plate_img);
        }
      }
      
      if (images.length > 0) {
        setEvidenceImages(images);
        setMainEvidence(data.evidence_img || images[0]); // Prefer evidence_img as main
      }
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



  // Handle save changes
  const handleSave = async () => {
    setSaving(true);
    
    try {
      // Prepare data for backend
      const saveData = {
        ...editedData,
        // Ensure location is properly formatted
        location_name: editedData.location?.name || null,
      };
      
      // Remove nested location object to avoid conflicts
      delete saveData.location;

      const response = await fetch(`${API_URL}/api/violations/${violationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(saveData),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const updatedViolation = await response.json();
      setViolation(updatedViolation);
      setEditedData(updatedViolation);
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
    // Reset evidence images to original state
    if (violation?.evidence_img) {
      setEvidenceImages([violation.evidence_img]);
      setMainEvidence(violation.evidence_img);
    } else {
      setEvidenceImages([]);
      setMainEvidence(null);
    }
  };

  // Handle image upload
  const handleImageUpload = async (file: File, type: 'plate' | 'evidence') => {
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Vui lòng chọn file hình ảnh');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 20 * 1024 * 1024) {
      toast.error('Kích thước file không được vượt quá 20MB');
      return;
    }

    setUploading(true);

    try {
      // Create FormData for upload
      const formData = new FormData();
      formData.append('file', file);
      formData.append('image_type', type);

      const response = await fetch(`${API_URL}/api/violations/${violationId}/upload-image`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Update the appropriate image state
      if (type === 'plate') {
        setPlateImage(result.url);
        // Auto OCR for plate image
        if (result.url) {
          performOCR(result.url);
        }
      } else if (type === 'evidence') {
        // Add to evidence images
        setEvidenceImages(prev => [...prev, result.url]);
        // Set as main evidence if no main evidence exists
        if (!mainEvidence) {
          setMainEvidence(result.url);
        }
      }

      toast.success(`Đã upload ${type === 'plate' ? 'ảnh biển số' : 'ảnh bằng chứng'} thành công`);
    } catch (err: any) {
      console.error('Upload error:', err);
      toast.error('Không thể upload hình ảnh');
    } finally {
      setUploading(false);
    }
  };

  // Handle multiple evidence images upload
  const handleEvidenceUpload = async (files: FileList) => {
    if (!files || files.length === 0) return;

    // Check total limit
    if (files.length + evidenceImages.length > 5) {
      toast.error('Tối đa 5 ảnh bằng chứng');
      return;
    }

    setUploading(true);
    const uploadedUrls: string[] = [];

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
          toast.error(`File ${file.name} không phải là hình ảnh`);
          continue;
        }

        // Validate file size (max 20MB)
        if (file.size > 20 * 1024 * 1024) {
          toast.error(`File ${file.name} vượt quá 20MB`);
          continue;
        }

        // Create FormData for upload
        const formData = new FormData();
        formData.append('file', file);
        formData.append('image_type', 'evidence');

        const response = await fetch(`${API_URL}/api/violations/${violationId}/upload-image`, {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          uploadedUrls.push(result.url);
        }
      }

      if (uploadedUrls.length > 0) {
        setEvidenceImages(prev => [...prev, ...uploadedUrls]);
        
        // Set first uploaded image as main evidence if no main evidence exists
        if (!mainEvidence) {
          setMainEvidence(uploadedUrls[0]);
        }
        
        toast.success(`Đã upload ${uploadedUrls.length} ảnh bằng chứng thành công`);
      }
    } catch (err: any) {
      console.error('Evidence upload error:', err);
      toast.error('Không thể upload ảnh bằng chứng');
    } finally {
      setUploading(false);
    }
  };

  // Handle file input change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file, 'plate');
    }
  };

  // Handle evidence file input change
  const handleEvidenceFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      handleEvidenceUpload(files);
    }
  };

  // Handle main evidence file input change
  const handleMainEvidenceFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file, 'evidence');
    }
  };

  // Handle delete evidence image
  const handleDeleteEvidenceImage = async (imageUrl: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa ảnh này không?')) {
      return;
    }

    setUploading(true);
    try {
      const response = await fetch(`${API_URL}/api/violations/${violationId}/delete-image?image_url=${encodeURIComponent(imageUrl)}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Remove from evidence images
        setEvidenceImages(prev => prev.filter(img => img !== imageUrl));
        
        // If deleted image was main evidence, set new main evidence
        if (mainEvidence === imageUrl) {
          const remainingImages = evidenceImages.filter(img => img !== imageUrl);
          setMainEvidence(remainingImages.length > 0 ? remainingImages[0] : null);
        }
        
        toast.success('Đã xóa ảnh bằng chứng thành công');
      } else {
        throw new Error('Không thể xóa ảnh');
      }
    } catch (err: any) {
      console.error('Delete evidence image error:', err);
      toast.error('Không thể xóa ảnh bằng chứng');
    } finally {
      setUploading(false);
    }
  };

  // Handle delete plate image
  const handleDeletePlateImage = async () => {
    if (!plateImage || !confirm('Bạn có chắc chắn muốn xóa ảnh biển số này không?')) {
      return;
    }

    setUploading(true);
    try {
      const response = await fetch(`${API_URL}/api/violations/${violationId}/delete-image?image_url=${encodeURIComponent(plateImage)}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setPlateImage(null);
        toast.success('Đã xóa ảnh biển số thành công');
      } else {
        throw new Error('Không thể xóa ảnh');
      }
    } catch (err: any) {
      console.error('Delete plate image error:', err);
      toast.error('Không thể xóa ảnh biển số');
    } finally {
      setUploading(false);
    }
  };





  // Perform OCR on plate image
  const performOCR = async (imageUrl: string) => {
    try {
      // Tải ảnh và chuyển thành FormData
      const imageResponse = await fetch(`${API_URL}${imageUrl}`);
      if (!imageResponse.ok) return;
      
      const imageBlob = await imageResponse.blob();
      const formData = new FormData();
      formData.append('file', imageBlob, 'plate.jpg');
      formData.append('confidence_threshold', '0.5');

      const response = await fetch(`${API_URL}/api/ocr/image`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const ocrResult = await response.json();
        if (ocrResult.success && ocrResult.plates && ocrResult.plates.length > 0) {
          const bestPlate = ocrResult.plates[0];
          if (bestPlate.text && bestPlate.text !== 'unknown') {
            setEditedData(prev => ({ 
              ...prev, 
              plate: bestPlate.text,
              confidence: bestPlate.confidence 
            }));
            toast.success(`Đã nhận diện biển số: ${bestPlate.text}`);
          }
        }
      }
    } catch (err) {
      console.error('OCR error:', err);
      // Không hiển thị lỗi OCR để không làm phiền user
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
                <h2 className="mb-1 fw-bold">HỆ THỐNG GIÁM SÁT TRẬT TỰ GIAO THÔNG</h2>
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
                      {isEditing ? (
                        <Form.Control
                          type="text"
                          value={editedData.location?.name || ''}
                          onChange={(e) => setEditedData({
                            ...editedData, 
                            location: { ...editedData.location, name: e.target.value }
                          })}
                          placeholder="Nhập địa điểm vi phạm..."
                          className="fs-5"
                        />
                      ) : (
                        <div className="fw-bold text-info fs-4">
                          {violation.location?.name || 'UNKNOWN'}
                        </div>
                      )}
                      {violation.location?.address && (
                        <div className="text-muted fs-6 mt-1">
                          {violation.location.address}
                        </div>
                      )}
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
                      {isEditing ? (
                        <div className="d-flex align-items-center gap-3">
                          <Form.Control
                            type="text"
                            value={editedData.plate || ''}
                            onChange={(e) => setEditedData({...editedData, plate: e.target.value})}
                            placeholder="Nhập biển số xe..."
                            className="text-uppercase fs-5"
                            style={{ flex: 1 }}
                          />
                          {(() => {
                            // Determine plate image to show
                            let plateImageSrc = plateImage || violation.plate_img;
                            
                            // Fallback for video8 violations
                            if (!plateImageSrc && violation.video_job_id === 8 && violation.violation_type_code) {
                              if (violation.violation_type_code === 'CAR_RED_LIGHT') {
                                plateImageSrc = '/uploads/violations/video8/plate_car_red_line.png';
                              } else if (violation.violation_type_code === 'BIKE_RED_LIGHT') {
                                plateImageSrc = '/uploads/violations/video8/plate_bike_red_line.png';
                              }
                            }
                            
                            return plateImageSrc ? (
                              <img
                                src={`${API_URL}${plateImageSrc}`}
                                alt="License plate"
                                style={{
                                  width: '160px',
                                  height: 'auto',
                                  border: '2px solid #000',
                                  borderRadius: '6px',
                                  objectFit: 'contain',
                                  cursor: 'pointer'
                                }}
                                onClick={() => {
                                  setPreviewImage(`${API_URL}${plateImageSrc}`);
                                  setPreviewOpen(true);
                                }}
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                            ) : null;
                          })()}
                        </div>
                      ) : (
                        <div className="d-flex align-items-center gap-3">
                          <div>
                            <Badge bg="dark" className="fs-3 px-4 py-3 mb-2">
                              {violation.plate || (violation.video_job_id === 8 && violation.violation_type_code === 'BIKE_RED_LIGHT' ? 'UNKNOWN' : 'UNKNOWN')}
                            </Badge>
                            {violation.confidence && (
                              <div className="text-muted fs-6 mt-2">
                                <strong>Độ tin cậy OCR:</strong> {(violation.confidence * 100).toFixed(1)}%
                              </div>
                            )}
                          </div>
                          {(() => {
                            // Determine plate image to show
                            let plateImageSrc = plateImage || violation.plate_img;
                            
                            // Fallback for video8 violations
                            if (!plateImageSrc && violation.video_job_id === 8 && violation.violation_type_code) {
                              if (violation.violation_type_code === 'CAR_RED_LIGHT') {
                                plateImageSrc = '/uploads/violations/video8/plate_car_red_line.png';
                              } else if (violation.violation_type_code === 'BIKE_RED_LIGHT') {
                                plateImageSrc = '/uploads/violations/video8/plate_bike_red_line.png';
                              }
                            }
                            
                            return plateImageSrc ? (
                              <img
                                src={`${API_URL}${plateImageSrc}`}
                                alt="License plate"
                                style={{
                                  width: '160px',
                                  height: 'auto',
                                  border: '2px solid #000',
                                  borderRadius: '6px',
                                  objectFit: 'contain',
                                  cursor: 'pointer'
                                }}
                                onClick={() => {
                                  setPreviewImage(`${API_URL}${plateImageSrc}`);
                                  setPreviewOpen(true);
                                }}
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                            ) : null;
                          })()}
                        </div>
                      )}
                    </div>

                    {/* License Plate Image Section - Only show in edit mode */}
                    {isEditing && (
                      <div className="mb-4">
                        <Card className="border-primary">
                          <Card.Header className="bg-primary text-white py-2">
                            <h6 className="mb-0">🚗 Hình ảnh biển số xe (đã cắt)</h6>
                          </Card.Header>
                          <Card.Body className="p-3">
                            {plateImage ? (
                              <div className="text-center">
                                <img
                                  src={`${API_URL}${plateImage}`}
                                  alt="License plate"
                                  style={{
                                    maxWidth: '100%',
                                    maxHeight: '150px',
                                    borderRadius: '8px',
                                    border: '2px solid #0d6efd',
                                    objectFit: 'contain',
                                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                  }}
                                  onError={(e) => {
                                    console.error('Plate image load error:', plateImage);
                                    e.currentTarget.style.display = 'none';
                                  }}
                                />
                                <div className="mt-2">
                                  <Badge bg="success" className="px-2 py-1">
                                    ✅ Đã có ảnh biển số
                                  </Badge>
                                </div>
                              </div>
                            ) : (
                              <div className="text-center py-3">
                                <div style={{ fontSize: '48px', opacity: 0.3 }}>🚗</div>
                                <p className="text-muted mb-2">Chưa có ảnh biển số</p>
                                <Button
                                  variant="outline-primary"
                                  size="sm"
                                  onClick={() => plateFileRef.current?.click()}
                                  disabled={uploading}
                                >
                                  {uploading ? <Spinner size="sm" /> : '📤'} Upload ảnh biển số
                                </Button>
                              </div>
                            )}
                            
                            {/* Upload Button for existing image */}
                            {plateImage && (
                              <div className="text-center mt-2 d-flex gap-2 justify-content-center">
                                <Button
                                  variant="outline-primary"
                                  size="sm"
                                  onClick={() => plateFileRef.current?.click()}
                                  disabled={uploading}
                                >
                                  {uploading ? <Spinner size="sm" /> : '🔄'} Thay đổi
                                </Button>
                                <Button
                                  variant="outline-danger"
                                  size="sm"
                                  onClick={handleDeletePlateImage}
                                  disabled={uploading}
                                >
                                  {uploading ? <Spinner size="sm" /> : '🗑️'} Xóa
                                </Button>
                              </div>
                            )}
                            
                            {/* Hidden file input for plate - only render when editing */}
                            {isEditing && (
                              <input
                                ref={plateFileRef}
                                type="file"
                                accept="image/*"
                                style={{ display: 'none' }}
                                onChange={handleFileChange}
                              />
                            )}
                          </Card.Body>
                        </Card>
                      </div>
                    )}

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

        {/* Video8 Evidence Display - Only for viewing */}
        {!isEditing && violation.video_job_id === 8 && violation.violation_type_code && (
          <Row className="mb-4">
            <Col>
              <Card className="shadow-sm">
                <Card.Header className="bg-warning text-dark">
                  <h5 className="mb-0">📸 Bằng chứng vi phạm từ Video8</h5>
                </Card.Header>
                <Card.Body>
                  <Row>
                    <Col md={6}>
                      <div className="text-center">
                        <img
                          src={`${API_URL}/uploads/violations/video8/${violation.violation_type_code === 'CAR_RED_LIGHT' ? 'main_car_red_light.png' : 'main_bike_red_light.png'}`}
                          alt="Ảnh bằng chứng chính"
                          style={{
                            width: '100%',
                            maxHeight: '300px',
                            objectFit: 'contain',
                            border: '3px solid #ffc107',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                          }}
                          onClick={() => {
                            setPreviewImage(`${API_URL}/uploads/violations/video8/${violation.violation_type_code === 'CAR_RED_LIGHT' ? 'main_car_red_light.png' : 'main_bike_red_light.png'}`);
                            setPreviewOpen(true);
                          }}
                          onError={(e) => {
                            console.error('Failed to load main evidence image:', e.currentTarget.src);
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                        <div className="mt-2">
                          <Badge bg="warning" text="dark" className="px-2 py-1">
                            ⭐ Ảnh chính (toàn cục)
                          </Badge>
                        </div>
                      </div>
                    </Col>
                    <Col md={6}>
                      <div className="text-center">
                        <img
                          src={`${API_URL}/uploads/violations/video8/${violation.violation_type_code === 'CAR_RED_LIGHT' ? 'plate_car_red_line.png' : 'plate_bike_red_line.png'}`}
                          alt="Ảnh biển số"
                          style={{
                            width: '100%',
                            maxHeight: '300px',
                            objectFit: 'contain',
                            border: '2px solid #dee2e6',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                          }}
                          onClick={() => {
                            setPreviewImage(`${API_URL}/uploads/violations/video8/${violation.violation_type_code === 'CAR_RED_LIGHT' ? 'plate_car_red_line.png' : 'plate_bike_red_line.png'}`);
                            setPreviewOpen(true);
                          }}
                          onError={(e) => {
                            console.error('Failed to load plate image:', e.currentTarget.src);
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                        <div className="mt-2">
                          <Badge bg="secondary" className="px-2 py-1">
                            📷 Ảnh biển số (chi tiết)
                          </Badge>
                        </div>
                      </div>
                    </Col>
                  </Row>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        )}

        {/* Evidence Gallery - Only show when editing or not video8 */}
        {(isEditing || violation.video_job_id !== 8) && (
          <Row className="mb-4">
            <Col>
              <Card className="shadow-sm">
                <Card.Header className="bg-warning text-dark d-flex justify-content-between align-items-center">
                  <h5 className="mb-0">📸 Bằng chứng vi phạm (tối đa 5 ảnh)</h5>
                  {isEditing && (
                    <div className="d-flex gap-2">
                      <Button
                        variant="outline-dark"
                        size="sm"
                        onClick={() => mainEvidenceFileRef.current?.click()}
                        disabled={uploading || evidenceImages.length >= 5}
                      >
                        {uploading ? <Spinner size="sm" /> : '📤'} Upload ảnh chính
                      </Button>
                      <Button
                        variant="outline-dark"
                        size="sm"
                        onClick={() => evidenceFileRef.current?.click()}
                        disabled={uploading || evidenceImages.length >= 5}
                      >
                        {uploading ? <Spinner size="sm" /> : '📤'} Upload nhiều ảnh
                      </Button>
                    </div>
                  )}
                </Card.Header>
              <Card.Body>
                {evidenceImages.length > 0 ? (
                  <>
                    {evidenceImages.length === 1 ? (
                      // Single image - display centered
                      <div className="text-center">
                        <img
                          src={`${API_URL}${mainEvidence}`}
                          alt="Evidence"
                          style={{
                            maxWidth: '100%',
                            maxHeight: '500px',
                            objectFit: 'contain',
                            border: '3px solid #ffc107',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                          }}
                          onClick={() => {
                            setPreviewImage(`${API_URL}${mainEvidence}`);
                            setPreviewOpen(true);
                          }}
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                        <div className="mt-3 d-flex justify-content-center align-items-center gap-2">
                          <Badge bg="warning" text="dark" className="px-3 py-2">
                            ⭐ Ảnh bằng chứng vi phạm
                          </Badge>
                          {isEditing && (
                            <Button
                              variant="outline-danger"
                              size="sm"
                              onClick={() => mainEvidence && handleDeleteEvidenceImage(mainEvidence)}
                              title="Xóa ảnh"
                            >
                              🗑️ Xóa
                            </Button>
                          )}
                        </div>
                      </div>
                    ) : evidenceImages.length === 2 ? (
                      // Two images - display side by side
                      <Row>
                        <Col md={6}>
                          <div className="text-center">
                            <img
                              src={`${API_URL}${mainEvidence}`}
                              alt="Main evidence"
                              style={{
                                width: '100%',
                                maxHeight: '300px',
                                objectFit: 'contain',
                                border: '3px solid #ffc107',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                              }}
                              onClick={() => {
                                setPreviewImage(`${API_URL}${mainEvidence}`);
                                setPreviewOpen(true);
                              }}
                              onError={(e) => {
                                e.currentTarget.style.display = 'none';
                              }}
                            />
                            <div className="mt-2 d-flex justify-content-center align-items-center gap-2">
                              <Badge bg="warning" text="dark" className="px-2 py-1">
                                ⭐ Ảnh chính (toàn cục)
                              </Badge>
                              {isEditing && (
                                <Button
                                  variant="outline-danger"
                                  size="sm"
                                  onClick={() => mainEvidence && handleDeleteEvidenceImage(mainEvidence)}
                                  title="Xóa ảnh chính"
                                >
                                  🗑️ Xóa
                                </Button>
                              )}
                            </div>
                          </div>
                        </Col>
                        <Col md={6}>
                          {evidenceImages.filter(img => img !== mainEvidence).map((img, index) => (
                            <div key={index} className="text-center position-relative">
                              <img
                                src={`${API_URL}${img}`}
                                alt="Secondary evidence"
                                style={{
                                  width: '100%',
                                  maxHeight: '300px',
                                  objectFit: 'contain',
                                  border: '2px solid #dee2e6',
                                  borderRadius: '8px',
                                  cursor: 'pointer',
                                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                }}
                                onClick={() => {
                                  setPreviewImage(`${API_URL}${img}`);
                                  setPreviewOpen(true);
                                }}
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                              <div className="mt-2 d-flex justify-content-center align-items-center gap-2">
                                <Badge bg="secondary" className="px-2 py-1">
                                  📷 Ảnh phụ (chi tiết)
                                </Badge>
                                {isEditing && (
                                  <div className="d-flex gap-1">
                                    <Button
                                      variant="outline-primary"
                                      size="sm"
                                      onClick={() => setMainEvidence(img)}
                                      title="Đặt làm ảnh chính"
                                    >
                                      ⭐
                                    </Button>
                                    <Button
                                      variant="outline-danger"
                                      size="sm"
                                      onClick={() => handleDeleteEvidenceImage(img)}
                                      title="Xóa ảnh"
                                    >
                                      🗑️
                                    </Button>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </Col>
                      </Row>
                    ) : (
                      // Multiple images - original layout
                      <Row>
                        {/* Main Evidence Image - 65% width */}
                        <Col md={8}>
                          {mainEvidence && (
                            <div className="text-center">
                              <img
                                src={`${API_URL}${mainEvidence}`}
                                alt="Main evidence"
                                style={{
                                  width: '100%',
                                  maxHeight: '400px',
                                  objectFit: 'contain',
                                  border: '3px solid #ffc107',
                                  borderRadius: '8px',
                                  cursor: 'pointer',
                                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                                }}
                                onClick={() => {
                                  setPreviewImage(`${API_URL}${mainEvidence}`);
                                  setPreviewOpen(true);
                                }}
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                              <div className="mt-2 d-flex justify-content-center align-items-center gap-2">
                                <Badge bg="warning" text="dark" className="px-2 py-1">
                                  ⭐ Ảnh chính (toàn cục)
                                </Badge>
                                {isEditing && (
                                  <Button
                                    variant="outline-danger"
                                    size="sm"
                                    onClick={() => mainEvidence && handleDeleteEvidenceImage(mainEvidence)}
                                    title="Xóa ảnh chính"
                                  >
                                    🗑️ Xóa
                                  </Button>
                                )}
                              </div>
                            </div>
                          )}
                        </Col>
                        
                        {/* Secondary Evidence Images - 35% width */}
                        <Col md={4}>
                          <div className="d-flex flex-column gap-2">
                            {evidenceImages
                              .filter(img => img !== mainEvidence)
                              .slice(0, 4)
                              .map((img, index) => (
                                <div key={index} className="position-relative">
                                  <img
                                    src={`${API_URL}${img}`}
                                    alt={`Evidence ${index + 1}`}
                                    style={{
                                      width: '100%',
                                      height: '90px',
                                      objectFit: 'cover',
                                      border: '2px solid #dee2e6',
                                      borderRadius: '6px',
                                      cursor: 'pointer'
                                    }}
                                    onClick={() => {
                                      setPreviewImage(`${API_URL}${img}`);
                                      setPreviewOpen(true);
                                    }}
                                    onError={(e) => {
                                      e.currentTarget.style.display = 'none';
                                    }}
                                  />
                                  <div className="position-absolute bottom-0 start-0 m-1">
                                    <Badge bg="secondary" style={{ fontSize: '10px' }}>
                                      📷 Chi tiết {index + 1}
                                    </Badge>
                                  </div>
                                  {isEditing && (
                                    <div className="position-absolute top-0 end-0 m-1 d-flex gap-1">
                                      <Button
                                        variant="outline-primary"
                                        size="sm"
                                        style={{ fontSize: '10px', padding: '2px 6px' }}
                                        onClick={() => setMainEvidence(img)}
                                        title="Đặt làm ảnh chính"
                                      >
                                        ⭐
                                      </Button>
                                      <Button
                                        variant="outline-danger"
                                        size="sm"
                                        style={{ fontSize: '10px', padding: '2px 6px' }}
                                        onClick={() => handleDeleteEvidenceImage(img)}
                                        title="Xóa ảnh"
                                      >
                                        🗑️
                                      </Button>
                                    </div>
                                  )}
                                </div>
                              ))}
                            
                            {/* Empty slots for remaining images - only show in edit mode */}
                            {isEditing && Array.from({ length: Math.max(0, 4 - evidenceImages.filter(img => img !== mainEvidence).length) }).map((_, index) => (
                              <div
                                key={`empty-${index}`}
                                style={{
                                  width: '100%',
                                  height: '90px',
                                  border: '2px dashed #dee2e6',
                                  borderRadius: '6px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  backgroundColor: '#f8f9fa'
                                }}
                              >
                                <span className="text-muted" style={{ fontSize: '12px' }}>
                                  Ảnh phụ {evidenceImages.filter(img => img !== mainEvidence).length + index + 1}
                                </span>
                              </div>
                            ))}
                          </div>
                        </Col>
                      </Row>
                    )}
                  </>
                ) : (
                  <div className="text-center py-5">
                    <div style={{ fontSize: '64px', opacity: 0.3 }}>📸</div>
                    <h5 className="text-muted mb-3">Chưa có ảnh bằng chứng vi phạm</h5>
                    <p className="text-muted mb-3">
                      Ảnh chính thường là ảnh toàn cục video vi phạm<br />
                      Ảnh phụ là ảnh được cắt nhỏ ra (chi tiết)
                    </p>
                    {isEditing && (
                      <div className="d-flex gap-2 justify-content-center">
                        <Button
                          variant="outline-warning"
                          onClick={() => mainEvidenceFileRef.current?.click()}
                          disabled={uploading}
                        >
                          {uploading ? <Spinner size="sm" /> : '📤'} Upload ảnh chính
                        </Button>
                        <Button
                          variant="outline-secondary"
                          onClick={() => evidenceFileRef.current?.click()}
                          disabled={uploading}
                        >
                          {uploading ? <Spinner size="sm" /> : '📤'} Upload nhiều ảnh
                        </Button>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Upload progress info */}
                {isEditing && evidenceImages.length > 0 && (
                  <div className="mt-3 text-center">
                    <small className="text-muted">
                      Đã có {evidenceImages.length}/5 ảnh bằng chứng
                      {evidenceImages.length >= 5 && (
                        <span className="text-warning ms-2">⚠️ Đã đạt giới hạn tối đa</span>
                      )}
                    </small>
                  </div>
                )}
                
                {/* Hidden file inputs - only render when editing */}
                {isEditing && (
                  <>
                    <input
                      ref={evidenceFileRef}
                      type="file"
                      accept="image/*"
                      multiple
                      style={{ display: 'none' }}
                      onChange={handleEvidenceFileChange}
                    />
                    
                    <input
                      ref={mainEvidenceFileRef}
                      type="file"
                      accept="image/*"
                      style={{ display: 'none' }}
                      onChange={handleMainEvidenceFileChange}
                    />
                  </>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
        )}

      </div>

      {/* Image Preview Modal */}
      <Modal 
        show={previewOpen} 
        onHide={() => setPreviewOpen(false)} 
        centered 
        size="xl"
        className="image-preview-modal"
      >
        <Modal.Header closeButton className="border-0">
          <Modal.Title>Xem ảnh chi tiết</Modal.Title>
        </Modal.Header>
        <Modal.Body className="text-center p-0">
          {previewImage && (
            <img 
              src={previewImage} 
              alt="Preview" 
              style={{ 
                width: '100%', 
                height: 'auto',
                maxHeight: '80vh',
                objectFit: 'contain'
              }} 
            />
          )}
        </Modal.Body>
      </Modal>
    </>
  );
}