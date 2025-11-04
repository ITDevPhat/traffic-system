'use client';
import React, { useState } from 'react';
import { Button, Card, Tabs, Tab } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import { DetectionGrid } from '@/components/DetectionGrid';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DetectionGridPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('grid');

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
                <p className="text-muted small mb-0">Xem tất cả video đã xử lý và phát hiện vi phạm</p>
              </div>
              <div className="d-flex gap-2">
                <Link href="/detection/live">
                  <Button variant="primary" className="rounded-pill">
                    🎥 Live Detection
                  </Button>
                </Link>
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

