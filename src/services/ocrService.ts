/**
 * OCR Service - API calls for static image license plate recognition
 */

import { API_URL } from './api';

export interface OCRResult {
  success: boolean;
  processing_time: number;
  total_time: number;
  image_info: {
    filename: string;
    original_size: { width: number; height: number };
    processed_size: { width: number; height: number };
    scale_factor: number;
  };
  detection_results: {
    plates_detected: number;
    plates_recognized: number;
  };
  plates: Array<{
    text: string;
    confidence: number;
    bbox: {
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      width: number;
      height: number;
    };
  }>;
}

export interface OCRHealthStatus {
  status: string;
  ocr_available: boolean;
  device?: string;
  model_type?: string;
  stats?: any;
  error?: string;
}

/**
 * Nhận dạng biển số từ file ảnh
 */
export async function ocrImage(
  file: File,
  options?: {
    confidenceThreshold?: number;
    drawBbox?: boolean;
  }
): Promise<OCRResult> {
  const formData = new FormData();
  formData.append('file', file);
  
  if (options?.confidenceThreshold !== undefined) {
    formData.append('confidence_threshold', options.confidenceThreshold.toString());
  }
  
  if (options?.drawBbox !== undefined) {
    formData.append('draw_bbox', options.drawBbox.toString());
  }
  
  const response = await fetch(`${API_URL}/api/ocr/image`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `OCR failed: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Kiểm tra trạng thái OCR service
 */
export async function checkOCRHealth(): Promise<OCRHealthStatus> {
  const response = await fetch(`${API_URL}/api/ocr/health`);
  
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Lấy thông tin OCR API
 */
export async function getOCRInfo() {
  const response = await fetch(`${API_URL}/api/ocr/`);
  
  if (!response.ok) {
    throw new Error(`Failed to get OCR info: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Validate image file before upload
 */
export function validateImageFile(file: File): { valid: boolean; error?: string } {
  // Check file type
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff'];
  if (!allowedTypes.includes(file.type.toLowerCase())) {
    return {
      valid: false,
      error: 'Chỉ hỗ trợ file ảnh: JPG, PNG, BMP, TIFF'
    };
  }
  
  // Check file size (max 10MB)
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (file.size > maxSize) {
    return {
      valid: false,
      error: 'File ảnh quá lớn (tối đa 10MB)'
    };
  }
  
  return { valid: true };
}