'use client';

import React, { useState } from 'react';
import { Card, Form, Button, Row, Col, Alert } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createVideoJob, VideoJobCreateInput } from '@/services/videoJobsApi';
import { toast } from 'react-toastify';

export default function CreateVideoJobPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState<VideoJobCreateInput>({
        file_name: '',
        status: 'pending',
        processing_stage: 'uploaded',
        camera_id: undefined,
        output_path: '',
        fps: undefined,
        duration: undefined,
        notes: '',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value, type } = e.target;
        let parsedValue: any = value;

        if (type === 'number') {
            parsedValue = value === '' ? undefined : parseFloat(value);
        }

        setFormData({
            ...formData,
            [name]: parsedValue,
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            if (!formData.file_name) {
                throw new Error("Tên file là bắt buộc");
            }

            await createVideoJob(formData);
            toast.success('Tạo video job thành công');
            router.push('/video-jobs');
        } catch (err: any) {
            setError(err.message || 'Lỗi khi tạo video job');
            toast.error('Lỗi khi tạo video job');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <PageTitle title="Quản lý Video Job" subName="Thêm mới" />

            <Row className="justify-content-center">
                <Col md={8}>
                    <Card className="shadow-sm">
                        <Card.Header className="bg-white py-3">
                            <h5 className="mb-0">Thêm Video Job Mới</h5>
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
                                            <Form.Label>Tên File <span className="text-danger">*</span></Form.Label>
                                            <Form.Control
                                                type="text"
                                                name="file_name"
                                                value={formData.file_name}
                                                onChange={handleChange}
                                                required
                                                placeholder="video_traffic_001.mp4"
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
                                                <option value="pending">Pending</option>
                                                <option value="processing">Processing</option>
                                                <option value="completed">Completed</option>
                                                <option value="failed">Failed</option>
                                            </Form.Select>
                                        </Form.Group>
                                    </Col>
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Giai đoạn xử lý</Form.Label>
                                            <Form.Control
                                                type="text"
                                                name="processing_stage"
                                                value={formData.processing_stage}
                                                onChange={handleChange}
                                                placeholder="uploaded, processing, done"
                                            />
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <Row className="mb-3">
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Camera ID</Form.Label>
                                            <Form.Control
                                                type="number"
                                                name="camera_id"
                                                value={formData.camera_id || ''}
                                                onChange={handleChange}
                                                placeholder="1"
                                            />
                                        </Form.Group>
                                    </Col>
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Output Path</Form.Label>
                                            <Form.Control
                                                type="text"
                                                name="output_path"
                                                value={formData.output_path || ''}
                                                onChange={handleChange}
                                                placeholder="/outputs/video_001"
                                            />
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <Row className="mb-3">
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>FPS</Form.Label>
                                            <Form.Control
                                                type="number"
                                                name="fps"
                                                value={formData.fps || ''}
                                                onChange={handleChange}
                                                placeholder="30"
                                                step="0.1"
                                            />
                                        </Form.Group>
                                    </Col>
                                    <Col md={6}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Duration (giây)</Form.Label>
                                            <Form.Control
                                                type="number"
                                                name="duration"
                                                value={formData.duration || ''}
                                                onChange={handleChange}
                                                placeholder="120"
                                                step="0.1"
                                            />
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <Row className="mb-3">
                                    <Col md={12}>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Ghi chú</Form.Label>
                                            <Form.Control
                                                as="textarea"
                                                rows={3}
                                                name="notes"
                                                value={formData.notes || ''}
                                                onChange={handleChange}
                                                placeholder="Ghi chú về video job..."
                                            />
                                        </Form.Group>
                                    </Col>
                                </Row>

                                <div className="d-flex justify-content-end gap-2 mt-4">
                                    <Link href="/video-jobs" passHref legacyBehavior>
                                        <Button variant="secondary">Hủy bỏ</Button>
                                    </Link>
                                    <Button variant="primary" type="submit" disabled={loading}>
                                        {loading ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                                Đang lưu...
                                            </>
                                        ) : (
                                            'Lưu Video Job'
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
