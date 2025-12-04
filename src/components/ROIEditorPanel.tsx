'use client';

import React, { useState, useEffect } from 'react';
import { Button, Form, Card, ListGroup } from 'react-bootstrap';
import { useRoiStore } from '@/store/useRoiStore';
import {
  RoiType,
  ROI_COLORS,
  ROI_SHAPES,
  ROI_TYPE_LABELS,
  Roi,
  RoiMetadata,
} from '@/types/roi';
import { ROIDrawingControls } from './ROIDrawingControls';

export const ROIEditorPanel: React.FC = () => {
  // Store state
  const rois = useRoiStore((state) => state.rois);
  const selectedRoiId = useRoiStore((state) => state.selectedRoiId);
  const currentCamera = useRoiStore((state) => state.currentCamera);
  const drawingMode = useRoiStore((state) => state.drawingMode);
  const addRoi = useRoiStore((state) => state.addRoi);
  const deleteRoi = useRoiStore((state) => state.deleteRoi);
  const cloneRoi = useRoiStore((state) => state.cloneRoi);
  const selectRoi = useRoiStore((state) => state.selectRoi);

  // Form state
  const [formData, setFormData] = useState({
    roi_type: 'detection_zone' as RoiType,
    name: '',
    metadata: {} as RoiMetadata,
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Get selected ROI
  const selectedRoi = rois.find((r) => r.id === selectedRoiId);

  // Keyboard shortcut for Delete
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle Delete when not in drawing mode and ROI is selected
      if (e.key === 'Delete' && selectedRoiId && !drawingMode) {
        handleDelete(selectedRoiId);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedRoiId, drawingMode]);

  // Handle type change
  const handleTypeChange = (type: RoiType) => {
    setFormData({
      ...formData,
      roi_type: type,
      metadata: {},
    });
  };

  // Handle drawing complete
  const handleDrawingComplete = () => {
    const currentPoints = useRoiStore.getState().currentPoints;
    const shape = ROI_SHAPES[formData.roi_type];

    // Add ROI with current points
    addRoi({
      roi_type: formData.roi_type,
      name: formData.name,
      shape: shape,
      coordinates: currentPoints,
      color: ROI_COLORS[formData.roi_type],
      metadata: formData.metadata,
    });

    // Reset form and drawing mode
    useRoiStore.getState().setDrawingMode(false);
    useRoiStore.getState().clearPoints();

    // Reset form
    setFormData({
      roi_type: 'detection_zone',
      name: '',
      metadata: {},
    });
    setValidationErrors([]);

    alert('ROI created successfully!');
  };

  // Handle form submit (for non-drawing mode - not used currently)
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate
    const errors: string[] = [];
    if (!formData.name || formData.name.trim().length < 3) {
      errors.push('Name must be at least 3 characters');
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    // Clear errors
    setValidationErrors([]);
  };

  // Handle edit ROI
  const handleEdit = (roi: Roi) => {
    setEditingId(roi.id);
    setFormData({
      roi_type: roi.roi_type,
      name: roi.name,
      metadata: roi.metadata || {},
    });
    selectRoi(roi.id);
  };

  // Handle delete ROI
  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this ROI?')) {
      deleteRoi(id);
    }
  };

  // Handle clone ROI
  const handleClone = (id: string) => {
    cloneRoi(id);
  };

  // Handle export JSON
  const handleExportJSON = async () => {
    try {
      const { RoiService } = await import('@/services/roiService');
      const json = RoiService.exportToJson(currentCamera || 'unknown', rois);

      // Create download link
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `roi-config-${currentCamera || 'export'}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      alert('JSON exported successfully!');
    } catch (error) {
      console.error('Export error:', error);
      alert('Failed to export JSON');
    }
  };

  // Handle import JSON
  const handleImportJSON = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';

    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const { RoiService } = await import('@/services/roiService');
        const { rois: importedRois } = RoiService.importFromJson(text);

        if (
          confirm(
            `This will replace all existing ROIs (${rois.length} ROIs). Continue?`
          )
        ) {
          // Clear existing ROIs and add imported ones
          rois.forEach((roi) => deleteRoi(roi.id));
          importedRois.forEach((roi) => {
            addRoi({
              roi_type: roi.roi_type,
              name: roi.name,
              shape: roi.shape,
              coordinates: roi.coordinates,
              color: roi.color,
              metadata: roi.metadata,
            });
          });

          alert(`Successfully imported ${importedRois.length} ROIs`);
        }
      } catch (error) {
        console.error('Import error:', error);
        alert(`Failed to import JSON: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    };

    input.click();
  };

  return (
    <div className="roi-editor-panel" style={{ width: '350px', height: '100%', overflowY: 'auto' }}>
      <Card className="mb-3">
        <Card.Header>
          <h5 className="mb-0">ROI Editor</h5>
        </Card.Header>
        <Card.Body>
          {/* Action Buttons */}
          <div className="d-flex gap-2 mb-3 flex-wrap">
            <Button variant="primary" size="sm" onClick={() => setEditingId(null)}>
              + Add ROI
            </Button>
            <Button
              variant="success"
              size="sm"
              onClick={async () => {
                try {
                  await useRoiStore.getState().saveToBackend();
                  alert('ROIs saved to backend successfully!');
                } catch (error) {
                  console.error('Save error:', error);
                  alert(`Failed to save ROIs: ${error instanceof Error ? error.message : 'Unknown error'}`);
                }
              }}
              disabled={rois.length === 0 || !currentCamera}
              title={!currentCamera ? 'Please set camera ID first' : 'Save ROIs to backend'}
            >
              💾 Save to Backend
            </Button>
            <Button
              variant="info"
              size="sm"
              onClick={async () => {
                const cameraId = prompt('Enter camera ID to load ROIs:', currentCamera || 'camera_01');
                if (!cameraId) return;

                try {
                  await useRoiStore.getState().loadFromBackend(cameraId);
                  alert(`Loaded ROIs from backend for camera: ${cameraId}`);
                } catch (error) {
                  console.error('Load error:', error);
                  alert(`Failed to load ROIs: ${error instanceof Error ? error.message : 'Unknown error'}`);
                }
              }}
            >
              📥 Load from Backend
            </Button>
            <Button variant="outline-secondary" size="sm" onClick={handleImportJSON}>
              Import JSON
            </Button>
            <Button variant="outline-success" size="sm" onClick={handleExportJSON}>
              Export JSON
            </Button>
          </div>

          {/* Camera ID Input */}
          <Form.Group className="mb-3">
            <Form.Label>Camera ID</Form.Label>
            <Form.Control
              type="text"
              value={currentCamera}
              onChange={(e) => useRoiStore.getState().setCurrentCamera(e.target.value)}
              placeholder="e.g., camera_01"
            />
            <Form.Text className="text-muted">
              Used for saving/loading ROIs from backend
            </Form.Text>
          </Form.Group>

          {/* ROI Form */}
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Type</Form.Label>
              <Form.Select
                value={formData.roi_type}
                onChange={(e) => handleTypeChange(e.target.value as RoiType)}
              >
                {Object.keys(ROI_TYPE_LABELS).map((type) => (
                  <option key={type} value={type}>
                    {ROI_TYPE_LABELS[type as RoiType]}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter ROI name"
                isInvalid={validationErrors.length > 0}
              />
              <Form.Control.Feedback type="invalid">
                {validationErrors.join(', ')}
              </Form.Control.Feedback>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Shape (Auto)</Form.Label>
              <Form.Control
                type="text"
                value={ROI_SHAPES[formData.roi_type]}
                disabled
                readOnly
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Color (Auto)</Form.Label>
              <div className="d-flex align-items-center gap-2">
                <div
                  style={{
                    width: '30px',
                    height: '30px',
                    backgroundColor: ROI_COLORS[formData.roi_type],
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                  }}
                />
                <Form.Control
                  type="text"
                  value={ROI_COLORS[formData.roi_type]}
                  disabled
                  readOnly
                  style={{ flex: 1 }}
                />
              </div>
            </Form.Group>

            {/* Metadata Editor for Special ROI Types */}
            {(formData.roi_type === 'direction_zone' || formData.roi_type === 'wrong_direction') && (
              <Form.Group className="mb-3">
                <Form.Label>Allowed Heading (degrees)</Form.Label>
                <div className="d-flex gap-2 align-items-center">
                  <Form.Control
                    type="number"
                    min="0"
                    max="360"
                    value={formData.metadata.allowed_heading?.[0] || 0}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        metadata: {
                          ...formData.metadata,
                          allowed_heading: [
                            parseInt(e.target.value),
                            formData.metadata.allowed_heading?.[1] || 360,
                          ],
                        },
                      })
                    }
                    placeholder="Min"
                  />
                  <span>to</span>
                  <Form.Control
                    type="number"
                    min="0"
                    max="360"
                    value={formData.metadata.allowed_heading?.[1] || 360}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        metadata: {
                          ...formData.metadata,
                          allowed_heading: [
                            formData.metadata.allowed_heading?.[0] || 0,
                            parseInt(e.target.value),
                          ],
                        },
                      })
                    }
                    placeholder="Max"
                  />
                </div>
                <Form.Text className="text-muted">
                  Configure heading range to detect vehicles going wrong way
                </Form.Text>
              </Form.Group>
            )}

            {(formData.roi_type === 'lane_car' ||
              formData.roi_type === 'lane_bike' ||
              formData.roi_type === 'lane_bus' ||
              formData.roi_type === 'lane_truck') && (
              <Form.Group className="mb-3">
                <Form.Label>Allowed Vehicle Classes</Form.Label>
                <div className="d-flex flex-column gap-2">
                  {['car', 'bus', 'truck', 'motorbike'].map((vehicleClass) => (
                    <Form.Check
                      key={vehicleClass}
                      type="checkbox"
                      id={`class-${vehicleClass}`}
                      label={vehicleClass.charAt(0).toUpperCase() + vehicleClass.slice(1)}
                      checked={formData.metadata.allowed_classes?.includes(vehicleClass) || false}
                      onChange={(e) => {
                        const currentClasses = formData.metadata.allowed_classes || [];
                        const newClasses = e.target.checked
                          ? [...currentClasses, vehicleClass]
                          : currentClasses.filter((c) => c !== vehicleClass);

                        setFormData({
                          ...formData,
                          metadata: {
                            ...formData.metadata,
                            allowed_classes: newClasses,
                          },
                        });
                      }}
                    />
                  ))}
                </div>
                <Form.Text className="text-muted">
                  Select which vehicle types are allowed in this lane
                </Form.Text>
              </Form.Group>
            )}

            {formData.roi_type === 'stopline' && (
              <Form.Group className="mb-3">
                <Form.Label>Related Traffic Light</Form.Label>
                <Form.Select
                  value={formData.metadata.related_light || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      metadata: {
                        ...formData.metadata,
                        related_light: e.target.value || undefined,
                      },
                    })
                  }
                >
                  <option value="">None (optional)</option>
                  {rois
                    .filter((r) => r.roi_type === 'traffic_light')
                    .map((light) => (
                      <option key={light.id} value={light.id}>
                        {light.name}
                      </option>
                    ))}
                </Form.Select>
                <Form.Text className="text-muted">
                  Link this stopline to a traffic light for red light violation detection
                </Form.Text>
              </Form.Group>
            )}

            {formData.roi_type === 'traffic_light' && (
              <Form.Group className="mb-3">
                <Form.Label>Description</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={formData.metadata.description || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      metadata: {
                        ...formData.metadata,
                        description: e.target.value,
                      },
                    })
                  }
                  placeholder="Enter traffic light description"
                />
              </Form.Group>
            )}

            {/* Drawing Controls */}
            <ROIDrawingControls
              roiType={formData.roi_type}
              roiName={formData.name}
              onDrawingComplete={handleDrawingComplete}
            />
          </Form>
        </Card.Body>
      </Card>

      {/* ROI List */}
      <Card className="mb-3">
        <Card.Header>
          <h6 className="mb-0">ROI List ({rois.length})</h6>
        </Card.Header>
        <Card.Body className="p-0">
          {rois.length === 0 ? (
            <div className="p-3 text-center text-muted">No ROIs yet</div>
          ) : (
            <ListGroup variant="flush">
              {rois.map((roi) => (
                <ListGroup.Item
                  key={roi.id}
                  active={roi.id === selectedRoiId}
                  className="d-flex align-items-center justify-content-between"
                >
                  <div className="d-flex align-items-center gap-2 flex-grow-1">
                    <div
                      style={{
                        width: '20px',
                        height: '20px',
                        backgroundColor: roi.color,
                        border: '1px solid #ccc',
                        borderRadius: '3px',
                      }}
                    />
                    <div>
                      <div className="fw-bold">{roi.name}</div>
                      <small className="text-muted">{ROI_TYPE_LABELS[roi.roi_type]}</small>
                    </div>
                  </div>
                  <div className="d-flex gap-1">
                    <Button
                      variant="outline-primary"
                      size="sm"
                      onClick={() => handleEdit(roi)}
                      title="Edit"
                    >
                      ✏️
                    </Button>
                    <Button
                      variant="outline-secondary"
                      size="sm"
                      onClick={() => handleClone(roi.id)}
                      title="Clone"
                    >
                      📋
                    </Button>
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => handleDelete(roi.id)}
                      title="Delete"
                    >
                      🗑️
                    </Button>
                  </div>
                </ListGroup.Item>
              ))}
            </ListGroup>
          )}
        </Card.Body>
      </Card>

      {/* JSON Preview */}
      {selectedRoi && (
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">JSON Preview</h6>
            <Button
              variant="outline-primary"
              size="sm"
              onClick={() => {
                const json = JSON.stringify(
                  {
                    roi_type: selectedRoi.roi_type,
                    name: selectedRoi.name,
                    coordinates: selectedRoi.coordinates.map((p) => [p.x, p.y]),
                    color: selectedRoi.color,
                    metadata: selectedRoi.metadata || {},
                  },
                  null,
                  2
                );
                navigator.clipboard.writeText(json);
                alert('JSON copied to clipboard!');
              }}
            >
              Copy JSON
            </Button>
          </Card.Header>
          <Card.Body>
            <pre
              style={{
                backgroundColor: '#f5f5f5',
                padding: '10px',
                borderRadius: '4px',
                fontSize: '12px',
                maxHeight: '300px',
                overflow: 'auto',
              }}
            >
              {JSON.stringify(
                {
                  roi_type: selectedRoi.roi_type,
                  name: selectedRoi.name,
                  coordinates: selectedRoi.coordinates.map((p) => [p.x, p.y]),
                  color: selectedRoi.color,
                  metadata: selectedRoi.metadata || {},
                },
                null,
                2
              )}
            </pre>
          </Card.Body>
        </Card>
      )}
    </div>
  );
};
