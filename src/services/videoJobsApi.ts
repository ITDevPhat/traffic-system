import { API_URL, API_PREFIX } from './api';

export interface VideoJob {
  video_job_id: number;
  camera_id?: number;
  file_name: string;
  upload_time: string;
  status: string;
  processing_stage: string;
  processed_at?: string;
  output_path?: string;
  fps?: number;
  duration?: number;
  notes?: string;
}

export interface VideoJobCreateInput {
  camera_id?: number;
  file_name: string;
  status: string;
  processing_stage: string;
  output_path?: string;
  fps?: number;
  duration?: number;
  notes?: string;
}

export interface VideoJobUpdateInput {
  camera_id?: number;
  file_name: string;
  status: string;
  processing_stage: string;
  processed_at?: string;
  output_path?: string;
  fps?: number;
  duration?: number;
  notes?: string;
}

export async function fetchVideoJobs(params?: {
  skip?: number;
  limit?: number;
  status?: string;
  camera_id?: number;
}): Promise<VideoJob[]> {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.status) queryParams.append('status', params.status);
  if (params?.camera_id) queryParams.append('camera_id', params.camera_id.toString());
  
  const url = `${API_URL}${API_PREFIX}/video-jobs?${queryParams.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) throw new Error(`Không thể tải danh sách video: ${res.statusText}`);
  return res.json();
}

export async function fetchVideoJobById(videoJobId: number): Promise<VideoJob> {
  const url = `${API_URL}${API_PREFIX}/video-jobs/${videoJobId}`;
  const res = await fetch(url, { cache: 'no-store' });
  
  if (!res.ok) throw new Error(`Không thể tải chi tiết video: ${res.statusText}`);
  return res.json();
}

export async function createVideoJob(data: VideoJobCreateInput): Promise<VideoJob> {
  const url = `${API_URL}${API_PREFIX}/video-jobs`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể tạo video job');
  }
  return res.json();
}

export async function updateVideoJob(videoJobId: number, data: VideoJobUpdateInput): Promise<VideoJob> {
  const url = `${API_URL}${API_PREFIX}/video-jobs/${videoJobId}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Không thể cập nhật video job');
  }
  return res.json();
}
