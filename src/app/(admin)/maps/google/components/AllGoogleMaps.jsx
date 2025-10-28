'use client';

import ComponentContainerCard from '@/components/ComponentContainerCard';
import UIExamplesList from '@/components/UIExamplesList';
import { Col, Row } from 'react-bootstrap';

const AllGoogleMaps = () => {
  return (
    <Row>
      <Col xl={9}>
        <ComponentContainerCard title="Google Maps Removed" description="The Google Maps functionality has been removed from this project. If you need map features, consider using alternatives like Leaflet or Mapbox.">
          <div style={{ height: '400px', display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: '#f0f0f0' }}>
            <p>Google Maps đã được gỡ bỏ. Liên hệ với đội ngũ phát triển nếu bạn cần tính năng bản đồ.</p>
          </div>
        </ComponentContainerCard>
      </Col>

      <Col xl={3}>
        <UIExamplesList examples={[]} />
      </Col>
    </Row>
  );
};

export default AllGoogleMaps;