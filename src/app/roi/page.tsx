'use client';

import React, { useEffect, useState } from 'react';
import { Container, Row, Col, Form, Button, Spinner, Tabs, Tab, Card } from 'react-bootstrap';
import { ROIEditorPanel } from '@/components/ROIEditorPanel';
import { ROIOverlay } from '@/components/ROIOverlay';
import { ROILegend } from '@/components/ROILegend';
import { ROIPointEditor } from '@/components/ROIPointEditor';
import { useRoiStore } from '@/store/useRoiStore';

export default function ROIEditorPage() {
  const [selectedCamera, setSelectedCamera] = useState('CAM_Q7_01');
  const [videoSize, setVideoSize] = useState({ width: 1280, height: 720 });

  const currentCamera = useRoiStore((state) => state.currentCamera);
  const loading = useRoiStore((state) => state.loading);
  const error = useRoiStore((state) => state.error);
  const setCurrentCamera = useRoiStore((state) => state.setCurrentCamera);
  const loadFromBackend = useRoiStore((state) => state.loadFromBackend);
  const saveToBackend = useRoiStore((state) => state.saveToBackend);

  // Load ROIs on mount and camera change
  useEffect(() => {
    if (selectedCamera) {
      setCurrentCamera(selectedCamera);
      loadFromBackend(selectedCamera).catch((err) => {
        console.error('Failed to load ROIs:', err);
      });
    }
  }, [selectedCamera]);

  // Handle save
  const handleSave = async () => {
    try {
      await saveToBackend();
      alert('ROIs saved successfully!');
    } catch (err) {
      console.error('Save error:', err);
      alert('Failed to save ROIs');
    }
  };

  return (
    <Container fluid className="p-4">
      {/* Header */}
      <Row className="mb-4">
        <Col>
          <h2>Advanced ROI Editor</h2>
          <p className="text-muted">
            Configure detection zones, lanes, and other ROI types for traffic monitoring
          </p>
        </Col>
      </Row>

      {/* Camera Selector and Actions */}
      <Row className="mb-3">
        <Col md={6}>
          <Form.Group>
            <Form.Label>Camera</Form.Label>
            <Form.Select
              value={selectedCamera}
              onChange={(e) => setSelectedCamera(e.target.value)}
              disabled={loading}
            >
              <option value="CAM_Q7_01">Camera Q7-01</option>
              <option value="CAM_Q7_02">Camera Q7-02</option>
              <option value="CAM_Q7_03">Camera Q7-03</option>
            </Form.Select>
          </Form.Group>
        </Col>
        <Col md={6} className="d-flex align-items-end gap-2">
          <Button variant="success" onClick={handleSave} disabled={loading}>
            {loading ? <Spinner animation="border" size="sm" /> : '💾 Save ROIs'}
          </Button>
          <Button
            variant="outline-secondary"
            onClick={() => loadFromBackend(selectedCamera)}
            disabled={loading}
          >
            🔄 Reload
          </Button>
        </Col>
      </Row>

      {/* Error Display */}
      {error && (
        <Row className="mb-3">
          <Col>
            <div className="alert alert-danger">{error}</div>
          </Col>
        </Row>
      )}

      {/* Main Content */}
      <Row>
        {/* Left Panel - ROI Editor with Tabs */}
        <Col md={3}>
          <Card>
            <Card.Body className="p-2">
              <Tabs defaultActiveKey="draw" className="mb-2">
                <Tab eventKey="draw" title="✏️ Draw">
                  <ROIEditorPanel />
                </Tab>
                <Tab eventKey="edit" title="🔧 Edit Points">
                  <Card.Body className="p-3">
                    <ROIPointEditor
                      videoWidth={videoSize.width}
                      videoHeight={videoSize.height}
                    />
                  </Card.Body>
                </Tab>
              </Tabs>
            </Card.Body>
          </Card>
        </Col>

        {/* Center - Video Canvas */}
        <Col md={9}>
          <div
            style={{
              position: 'relative',
              width: '100%',
              maxWidth: `${videoSize.width}px`,
              margin: '0 auto',
            }}
          >
            {/* Video Background (placeholder) */}
            <div
              style={{
                width: videoSize.width,
                height: videoSize.height,
                backgroundColor: '#000',
                position: 'relative',
                border: '2px solid #ccc',
                borderRadius: '4px',
              }}
            >
              {/* Placeholder text */}
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  color: '#666',
                  textAlign: 'center',
                }}
              >
                <h4>Video Feed</h4>
                <p>Camera: {currentCamera || 'Not selected'}</p>
                <small>Video stream will be displayed here</small>
              </div>

              {/* ROI Overlay */}
              <ROIOverlay videoWidth={videoSize.width} videoHeight={videoSize.height} />
            </div>

            {/* Video Controls */}
            <div className="mt-2 d-flex gap-2">
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => setVideoSize({ width: 1280, height: 720 })}
              >
                720p
              </Button>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => setVideoSize({ width: 1920, height: 1080 })}
              >
                1080p
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      {/* ROI Legend (floating) */}
      <ROILegend />
    </Container>
  );
}
