'use client';
import React from 'react';
import { Card, Row, Col } from 'react-bootstrap';

const Statistics = () => {
    return (
        <Row>
            <Col md={6} xl={3}>
                <Card className="shadow-sm border-0">
                    <Card.Body>
                        <div className="d-flex align-items-center">
                            <div className="flex-shrink-0 me-3">
                                <div className="avatar-sm bg-primary bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center">
                                    <i className="ri-car-line fs-2 text-primary"></i>
                                </div>
                            </div>
                            <div className="flex-grow-1">
                                <h5 className="mb-1">12,540</h5>
                                <p className="mb-0 text-muted">Total Vehicles Today</p>
                            </div>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
            <Col md={6} xl={3}>
                <Card className="shadow-sm border-0">
                    <Card.Body>
                        <div className="d-flex align-items-center">
                            <div className="flex-shrink-0 me-3">
                                <div className="avatar-sm bg-danger bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center">
                                    <i className="ri-alarm-warning-line fs-2 text-danger"></i>
                                </div>
                            </div>
                            <div className="flex-grow-1">
                                <h5 className="mb-1">145</h5>
                                <p className="mb-0 text-muted">Violations Detected</p>
                            </div>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
            <Col md={6} xl={3}>
                <Card className="shadow-sm border-0">
                    <Card.Body>
                        <div className="d-flex align-items-center">
                            <div className="flex-shrink-0 me-3">
                                <div className="avatar-sm bg-success bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center">
                                    <i className="ri-camera-lens-line fs-2 text-success"></i>
                                </div>
                            </div>
                            <div className="flex-grow-1">
                                <h5 className="mb-1">8</h5>
                                <p className="mb-0 text-muted">Active Cameras</p>
                            </div>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
            <Col md={6} xl={3}>
                <Card className="shadow-sm border-0">
                    <Card.Body>
                        <div className="d-flex align-items-center">
                            <div className="flex-shrink-0 me-3">
                                <div className="avatar-sm bg-info bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center">
                                    <i className="ri-timer-flash-line fs-2 text-info"></i>
                                </div>
                            </div>
                            <div className="flex-grow-1">
                                <h5 className="mb-1">99.8%</h5>
                                <p className="mb-0 text-muted">System Uptime</p>
                            </div>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
        </Row>
    );
};

export default Statistics;
