-- Thêm dữ liệu mẫu cho violation_types
INSERT INTO violation_types (violation_type_code, description, fine_amount, severity) VALUES
('RED_LIGHT', 'Vượt đèn đỏ', 1000000, 'high'),
('WRONG_LANE', 'Đi sai làn đường', 500000, 'medium'),
('STOP_LINE', 'Vượt vạch dừng', 300000, 'medium'),
('SPEED_LIMIT', 'Vượt quá tốc độ cho phép', 800000, 'high'),
('NO_HELMET', 'Không đội mũ bảo hiểm', 200000, 'low'),
('PHONE_DRIVING', 'Sử dụng điện thoại khi lái xe', 600000, 'medium'),
('NO_TURN_SIGNAL', 'Không bật tín hiệu rẽ', 150000, 'low'),
('PARKING_VIOLATION', 'Đỗ xe sai quy định', 250000, 'low')
ON CONFLICT (violation_type_code) DO NOTHING;

-- Thêm dữ liệu mẫu cho violations
INSERT INTO violations (
    video_job_id, violation_type_code, frame, timestamp, roi_type, 
    evidence_img, plate, confidence, verification_status
) VALUES
(1, 'RED_LIGHT', 150, '2024-12-11 08:30:15', 'intersection', '/evidence/violation_1.jpg', '51A-12345', 0.95, 'verified'),
(2, 'WRONG_LANE', 89, '2024-12-11 09:15:22', 'lane_change', '/evidence/violation_2.jpg', '59B-67890', 0.87, 'unverified'),
(3, 'STOP_LINE', 45, '2024-12-11 10:05:33', 'stopline', '/evidence/violation_3.jpg', '43C-11111', 0.92, 'verified'),
(4, 'SPEED_LIMIT', 200, '2024-12-11 11:20:44', 'highway', '/evidence/violation_4.jpg', '77D-22222', 0.89, 'unverified'),
(5, 'NO_HELMET', 75, '2024-12-11 12:45:55', 'street', '/evidence/violation_5.jpg', '29E-33333', 0.78, 'rejected'),
(1, 'PHONE_DRIVING', 120, '2024-12-11 13:30:10', 'intersection', '/evidence/violation_6.jpg', '51F-44444', 0.85, 'verified'),
(2, 'NO_TURN_SIGNAL', 60, '2024-12-11 14:15:25', 'turn', '/evidence/violation_7.jpg', '59G-55555', 0.82, 'unverified'),
(3, 'PARKING_VIOLATION', 30, '2024-12-11 15:00:40', 'parking', '/evidence/violation_8.jpg', '43H-66666', 0.90, 'verified');

-- Thêm bounding boxes mẫu cho violations
INSERT INTO bboxes (violation_id, x1, y1, x2, y2, confidence, label) VALUES
-- Violation 1 (RED_LIGHT)
(1, 100, 150, 300, 350, 0.95, 'vehicle'),
(1, 120, 180, 180, 220, 0.88, 'plate'),
(1, 50, 50, 150, 100, 0.92, 'traffic_light'),

-- Violation 2 (WRONG_LANE)
(2, 200, 200, 400, 400, 0.87, 'vehicle'),
(2, 220, 230, 280, 270, 0.85, 'plate'),

-- Violation 3 (STOP_LINE)
(3, 150, 100, 350, 300, 0.92, 'vehicle'),
(3, 170, 130, 230, 170, 0.89, 'plate'),
(3, 0, 320, 640, 325, 0.95, 'stopline'),

-- Violation 4 (SPEED_LIMIT)
(4, 80, 120, 280, 320, 0.89, 'vehicle'),
(4, 100, 150, 160, 190, 0.86, 'plate'),

-- Violation 5 (NO_HELMET)
(5, 250, 80, 350, 200, 0.78, 'motorcycle'),
(5, 270, 100, 330, 140, 0.75, 'person'),
(5, 280, 110, 320, 130, 0.72, 'no_helmet'),

-- Violation 6 (PHONE_DRIVING)
(6, 120, 160, 320, 360, 0.85, 'vehicle'),
(6, 140, 190, 200, 230, 0.83, 'plate'),
(6, 180, 200, 200, 220, 0.80, 'phone'),

-- Violation 7 (NO_TURN_SIGNAL)
(7, 90, 140, 290, 340, 0.82, 'vehicle'),
(7, 110, 170, 170, 210, 0.79, 'plate'),

-- Violation 8 (PARKING_VIOLATION)
(8, 300, 250, 500, 450, 0.90, 'vehicle'),
(8, 320, 280, 380, 320, 0.87, 'plate'),
(8, 280, 200, 520, 480, 0.85, 'parking_zone');