'use client';

import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Row, Col, Alert } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { useRouter, useParams } from 'next/navigation';
import { fetchVideoJobById, updateVideoJob, VideoJobUpdateInput } from '@/services/videoJobsApi';
import { toast } from 'react-toastify';

export default function EditVideoJobPage() {
    const router = useRouter();
    const params = useParams();
    const videoJobId = parseInt(params.id as string);

    const [loading, setLoading] = useState(false);
    const [loadingData, setLoadingData] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState<VideoJobUpdateInput>({
        file_name: '',
        status: 'pending',
        processing_stage: 'uploaded',
        camera_id: undefined,
        processed_at: undefined,
        output_path: '',
        fps: undefined,
        duration: undefined,
        notes: '',
    });

    useEffect(() => {
        const loadVideoJob = async () => {
            try {
                const data = await fetchVideoJobById(videoJobId);
                setFormData({
                    file_name: data.file_name,
                    status: data.status,
                    processing_stage: data.processing_stage,
                    camera_id: data.camera_id,
                    processed_at: data.processed_at,
                    output_path: data.output_path || '',
                    fps: data.fps,
                    duration: data.duration,
                    notes: data.notes || '',
                });
            } catch (err: any) {
                setError(err.message || 'Không thể tải thông tin video job');
                toast.error('Không thể tải thông tin video job');
            } finally {
                setLoadingData(false);
            }
        };

        loadVideoJob();
    }, [videoJobId]);

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

            await updateVideoJob(videoJobId, formData);
            toast.success('Cập nhật video job thành công');
            router.push('/video-jobs');
        } catch (err: any) {
            setError(err.message || 'Lỗi khi cập nhật video job');
            toast.error('Lỗi khi cập nhật video job');
        } finally {
            setLoading(false);
        }
    };

    if (loadingData) {
        return (
            <div className="text-center py-5">
                <div className="spinner-border text-primary" role="status"></div>
                <p className="mt-2">Đang tải dữ liệu...</p>
            </div>
        );
    }

    return (
        <>
            <PageTitle title="Quản lý Video Job" subName="Chỉnh sửa" />

            <Row className="justify-content-center">
                <Col md={8}>
                    <Card className="shadow-sm">
                        <Card.Header className="bg-white py-3">
                            <h5 className="mb-0">Chỉnh sửa Video Job #{videoJobId}</h5>
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
                                            'Cập nhật Video Job'
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
