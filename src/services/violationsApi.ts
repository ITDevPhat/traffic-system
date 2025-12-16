/**
 * API Service cho Quản lý Vi phạm
 * 
 * Endpoints:
 * - GET /api/violations - Lấy danh sách vi phạm
 * - GET /api/violations/{id} - Lấy chi tiết vi phạm
 * - POST /api/violations - Tạo vi phạm mới
 * - PUT /api/violations/{id} - Cập nhật vi phạm
 * - DELETE /api/violations/{id} - Xóa vi phạm
 */

import { API_URL, API_PREFIX } from './api';

export interface ViolationItem {
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
  model_id?: number;
  verification_status: string;
  verified_by?: number;
  verified_source: string;
  verified_at?: string;
  created_at: string;
}

export interface ViolationCreateInput {
  video_job_id: number;
  vehicle_id?: number;
  violation_type_code?: string;
  frame?: number;
  timestamp?: string;
  roi_type?: string;
  evidence_img?: string;
  plate?: string;
  confidence?: number;
  model_id?: number;
  verification_status: string;
  verified_source: string;
}

export interface ViolationUpdateInput {
  video_job_id: number;
  vehicle_id?: number;
  violation_type_code?: string;
  frame?: number;
  timestamp?: string;
  roi_type?: string;
  evidence_img?: string;
  plate?: string;
  confidence?: number;
  model_id?: number;
  verification_status: string;
  verified_by?: number;
  verified_source: string;
  verified_at?: string;
}

/**
 * Lấy danh sách vi phạm
 */
export async function fetchViolationsManagement(params?: {
  skip?: number;
  limit?: number;
  violation_type_code?: string;
  video_job_id?: number;
  verification_status?: string;
  plate?: string;
}): Promise<ViolationItem[]> {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.violation_type_code) queryParams.append('violation_type_code', params.violation_type_code);
  if (params?.video_job_id) queryParams.append('video_job_id', params.video_job_id.toString());
  if (params?.verification_status) queryParams.append('verification_status', params.verification_status);
  if (params?.plate) queryParams.append('plate', params.plate);
  
  const url = `${API_URL}${API_PREFIX}/violations?${queryParams.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) {
    throw new Error(`Không thể tải danh sách vi phạm: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Lấy chi tiết một vi phạm theo ID
 */
export async function fetchViolationById(violationId: number): Promise<ViolationItem> {
  const url = `${API_URL}${API_PREFIX}/violations/${violationId}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) {
    throw new Error(`Không thể tải chi tiết vi phạm: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Tạo vi phạm mới
 */
export async function createViolation(data: ViolationCreateInput): Promise<ViolationItem> {
  const url = `${API_URL}${API_PREFIX}/violations`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể tạo vi phạm');
  }
  
  return res.json();
}

/**
 * Cập nhật vi phạm
 */
export async function updateViolation(
  violationId: number,
  data: ViolationUpdateInput
): Promise<ViolationItem> {
  const url = `${API_URL}${API_PREFIX}/violations/${violationId}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể cập nhật vi phạm');
  }
  
  return res.json();
}

/**
 * Xóa vi phạm
 */
export async function deleteViolationItem(violationId: number): Promise<{ message: string; violation_id: number }> {
  const url = `${API_URL}${API_PREFIX}/violations/${violationId}`;
  const res = await fetch(url, { method: 'DELETE' });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể xóa vi phạm');
  }
  
  return res.json();
}

/**
 * Tự động tạo vi phạm cho video8.mp4 với hình ảnh có sẵn
 */
export interface AutoViolationRequest {
  violation_type: 'CAR_RED_LIGHT' | 'BIKE_RED_LIGHT';
  track_id: number;
  frame?: number;
  confidence?: number;
  plate?: string;
  timestamp?: string;
}

export interface AutoViolationResponse {
  ok: boolean;
  message: string;
  violation_id: number;
  track_id: number;
  violation_type: string;
  images: {
    plate: string | null;
    evidence: string | null;
  };
  video_job_id: number;
}

export async function autoCreateVideo8Violation(data: AutoViolationRequest): Promise<AutoViolationResponse> {
  const url = `${API_URL}${API_PREFIX}/violations/auto-create-video8`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể tạo vi phạm tự động');
  }
  
  return res.json();
}
