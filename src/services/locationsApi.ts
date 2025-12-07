/**
 * API Service cho Quản lý Vị trí
 */

import { API_URL, API_PREFIX } from './api';

export interface Location {
  location_id: number;
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  description?: string;
  created_at: string;
}

export interface LocationCreateInput {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  description?: string;
}

export interface LocationUpdateInput {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  description?: string;
}

export async function fetchLocations(params?: {
  skip?: number;
  limit?: number;
}): Promise<Location[]> {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  
  const url = `${API_URL}${API_PREFIX}/locations?${queryParams.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) {
    throw new Error(`Không thể tải danh sách vị trí: ${res.statusText}`);
  }
  
  return res.json();
}

export async function fetchLocationById(locationId: number): Promise<Location> {
  const url = `${API_URL}${API_PREFIX}/locations/${locationId}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) {
    throw new Error(`Không thể tải chi tiết vị trí: ${res.statusText}`);
  }
  
  return res.json();
}

export async function createLocation(data: LocationCreateInput): Promise<Location> {
  const url = `${API_URL}${API_PREFIX}/locations`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể tạo vị trí');
  }
  
  return res.json();
}

export async function updateLocation(locationId: number, data: LocationUpdateInput): Promise<Location> {
  const url = `${API_URL}${API_PREFIX}/locations/${locationId}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể cập nhật vị trí');
  }
  
  return res.json();
}

export async function deleteLocation(locationId: number): Promise<{ message: string; location_id: number }> {
  const url = `${API_URL}${API_PREFIX}/locations/${locationId}`;
  const res = await fetch(url, { method: 'DELETE' });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể xóa vị trí');
  }
  
  return res.json();
}
