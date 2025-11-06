#!/usr/bin/env python3
"""
CORE MODULE - HUYẾT MẠCH CỦA DỰ ÁN
Tập trung tất cả logic quan trọng: model inference, xử lý ảnh, vẽ bbox, output
Sử dụng Ultralytics YOLO (v8/v10) - Dễ dàng deploy lên web
"""

import cv2
import torch
import numpy as np
import time
from typing import List, Tuple, Optional, Dict, Any
from ultralytics import YOLO

# Import utils_rotate - hỗ trợ cả relative và absolute import
try:
    from .function import utils_rotate
except ImportError:
    from function import utils_rotate


class LicensePlateDetector:
    """
    Class chính chứa toàn bộ huyết mạch của hệ thống nhận dạng biển số xe
    """
    
    def __init__(self, 
                 detector_model_path: str = 'models/lp_v10n_1280_adamw.pt',
                 ocr_model_path: str = 'models/ocr_chars_yolov10s_T4x2.pt',
                 confidence_threshold: float = 0.60,
                 device: str = 'auto'):
        """
        Khởi tạo detector với các model
        
        Args:
            detector_model_path: Đường dẫn model phát hiện biển số
            ocr_model_path: Đường dẫn model OCR ký tự
            confidence_threshold: Ngưỡng confidence cho OCR
            device: Thiết bị sử dụng ('auto', 'cuda', 'cpu')
        """
        self.detector_model_path = detector_model_path
        self.ocr_model_path = ocr_model_path
        self.confidence_threshold = confidence_threshold
        
        # Cấu hình thiết bị - HUYẾT MẠCH 0: Phát hiện GPU
        self.device = self._setup_device(device)
        
        # Load models - HUYẾT MẠCH 1: Khởi tạo model
        self._load_models()
        
        # Cấu hình vẽ bbox
        self.bbox_color = (0, 0, 255)  # Màu đỏ cho bbox
        self.bbox_thickness = 2
        self.text_color = (36, 255, 12)  # Màu xanh lá cho text
        self.text_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_scale = 0.9
        self.text_thickness = 2
        
        # Thống kê
        self.stats = {
            'total_frames': 0,
            'total_plates_detected': 0,
            'total_plates_recognized': 0,
            'total_processing_time': 0.0
        }
    
    def _setup_device(self, device: str) -> str:
        """
        HUYẾT MẠCH 0: Cấu hình thiết bị (GPU/CPU)
        Ưu tiên GPU, chỉ dùng CPU khi không có GPU
        
        Args:
            device: Thiết bị mong muốn ('auto', 'cuda', 'cpu')
            
        Returns:
            Thiết bị thực tế sẽ sử dụng
        """
        if device == 'auto' or device == 'cuda':
            # Luôn ưu tiên GPU
            if torch.cuda.is_available():
                device = 'cuda'
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                print(f"GPU detected: {gpu_name} ({gpu_memory:.1f}GB)")
                print(f"Using GPU for inference")
            else:
                if device == 'cuda':
                    print("WARNING: CUDA requested but not available, falling back to CPU")
                else:
                    print("GPU not available, using CPU")
                    print("Install CUDA and PyTorch with CUDA support for better performance")
                device = 'cpu'
        else:
            # Chỉ dùng CPU khi user yêu cầu cụ thể
            print(f"Using CPU (user specified)")
        
        return device
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết về thiết bị đang sử dụng
        
        Returns:
            Dict chứa thông tin thiết bị
        """
        device_info = {
            'device': self.device,
            'cuda_available': torch.cuda.is_available(),
            'cuda_device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        if self.device == 'cuda' and torch.cuda.is_available():
            device_info.update({
                'gpu_name': torch.cuda.get_device_name(0),
                'gpu_memory_total': torch.cuda.get_device_properties(0).total_memory / 1024**3,
                'gpu_memory_allocated': torch.cuda.memory_allocated(0) / 1024**3,
                'gpu_memory_cached': torch.cuda.memory_reserved(0) / 1024**3
            })
        
        return device_info
    
    def benchmark_device(self, test_image: np.ndarray = None, warmup: bool = True) -> Dict[str, float]:
        """
        Benchmark hiệu suất thiết bị hiện tại
        
        Args:
            test_image: Ảnh test (nếu None sẽ tạo ảnh test)
            warmup: Chạy warm-up trước khi benchmark
            
        Returns:
            Dict chứa thời gian xử lý
        """
        if test_image is None:
            # Tạo ảnh test
            test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Warm-up GPU (rất quan trọng cho lần đầu tiên)
        if warmup and self.device == 'cuda':
            for _ in range(3):
                self.detect_license_plates(test_image)
        
        # Test detection (chạy nhiều lần và lấy trung bình)
        detection_times = []
        for _ in range(5):
            start_time = time.time()
            plates = self.detect_license_plates(test_image)
            detection_times.append(time.time() - start_time)
        
        detection_time = min(detection_times)  # Lấy thời gian tốt nhất
        
        # Test OCR nếu có biển số
        ocr_time = 0.0
        if len(plates) > 0:
            crop_img = self.crop_license_plate(test_image, plates[0])
            ocr_times = []
            for _ in range(5):
                start_time = time.time()
                self.recognize_license_plate(crop_img)
                ocr_times.append(time.time() - start_time)
            ocr_time = min(ocr_times)
        
        return {
            'device': self.device,
            'detection_time': detection_time,
            'ocr_time': ocr_time,
            'total_time': detection_time + ocr_time,
            'fps': 1.0 / (detection_time + ocr_time) if (detection_time + ocr_time) > 0 else 0
        }
    
    def _load_models(self):
        """HUYẾT MẠCH 1: Load các model YOLO với GPU support (Ultralytics)"""
        try:
            print(f"Loading detector model: {self.detector_model_path}")
            # Load model và set device ngay từ đầu
            self.detector_model = YOLO(self.detector_model_path)
            # Đảm bảo model được move lên device đúng
            if self.device == 'cuda' and torch.cuda.is_available():
                # YOLO tự động sử dụng device khi predict, nhưng có thể set trước
                print(f"✅ Detector model loaded - will use GPU: {torch.cuda.get_device_name(0)}")
            else:
                print("⚠️  Detector model loaded on CPU")
            
            print(f"Loading OCR model: {self.ocr_model_path}")
            self.ocr_model = YOLO(self.ocr_model_path)
            if self.device == 'cuda' and torch.cuda.is_available():
                print(f"✅ OCR model loaded - will use GPU: {torch.cuda.get_device_name(0)}")
            else:
                print("⚠️  OCR model loaded on CPU")
            
            print("✅ Models loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            raise
    
    def detect_license_plates(self, image: np.ndarray, size: int = 1280) -> List[List[float]]:
        """
        HUYẾT MẠCH 2: Phát hiện biển số trong ảnh với GPU support (Ultralytics)
        
        Args:
            image: Ảnh đầu vào (numpy array)
            size: Kích thước resize cho inference
            
        Returns:
            List các bounding box [xmin, ymin, xmax, ymax, confidence, class]
        """
        try:
            # Đảm bảo device đúng - nếu cuda không available thì dùng cpu
            device_to_use = self.device
            if device_to_use == 'cuda' and not torch.cuda.is_available():
                device_to_use = 'cpu'
            
            # Chạy model phát hiện với Ultralytics YOLO
            results = self.detector_model.predict(
                image, 
                imgsz=size, 
                device=device_to_use,  # Đảm bảo dùng device đúng
                verbose=False,
                conf=0.25  # Confidence threshold
            )
            
            # Parse kết quả
            plates = []
            if len(results) > 0:
                result = results[0]
                boxes = result.boxes
                
                for box in boxes:
                    # Lấy tọa độ xyxy
                    xyxy = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    
                    # Format: [xmin, ymin, xmax, ymax, confidence, class]
                    plates.append([
                        float(xyxy[0]), float(xyxy[1]), 
                        float(xyxy[2]), float(xyxy[3]),
                        conf, cls
                    ])
            
            self.stats['total_plates_detected'] += len(plates)
            return plates
            
        except Exception as e:
            print(f"Error in detect_license_plates: {e}")
            return []
    
    def crop_license_plate(self, image: np.ndarray, bbox: List[float]) -> np.ndarray:
        """
        HUYẾT MẠCH 3: Cắt biển số từ ảnh gốc
        
        Args:
            image: Ảnh gốc
            bbox: Bounding box [xmin, ymin, xmax, ymax, ...]
            
        Returns:
            Ảnh biển số đã cắt
        """
        x_min, y_min, x_max, y_max = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        
        # Đảm bảo tọa độ trong phạm vi ảnh
        h, w = image.shape[:2]
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(w, x_max)
        y_max = min(h, y_max)
        
        crop_img = image[y_min:y_max, x_min:x_max]
        return crop_img
    
    def _read_plate_characters(self, plate_image: np.ndarray) -> str:
        """
        Đọc ký tự từ ảnh biển số sử dụng YOLO OCR model (Ultralytics)
        
        Args:
            plate_image: Ảnh biển số đã cắt
            
        Returns:
            Chuỗi biển số hoặc "unknown"
        """
        try:
            # Đảm bảo device đúng - nếu cuda không available thì dùng cpu
            device_to_use = self.device
            if device_to_use == 'cuda' and not torch.cuda.is_available():
                device_to_use = 'cpu'
            
            # Chạy OCR model với confidence thấp hơn để phát hiện nhiều ký tự hơn
            results = self.ocr_model.predict(
                plate_image,
                device=device_to_use,  # Đảm bảo dùng device đúng
                verbose=False,
                conf=0.25  # Giảm xuống 0.25 để phát hiện tốt hơn
            )
            
            if len(results) == 0:
                return "unknown"
            
            result = results[0]
            boxes = result.boxes
            
            # Cần ít nhất 5 ký tự (biển số ngắn nhất), tối đa 10
            if len(boxes) == 0 or len(boxes) < 5 or len(boxes) > 10:
                return "unknown"
            
            # Parse kết quả - lấy tọa độ và class của từng ký tự
            char_list = []
            y_sum = 0
            
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                cls = int(box.cls[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())
                
                x_c = (xyxy[0] + xyxy[2]) / 2
                y_c = (xyxy[1] + xyxy[3]) / 2
                y_sum += y_c
                
                # Lấy tên class từ model (ký tự thực tế)
                char = self.ocr_model.names[cls]
                char_list.append([x_c, y_c, char])
            
            # Phát hiện biển 1 hay 2 dòng
            y_mean = y_sum / len(char_list)
            LP_type = "1"
            
            # Tìm 2 điểm xa nhất để kiểm tra
            l_point = min(char_list, key=lambda x: x[0])
            r_point = max(char_list, key=lambda x: x[0])
            
            # Kiểm tra xem các ký tự có nằm trên cùng 1 đường thẳng không
            for char in char_list:
                if not self._check_point_linear(char[0], char[1], l_point[0], l_point[1], r_point[0], r_point[1]):
                    LP_type = "2"
                    break
            
            # Ghép chuỗi biển số
            license_plate = ""
            if LP_type == "2":
                line_1 = [c for c in char_list if c[1] <= y_mean]
                line_2 = [c for c in char_list if c[1] > y_mean]
                
                for char in sorted(line_1, key=lambda x: x[0]):
                    license_plate += char[2]  # char[2] đã là string rồi
                license_plate += "-"
                for char in sorted(line_2, key=lambda x: x[0]):
                    license_plate += char[2]
            else:
                for char in sorted(char_list, key=lambda x: x[0]):
                    license_plate += char[2]
            
            return license_plate
            
        except Exception as e:
            return "unknown"
    
    def _check_point_linear(self, x, y, x1, y1, x2, y2):
        """Kiểm tra xem điểm có nằm trên đường thẳng không"""
        import math
        if x1 == x2:
            return True
        b = y1 - (y2 - y1) * x1 / (x2 - x1)
        a = (y1 - b) / x1
        y_pred = a * x + b
        return math.isclose(y_pred, y, abs_tol=3)
    
    def recognize_license_plate(self, plate_image: np.ndarray) -> str:
        """
        HUYẾT MẠCH 4: OCR biển số - CORE LOGIC
        
        Args:
            plate_image: Ảnh biển số đã cắt
            
        Returns:
            Chuỗi biển số đã nhận dạng hoặc "unknown"
        """
        try:
            # Thử nhiều cách xử lý ảnh để tối ưu OCR
            for contrast_change in range(2):  # 0: không đổi, 1: đổi contrast
                for threshold_change in range(2):  # 0: không đổi, 1: đổi threshold
                    try:
                        # Xử lý ảnh (xoay, chỉnh contrast)
                        processed_img = utils_rotate.deskew(plate_image, contrast_change, threshold_change)
                        
                        # Chạy OCR với Ultralytics
                        license_plate = self._read_plate_characters(processed_img)
                        
                        if license_plate != "unknown":
                            self.stats['total_plates_recognized'] += 1
                            return license_plate
                            
                    except Exception as e:
                        continue
            
            return "unknown"
            
        except Exception as e:
            print(f"Error in recognize_license_plate: {e}")
            return "unknown"
    
    def draw_bbox(self, image: np.ndarray, bbox: List[float], 
                  label: str = "", confidence: float = 0.0) -> np.ndarray:
        """
        HUYẾT MẠCH 5: Vẽ bounding box và label
        
        Args:
            image: Ảnh để vẽ
            bbox: Bounding box [xmin, ymin, xmax, ymax, ...]
            label: Text hiển thị
            confidence: Độ tin cậy
            
        Returns:
            Ảnh đã vẽ bbox và text
        """
        x_min, y_min, x_max, y_max = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        
        # Vẽ bounding box
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), 
                     self.bbox_color, self.bbox_thickness)
        
        # Vẽ label nếu có
        if label and label != "unknown":
            # Tính vị trí text (phía trên bbox)
            text_y = max(y_min - 10, 20)
            
            # Vẽ background cho text
            (text_width, text_height), _ = cv2.getTextSize(
                label, self.text_font, self.text_scale, self.text_thickness)
            
            cv2.rectangle(image, 
                         (x_min, text_y - text_height - 5), 
                         (x_min + text_width + 5, text_y + 5),
                         (0, 0, 0), -1)
            
            # Vẽ text
            cv2.putText(image, label, (x_min + 2, text_y - 2), 
                       self.text_font, self.text_scale, 
                       self.text_color, self.text_thickness)
        
        return image
    
    def draw_fps(self, image: np.ndarray, fps: float) -> np.ndarray:
        """
        Vẽ FPS lên ảnh
        
        Args:
            image: Ảnh để vẽ
            fps: FPS hiện tại
            
        Returns:
            Ảnh đã vẽ FPS
        """
        fps_text = f"FPS: {int(fps)}"
        cv2.putText(image, fps_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return image
    
    def draw_stats(self, image: np.ndarray) -> np.ndarray:
        """
        Vẽ thống kê lên ảnh
        
        Args:
            image: Ảnh để vẽ
            
        Returns:
            Ảnh đã vẽ stats
        """
        y_offset = 60
        stats_texts = [
            f"Frames: {self.stats['total_frames']}",
            f"Plates Detected: {self.stats['total_plates_detected']}",
            f"Plates Recognized: {self.stats['total_plates_recognized']}",
            f"Avg Time: {self.stats['total_processing_time']/max(1, self.stats['total_frames']):.3f}s"
        ]
        
        for text in stats_texts:
            cv2.putText(image, text, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_offset += 25
        
        return image
    
    def process_image(self, image: np.ndarray, 
                     draw_bbox: bool = True, 
                     draw_stats: bool = False,
                     save_crop: bool = False) -> Dict[str, Any]:
        """
        HUYẾT MẠCH CHÍNH: Xử lý toàn bộ pipeline từ ảnh đến kết quả
        
        Args:
            image: Ảnh đầu vào
            draw_bbox: Có vẽ bbox không
            draw_stats: Có vẽ thống kê không
            save_crop: Có lưu ảnh crop không
            
        Returns:
            Dict chứa kết quả xử lý
        """
        start_time = time.time()
        self.stats['total_frames'] += 1
        
        result = {
            'image': image.copy(),
            'plates_detected': [],
            'plates_recognized': [],
            'processing_time': 0.0,
            'success': False
        }
        
        try:
            # Bước 1: Phát hiện biển số
            plates = self.detect_license_plates(image)
            
            if len(plates) == 0:
                # Không tìm thấy biển số, thử OCR trực tiếp trên toàn ảnh
                license_plate = self._read_plate_characters(image)
                if license_plate != "unknown":
                    result['plates_recognized'].append({
                        'text': license_plate,
                        'bbox': [0, 0, image.shape[1], image.shape[0]],
                        'confidence': 1.0
                    })
                    if draw_bbox:
                        cv2.putText(result['image'], license_plate, (7, 70), 
                                   self.text_font, self.text_scale, 
                                   self.text_color, self.text_thickness)
            else:
                # Bước 2: Xử lý từng biển số tìm được
                for plate in plates:
                    # Lưu thông tin bbox
                    bbox_info = {
                        'bbox': plate[:4],
                        'confidence': plate[4] if len(plate) > 4 else 1.0,
                        'class': plate[5] if len(plate) > 5 else 0
                    }
                    result['plates_detected'].append(bbox_info)
                    
                    # Cắt biển số
                    crop_img = self.crop_license_plate(image, plate)
                    
                    # Lưu ảnh crop nếu cần
                    if save_crop:
                        cv2.imwrite(f"crop_plate_{len(result['plates_detected'])}.jpg", crop_img)
                    
                    # OCR biển số
                    license_plate = self.recognize_license_plate(crop_img)
                    
                    if license_plate != "unknown":
                        plate_info = {
                            'text': license_plate,
                            'bbox': plate[:4],
                            'confidence': plate[4] if len(plate) > 4 else 1.0
                        }
                        result['plates_recognized'].append(plate_info)
                        
                        # Vẽ bbox và text
                        if draw_bbox:
                            result['image'] = self.draw_bbox(
                                result['image'], plate, license_plate, plate[4] if len(plate) > 4 else 1.0)
            
            # Tính thời gian xử lý
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time
            self.stats['total_processing_time'] += processing_time
            
            # Vẽ thống kê nếu cần
            if draw_stats:
                result['image'] = self.draw_stats(result['image'])
            
            result['success'] = True
            
        except Exception as e:
            print(f"Error in process_image: {e}")
            result['success'] = False
        
        return result
    
    def process_video_frame(self, frame: np.ndarray, 
                           prev_time: float = 0.0) -> Tuple[np.ndarray, float, Dict[str, Any]]:
        """
        Xử lý frame video với FPS calculation
        
        Args:
            frame: Frame video
            prev_time: Thời gian frame trước
            
        Returns:
            Tuple (processed_frame, current_time, result_dict)
        """
        current_time = time.time()
        
        # Xử lý frame
        result = self.process_image(frame, draw_bbox=True, draw_stats=True)
        
        # Tính FPS
        if prev_time > 0:
            fps = 1.0 / (current_time - prev_time)
            result['image'] = self.draw_fps(result['image'], fps)
        
        return result['image'], current_time, result
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê hiện tại"""
        stats = self.stats.copy()
        if stats['total_frames'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['total_frames']
            stats['detection_rate'] = stats['total_plates_detected'] / stats['total_frames']
            stats['recognition_rate'] = stats['total_plates_recognized'] / max(1, stats['total_plates_detected'])
        else:
            stats['avg_processing_time'] = 0.0
            stats['detection_rate'] = 0.0
            stats['recognition_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset thống kê"""
        self.stats = {
            'total_frames': 0,
            'total_plates_detected': 0,
            'total_plates_recognized': 0,
            'total_processing_time': 0.0
        }
    
    def set_bbox_style(self, color: Tuple[int, int, int] = (0, 0, 255), 
                      thickness: int = 2):
        """Thay đổi style vẽ bbox"""
        self.bbox_color = color
        self.bbox_thickness = thickness
    
    def set_text_style(self, color: Tuple[int, int, int] = (36, 255, 12),
                      scale: float = 0.9, thickness: int = 2):
        """Thay đổi style vẽ text"""
        self.text_color = color
        self.text_scale = scale
        self.text_thickness = thickness


# Factory function để tạo detector với cấu hình khác nhau
def create_detector(model_type: str = "default", device: str = "auto") -> LicensePlateDetector:
    """
    Factory function tạo detector với các cấu hình khác nhau
    
    Args:
        model_type: "default" (sử dụng model v10 mới nhất)
        device: Thiết bị sử dụng ('auto', 'cuda', 'cpu')
        
    Returns:
        LicensePlateDetector instance
    """
    # Sử dụng model YOLO v10 mới nhất
    return LicensePlateDetector(
        detector_model_path='models/lp_v10n_1280_adamw.pt',
        ocr_model_path='models/ocr_chars_yolov10s_T4x2.pt',
        device=device
    )


# Test function
def test_core():
    """Test function để kiểm tra core module"""
    print("Testing Core Module...")
    
    try:
        # Tạo detector
        detector = create_detector("standard")
        print("Detected created successfully")
        
        # Test với ảnh mẫu
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.process_image(test_image)
        
        print(f"Process image test passed")
        print(f"Processing time: {result['processing_time']:.3f}s")
        print(f"Plates detected: {len(result['plates_detected'])}")
        print(f"Plates recognized: {len(result['plates_recognized'])}")
        
        # Test stats
        stats = detector.get_stats()
        print(f"Stats: {stats}")
        
        print("Core module test completed successfully!")
        
    except Exception as e:
        print(f"Core module test failed: {e}")


if __name__ == "__main__":
    test_core()
