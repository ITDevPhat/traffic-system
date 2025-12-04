'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Card, Badge, ListGroup, Button, ButtonGroup } from 'react-bootstrap';

export function ViolationPanel({ detections = [] }) {
  const [violations, setViolations] = useState([]);
  const [violationStats, setViolationStats] = useState({});
  const [filterSeverity, setFilterSeverity] = useState('all'); // 'all', 'critical', 'high', 'medium'
  const [autoScroll, setAutoScroll] = useState(true);
  const lastViolationRef = useRef(new Map()); // track_id+type -> timestamp
  const scrollContainerRef = useRef(null);

  // Process detections to extract violations
  useEffect(() => {
    const now = Date.now();
    const newViolations = [];

    detections.forEach((det) => {
      if (det.violation && det.status === 'violation') {
        const trackId = det.track_id || -1;
        const violationType = det.violation.type;
        const key = `${trackId}_${violationType}`;

        // Debounce: only add if not seen in last 2 seconds
        const lastSeen = lastViolationRef.current.get(key);
        if (!lastSeen || now - lastSeen > 2000) {
          newViolations.push({
            id: `${now}_${trackId}_${violationType}`,
            timestamp: now,
            trackId,
            className: det.class_name || det.label || 'vehicle',
            violation: det.violation,
          });

          lastViolationRef.current.set(key, now);
        }
      }
    });

    // Add new violations to list (keep last 20)
    if (newViolations.length > 0) {
      setViolations((prev) => {
        const updated = [...newViolations, ...prev];
        return updated.slice(0, 20); // Keep only 20 most recent
      });
    }

    // Cleanup old entries from debounce map (older than 5 seconds)
    const keysToDelete = [];
    lastViolationRef.current.forEach((timestamp, key) => {
      if (now - timestamp > 5000) {
        keysToDelete.push(key);
      }
    });
    keysToDelete.forEach((key) => lastViolationRef.current.delete(key));
  }, [detections]);

  // Calculate violation statistics
  useEffect(() => {
    const stats = {};
    violations.forEach((v) => {
      const type = v.violation.type;
      stats[type] = (stats[type] || 0) + 1;
    });
    setViolationStats(stats);
  }, [violations]);

  // Auto scroll to top when new violations arrive
  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = 0;
    }
  }, [violations, autoScroll]);

  // Format timestamp
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Get severity badge color
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'danger';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      default:
        return 'secondary';
    }
  };

  // Get violation type icon
  const getViolationIcon = (type) => {
    switch (type) {
      case 'wrong_lane':
        return '🚗';
      case 'wrong_direction':
        return '⚠️';
      case 'forbidden_area':
        return '🚫';
      case 'stopline':
        return '🛑';
      case 'solid_line':
        return '〰️';
      case 'red_light':
        return '🚦';
      default:
        return '⚡';
    }
  };

  const totalViolations = violations.length;
  const filteredViolations =
    filterSeverity === 'all'
      ? violations
      : violations.filter((v) => v.violation.severity === filterSeverity);

  return (
    <Card className="shadow-sm border-0 h-100">
      <Card.Header className="bg-danger text-white">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h6 className="mb-0">🚨 Realtime Violations</h6>
          <Badge bg="light" text="dark">
            {totalViolations}
          </Badge>
        </div>

        {/* Severity Filter Buttons */}
        <ButtonGroup size="sm" className="w-100">
          <Button
            variant={filterSeverity === 'all' ? 'light' : 'outline-light'}
            onClick={() => setFilterSeverity('all')}
          >
            All ({violations.length})
          </Button>
          <Button
            variant={filterSeverity === 'critical' ? 'light' : 'outline-light'}
            onClick={() => setFilterSeverity('critical')}
          >
            Critical ({violations.filter((v) => v.violation.severity === 'critical').length})
          </Button>
          <Button
            variant={filterSeverity === 'high' ? 'light' : 'outline-light'}
            onClick={() => setFilterSeverity('high')}
          >
            High ({violations.filter((v) => v.violation.severity === 'high').length})
          </Button>
          <Button
            variant={filterSeverity === 'medium' ? 'light' : 'outline-light'}
            onClick={() => setFilterSeverity('medium')}
          >
            Medium ({violations.filter((v) => v.violation.severity === 'medium').length})
          </Button>
        </ButtonGroup>

        {/* Auto Scroll Toggle */}
        <div className="d-flex justify-content-end mt-2">
          <Button
            variant={autoScroll ? 'light' : 'outline-light'}
            size="sm"
            onClick={() => setAutoScroll(!autoScroll)}
          >
            {autoScroll ? '📌 Auto Scroll: ON' : '📌 Auto Scroll: OFF'}
          </Button>
        </div>
      </Card.Header>

      <Card.Body
        ref={scrollContainerRef}
        className="p-0"
        style={{ maxHeight: '500px', overflowY: 'auto' }}
      >
        {filteredViolations.length === 0 ? (
          <div className="text-center py-4 text-muted">
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>
              {violations.length === 0 ? '✅' : '🔍'}
            </div>
            <small>{violations.length === 0 ? 'No violations detected' : `No ${filterSeverity} violations`}</small>
          </div>
        ) : (
          <ListGroup variant="flush">
            {filteredViolations.map((v) => (
              <ListGroup.Item key={v.id} className="py-3 border-start border-5" style={{
                borderColor:
                  v.violation.severity === 'critical'
                    ? '#dc3545'
                    : v.violation.severity === 'high'
                    ? '#ffc107'
                    : '#17a2b8'
              }}>
                <div className="d-flex justify-content-between align-items-start">
                  <div className="flex-grow-1">
                    <div className="d-flex align-items-center gap-2 mb-2">
                      <span style={{ fontSize: '20px' }}>{getViolationIcon(v.violation.type)}</span>
                      <Badge bg={getSeverityColor(v.violation.severity)} className="text-uppercase">
                        {v.violation.type.replace(/_/g, ' ')}
                      </Badge>
                      <small className="text-muted">
                        Track #{v.trackId}
                      </small>
                    </div>
                    <div className="d-flex align-items-center gap-2 mb-1">
                      <Badge bg="secondary" pill>
                        {v.className}
                      </Badge>
                      <small className="text-muted">
                        📍 {v.violation.roi_name || 'Unknown ROI'}
                      </small>
                    </div>
                    {v.violation.message && (
                      <div className="small mt-2 p-2 bg-light rounded">
                        💬 {v.violation.message}
                      </div>
                    )}
                  </div>
                  <div className="text-end">
                    <small className="text-muted text-nowrap">
                      {formatTime(v.timestamp)}
                    </small>
                  </div>
                </div>
              </ListGroup.Item>
            ))}
          </ListGroup>
        )}
      </Card.Body>

      {/* Statistics Footer */}
      {Object.keys(violationStats).length > 0 && (
        <Card.Footer className="bg-light">
          <small className="text-muted">
            <strong>Stats:</strong>{' '}
            {Object.entries(violationStats).map(([type, count], idx) => (
              <span key={type}>
                {idx > 0 && ' • '}
                {type.replace(/_/g, ' ')}: {count}
              </span>
            ))}
          </small>
        </Card.Footer>
      )}
    </Card>
  );
}
