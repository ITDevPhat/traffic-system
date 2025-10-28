'use client';

import Link from 'next/link';
import { Card, CardBody, CardTitle, Col, Row } from 'react-bootstrap';

const AllInputMasks = () => {
  return <Card>
      <CardBody>
        <CardTitle as={'h5'} className="anchor" id="default">
          Input Masks
          <Link className="anchor-link" href="#default">
            #
          </Link>
        </CardTitle>
        <p className="text-muted">A Java-Script Plugin to make masks on form fields and HTML elements.</p>
        <div>
          <Row>
            <Col md={6}>
              <form action="#">
                <div className="mb-3">
                  <label className="form-label">Input Masks Removed</label>
                  <div style={{ height: '200px', display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: '#f0f0f0' }}>
                    <p>Chức năng Input Masks đã được gỡ bỏ. Liên hệ với đội ngũ phát triển nếu bạn cần tính năng này.</p>
                  </div>
                </div>
              </form>
            </Col>
          </Row>
        </div>
      </CardBody>
    </Card>;
};

export default AllInputMasks;