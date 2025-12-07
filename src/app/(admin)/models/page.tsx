'use client';

import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Row, Col, Alert, Form } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { fetchModels, AIModel } from '@/services/modelsApi';
import { toast } from 'react-toastify';

export default function ModelsPage() {
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hiddenItems, setHiddenItems] = useState<Set<number>>(new Set());
  const [filterType, setFilterType] = useState<string>('all');

  const loadModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = filterType !== 'all' ? { model_type: filterType } : undefined;
      const data = await fetchModels(params);
      setModels(data);
    } catch (err: any) {
      setError(err.message || 'Không thể tải danh sách mô hình');
      toast.error('Không thể tải danh sách mô hình');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, [filterType]);

  const handleDelete = (modelId: number) => {
    // Không xóa DB, chỉ ẩn item trên UI
    setHiddenItems(prev => new Set(prev).add(modelId));
    toast.success('Đã ẩn mô hình khỏi danh sách');
  };

  const getModelTypeBadge = (type: string) => {
    const variants: Record<string, string> = {
      vehicle: 'primary',
      plate: 'success',
      ocr: 'info',
      traffic_light: 'warning',
      violation: 'danger',
    };
    return variants[type] || 'secondary';
  };

  const getModelTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      vehicle: 'Phương tiện',
      plate: 'Biển số',
      ocr: 'OCR',
      traffic_light: 'Đèn giao thông',
      violation: 'Vi phạm',
    };
    return labels[type] || type;
  };

  const visibleModels = models.filter(
    model => !hiddenItems.has(model.model_id)
  );

  return (
    <>
      <PageTitle title="Quản lý mô hình AI" subName="Danh sách" />

      <Card className="shadow-sm">
        <Card.Header className="bg-white py-3">
          <Row className="align-items-center">
            <Col md={6}>
              <h5 className="mb-0">🧠 Danh sách mô hình AI</h5>
            </Col>
            <Col md={6} className="d-flex justify-content-end gap-2">
              <Form.Select
                style={{ width: '200px' }}
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
              >
                <option value="all">Tất cả loại</option>
                <option value="vehicle">Phương tiện</option>
                <option value="plate">Biển số</option>
                <option value="ocr">OCR</option>
                <option value="traffic_light">Đèn giao thông</option>
                <option value="violation">Vi phạm</option>
              </Form.Select>
              <Link href="/models/create" passHref legacyBehavior>
                <Button variant="primary">
                  <i className="ri-add-line me-1"></i>
                  Thêm mô hình
                </Button>
              </Link>
              <Button variant="secondary" onClick={loadModels}>
                <i className="ri-refresh-line me-1"></i>
                Làm mới
              </Button>
            </Col>
          </Row>
        </Card.Header>

        <Card.Body className="p-0">
          {error && (
            <Alert variant="danger" className="m-3">
              {error}
            </Alert>
          )}

          <div className="table-responsive">
            <Table hover className="mb-0 align-middle">
              <thead className="bg-light">
                <tr>
                  <th className="ps-4">ID</th>
                  <th>Tên mô hình</th>
                  <th>Loại</th>
                  <th>Framework</th>
                  <th>Phiên bản</th>
                  <th>Confidence</th>
                  <th>Đường dẫn</th>
                  <th className="text-end pe-4">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status"></div>
                      <p className="mt-2 text-muted">Đang tải dữ liệu...</p>
                    </td>
                  </tr>
                ) : visibleModels.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-5 text-muted">
                      Chưa có mô hình nào.
                    </td>
                  </tr>
                ) : (
                  visibleModels.map((model) => (
                    <tr key={model.model_id}>
                      <td className="ps-4">
                        <Badge bg="secondary">#{model.model_id}</Badge>
                      </td>
                      <td>
                        <strong>{model.name}</strong>
                        {model.description && (
                          <div className="text-muted small">{model.description}</div>
                        )}
                      </td>
                      <td>
                        <Badge bg={getModelTypeBadge(model.model_type)}>
                          {getModelTypeLabel(model.model_type)}
                        </Badge>
                      </td>
                      <td>{model.framework}</td>
                      <td>
                        <Badge bg="info">{model.version}</Badge>
                      </td>
                      <td>{(model.confidence_threshold * 100).toFixed(0)}%</td>
                      <td>
                        <code className="small">{model.file_path}</code>
                      </td>
                      <td className="text-end pe-4">
                        <div className="d-flex gap-2 justify-content-end">
                          <Link href={`/models/edit/${model.model_id}`} passHref legacyBehavior>
                            <Button
                              variant="outline-primary"
                              size="sm"
                            >
                              <i className="ri-edit-line me-1"></i>
                              Sửa
                            </Button>
                          </Link>
                          <Button
                            variant="outline-danger"
                            size="sm"
                            disabled
                            onClick={() => handleDelete(model.model_id)}
                          >
                            <i className="ri-delete-bin-line me-1"></i>
                            Xóa
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>
    </>
  );
}
