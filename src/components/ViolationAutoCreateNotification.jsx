import React from 'react';
import { Alert, Badge, Button } from 'react-bootstrap';
import Link from 'next/link';

const ViolationAutoCreateNotification = ({ 
  violations = [], 
  onDismiss = () => {},
  show = true 
}) => {
  // Auto-dismiss after 10 seconds
  React.useEffect(() => {
    if (violations.length > 0) {
      const timer = setTimeout(() => {
        violations.forEach(v => onDismiss(v.violationId));
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, [violations, onDismiss]);

  if (!show || violations.length === 0) return null;

  return (
    <div 
      style={{
        position: 'fixed',
        top: '80px',
        right: '20px',
        zIndex: 1050,
        maxWidth: '400px'
      }}
    >
      {violations.map((violation, index) => (
        <Alert 
          key={`${violation.violationId}-${index}`}
          variant="success" 
          dismissible 
          onClose={() => onDismiss(violation.violationId)}
          className="mb-2 shadow-lg"
          style={{
            border: '2px solid #28a745',
            borderRadius: '10px'
          }}
        >
          <Alert.Heading className="h6 mb-2">
            🚨 Vi phạm được tạo tự động!
          </Alert.Heading>
          
          <div className="mb-2">
            <Badge bg="danger" className="me-2">
              {violation.violationType}
            </Badge>
            <Badge bg="info">
              Track #{violation.trackId}
            </Badge>
          </div>
          
          <p className="mb-2 small">
            <strong>ID Vi phạm:</strong> #{violation.violationId}<br/>
            <strong>Frame:</strong> {violation.frame}<br/>
            <strong>Độ tin cậy:</strong> {(violation.confidence * 100).toFixed(1)}%
          </p>
          
          <div className="d-flex gap-2">
            <Link href="/violations/management" passHref legacyBehavior>
              <Button variant="outline-primary" size="sm">
                📋 Xem danh sách
              </Button>
            </Link>
            <Link href={`/violations/management/${violation.violationId}`} passHref legacyBehavior>
              <Button variant="primary" size="sm">
                👁️ Chi tiết
              </Button>
            </Link>
          </div>
        </Alert>
      ))}
    </div>
  );
};

export default ViolationAutoCreateNotification;