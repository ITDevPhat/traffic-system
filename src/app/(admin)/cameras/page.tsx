'use client';

import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Row, Col, Alert } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { fetchCameras, Camera } from '@/services/camerasApi';
import { toast } from 'react-toastify';

export default function CamerasPage() {
    const [cameras, setCameras] = useState<Camera[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadCameras = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchCameras();
            setCameras(data);
        } catch (err: any) {
            setError(err.message || 'Không thể tải danh sách camera');
            toast.error('Không thể tải danh sách camera');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadCameras();
    }, []);

    const handleDelete = async (cameraId: number) => {
        // Delete functionality to be implemented or linked to remove API
        alert("Chức năng xóa chưa được tích hợp hoàn toàn trong API service (cần kiểm tra deleteCamera)");
    };

    return (
        <>
            <PageTitle title="Quản lý Camera" subName="Danh sách" />

            <Card className="shadow-sm">
                <Card.Header className="bg-white py-3">
                    <Row className="align-items-center">
                        <Col md={6}>
                            <h5 className="mb-0">📷 Danh sách Camera</h5>
                        </Col>
                        <Col md={6} className="d-flex justify-content-end gap-2">
                            <Link href="/cameras/create" passHref legacyBehavior>
                                <Button variant="primary">
                                    <i className="ri-add-line me-1"></i>
                                    Thêm Camera
                                </Button>
                            </Link>
                            <Button variant="secondary" onClick={loadCameras}>
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
                                    <th>Tên Camera</th>
                                    <th>IP Address</th>
                                    <th>Status</th>
                                    <th>Location ID</th>
                                    <th>Model</th>
                                    <th className="text-end pe-4">Thao tác</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr>
                                        <td colSpan={7} className="text-center py-5">
                                            <div className="spinner-border text-primary" role="status"></div>
                                            <p className="mt-2 text-muted">Đang tải dữ liệu...</p>
                                        </td>
                                    </tr>
                                ) : cameras.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="text-center py-5 text-muted">
                                            Chưa có camera nào.
                                        </td>
                                    </tr>
                                ) : (
                                    cameras.map((camera) => (
                                        <tr key={camera.camera_id}>
                                            <td className="ps-4">
                                                <Badge bg="secondary">#{camera.camera_id}</Badge>
                                            </td>
                                            <td>
                                                <strong>{camera.name}</strong>
                                            </td>
                                            <td>{camera.ip_address || <em className="text-muted">N/A</em>}</td>
                                            <td>
                                                <Badge bg={camera.status === 'active' ? 'success' : 'secondary'}>
                                                    {camera.status}
                                                </Badge>
                                            </td>
                                            <td>{camera.location_id || <em className="text-muted">-</em>}</td>
                                            <td>{camera.model || <em className="text-muted">-</em>}</td>
                                            <td className="text-end pe-4">
                                                <div className="d-flex gap-2 justify-content-end">
                                                    <Link href={`/cameras/edit/${camera.camera_id}`} passHref legacyBehavior>
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
                                                        onClick={() => handleDelete(camera.camera_id)}
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
