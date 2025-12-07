'use client';

import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Row, Col, Alert, Form } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { fetchViolationsManagement, ViolationItem } from '@/services/violationsApi';
import { toast } from 'react-toastify';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ViolationsManagementPage() {
  const [violations, setViolations] = useState<ViolationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hiddenItems, setHiddenItems] = useState<Set<number>>(new Set());
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterPlate, setFilterPlate] = useState<string>('');

  const loadViolations = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {};
      if (filterStatus !== 'all') params.verification_status = filterStatus;
      if (filterPlate) params.plate = filterPlate;
      
      const data = await fetchViolationsManagement(params);
      setViolations(data);
    } catch (err: any) {
      setError(err.message || 'Không thể tải danh sách vi phạm');
      toast.error('Không thể tải danh sách vi phạm');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadViolations();
  }, [filterStatus]);

  const handleDelete = (violationId: number) => {
    setHiddenItems(prev => new Set(prev).add(violationId));
    toast.success('Đã ẩn vi phạm khỏi danh sách');
  };

  const handleSearch = () => {
    loadViolations();
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      unverified: 'warning',
      verified: 'success',
      rejected: 'danger',
    };
    return variants[status] || 'secondary';
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      unverified: 'Chưa xác minh',
      verified: 'Đã xác minh',
      rejected: 'Từ chối',
    };
    return labels[status] || status;
  };

  const visibleViolations = violations.filter(
    v => !hiddenItems.has(v.violation_id)
  );

  return (
    <>
      <PageTitle title="Quản lý vi phạm" subName="Danh sách" />

      <Card className="shadow-sm">
        <Card.Header className="bg-white py-3">
          <Row className="align-items-center">
            <Col md={6}>
              <h5 className="mb-0">🚨 Danh sách vi phạm giao thông</h5>
            </Col>
            <Col md={6} className="d-flex justify-content-end gap-2">
              <Form.Control
                type="text"
                placeholder="Tìm theo biển số..."
                value={filterPlate}
                onChange={(e) => setFilterPlate(e.target.value)}
                style={{ width: '200px' }}
              />
              <Button variant="info" onClick={handleSearch}>
                <i className="ri-search-line me-1"></i>
                Tìm
              </Button>
              <Form.Select
                style={{ width: '200px' }}
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="all">Tất cả trạng thái</option>
                <option value="unverified">Chưa xác minh</option>
                <option value="verified">Đã xác minh</option>
                <option value="rejected">Từ chối</option>
              </Form.Select>
              <Link href="/violations/management/create" passHref legacyBehavior>
                <Button variant="primary">
                  <i className="ri-add-line me-1"></i>
                  Thêm vi phạm
                </Button>
              </Link>
              <Button variant="secondary" onClick={loadViolations}>
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
                  <th>Thời gian</th>
                  <th>Biển số</th>
                  <th>Loại vi phạm</th>
                  <th>Video Job</th>
                  <th>Độ tin cậy</th>
                  <th>Trạng thái</th>
                  <th>Bằng chứng</th>
                  <th className="text-end pe-4">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status"></div>
                      <p className="mt-2 text-muted">Đang tải dữ liệu...</p>
                    </td>
                  </tr>
                ) : visibleViolations.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-5 text-muted">
                      Chưa có vi phạm nào.
                    </td>
                  </tr>
                ) : (
                  visibleViolations.map((violation) => (
                    <tr key={violation.violation_id}>
                      <td className="ps-4">
                        <Badge bg="secondary">#{violation.violation_id}</Badge>
                      </td>
                      <td>
                        {violation.timestamp 
                          ? new Date(violation.timestamp).toLocaleString('vi-VN')
                          : new Date(violation.created_at).toLocaleString('vi-VN')}
                      </td>
                      <td>
                        {violation.plate ? (
                          <Badge bg="dark">{violation.plate}</Badge>
                        ) : (
                          <span className="text-muted">N/A</span>
                        )}
                      </td>
                      <td>
                        {violation.violation_type_code ? (
                          <Badge bg="danger" className="text-uppercase">
                            {violation.violation_type_code.replace(/_/g, ' ')}
                          </Badge>
                        ) : (
                          <span className="text-muted">N/A</span>
                        )}
                      </td>
                      <td>
                        <Badge bg="info">Job #{violation.video_job_id}</Badge>
                      </td>
                      <td>
                        {violation.confidence 
                          ? `${(violation.confidence * 100).toFixed(1)}%`
                          : 'N/A'}
                      </td>
                      <td>
                        <Badge bg={getStatusBadge(violation.verification_status)}>
                          {getStatusLabel(violation.verification_status)}
                        </Badge>
                      </td>
                      <td>
                        {violation.evidence_img ? (
                          <a 
                            href={`${API_URL}${violation.evidence_img}`} 
                            target="_blank" 
                            rel="noreferrer"
                            className="btn btn-sm btn-outline-primary"
                          >
                            <i className="ri-image-line me-1"></i>
                            Xem
                          </a>
                        ) : (
                          <span className="text-muted">Không có</span>
                        )}
                      </td>
                      <td className="text-end pe-4">
                        <div className="d-flex gap-2 justify-content-end">
                          <Link 
                            href={`/violations/management/edit/${violation.violation_id}`} 
                            passHref 
                            legacyBehavior
                          >
                            <Button variant="outline-primary" size="sm">
                              <i className="ri-edit-line me-1"></i>
                              Sửa
                            </Button>
                          </Link>
                          <Button
                            variant="outline-danger"
                            size="sm"
                            onClick={() => handleDelete(violation.violation_id)}
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
