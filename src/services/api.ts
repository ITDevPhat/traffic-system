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
    throw new Error(`Failed to fetch violations: ${res.statusText}`);
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
    throw new Error(`Failed to fetch violation detail: ${res.statusText}`);
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
    throw new Error(`Failed to fetch videos: ${res.statusText}`);
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
    throw new Error(`Failed to fetch video detail: ${res.statusText}`);
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
    throw new Error(`Failed to upload video: ${res.statusText}`);
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
    throw new Error(`Failed to check detection status: ${res.statusText}`);
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
    throw new Error(`Failed to delete violation: ${res.statusText}`);
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
    throw new Error(`Failed to delete video: ${res.statusText}`);
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
    throw new Error(`Server health check failed: ${res.statusText}`);
  }
  
  return res.json();
}

