'use client';
import React, { useState, useEffect } from 'react';
import { Row, Col, Spinner, Alert } from 'react-bootstrap';
import { DetectionCard } from './DetectionCard';
import { DetectionCardRealtime } from './DetectionCardRealtime';
import { fetchVideos } from '@/services/api';

export function DetectionGrid({ 
  videos: initialVideos = null, 
  autoRefresh = true, 
  refreshInterval = 30000,
  useRealtime = true  // Enable realtime detection by default
}) {
  const [videos, setVideos] = useState(initialVideos || []);
  const [loading, setLoading] = useState(!initialVideos);
  const [error, setError] = useState(null);

  const loadVideos = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to load from database first
      try {
        const response = await fetchVideos({ limit: 100 });
        // Handle both response formats: { videos: [...] } or [...]
        const videoList = Array.isArray(response) ? response : (response.videos || []);
        if (videoList && videoList.length > 0) {
          setVideos(videoList);
          return;
        }
      } catch (dbErr) {
        console.warn('Database load failed, trying folder fallback:', dbErr);
      }
      
      // Fallback: Load from folder if database fails or empty
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const fallbackResponse = await fetch(`${API_URL}/api/videos/from-folder`);
      if (fallbackResponse.ok) {
        const fallbackData = await fallbackResponse.json();
        const videoList = Array.isArray(fallbackData) ? fallbackData : (fallbackData.videos || []);
        setVideos(videoList);
      } else {
        throw new Error('Không thể tải video từ database hoặc thư mục');
      }
    } catch (err) {
      console.error('Error loading videos:', err);
      setError(err.message || 'Không thể tải danh sách video');
      setVideos([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialVideos) {
      loadVideos();
    }
  }, [initialVideos]);

  // Auto refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      loadVideos();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  if (loading && videos.length === 0) {
    return (
      <div className="text-center py-5">
        <Spinner animation="border" role="status" className="mb-3">
          <span className="visually-hidden">Đang tải...</span>
        </Spinner>
        <p className="text-muted">Đang tải danh sách video...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="danger" className="m-4">
        <Alert.Heading>Lỗi tải dữ liệu</Alert.Heading>
        <p>{error}</p>
        <button className="btn btn-sm btn-danger" onClick={loadVideos}>
          Thử lại
        </button>
      </Alert>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="text-center py-5">
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>📹</div>
        <h5 className="text-muted">Chưa có video nào</h5>
        <p className="text-muted small">Tải video lên để bắt đầu phát hiện vi phạm</p>
      </div>
    );
  }

  // Choose which card component to use
  const CardComponent = useRealtime ? DetectionCardRealtime : DetectionCard;

  return (
    <Row className="g-4">
      {videos.map((video) => {
        const key = video.id || video.video_job_id || video.filename || video.file_name || Math.random();
        return (
          <Col key={key} xs={12} md={6} lg={6}>
            <CardComponent video={video} />
          </Col>
        );
      })}
    </Row>
  );
}

