-- =========================================================
-- 🚦 TRAFFIC VIOLATION DETECTION DATABASE SCHEMA (PostgreSQL)
-- =========================================================
-- Phiên bản: 1.3s (Pluralized Table Names)
-- Ngày cập nhật: 2025-10-23
-- =========================================================

-- =========================================================
-- XÓA CÁC BẢNG CŨ (NẾU CÓ)
-- =========================================================
DROP VIEW IF EXISTS violation_summary CASCADE;
DROP VIEW IF EXISTS violation_stats CASCADE;
DROP TABLE IF EXISTS violations CASCADE;
DROP TABLE IF EXISTS rois CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS video_jobs CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS cameras CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS violation_types CASCADE;

-- =========================================================
-- 1️⃣ BẢNG NGƯỜI DÙNG (USERS)
-- =========================================================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    avatar_url TEXT,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Lưu thông tin người dùng hệ thống (admin hoặc user).';
COMMENT ON COLUMN users.role IS 'Phân quyền người dùng: admin hoặc user.';

-- =========================================================
-- 2️⃣ BẢNG VỊ TRÍ (LOCATIONS)
-- =========================================================
CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE locations IS 'Thông tin vị trí địa lý của các camera hoặc khu vực giám sát giao thông.';

-- =========================================================
-- 3️⃣ BẢNG CAMERAS
-- =========================================================
CREATE TABLE cameras (
    camera_id SERIAL PRIMARY KEY,
    location_id INT REFERENCES locations(location_id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    ip_address VARCHAR(45),
    stream_url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    install_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE cameras IS 'Thông tin các camera giám sát giao thông.';

-- =========================================================
-- 4️⃣ BẢNG VIDEO_JOBS
-- =========================================================
CREATE TABLE video_jobs (
    video_job_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    camera_id INT REFERENCES cameras(camera_id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    upload_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending',
    output_path TEXT,
    fps FLOAT,
    duration FLOAT,
    notes TEXT
);

CREATE INDEX idx_video_jobs_status ON video_jobs(status);

COMMENT ON TABLE video_jobs IS 'Lưu thông tin từng video được người dùng tải lên để xử lý AI.';

-- =========================================================
-- 5️⃣ BẢNG VEHICLES
-- =========================================================
CREATE TABLE vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    plate VARCHAR(20) UNIQUE,
    type VARCHAR(20),
    color VARCHAR(50),
    brand VARCHAR(100),
    total_violations INT DEFAULT 0,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

COMMENT ON TABLE vehicles IS 'Lưu thông tin phương tiện đã nhận dạng.';

-- =========================================================
-- 6️⃣ BẢNG ROIS (REGION OF INTEREST)
-- =========================================================
CREATE TABLE rois (
    roi_id SERIAL PRIMARY KEY,
    video_job_id INT REFERENCES video_jobs(video_job_id) ON DELETE CASCADE,
    roi_type VARCHAR(50) NOT NULL,
    coordinates JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rois_video_job_id ON rois(video_job_id);
CREATE INDEX idx_rois_type ON rois(roi_type);

COMMENT ON TABLE rois IS 'Lưu vùng ROI (vạch dừng, khu vực vi phạm, v.v.) cho từng video.';

-- =========================================================
-- 7️⃣ BẢNG VIOLATION_TYPES
-- =========================================================
CREATE TABLE violation_types (
    violation_type_code VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    fine_amount DECIMAL(12,2),
    severity VARCHAR(20) DEFAULT 'medium'
);

COMMENT ON TABLE violation_types IS 'Danh mục các loại vi phạm được hệ thống nhận dạng.';

-- =========================================================
-- 8️⃣ BẢNG VIOLATIONS
-- =========================================================
CREATE TABLE violations (
    violation_id SERIAL PRIMARY KEY,
    video_job_id INT REFERENCES video_jobs(video_job_id) ON DELETE CASCADE,
    vehicle_id INT REFERENCES vehicles(vehicle_id) ON DELETE SET NULL,
    violation_type VARCHAR(50),
    violation_type_code VARCHAR(50) REFERENCES violation_types(violation_type_code) ON DELETE SET NULL,
    frame INT,
    timestamp TIMESTAMP,
    bbox JSONB,
    roi_type VARCHAR(50),
    evidence_img TEXT,
    plate VARCHAR(20),
    confidence FLOAT,
    verification_status VARCHAR(20) DEFAULT 'unverified',
    verified_by INT REFERENCES users(user_id) ON DELETE SET NULL,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_violations_video_job_id ON violations(video_job_id);
CREATE INDEX idx_violations_type ON violations(violation_type);
CREATE INDEX idx_violations_timestamp ON violations(timestamp);
CREATE INDEX idx_violations_plate ON violations(plate);
CREATE INDEX idx_violations_bbox_jsonb ON violations USING gin(bbox);

COMMENT ON TABLE violations IS 'Lưu thông tin chi tiết các hành vi vi phạm.';

-- =========================================================
-- 9️⃣ VIEW THỐNG KÊ
-- =========================================================
CREATE OR REPLACE VIEW violation_summary AS
SELECT 
    v.violation_type_code,
    t.description AS violation_name,
    COUNT(v.violation_id) AS total,
    DATE_TRUNC('day', v.timestamp) AS day,
    COALESCE(c.name, 'Unknown') AS camera_name,
    COALESCE(l.name, 'Unknown') AS location_name
FROM violations v
LEFT JOIN violation_types t ON v.violation_type_code = t.violation_type_code
LEFT JOIN video_jobs j ON v.video_job_id = j.video_job_id
LEFT JOIN cameras c ON j.camera_id = c.camera_id
LEFT JOIN locations l ON c.location_id = l.location_id
GROUP BY v.violation_type_code, t.description, day, camera_name, location_name
ORDER BY day DESC;

COMMENT ON VIEW violation_summary IS 'Thống kê tổng hợp số lượng vi phạm theo ngày, loại, camera và vị trí.';

-- =========================================================
-- 🔟 DỮ LIỆU MẪU DEMO
-- =========================================================
INSERT INTO locations (name, address, latitude, longitude, description)
VALUES ('Ngã tư Nguyễn Văn Linh - 3/2', 'Quận 7, TP.HCM', 10.732100, 106.705900, 'Khu vực thường xảy ra vượt đèn đỏ');

INSERT INTO cameras (location_id, name, model, ip_address, stream_url, status)
VALUES (1, 'CAM_Q7_01', 'Hikvision DS-2CD2085FWD', '192.168.1.10', 'rtsp://192.168.1.10/stream1', 'active');

INSERT INTO violation_types (violation_type_code, description, fine_amount, severity)
VALUES 
('RED_LIGHT', 'Vượt đèn đỏ', 900000, 'high'),
('STOP_LINE', 'Dừng quá vạch', 400000, 'medium'),
('SPEED', 'Chạy quá tốc độ', 1000000, 'high');

INSERT INTO video_jobs (file_name, status, fps, duration, notes, camera_id)
VALUES ('cam_q1_2025_10_15.mp4', 'done', 30.0, 120.0, 'Video demo test', 1);

INSERT INTO rois (video_job_id, roi_type, coordinates)
VALUES 
(1, 'stop_line', '[ [321,540], [800,540], [800,600], [321,600] ]'::jsonb),
(1, 'violation_zone', '[ [320,480], [900,480], [900,540], [320,540] ]'::jsonb);

INSERT INTO violations (video_job_id, violation_type, violation_type_code, frame, timestamp, plate, evidence_img, bbox, confidence)
VALUES 
(1, 'red_light', 'RED_LIGHT', 158, NOW(), '59A-123.45', '/static/outputs/job_1/frame_158.jpg', '{"x1":320,"y1":420,"x2":480,"y2":560}', 0.93),
(1, 'stop_line', 'STOP_LINE', 201, NOW(), '59B-456.78', '/static/outputs/job_1/frame_201.jpg', '{"x1":500,"y1":410,"x2":660,"y2":560}', 0.89);

-- =========================================================
-- ✅ HOÀN TẤT SCHEMA V1.3s
-- =========================================================
