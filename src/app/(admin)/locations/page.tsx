'use client';

import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Row, Col, Alert } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { fetchLocations, deleteLocation, Location } from '@/services/locationsApi';
import { toast } from 'react-toastify';

export default function LocationsPage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLocations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLocations();
      setLocations(data);
    } catch (err: any) {
      setError(err.message || 'Không thể tải danh sách vị trí');
      toast.error('Không thể tải danh sách vị trí');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLocations();
  }, []);

  const handleDelete = async (locationId: number) => {
    if (window.confirm('Bạn có chắc chắn muốn xóa vị trí này không?')) {
      try {
        await deleteLocation(locationId);
        toast.success('Xóa vị trí thành công');
        loadLocations();
      } catch (err: any) {
        toast.error(err.message || 'Không thể xóa vị trí');
      }
    }
  };

  return (
    <>
      <PageTitle title="Quản lý vị trí" subName="Danh sách" />

      <Card className="shadow-sm">
        <Card.Header className="bg-white py-3">
          <Row className="align-items-center">
            <Col md={6}>
              <h5 className="mb-0">📍 Danh sách vị trí</h5>
            </Col>
            <Col md={6} className="d-flex justify-content-end gap-2">
              <Link href="/locations/create" passHref legacyBehavior>
                <Button variant="primary">
                  <i className="ri-add-line me-1"></i>
                  Thêm vị trí
                </Button>
              </Link>
              <Button variant="secondary" onClick={loadLocations}>
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
                  <th>Tên vị trí</th>
                  <th>Địa chỉ</th>
                  <th>Tọa độ (Lat, Long)</th>
                  <th>Mô tả</th>
                  <th className="text-end pe-4">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status"></div>
                      <p className="mt-2 text-muted">Đang tải dữ liệu...</p>
                    </td>
                  </tr>
                ) : locations.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-5 text-muted">
                      Chưa có vị trí nào.
                    </td>
                  </tr>
                ) : (
                  locations.map((location) => (
                    <tr key={location.location_id}>
                      <td className="ps-4">
                        <Badge bg="secondary">#{location.location_id}</Badge>
                      </td>
                      <td>
                        <strong>{location.name}</strong>
                      </td>
                      <td>{location.address || <em className="text-muted">Chưa cập nhật</em>}</td>
                      <td>
                        {location.latitude && location.longitude ? (
                          <div className="small">
                            <div>Lat: {location.latitude}</div>
                            <div>Long: {location.longitude}</div>
                          </div>
                        ) : (
                          <em className="text-muted">N/A</em>
                        )}
                      </td>
                      <td>
                         {location.description || <em className="text-muted text-small">-</em>}
                      </td>
                      <td className="text-end pe-4">
                        <div className="d-flex gap-2 justify-content-end">
                          <Link href={`/locations/edit/${location.location_id}`} passHref legacyBehavior>
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
                            onClick={() => handleDelete(location.location_id)}
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
