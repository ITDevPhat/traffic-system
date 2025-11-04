'use client';
import React, { useState, useRef, useEffect } from 'react';
import { Card, Badge, Button } from 'react-bootstrap';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function DetectionCard({ video }) {
  const router = useRouter();
  const videoRef = useRef(null);
  const cardRef = useRef(null);
  const [isHovered, setIsHovered] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [videoLoading, setVideoLoading] = useState(true);

  // IntersectionObserver để lazy load video
  useEffect(() => {
    if (!cardRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
          }
        });
      },
      {
        threshold: 0.1, // Trigger khi 10% visible
        rootMargin: '50px' // Load sớm 50px trước khi vào viewport
      }
    );

    observer.observe(cardRef.current);

    return () => {
      if (cardRef.current) {
        observer.unobserve(cardRef.current);
      }
    };
  }, []);

  // Get status badge color
  const getStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'secondary', text: 'Chờ xử lý' },
      processing: { bg: 'warning', text: 'Đang xử lý' },
      done: { bg: 'success', text: 'Hoàn thành' },
      completed: { bg: 'success', text: 'Hoàn thành' },
      failed: { bg: 'danger', text: 'Thất bại' }
    };
    return statusMap[status] || statusMap.pending;
  };

  // Handle video error
  const handleVideoError = (e) => {
    const videoElement = e.target;
    const errorCode = videoElement?.error?.code;
    const errorMessages = {
      1: 'MEDIA_ERR_ABORTED - User aborted',
      2: 'MEDIA_ERR_NETWORK - Network error',
      3: 'MEDIA_ERR_DECODE - Decode error',
      4: 'MEDIA_ERR_SRC_NOT_SUPPORTED - Source not supported'
    };
    
    const errorDetails = {
      file: video.file_name || video.filename,
      videoUrl: videoUrl,
      networkState: videoElement?.networkState,
      readyState: videoElement?.readyState,
      errorCode: errorCode,
      errorMessage: errorCode ? errorMessages[errorCode] || 'Unknown error' : 'No error code',
      error: videoElement?.error ? {
        code: videoElement.error.code,
        message: videoElement.error.message
      } : null
    };
    console.error(`❌ Video error for ${video.file_name || video.filename}:`, errorDetails);
    
    // Try to fetch video URL to check if file exists
    if (videoUrl) {
      fetch(videoUrl, { method: 'HEAD' })
        .then(response => {
          if (!response.ok) {
            console.error(`❌ Video file not found (${response.status}): ${videoUrl}`);
          } else {
            console.log(`✅ Video file exists but can't play: ${videoUrl}`);
          }
        })
        .catch(err => {
          console.error(`❌ Failed to check video file:`, err);
        });
    }
    
    setVideoError(true);
    setVideoLoading(false);
  };

  // Handle video loaded
  const handleVideoLoaded = () => {
    setVideoLoading(false);
    setVideoError(false);
  };

  // Handle video loading
  const handleVideoLoading = () => {
    setVideoLoading(true);
  };

  // Get video URL
  const getVideoUrl = () => {
    // Database output_path: "/videos/video.mp4"
    // We need to request from FastAPI: "http://localhost:8000/videos/video.mp4"
    const pathToTry = video.output_path || video.file_path;
    let finalUrl = null;
    
    if (pathToTry) {
      // If path starts with /videos/, use it directly
      if (pathToTry.startsWith('/videos/')) {
        finalUrl = `${API_URL}${pathToTry}`;
      }
      // If path is just a filename, prepend /videos/
      else if (!pathToTry.startsWith('/')) {
        finalUrl = `${API_URL}/videos/${pathToTry}`;
      }
      // If path starts with /, prepend API URL
      else {
        finalUrl = `${API_URL}${pathToTry}`;
      }
    }
    // Fallback: try videos folder with filename
    else {
      const fileName = video.filename || video.file_name;
      if (fileName) {
        finalUrl = `${API_URL}/videos/${fileName}`;
      }
    }
    
    // Debug logging
    if (finalUrl) {
      console.log(`🎬 Video URL for ${video.file_name || video.filename}:`, finalUrl);
    }
    
    return finalUrl;
  };

  const statusBadge = getStatusBadge(video.status);
  const videoUrl = getVideoUrl();

  // Auto-play video khi visible (không cần hover)
  useEffect(() => {
    if (!videoRef.current || !isVisible || videoError) return;

    const playVideo = async () => {
      try {
        if (videoRef.current && videoRef.current.readyState >= 2) {
          // Video đã load metadata, play ngay
          await videoRef.current.play();
        }
      } catch (error) {
        // Browser policy may prevent autoplay - try again after user interaction
        console.debug('Video autoplay prevented:', error);
      }
    };

    // Play ngay khi visible
    playVideo();
  }, [isVisible, videoError]);

  // Resume play khi hover (nếu đang paused)
  useEffect(() => {
    if (!videoRef.current || !isVisible || videoError) return;

    const handleHover = async () => {
      try {
        if (videoRef.current && videoRef.current.paused) {
          await videoRef.current.play();
        }
      } catch (error) {
        // Ignore errors
      }
    };

    if (isHovered) {
      handleHover();
    }
  }, [isHovered, isVisible, videoError]);

  const handleCardClick = () => {
    // Navigate to live detection page with this video
    const videoId = video.id || video.video_job_id;
    const videoPath = video.file_path || video.output_path || video.filename || video.file_name;
    router.push(`/detection/live?video=${encodeURIComponent(videoPath)}&id=${videoId}`);
  };

  return (
    <Card
      ref={cardRef}
      className="h-100 shadow-sm border-0"
      style={{
        transition: 'all 0.3s ease',
        transform: isHovered ? 'scale(1.02)' : 'scale(1)',
        cursor: 'pointer'
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleCardClick}
    >
      {/* Video Preview */}
      <div style={{ position: 'relative', width: '100%', paddingTop: '56.25%', backgroundColor: '#000', overflow: 'hidden' }}>
        {videoError || !videoUrl ? (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '14px',
              gap: '8px'
            }}
          >
            {videoError ? (
              <>
                <div>❌ Video không khả dụng</div>
                <div style={{ fontSize: '12px', opacity: 0.7 }}>
                  {video.file_name || video.filename || 'Unknown'}
                </div>
                <div style={{ fontSize: '10px', opacity: 0.5, marginTop: '4px' }}>
                  {videoUrl ? `URL: ${videoUrl.split('/').pop()}` : 'No URL'}
                </div>
              </>
            ) : (
              <div>📹 Video Preview</div>
            )}
          </div>
        ) : (
          <>
            {videoLoading && (
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: '#000',
                  zIndex: 1
                }}
              >
                <div style={{ color: '#fff', fontSize: '12px' }}>Loading...</div>
              </div>
            )}
            {isVisible && (
              <video
                ref={videoRef}
                src={videoUrl}
                className="position-absolute top-0 start-0 w-100 h-100"
                style={{ 
                  objectFit: 'cover',
                  display: videoLoading ? 'none' : 'block'
                }}
                autoPlay // Tự động play khi load
                muted
                loop
                playsInline
                preload="auto" // Load toàn bộ video để autoplay mượt
                crossOrigin="anonymous" // Help with CORS if needed
                onError={handleVideoError}
                onLoadedData={async () => {
                  handleVideoLoaded();
                  // Play ngay khi loaded data
                  if (videoRef.current && isVisible && !videoError) {
                    try {
                      await videoRef.current.play();
                    } catch (error) {
                      console.debug('Autoplay prevented:', error);
                    }
                  }
                }}
                onLoadStart={handleVideoLoading}
                onCanPlay={async () => {
                  setVideoLoading(false);
                  // Play ngay khi can play
                  if (videoRef.current && isVisible && !videoError && videoRef.current.paused) {
                    try {
                      await videoRef.current.play();
                    } catch (error) {
                      console.debug('Autoplay prevented on canPlay:', error);
                    }
                  }
                }}
                onStalled={() => {
                  console.warn(`⚠️ Video stalled: ${video.file_name || video.filename}`);
                }}
                onAbort={() => {
                  console.warn(`⚠️ Video aborted: ${video.file_name || video.filename}`);
                  setVideoError(true);
                }}
              />
            )}
          </>
        )}
        
        {/* Status Badge Overlay */}
        <div className="position-absolute top-0 end-0 m-2" style={{ zIndex: 2 }}>
          <Badge bg={statusBadge.bg} className="px-2 py-1">
            {statusBadge.text}
          </Badge>
        </div>
      </div>

      {/* Card Body */}
      <Card.Body className="d-flex flex-column">
        <div className="mb-2">
          <h6 className="mb-1 fw-semibold" style={{ fontSize: '16px', lineHeight: '1.3' }}>
            {video.filename || video.file_name || 'Video không tên'}
          </h6>
          <p className="text-muted small mb-0" style={{ fontSize: '12px' }}>
            ID: {video.id || video.video_job_id} • {video.created_at || video.upload_time ? new Date(video.created_at || video.upload_time).toLocaleDateString('vi-VN') : 'N/A'}
          </p>
        </div>

        {/* Stats Row */}
        <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top">
          <div className="d-flex gap-2 flex-wrap">
            {video.fps && (
              <Badge bg="info" className="px-2 py-1" style={{ fontSize: '11px' }}>
                ⚡ {video.fps.toFixed(1)} FPS
              </Badge>
            )}
            {video.duration && (
              <Badge bg="secondary" className="px-2 py-1" style={{ fontSize: '11px' }}>
                ⏱️ {video.duration.toFixed(1)}s
              </Badge>
            )}
            {video.violations_count !== undefined && (
              <Badge bg={video.violations_count > 0 ? 'danger' : 'success'} className="px-2 py-1" style={{ fontSize: '11px' }}>
                🚨 {video.violations_count} vi phạm
              </Badge>
            )}
          </div>
        </div>

        {/* Action Button */}
        <Button
          variant="primary"
          size="sm"
          className="mt-2 rounded-pill"
          onClick={(e) => {
            e.stopPropagation();
            handleCardClick();
          }}
        >
          Xem Chi Tiết
        </Button>
      </Card.Body>
    </Card>
  );
}
