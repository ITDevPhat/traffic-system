/**
 * API Service cho Quản lý Mô hình AI
 * 
 * Endpoints:
 * - GET /api/models - Lấy danh sách mô hình
 * - GET /api/models/{id} - Lấy chi tiết mô hình
 * - POST /api/models - Tạo mô hình mới
 * - PUT /api/models/{id} - Cập nhật mô hình
 * - DELETE /api/models/{id} - Xóa mô hình
 */

import { API_URL, API_PREFIX } from './api';

export type ModelType = 'vehicle' | 'plate' | 'ocr' | 'traffic_light' | 'violation';

export interface AIModel {
  model_id: number;
  name: string;
  model_type: ModelType;
  file_path: string;
  version: string;
  framework: string;
  confidence_threshold: number;
  description?: string;
  created_at: string;
}

export interface ModelCreateInput {
  name: string;
  model_type: string;
  file_path: string;
  version: string;
  framework: string;
  confidence_threshold: number;
  description?: string;
}

export interface ModelUpdateInput {
  name: string;
  model_type: string;
  file_path: string;
  version: string;
  framework: string;
  confidence_threshold: number;
  description?: string;
}

/**
 * Lấy danh sách mô hình AI
 */
export async function fetchModels(params?: {
  skip?: number;
  limit?: number;
  model_type?: string;
}): Promise<AIModel[]> {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.model_type) queryParams.append('model_type', params.model_type);
  
  const url = `${API_URL}${API_PREFIX}/models?${queryParams.toString()}`;
  const res = await fetch(url, {
    cache: 'no-store',
  });
  
  if (!res.ok) {
    throw new Error(`Không thể tải danh sách mô hình: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Lấy chi tiết một mô hình theo ID
 */
export async function fetchModelById(modelId: number): Promise<AIModel> {
  const url = `${API_URL}${API_PREFIX}/models/${modelId}`;
  const res = await fetch(url, {
    cache: 'no-store',
  });
  
  if (!res.ok) {
    throw new Error(`Không thể tải chi tiết mô hình: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Tạo mô hình mới
 */
export async function createModel(data: ModelCreateInput): Promise<AIModel> {
  const url = `${API_URL}${API_PREFIX}/models`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể tạo mô hình');
  }
  
  return res.json();
}

/**
 * Cập nhật mô hình
 */
export async function updateModel(
  modelId: number,
  data: ModelUpdateInput
): Promise<AIModel> {
  const url = `${API_URL}${API_PREFIX}/models/${modelId}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể cập nhật mô hình');
  }
  
  return res.json();
}

/**
 * Xóa mô hình
 */
export async function deleteModel(modelId: number): Promise<{ message: string; model_id: number }> {
  const url = `${API_URL}${API_PREFIX}/models/${modelId}`;
  const res = await fetch(url, {
    method: 'DELETE',
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể xóa mô hình');
  }
  
  return res.json();
}
