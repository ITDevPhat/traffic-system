/**
 * API Service để kết nối với FastAPI backend
 * 
 * Backend URL: http://localhost:8000
 * API Prefix: /api
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_PREFIX = "/api";

/**
 * Fetch danh sách vi phạm từ backend
 */
export async function fetchViolations(params?: {
  skip?: number;
  limit?: number;
  violationType?: string;
  videoJobId?: number;
}) {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.violationType) queryParams.append('violation_type', params.violationType);
  if (params?.videoJobId !== undefined) queryParams.append('video_job_id', params.videoJobId.toString());
  
  const url = `${API_URL}${API_PREFIX}/violations?${queryParams.toString()}`;
  const res = await fetch(url);
  
  if (!res.ok) {
    throw new Error(`Không thể tải danh sách vi phạm: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Fetch chi tiết một vi phạm
 */
export async function fetchViolationDetail(violationId: number) {
  const url = `${API_URL}${API_PREFIX}/violations/${violationId}`;
  const res = await fetch(url);
  
  if (!res.ok) {
    throw new Error(`Không thể tải chi tiết vi phạm: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Fetch danh sách video jobs
 */
export async function fetchVideos(params?: {
  skip?: number;
  limit?: number;
  status?: string;
}) {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.status) queryParams.append('status', params.status);
  
  const url = `${API_URL}${API_PREFIX}/videos?${queryParams.toString()}`;
  const res = await fetch(url);
  
  if (!res.ok) {
    throw new Error(`Không thể tải danh sách video: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Fetch chi tiết một video job
 */
export async function fetchVideoDetail(videoId: number) {
  const url = `${API_URL}${API_PREFIX}/videos/${videoId}`;
  const res = await fetch(url);
  
  if (!res.ok) {
    throw new Error(`Không thể tải chi tiết video: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Upload video để phát hiện vi phạm
 */
export async function uploadVideoForDetection(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  
  const url = `${API_URL}${API_PREFIX}/detection/video`;
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
  });
  
  if (!res.ok) {
    throw new Error(`Không thể tải lên video: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Kiểm tra trạng thái xử lý video
 */
export async function checkDetectionStatus(jobId: number) {
  const url = `${API_URL}${API_PREFIX}/detection/status/${jobId}`;
  const res = await fetch(url);
  
  if (!res.ok) {
    throw new Error(`Không thể kiểm tra trạng thái phát hiện: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Xóa một vi phạm
 */
export async function deleteViolation(violationId: number) {
  const url = `${API_URL}${API_PREFIX}/violations/${violationId}`;
  const res = await fetch(url, {
    method: 'DELETE',
  });
  
  if (!res.ok) {
    throw new Error(`Không thể xóa vi phạm: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Xóa một video job
 */
export async function deleteVideo(videoId: number) {
  const url = `${API_URL}${API_PREFIX}/videos/${videoId}`;
  const res = await fetch(url, {
    method: 'DELETE',
  });
  
  if (!res.ok) {
    throw new Error(`Không thể xóa video: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Health check endpoint
 */
export async function checkServerHealth() {
  const url = `${API_URL}/health`;
  const res = await fetch(url);
  
  if (!res.ok) {
    throw new Error(`Kiểm tra trạng thái máy chủ thất bại: ${res.statusText}`);
  }
  
  return res.json();
}

// ===============================
// 🔐 Authentication API
// ===============================

/**
 * Đăng ký tài khoản mới
 */
export async function registerUser(data: {
  username: string;
  password: string;
  email?: string;
  full_name?: string;
}) {
  const url = `${API_URL}${API_PREFIX}/auth/register`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Đăng ký thất bại');
  }
  
  return res.json();
}

/**
 * Đăng nhập bằng username/password
 * Trả về access token
 */
export async function loginUser(username: string, password: string) {
  const url = `${API_URL}${API_PREFIX}/auth/login`;
  
  console.log('🔑 Login attempt:', { url, username });
  
  // FastAPI OAuth2PasswordRequestForm expects form data
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
    credentials: 'include', // Include cookies
  });
  
  console.log('📡 Login response status:', res.status);
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    console.error('❌ Login error:', errorData);
    // Extract error message from backend
    const errorMessage = errorData.detail || errorData.message || 'Tên đăng nhập/email hoặc mật khẩu không đúng';
    throw new Error(errorMessage);
  }
  
  const data = await res.json();
  console.log('✅ Login success');
  return data;
}

/**
 * Đăng xuất
 */
export async function logoutUser() {
  const url = `${API_URL}${API_PREFIX}/auth/logout`;
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'include',
  });
  
  if (!res.ok) {
    throw new Error(`Đăng xuất thất bại: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Lấy thông tin user hiện tại
 */
export async function getCurrentUser(token?: string) {
  const url = `${API_URL}${API_PREFIX}/auth/me`;
  const headers: HeadersInit = {};
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(url, {
    headers,
    credentials: 'include', // Include cookies
  });
  
  if (!res.ok) {
    throw new Error(`Không thể lấy thông tin người dùng hiện tại: ${res.statusText}`);
  }
  
  return res.json();
}

/**
 * Đổi mật khẩu
 */
export async function changePassword(
  currentPassword: string,
  newPassword: string,
  token?: string
) {
  const url = `${API_URL}${API_PREFIX}/auth/change-password`;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể đổi mật khẩu');
  }
  
  return res.json();
}

