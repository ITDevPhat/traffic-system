/**
 * API Service cho Quản lý Loại Vi Phạm
 * 
 * Endpoints:
 * - GET /api/violation-types - Lấy danh sách loại vi phạm
 * - GET /api/violation-types/{code} - Lấy chi tiết loại vi phạm
 * - POST /api/violation-types - Tạo loại vi phạm mới
 * - PUT /api/violation-types/{code} - Cập nhật loại vi phạm
 */

import { API_URL, API_PREFIX } from './api';

export type SeverityType = 'low' | 'medium' | 'high';

export interface ViolationType {
  violation_type_code: string;
  description: string;
  fine_amount: number;
  severity: SeverityType;
}

export interface ViolationTypeCreateInput {
  violation_type_code: string;
  description: string;
  fine_amount: number;
  severity: string;
}

export interface ViolationTypeUpdateInput {
  description: string;
  fine_amount: number;
  severity: string;
}

/**
 * Lấy danh sách tất cả loại vi phạm
 */
export async function fetchViolationTypes(): Promise<ViolationType[]> {
  const url = `${API_URL}${API_PREFIX}/violation-types`;
  const res = await fetch(url, {
    cache: 'no-store',
  });
  
  if (!res.ok) {
    throw new Error(`Không thể tải danh sách loại vi phạm: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Lấy chi tiết một loại vi phạm theo code
 */
export async function fetchViolationTypeByCode(code: string): Promise<ViolationType> {
  const url = `${API_URL}${API_PREFIX}/violation-types/${code}`;
  const res = await fetch(url, {
    cache: 'no-store',
  });
  
  if (!res.ok) {
    throw new Error(`Không thể tải chi tiết loại vi phạm: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Tạo loại vi phạm mới
 */
export async function createViolationType(data: ViolationTypeCreateInput): Promise<ViolationType> {
  const url = `${API_URL}${API_PREFIX}/violation-types`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể tạo loại vi phạm');
  }
  
  return res.json();
}

/**
 * Cập nhật loại vi phạm
 */
export async function updateViolationType(
  code: string,
  data: ViolationTypeUpdateInput
): Promise<ViolationType> {
  const url = `${API_URL}${API_PREFIX}/violation-types/${code}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể cập nhật loại vi phạm');
  }
  
  return res.json();
}
