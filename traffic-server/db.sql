-- =========================================================
-- 🚦 TRAFFIC VIOLATION DETECTION DATABASE SCHEMA (PostgreSQL)
-- =========================================================
-- Phiên bản: 1.6 (Replaced ENUM → TEXT)
-- Ngày cập nhật: 2025-10-30
-- =========================================================

-- =========================================================
-- XÓA CÁC BẢNG, VIEW CŨ
-- =========================================================
DROP VIEW IF EXISTS vehicle_violation_stats CASCADE;
DROP VIEW IF EXISTS violation_summary CASCADE;
DROP VIEW IF EXISTS violation_stats CASCADE;
DROP TABLE IF EXISTS bboxes CASCADE;
DROP TABLE IF EXISTS violations CASCADE;
DROP TABLE IF EXISTS rois CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS video_jobs CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS cameras CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS violation_types CASCADE;
DROP TABLE IF EXISTS models CASCADE;

-- =========================================================
-- 1️⃣ BẢNG NGƯỜI DÙNG (USERS)
-- =========================================================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',          -- admin | user
    avatar_url TEXT,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Lưu thông tin người dùng hệ thống (admin hoặc user).';

-- =========================================================
-- 2️⃣ BẢNG MODELS (Thông tin mô hình AI)
-- =========================================================
CREATE TABLE models (
    model_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    model_type TEXT NOT NULL,                -- vehicle | plate | ocr | traffic_light | violation
    file_path TEXT NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    framework VARCHAR(50) DEFAULT 'YOLO',
    confidence_threshold FLOAT DEFAULT 0.5,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE models IS 'Lưu thông tin các mô hình AI (YOLO, OCR, Traffic Light, ...).';

-- =========================================================
-- 3️⃣ BẢNG VỊ TRÍ (LOCATIONS)
-- =========================================================
CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_location UNIQUE (latitude, longitude)
);

COMMENT ON TABLE locations IS 'Thông tin vị trí địa lý của camera và khu vực giám sát.';

-- =========================================================
-- 4️⃣ BẢNG CAMERAS
-- =========================================================
CREATE TABLE cameras (
    camera_id SERIAL PRIMARY KEY,
    location_id INT REFERENCES locations(location_id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    ip_address VARCHAR(45),
    stream_url TEXT,
    status TEXT DEFAULT 'active',
    install_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE cameras IS 'Thông tin camera giám sát giao thông.';

-- =========================================================
-- 5️⃣ BẢNG VIDEO_JOBS
-- =========================================================
CREATE TABLE video_jobs (
    video_job_id SERIAL PRIMARY KEY,
    camera_id INT REFERENCES cameras(camera_id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    upload_time TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'pending',                  -- pending | processing | done | failed
    processing_stage VARCHAR(30) DEFAULT 'uploaded',-- uploaded | detecting | tracking | completed
    processed_at TIMESTAMP,
    output_path TEXT,
    fps FLOAT,
    duration FLOAT,
    notes TEXT
);

CREATE INDEX idx_video_jobs_status ON video_jobs(status);
COMMENT ON TABLE video_jobs IS 'Video được tải lên và trạng thái pipeline AI.';

-- =========================================================
-- 6️⃣ BẢNG VEHICLES
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

COMMENT ON TABLE vehicles IS 'Thông tin phương tiện đã nhận dạng.';

-- =========================================================
-- 7️⃣ BẢNG ROIS (REGION OF INTEREST)
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
COMMENT ON TABLE rois IS 'Vùng ROI (vạch dừng, khu vực vi phạm, v.v.).';

-- =========================================================
-- 8️⃣ BẢNG VIOLATION_TYPES
-- =========================================================
CREATE TABLE violation_types (
    violation_type_code VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    fine_amount DECIMAL(12,2),
    severity TEXT DEFAULT 'medium'                  -- low | medium | high
);

COMMENT ON TABLE violation_types IS 'Danh mục các loại vi phạm.';

-- =========================================================
-- 9️⃣ BẢNG VIOLATIONS
-- =========================================================
CREATE TABLE violations (
    violation_id SERIAL PRIMARY KEY,
    video_job_id INT REFERENCES video_jobs(video_job_id) ON DELETE CASCADE,
    vehicle_id INT REFERENCES vehicles(vehicle_id) ON DELETE SET NULL,
    violation_type_code VARCHAR(50) REFERENCES violation_types(violation_type_code) ON DELETE SET NULL,
    frame INT,
    timestamp TIMESTAMP,
    roi_type VARCHAR(50),
    evidence_img TEXT,
    plate VARCHAR(20),
    confidence FLOAT,
    model_id INT REFERENCES models(model_id) ON DELETE SET NULL,
    verification_status TEXT DEFAULT 'unverified',  -- unverified | verified | rejected
    verified_by INT REFERENCES users(user_id) ON DELETE SET NULL,
    verified_source TEXT DEFAULT 'manual',          -- manual | ai | external
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_violations_video_job_id ON violations(video_job_id);
CREATE INDEX idx_violations_timestamp ON violations(timestamp);
CREATE INDEX idx_violations_plate ON violations(plate);
COMMENT ON TABLE violations IS 'Chi tiết các hành vi vi phạm.';

-- =========================================================
-- 🔟 BẢNG BBOXES
-- =========================================================
CREATE TABLE bboxes (
    bbox_id SERIAL PRIMARY KEY,
    violation_id INT REFERENCES violations(violation_id) ON DELETE CASCADE,
    x1 FLOAT NOT NULL,
    y1 FLOAT NOT NULL,
    x2 FLOAT NOT NULL,
    y2 FLOAT NOT NULL,
    width FLOAT GENERATED ALWAYS AS (x2 - x1) STORED,
    height FLOAT GENERATED ALWAYS AS (y2 - y1) STORED,
    confidence FLOAT,
    label VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bboxes_violation_id ON bboxes(violation_id);
CREATE INDEX idx_bboxes_label ON bboxes(label);
COMMENT ON TABLE bboxes IS 'Bounding box của đối tượng hoặc hành vi vi phạm.';

-- =========================================================
-- 🔢 VIEW THỐNG KÊ
-- =========================================================
CREATE OR REPLACE VIEW violation_summary AS
SELECT 
    v.violation_type_code,
    t.description AS violation_name,
    COUNT(*) FILTER (WHERE v.violation_type_code IS NOT NULL) AS total,
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

CREATE OR REPLACE VIEW vehicle_violation_stats AS
SELECT 
    v.vehicle_id,
    v.plate,
    COUNT(vi.violation_id) AS total_violations,
    MAX(vi.timestamp) AS last_violation_at
FROM vehicles v
LEFT JOIN violations vi ON v.vehicle_id = vi.vehicle_id
GROUP BY v.vehicle_id, v.plate;

COMMENT ON VIEW vehicle_violation_stats IS 'Thống kê số lượng và thời gian vi phạm gần nhất của từng phương tiện.';

-- =========================================================
-- 📍 THÊM 10 ĐỊA ĐIỂM GIÁM SÁT GIAO THÔNG Ở TP.HCM
-- =========================================================
INSERT INTO locations (name, address, latitude, longitude, description)
VALUES
('Nguyễn Văn Linh - 3/2', 'Quận 7, TP.HCM', 10.732100, 106.705900, 'Ngã tư lớn, thường xảy ra vượt đèn đỏ'),
('Cộng Hòa - Trường Chinh', 'Tân Bình, TP.HCM', 10.801000, 106.653500, 'Giao lộ đông đúc, kẹt xe giờ cao điểm'),
('Cộng Hòa - Út Tịch', 'Tân Bình, TP.HCM', 10.797800, 106.662200, 'Ngã tư gần Etown, lưu lượng lớn'),
('Dương Bá Trạc - Tạ Quang Bửu', 'Quận 8, TP.HCM', 10.743900, 106.679200, 'Khu vực nhiều xe máy vi phạm vạch dừng'),
('Võ Thị Sáu - Nam Kỳ Khởi Nghĩa', 'Quận 3, TP.HCM', 10.783500, 106.692800, 'Ngã tư trung tâm, giao thông phức tạp'),
('Điện Biên Phủ - D1', 'Bình Thạnh, TP.HCM', 10.802300, 106.713400, 'Khu Pearl Plaza, nhiều xe rẽ trái sai làn'),
('Phan Đăng Lưu - Nguyễn Văn Đậu', 'Phú Nhuận, TP.HCM', 10.801100, 106.684300, 'Ngã tư gần Coopmart Phú Nhuận'),
('Nguyễn Hữu Cảnh - Tôn Đức Thắng', 'Quận 1, TP.HCM', 10.787900, 106.710000, 'Khu cầu Thủ Thiêm, lưu lượng xe hơi lớn'),
('Trường Sơn - Hồng Hà', 'Tân Bình, TP.HCM', 10.814600, 106.661500, 'Đường vào sân bay Tân Sơn Nhất'),
('Xa Lộ Hà Nội - Mai Chí Thọ', 'TP Thủ Đức', 10.798800, 106.740900, 'Giao lộ cửa ngõ Đông Sài Gòn, nhiều container');

-- =========================================================
-- 📸 THÊM 10 CAMERA (mỗi camera tương ứng 1 địa điểm)
-- =========================================================
INSERT INTO cameras (location_id, name, model, ip_address, stream_url, status)
VALUES
(1, 'CAM_Q7_01', 'Hikvision DS-2CD2085FWD', '192.168.1.11', 'rtsp://192.168.1.11/stream', 'active'),
(2, 'CAM_TB_01', 'Hikvision DS-2CD2085FWD', '192.168.1.12', 'rtsp://192.168.1.12/stream', 'active'),
(3, 'CAM_ET_01', 'Hikvision DS-2CD2085FWD', '192.168.1.13', 'rtsp://192.168.1.13/stream', 'active'),
(4, 'CAM_Q8_01', 'Hikvision DS-2CD2085FWD', '192.168.1.14', 'rtsp://192.168.1.14/stream', 'active'),
(5, 'CAM_Q3_01', 'Hikvision DS-2CD2085FWD', '192.168.1.15', 'rtsp://192.168.1.15/stream', 'active'),
(6, 'CAM_BT_01', 'Hikvision DS-2CD2085FWD', '192.168.1.16', 'rtsp://192.168.1.16/stream', 'active'),
(7, 'CAM_PN_01', 'Hikvision DS-2CD2085FWD', '192.168.1.17', 'rtsp://192.168.1.17/stream', 'active'),
(8, 'CAM_Q1_01', 'Hikvision DS-2CD2085FWD', '192.168.1.18', 'rtsp://192.168.1.18/stream', 'active'),
(9, 'CAM_SB_01', 'Hikvision DS-2CD2085FWD', '192.168.1.19', 'rtsp://192.168.1.19/stream', 'active'),
(10, 'CAM_TD_01', 'Hikvision DS-2CD2085FWD', '192.168.1.20', 'rtsp://192.168.1.20/stream', 'active');

-- =========================================================
-- 🎞️ THÊM 10 VIDEO TƯƠNG ỨNG CAMERA (ghép từ thư mục D:\ITDevPhat\...)
-- =========================================================
-- =========================================================
-- 🎞️ THÊM 10 VIDEO (CÓ OUTPUT_PATH TRỰC TIẾP)
-- =========================================================
INSERT INTO video_jobs (camera_id, file_name, output_path, status, fps, duration, notes)
VALUES
(1, 'video.mp4', '/videos/video.mp4', 'done', 30.0, 60.0, 'Demo upload - Nguyễn Văn Linh - 3/2'),
(2, 'video2.mp4', '/videos/video2.mp4', 'done', 30.0, 60.0, 'Demo upload - Cộng Hòa - Trường Chinh'),
(3, 'video3.mp4', '/videos/video3.mp4', 'done', 30.0, 60.0, 'Demo upload - Cộng Hòa - Út Tịch'),
(4, 'video4.mp4', '/videos/video4.mp4', 'done', 30.0, 60.0, 'Demo upload - Dương Bá Trạc - Tạ Quang Bửu'),
(5, 'video5.mp4', '/videos/video5.mp4', 'done', 30.0, 60.0, 'Demo upload - Võ Thị Sáu - Nam Kỳ Khởi Nghĩa'),
(6, 'video6.mp4', '/videos/video6.mp4', 'done', 30.0, 60.0, 'Demo upload - Điện Biên Phủ - D1'),
(7, 'video7.mp4', '/videos/video7.mp4', 'done', 30.0, 60.0, 'Demo upload - Phan Đăng Lưu - Nguyễn Văn Đậu'),
(8, 'video8.mp4', '/videos/video8.mp4', 'done', 30.0, 60.0, 'Demo upload - Nguyễn Hữu Cảnh - Tôn Đức Thắng'),
(9, 'video9.mp4', '/videos/video9.mp4', 'done', 30.0, 60.0, 'Demo upload - Trường Sơn - Hồng Hà'),
(10, 'video10.mp4', '/videos/video10.mp4', 'done', 30.0, 60.0, 'Demo upload - Xa Lộ Hà Nội - Mai Chí Thọ');
