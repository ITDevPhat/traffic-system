'use client';

import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Row, Col, Alert } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { fetchViolationTypes, ViolationType } from '@/services/violationTypesApi';
import { toast } from 'react-toastify';

export default function ViolationTypesPage() {
  const [violationTypes, setViolationTypes] = useState<ViolationType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(new Set());

  const loadViolationTypes = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchViolationTypes();
      setViolationTypes(data);
    } catch (err: any) {
      setError(err.message || 'Không thể tải danh sách loại vi phạm');
      toast.error('Không thể tải danh sách loại vi phạm');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadViolationTypes();
  }, []);

  const handleDelete = (code: string) => {
    // Không xóa DB, chỉ ẩn item trên UI
    setHiddenItems(prev => new Set(prev).add(code));
    toast.success('Đã ẩn loại vi phạm khỏi danh sách');
  };

  const getSeverityBadge = (severity: string) => {
    const variants: Record<string, string> = {
      low: 'success',
      medium: 'warning',
      high: 'danger',
    };
    return variants[severity] || 'secondary';
  };

  const getSeverityLabel = (severity: string) => {
    const labels: Record<string, string> = {
      low: 'Thấp',
      medium: 'Trung bình',
      high: 'Cao',
    };
    return labels[severity] || severity;
  };

  const visibleViolationTypes = violationTypes.filter(
    vt => !hiddenItems.has(vt.violation_type_code)
  );

  return (
    <>
      <PageTitle title="Quản lý loại vi phạm" subName="Danh sách" />

      <Card className="shadow-sm">
        <Card.Header className="bg-white py-3">
          <Row className="align-items-center">
            <Col md={6}>
              <h5 className="mb-0">📋 Danh sách loại vi phạm</h5>
            </Col>
            <Col md={6} className="d-flex justify-content-end gap-2">
              <Link href="/violations/types/create" passHref legacyBehavior>
                <Button variant="primary">
                  <i className="ri-add-line me-1"></i>
                  Thêm loại vi phạm
                </Button>
              </Link>
              <Button variant="secondary" onClick={loadViolationTypes}>
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
                  <th className="ps-4">Mã loại vi phạm</th>
                  <th>Mô tả</th>
                  <th>Mức phạt (VNĐ)</th>
                  <th>Mức độ</th>
                  <th className="text-end pe-4">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status"></div>
                      <p className="mt-2 text-muted">Đang tải dữ liệu...</p>
                    </td>
                  </tr>
                ) : visibleViolationTypes.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-5 text-muted">
                      Chưa có loại vi phạm nào.
                    </td>
                  </tr>
                ) : (
                  visibleViolationTypes.map((vt) => (
                    <tr key={vt.violation_type_code}>
                      <td className="ps-4">
                        <Badge bg="secondary" className="text-uppercase">
                          {vt.violation_type_code}
                        </Badge>
                      </td>
                      <td>{vt.description}</td>
                      <td>
                        {vt.fine_amount?.toLocaleString('vi-VN') || 'N/A'}
                      </td>
                      <td>
                        <Badge bg={getSeverityBadge(vt.severity)}>
                          {getSeverityLabel(vt.severity)}
                        </Badge>
                      </td>
                      <td className="text-end pe-4">
                        <div className="d-flex gap-2 justify-content-end">
                          <Link href={`/violations/types/edit/${vt.violation_type_code}`} passHref legacyBehavior>
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
                            onClick={() => handleDelete(vt.violation_type_code)}
                          >
                            <i className="ri-delete-bin-line me-1" ></i>
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
