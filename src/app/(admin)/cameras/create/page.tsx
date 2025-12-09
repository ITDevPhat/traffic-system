'use client';

import React, { useState } from 'react';
import { Card, Form, Button, Row, Col, Alert } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createCamera, CameraCreateInput } from '@/services/camerasApi';
import { toast } from 'react-toastify';
import { TextFormInput } from '@/components/FormInput'; // Assuming this exists based on guide

export default function CreateCameraPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState<CameraCreateInput>({
        name: '',
        status: 'active',
        ip_address: '',
        stream_url: '',
        model: '',
        location_id: 0, // Should be a select, but keeping simple for now
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const value = e.target.type === 'number' ? parseInt(e.target.value) : e.target.value;
        setFormData({
            ...formData,
            [e.target.name]: value,
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            // Basic validation
            if (!formData.name) {
                throw new Error("Tên camera là bắt buộc");
            }

            // Clean up data before sending if needed (e.g. location_id 0 to undefined)
            const dataToSend = { ...formData };
            if (dataToSend.location_id === 0) delete dataToSend.location_id;

            await createCamera(dataToSend);
            toast.success('Tạo camera thành công');
            router.push('/cameras');
        } catch (err: any) {
            setError(err.message || 'Lỗi khi tạo camera');
            toast.error('Lỗi khi tạo camera');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <PageTitle title="Quản lý Camera" subName="Thêm mới" />

            <Row className="justify-content-center">
                <Col md={8}>
                    <Card className="shadow-sm">
                        <Card.Header className="bg-white py-3">
                            <h5 className="mb-0">Thêm Camera Mới</h5>
                        </Card.Header>
                        <Card.Body>
                            {error && (
                                <Alert variant="danger">
                                    {error}
                                </Alert>
                            )}

                            <Form onSubmit={handleSubmit}>
                                <Row className="mb-3">
                                    <Col md={12}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Tên Camera <span className="text-danger">*</span></Form.Label>
                                            <Form.Control
                                                type="text"
                                                name="name"
                                                value={formData.name}
                                                onChange={handleChange}
                                                required
                                                placeholder="Ví dụ: Camera Cổng Chính"
                                            />
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <Row className="mb-3">
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>IP Address</Form.Label>
                                            <Form.Control
                                                type="text"
                                                name="ip_address"
                                                value={formData.ip_address || ''}
                                                onChange={handleChange}
                                                placeholder="192.168.1.10"
                                            />
                                        </Form.Group>
                                    </Col>
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Model</Form.Label>
                                            <Form.Control
                                                type="text"
                                                name="model"
                                                value={formData.model || ''}
                                                onChange={handleChange}
                                                placeholder="Hikvision, Dahua..."
                                            />
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <Row className="mb-3">
                                    <Col md={12}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Stream URL</Form.Label>
                                            <Form.Control
                                                type="text"
                                                name="stream_url"
                                                value={formData.stream_url || ''}
                                                onChange={handleChange}
                                                placeholder="rtsp://admin:password@192.168.1.10:554/..."
                                            />
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <Row className="mb-3">
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Trạng thái</Form.Label>
                                            <Form.Select
                                                name="status"
                                                value={formData.status}
                                                onChange={handleChange}
                                            >
                                                <option value="active">Active</option>
                                                <option value="inactive">Inactive</option>
                                                <option value="maintenance">Maintenance</option>
                                            </Form.Select>
                                        </Form.Group>
                                    </Col>

                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Location ID (Tạm thời nhập ID)</Form.Label>
                                            <Form.Control
                                                type="number"
                                                name="location_id"
                                                value={formData.location_id || 0}
                                                onChange={handleChange}
                                            />
                                            <Form.Text className="text-muted">
                                                Sau này sẽ thay bằng Dropdown chọn vị trí
                                            </Form.Text>
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <div className="d-flex justify-content-end gap-2 mt-4">
                                    <Link href="/cameras" passHref legacyBehavior>
                                        <Button variant="secondary">Hủy bỏ</Button>
                                    </Link>
                                    <Button variant="primary" type="submit" disabled={loading}>
                                        {loading ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                                Đang lưu...
                                            </>
                                        ) : (
                                            'Lưu Camera'
                                        )}
                                    </Button>
                                </div>
                            </Form>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </>
    );
}
