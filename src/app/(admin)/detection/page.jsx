'use client';
import React, { useState } from 'react';
import { Button, Card, Form, Badge } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import { DetectionGrid } from '@/components/DetectionGrid';
import Link from 'next/link';

export default function DetectionPage() {
  const [realtimeMode, setRealtimeMode] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);

  return (
    <>
      <PageTitle title="Traffic Violation Detection Dashboard" />
      <div className="container-fluid mt-3">
        {/* Header with Actions */}
        <Card className="mb-3 shadow-sm">
          <Card.Body>
            <div className="d-flex justify-content-between align-items-center flex-wrap gap-3">
              <div>
                <h5 className="mb-1">📹 Detection Dashboard</h5>
                <p className="text-muted small mb-0">
                  {realtimeMode 
                    ? '🔴 Realtime Detection Mode - YOLO + ByteTrack với bbox overlay' 
                    : '📊 Static Mode - Chỉ hiển thị video preview'}
                </p>
              </div>
              <div className="d-flex gap-2 align-items-center flex-wrap">
                {/* Realtime Toggle */}
                <Form.Check 
                  type="switch"
                  id="realtime-switch"
                  label={
                    <span className="d-flex align-items-center gap-1">
                      {realtimeMode ? '🔴' : '⚪'} Realtime Detection
                      {realtimeMode && <Badge bg="danger" className="ms-1">LIVE</Badge>}
                    </span>
                  }
                  checked={realtimeMode}
                  onChange={(e) => setRealtimeMode(e.target.checked)}
                  className="me-3"
                />

                {/* Auto Refresh Toggle */}
                <Form.Check 
                  type="switch"
                  id="refresh-switch"
                  label="🔄 Auto Refresh"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="me-3"
                />

                <Link href="/detection/live">
                  <Button variant="primary" className="rounded-pill">
                    🎥 Live Detection
                  </Button>
                </Link>
              </div>
            </div>
          </Card.Body>
        </Card>

        {/* Info Banner */}
        {realtimeMode && (
          <Card className="mb-3 border-warning shadow-sm">
            <Card.Body className="py-2">
              <div className="d-flex align-items-center gap-2">
                <span style={{ fontSize: '20px' }}>⚡</span>
                <div className="small">
                  <strong>Realtime Detection Active:</strong> Click <kbd>▶️ Start Detection</kbd> trên mỗi card để bắt đầu phát hiện realtime với YOLO + ByteTrack.
                  Model tự động load định dạng tối ưu (.engine {'->'} .onnx {'->'} .pt).
                </div>
              </div>
            </Card.Body>
          </Card>
        )}

        {/* Grid View */}
        <Card className="shadow-sm">
          <Card.Body>
            <DetectionGrid 
              autoRefresh={autoRefresh} 
              refreshInterval={30000} 
              useRealtime={realtimeMode}
            />
          </Card.Body>
        </Card>
      </div>
    </>
  );
}

