'use client';

import React, { useState, useEffect } from 'react';
import { Card, ListGroup, Button, Badge } from 'react-bootstrap';
import { useRoiStore } from '@/store/useRoiStore';
import { RoiType, ROI_COLORS, ROI_TYPE_LABELS } from '@/types/roi';

export const ROILegend: React.FC = () => {
  const rois = useRoiStore((state) => state.rois);
  const filterType = useRoiStore((state) => state.filterType);
  const hoveredType = useRoiStore((state) => state.hoveredType);
  const setFilterType = useRoiStore((state) => state.setFilterType);
  const setHoveredType = useRoiStore((state) => state.setHoveredType);
  const [isVisible, setIsVisible] = useState(true);

  // Load visibility state from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('roi-legend-visible');
    if (saved !== null) {
      setIsVisible(JSON.parse(saved));
    }
  }, []);

  // Save visibility state to localStorage
  const toggleVisibility = () => {
    const newState = !isVisible;
    setIsVisible(newState);
    localStorage.setItem('roi-legend-visible', JSON.stringify(newState));
  };

  // Count ROIs by type
  const getCountByType = (type: RoiType): number => {
    return rois.filter((roi) => roi.roi_type === type).length;
  };

  // Get all ROI types (15 types)
  const allTypes = Object.keys(ROI_TYPE_LABELS) as RoiType[];

  // Handle filter toggle
  const handleFilterToggle = (type: RoiType) => {
    if (filterType === type) {
      setFilterType(null); // Clear filter
    } else {
      setFilterType(type as string); // Set filter
    }
  };

  if (!isVisible) {
    return (
      <div style={{ position: 'fixed', top: '20px', right: '20px', zIndex: 1000 }}>
        <Button variant="secondary" size="sm" onClick={toggleVisibility}>
          Show Legend
        </Button>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        width: '250px',
        maxHeight: '80vh',
        overflowY: 'auto',
        zIndex: 1000,
      }}
    >
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <h6 className="mb-0">ROI Legend</h6>
          <Button variant="link" size="sm" onClick={toggleVisibility} className="p-0">
            ✕
          </Button>
        </Card.Header>
        <Card.Body className="p-0">
          <ListGroup variant="flush">
            {allTypes.map((type) => {
              const count = getCountByType(type);
              const isActive = filterType === type;
              const isHovered = hoveredType === type;

              return (
                <ListGroup.Item
                  key={type}
                  action
                  active={isActive}
                  onClick={() => handleFilterToggle(type)}
                  onMouseEnter={() => setHoveredType(type as string)}
                  onMouseLeave={() => setHoveredType(null)}
                  style={{
                    cursor: 'pointer',
                    backgroundColor: isHovered && !isActive ? '#f8f9fa' : undefined,
                  }}
                >
                  <div className="d-flex align-items-center justify-content-between">
                    <div className="d-flex align-items-center gap-2">
                      <div
                        style={{
                          width: '20px',
                          height: '20px',
                          backgroundColor: ROI_COLORS[type],
                          border: '1px solid #ccc',
                          borderRadius: '3px',
                        }}
                      />
                      <small>{ROI_TYPE_LABELS[type]}</small>
                    </div>
                    {count > 0 && (
                      <Badge bg="secondary" pill>
                        {count}
                      </Badge>
                    )}
                  </div>
                </ListGroup.Item>
              );
            })}
          </ListGroup>
        </Card.Body>
        {filterType && (
          <Card.Footer className="text-center py-2">
            <small className="text-muted">
              Filtering: {ROI_TYPE_LABELS[filterType as RoiType]}
              <Button
                variant="link"
                size="sm"
                className="p-0 ms-2"
                onClick={() => setFilterType(null)}
              >
                Clear
              </Button>
            </small>
          </Card.Footer>
        )}
      </Card>
    </div>
  );
};
