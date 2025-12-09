'use client';

import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Row, Col, Alert } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
import { fetchVideoJobs, VideoJob } from '@/services/videoJobsApi';
import { toast } from 'react-toastify';

export default function VideoJobsPage() {
    const [videoJobs, setVideoJobs] = useState<VideoJob[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadVideoJobs = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchVideoJobs();
            setVideoJobs(data);
        } catch (err: any) {
            setError(err.message || 'Không thể tải danh sách video job');
            toast.error('Không thể tải danh sách video job');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadVideoJobs();
    }, []);

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, string> = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'failed': 'danger',
        };
        return statusMap[status] || 'secondary';
    };

    return (
        <>
            <PageTitle title="Quản lý Video Job" subName="Danh sách" />

            <Card className="shadow-sm">
                <Card.Header className="bg-white py-3">
                    <Row className="align-items-center">
                        <Col md={6}>
                            <h5 className="mb-0">🎬 Danh sách Video Job</h5>
                        </Col>
                        <Col md={6} className="d-flex justify-content-end gap-2">
                            <Link href="/video-jobs/create" passHref legacyBehavior>
                                <Button variant="primary">
                                    <i className="ri-add-line me-1"></i>
                                    Thêm Video Job
                                </Button>
                            </Link>
                            <Button variant="secondary" onClick={loadVideoJobs}>
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
                                    <th>Tên File</th>
                                    <th>Camera ID</th>
                                    <th>Trạng thái</th>
                                    <th>Giai đoạn</th>
                                    <th>Thời gian tải lên</th>
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
                                ) : videoJobs.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="text-center py-5 text-muted">
                                            Chưa có video job nào.
                                        </td>
                                    </tr>
                                ) : (
                                    videoJobs.map((job) => (
                                        <tr key={job.video_job_id}>
                                            <td className="ps-4">
                                                <Badge bg="secondary">#{job.video_job_id}</Badge>
                                            </td>
                                            <td>
                                                <strong>{job.file_name}</strong>
                                            </td>
                                            <td>{job.camera_id || <em className="text-muted">-</em>}</td>
                                            <td>
                                                <Badge bg={getStatusBadge(job.status)}>
                                                    {job.status}
                                                </Badge>
                                            </td>
                                            <td>{job.processing_stage}</td>
                                            <td>{new Date(job.upload_time).toLocaleString('vi-VN')}</td>
                                            <td className="text-end pe-4">
                                                <div className="d-flex gap-2 justify-content-end">
                                                    <Link href={`/video-jobs/edit/${job.video_job_id}`} passHref legacyBehavior>
                                                        <Button variant="outline-primary" size="sm">
                                                            <i className="ri-edit-line me-1"></i>
                                                            Sửa
                                                        </Button>
                                                    </Link>
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
