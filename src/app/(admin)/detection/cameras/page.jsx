'use client';
import React, { useState } from 'react';
import { Button, Card, Tabs, Tab } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import { DetectionGrid } from '@/components/DetectionGrid';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CamerasPage() {
  const router = useRouter();

  return (
    <>
      <PageTitle title="Cameras - Traffic Detection" />
      <div className="container-fluid mt-3">
        {/* Header with Actions */}
        <Card className="mb-3 shadow-sm">
          <Card.Body>
            <div className="d-flex justify-content-between align-items-center flex-wrap gap-3">
              <div>
                <h5 className="mb-1">📹 Cameras Dashboard</h5>
                <p className="text-muted small mb-0">Danh sách camera/video để phát hiện vi phạm giao thông</p>
              </div>
            </div>
          </Card.Body>
        </Card>

        {/* Grid View */}
        <Card className="shadow-sm">
          <Card.Body>
            <DetectionGrid autoRefresh={true} refreshInterval={30000} />
          </Card.Body>
        </Card>
      </div>
    </>
  );
}

