'use client';
import React, { useState, useEffect } from 'react';
import { Card, Badge, Table, Button, Form, Row, Col } from 'react-bootstrap';

const LicensePlatePanel = ({ detections = [], isConnected = false }) => {
  const [plateHistory, setPlateHistory] = useState([]);
  const [settings, setSettings] = useState({
    showConfidence: true,
    minConfidence: 0.6,
    maxHistory: 50,
    autoScroll: true
  });

  // Extract license plates from detections
  useEffect(() => {
    if (!detections || detections.length === 0) return;

    const newPlates = [];
    const timestamp = Date.now();

    detections.forEach(obj => {
      if (obj.plate && obj.plate.trim()) {
        // Check if confidence meets minimum threshold
        const confidence = obj.plate_confidence || obj.confidence || 1.0;
        if (confidence >= settings.minConfidence) {
          newPlates.push({
            id: `${obj.track_id}-${timestamp}`,
            track_id: obj.track_id,
            plate_text: obj.plate.trim(),
            confidence: confidence,
            class_name: obj.class_name || 'vehicle',
            timestamp: timestamp,
            bbox: obj.bbox,
            is_violation: obj.is_violation || false
          });
        }
      }
    });

    if (newPlates.length > 0) {
      setPlateHistory(prev => {
        // Add new plates and remove duplicates (same track_id + plate_text)
        const updated = [...prev];
        
        newPlates.forEach(newPlate => {
          // Check if this plate already exists for this track
          const existingIndex = updated.findIndex(p => 
            p.track_id === newPlate.track_id && 
            p.plate_text === newPlate.plate_text
          );
          
          if (existingIndex >= 0) {
            // Update existing plate with latest info
            updated[existingIndex] = { ...updated[existingIndex], ...newPlate };
          } else {
            // Add new plate
            updated.push(newPlate);
          }
        });

        // Sort by timestamp (newest first) and limit history
        return updated
          .sort((a, b) => b.timestamp - a.timestamp)
          .slice(0, settings.maxHistory);
      });
    }
  }, [detections, settings.minConfidence, settings.maxHistory]);

  const clearHistory = () => {
    setPlateHistory([]);
  };

  const exportPlates = () => {
    if (plateHistory.length === 0) return;

    const exportData = {
      export_time: new Date().toISOString(),
      total_plates: plateHistory.length,
      plates: plateHistory.map(plate => ({
        plate_text: plate.plate_text,
        confidence: plate.confidence,
        vehicle_type: plate.class_name,
        detection_time: new Date(plate.timestamp).toISOString(),
        track_id: plate.track_id,
        is_violation: plate.is_violation
      }))
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `license_plates_${Date.now()}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getConfidenceBadge = (confidence) => {
    if (confidence >= 0.9) return 'success';
    if (confidence >= 0.7) return 'warning';
    return 'danger';
  };

  // Get unique plates count
  const uniquePlates = new Set(plateHistory.map(p => p.plate_text)).size;
  const violationPlates = plateHistory.filter(p => p.is_violation).length;

  return (
    <Card className="h-100">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div>
          <h6 className="mb-0">🚗 License Plates</h6>
          <small className="text-muted">
            {plateHistory.length} detections • {uniquePlates} unique plates
            {violationPlates > 0 && ` • ${violationPlates} violations`}
          </small>
        </div>
        <div className="d-flex gap-2">
          <Badge bg={isConnected ? 'success' : 'secondary'}>
            {isConnected ? '🟢 Live' : '🔴 Offline'}
          </Badge>
          {plateHistory.length > 0 && (
            <>
              <Button size="sm" variant="outline-primary" onClick={exportPlates}>
                💾
              </Button>
              <Button size="sm" variant="outline-danger" onClick={clearHistory}>
                🗑️
              </Button>
            </>
          )}
        </div>
      </Card.Header>

      <Card.Body className="p-0">
        {/* Settings Panel */}
        <div className="p-3 border-bottom bg-light">
          <Row className="g-2 align-items-center">
            <Col md={3}>
              <Form.Group className="mb-0">
                <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>
                  Min Confidence: {settings.minConfidence}
                </Form.Label>
                <Form.Range
                  size="sm"
                  value={settings.minConfidence}
                  min={0.1}
                  max={0.95}
                  step={0.05}
                  onChange={(e) => setSettings(prev => ({ 
                    ...prev, 
                    minConfidence: parseFloat(e.target.value) 
                  }))}
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group className="mb-0">
                <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>
                  Max History: {settings.maxHistory}
                </Form.Label>
                <Form.Select
                  size="sm"
                  value={settings.maxHistory}
                  onChange={(e) => setSettings(prev => ({ 
                    ...prev, 
                    maxHistory: parseInt(e.target.value) 
                  }))}
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Check
                type="switch"
                id="show-confidence"
                label="Show Confidence"
                checked={settings.showConfidence}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  showConfidence: e.target.checked 
                }))}
                style={{ fontSize: '0.85rem' }}
              />
            </Col>
            <Col md={3}>
              <Form.Check
                type="switch"
                id="auto-scroll"
                label="Auto Scroll"
                checked={settings.autoScroll}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  autoScroll: e.target.checked 
                }))}
                style={{ fontSize: '0.85rem' }}
              />
            </Col>
          </Row>
        </div>

        {/* License Plates Table */}
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {plateHistory.length === 0 ? (
            <div className="text-center py-4 text-muted">
              <div style={{ fontSize: '2rem' }}>🚗</div>
              <p className="mb-0">No license plates detected</p>
              <small>Plates will appear here during live detection</small>
            </div>
          ) : (
            <Table striped hover size="sm" className="mb-0">
              <thead className="table-dark sticky-top">
                <tr>
                  <th style={{ width: '25%' }}>License Plate</th>
                  <th style={{ width: '15%' }}>Vehicle</th>
                  <th style={{ width: '10%' }}>Track ID</th>
                  {settings.showConfidence && <th style={{ width: '15%' }}>Confidence</th>}
                  <th style={{ width: '15%' }}>Time</th>
                  <th style={{ width: '10%' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {plateHistory.map((plate, index) => (
                  <tr 
                    key={plate.id}
                    className={plate.is_violation ? 'table-danger' : ''}
                  >
                    <td>
                      <strong style={{ 
                        fontFamily: 'monospace', 
                        fontSize: '1.1rem',
                        color: plate.is_violation ? '#dc3545' : '#0066cc'
                      }}>
                        {plate.plate_text}
                      </strong>
                    </td>
                    <td>
                      <Badge bg="secondary" className="text-capitalize">
                        {plate.class_name}
                      </Badge>
                    </td>
                    <td>
                      <code>#{plate.track_id}</code>
                    </td>
                    {settings.showConfidence && (
                      <td>
                        <Badge bg={getConfidenceBadge(plate.confidence)}>
                          {(plate.confidence * 100).toFixed(1)}%
                        </Badge>
                      </td>
                    )}
                    <td>
                      <small className="text-muted">
                        {formatTime(plate.timestamp)}
                      </small>
                    </td>
                    <td>
                      {plate.is_violation ? (
                        <Badge bg="danger">🚨 Violation</Badge>
                      ) : (
                        <Badge bg="success">✅ Normal</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
      </Card.Body>

      {plateHistory.length > 0 && (
        <Card.Footer className="text-center py-2">
          <small className="text-muted">
            Showing {plateHistory.length} most recent detections
            {settings.autoScroll && ' • Auto-scrolling enabled'}
          </small>
        </Card.Footer>
      )}
    </Card>
  );
};

export default LicensePlatePanel;