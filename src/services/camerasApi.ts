import { API_URL, API_PREFIX } from './api';

export interface Camera {
  camera_id: number;
  location_id?: number;
  name: string;
  model?: string;
  ip_address?: string;
  stream_url?: string;
  status: string;
  install_date?: string;
  created_at: string;
}

export interface CameraCreateInput {
  location_id?: number;
  name: string;
  model?: string;
  ip_address?: string;
  stream_url?: string;
  status: string;
  install_date?: string;
}

export interface CameraUpdateInput {
  location_id?: number;
  name: string;
  model?: string;
  ip_address?: string;
  stream_url?: string;
  status: string;
  install_date?: string;
}

export async function fetchCameras(params?: {
  skip?: number;
  limit?: number;
  status?: string;
  location_id?: number;
}): Promise<Camera[]> {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.status) queryParams.append('status', params.status);
  if (params?.location_id) queryParams.append('location_id', params.location_id.toString());
  
  const url = `${API_URL}${API_PREFIX}/cameras?${queryParams.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) throw new Error(`Không thể tải danh sách camera: ${res.statusText}`);
  return res.json();
}

export async function fetchCameraById(cameraId: number): Promise<Camera> {
  const url = `${API_URL}${API_PREFIX}/cameras/${cameraId}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) throw new Error(`Không thể tải chi tiết camera: ${res.statusText}`);
  return res.json();
}

export async function createCamera(data: CameraCreateInput): Promise<Camera> {
  const url = `${API_URL}${API_PREFIX}/cameras`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể tạo camera');
  }
  return res.json();
}

export async function updateCamera(cameraId: number, data: CameraUpdateInput): Promise<Camera> {
  const url = `${API_URL}${API_PREFIX}/cameras/${cameraId}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể cập nhật camera');
  }
  return res.json();
}
