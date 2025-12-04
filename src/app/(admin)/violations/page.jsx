'use client';
import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Form, Row, Col, Pagination } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ViolationsPage() {
    const [violations, setViolations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [filterType, setFilterType] = useState('all');

    const fetchViolations = async () => {
        setLoading(true);
        try {
            // Corrected query params to match backend: violation_type, skip, limit
            const skip = (page - 1) * 20;
            const typeParam = filterType !== 'all' ? `&violation_type=${filterType}` : '';
            const res = await fetch(`${API_URL}/api/violations?skip=${skip}&limit=20${typeParam}`);

            if (res.ok) {
                const data = await res.json();
                // Backend returns { total, skip, limit, violations: [...] }
                setViolations(data.violations || []);
                const total = data.total || 0;
                setTotalPages(Math.ceil(total / 20) || 1);
            }
        } catch (error) {
            console.error('Failed to fetch violations:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchViolations();
    }, [page, filterType]);

    return (
        <>
            <PageTitle title="Violation History" subName="Records" />

            <Card className="shadow-sm">
                <Card.Header className="bg-white py-3">
                    <Row className="align-items-center">
                        <Col md={6}>
                            <h5 className="mb-0">📋 Violation Records</h5>
                        </Col>
                        <Col md={6} className="d-flex justify-content-end gap-2">
                            <Form.Select
                                style={{ width: '200px' }}
                                value={filterType}
                                onChange={(e) => setFilterType(e.target.value)}
                            >
                                <option value="all">All Types</option>
                                <option value="red_light">Red Light</option>
                                <option value="wrong_lane">Wrong Lane</option>
                                <option value="speeding">Speeding</option>
                                <option value="no_helmet">No Helmet</option>
                            </Form.Select>
                            <Button variant="primary" onClick={fetchViolations}>
                                Refresh
                            </Button>
                        </Col>
                    </Row>
                </Card.Header>
                <Card.Body className="p-0">
                    <div className="table-responsive">
                        <Table hover className="mb-0 align-middle">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-4">ID</th>
                                    <th>Time</th>
                                    <th>Plate</th>
                                    <th>Violation Type</th>
                                    <th>ROI Type</th>
                                    <th>Evidence</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr>
                                        <td colSpan="7" className="text-center py-5">
                                            <div className="spinner-border text-primary" role="status"></div>
                                            <p className="mt-2 text-muted">Loading records...</p>
                                        </td>
                                    </tr>
                                ) : violations.length === 0 ? (
                                    <tr>
                                        <td colSpan="7" className="text-center py-5 text-muted">
                                            No violations found.
                                        </td>
                                    </tr>
                                ) : (
                                    violations.map((v) => (
                                        <tr key={v.violation_id}>
                                            <td className="ps-4">#{v.violation_id}</td>
                                            <td>
                                                {new Date(v.timestamp || v.created_at).toLocaleString('vi-VN')}
                                            </td>
                                            <td>
                                                <div className="d-flex align-items-center gap-2">
                                                    <Badge bg="secondary">{v.plate || 'Unknown'}</Badge>
                                                </div>
                                            </td>
                                            <td>
                                                <Badge bg="danger" className="text-uppercase">
                                                    {v.violation_type_code?.replace(/_/g, ' ')}
                                                </Badge>
                                            </td>
                                            <td>{v.roi_type || 'N/A'}</td>
                                            <td>
                                                {v.evidence_img ? (
                                                    <a href={`${API_URL}/${v.evidence_img}`} target="_blank" rel="noreferrer">
                                                        View Image
                                                    </a>
                                                ) : 'No Image'}
                                            </td>
                                            <td>
                                                <Badge bg={v.verification_status === 'verified' ? 'success' : 'warning'}>
                                                    {v.verification_status || 'Pending'}
                                                </Badge>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </Table>
                    </div>
                </Card.Body>
                <Card.Footer className="bg-white">
                    <div className="d-flex justify-content-end">
                        <Pagination>
                            <Pagination.Prev onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} />
                            <Pagination.Item active>{page}</Pagination.Item>
                            <Pagination.Next onClick={() => setPage(p => p + 1)} disabled={page >= totalPages} />
                        </Pagination>
                    </div>
                </Card.Footer>
            </Card>
        </>
    );
}
