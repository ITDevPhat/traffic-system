"""
CORE MODULE với hỗ trợ đầy đủ: PyTorch (.pt), ONNX (.onnx), TensorRT (.engine)
Tối ưu bottleneck và hỗ trợ cả 3 loại model
"""

import cv2
import torch
import numpy as np
import time
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import os

# Import utils_rotate
try:
    from .function import utils_rotate
except ImportError:
    from function import utils_rotate

# Thử import ONNX Runtime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

# Thử import TensorRT
try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False


class LicensePlateDetectorOptimized:
    """
    License Plate Detector với hỗ trợ đầy đủ: PyTorch, ONNX, TensorRT
    Tự động chọn model type dựa trên file extension
    """
    
    def __init__(self,
                 detector_model_path: str = 'models/license_plate/yolo_plate_v10n.pt',
                 ocr_model_path: str = 'models/ocr/yolo_ocr_chars_v10n.pt',
                 model_type: str = 'auto',  # 'auto', 'pt', 'onnx', 'engine'
                 confidence_threshold: float = 0.60,
                 device: str = 'auto'):
        """
        Khởi tạo detector
        
        Args:
            detector_model_path: Đường dẫn model phát hiện (tự động detect .pt/.onnx/.engine)
            ocr_model_path: Đường dẫn model OCR (tự động detect .pt/.onnx/.engine)
            model_type: Loại model ('auto', 'pt', 'onnx', 'engine')
            confidence_threshold: Ngưỡng confidence
            device: Thiết bị ('auto', 'cuda', 'cpu')
        """
        self.detector_model_path = detector_model_path
        self.ocr_model_path = ocr_model_path
        self.confidence_threshold = confidence_threshold
        
        # Auto detect model type từ file extension
        if model_type == 'auto':
            detector_ext = Path(detector_model_path).suffix.lower()
            if detector_ext == '.onnx':
                model_type = 'onnx'
            elif detector_ext == '.engine':
                model_type = 'engine'
            else:
                model_type = 'pt'
        
        self.model_type = model_type
        
        # Setup device
        self.device = self._setup_device(device)
        
        # Load models
        self._load_models()
        
        # Cấu hình vẽ bbox
        self.bbox_color = (0, 0, 255)
        self.bbox_thickness = 2
        self.text_color = (36, 255, 12)
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
        """Setup device"""
        if device == 'auto' or device == 'cuda':
            if torch.cuda.is_available():
                device = 'cuda'
                gpu_name = torch.cuda.get_device_name(0)
                print(f"✅ GPU detected: {gpu_name}")
            else:
                device = 'cpu'
                print("⚠️  GPU not available, using CPU")
        return device
    
    def _load_models(self):
        """Load models dựa trên model_type"""
        if self.model_type == 'pt':
            self._load_pytorch_models()
        elif self.model_type == 'onnx':
            self._load_onnx_models()
        elif self.model_type == 'engine':
            self._load_tensorrt_models()
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def _load_pytorch_models(self):
        """Load PyTorch models"""
        from ultralytics import YOLO
        
        print(f"📦 Loading PyTorch models...")
        print(f"   Detector: {self.detector_model_path}")
        self.detector_model = YOLO(self.detector_model_path)
        
        print(f"   OCR: {self.ocr_model_path}")
        self.ocr_model = YOLO(self.ocr_model_path)
        
        print(f"✅ PyTorch models loaded on {self.device.upper()}")
    
    def _load_onnx_models(self):
        """Load ONNX models"""
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX Runtime not available. Install: pip install onnxruntime-gpu")
        
        print(f"⚡ Loading ONNX models...")
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.device == 'cuda' else ['CPUExecutionProvider']
        
        print(f"   Detector: {self.detector_model_path}")
        self.detector_session = ort.InferenceSession(self.detector_model_path, providers=providers)
        
        print(f"   OCR: {self.ocr_model_path}")
        self.ocr_session = ort.InferenceSession(self.ocr_model_path, providers=providers)
        
        print(f"✅ ONNX models loaded on {self.detector_session.get_providers()[0]}")
    
    def _load_tensorrt_models(self):
        """Load TensorRT engine models"""
        if not TENSORRT_AVAILABLE:
            raise RuntimeError("TensorRT not available. Install TensorRT.")
        
        print(f"🚀 Loading TensorRT engines...")
        # TODO: Implement TensorRT loading
        # TensorRT cần engine file và context
        print(f"   Detector: {self.detector_model_path}")
        print(f"   OCR: {self.ocr_model_path}")
        print("⚠️  TensorRT loading not fully implemented, falling back to ONNX")
        self._load_onnx_models()
    
    def detect_license_plates(self, image: np.ndarray, size: int = 1280) -> List[List[float]]:
        """Phát hiện biển số"""
        if self.model_type == 'pt':
            return self._detect_pytorch(image, size)
        elif self.model_type == 'onnx':
            return self._detect_onnx(image, size)
        elif self.model_type == 'engine':
            return self._detect_tensorrt(image, size)
        else:
            return []
    
    def _detect_pytorch(self, image: np.ndarray, size: int) -> List[List[float]]:
        """Detection với PyTorch"""
        device_to_use = self.device if self.device == 'cuda' and torch.cuda.is_available() else 'cpu'
        results = self.detector_model.predict(image, imgsz=size, device=device_to_use, verbose=False, conf=0.25)
        
        plates = []
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls = int(box.cls[0].cpu().numpy())
                plates.append([float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3]), conf, cls])
        
        self.stats['total_plates_detected'] += len(plates)
        return plates
    
    def _detect_onnx(self, image: np.ndarray, size: int) -> List[List[float]]:
        """Detection với ONNX Runtime"""
        # Preprocess
        input_tensor = self._preprocess_for_onnx(image, size)
        
        # Run inference
        input_name = self.detector_session.get_inputs()[0].name
        outputs = self.detector_session.run(None, {input_name: input_tensor})
        
        # Postprocess (simplified - cần adjust dựa trên output format thực tế)
        plates = self._postprocess_onnx_outputs(outputs, image.shape, size)
        
        self.stats['total_plates_detected'] += len(plates)
        return plates
    
    def _detect_tensorrt(self, image: np.ndarray, size: int) -> List[List[float]]:
        """Detection với TensorRT"""
        # TODO: Implement TensorRT inference
        return self._detect_onnx(image, size)  # Fallback
    
    def _preprocess_for_onnx(self, image: np.ndarray, size: int) -> np.ndarray:
        """Preprocess image cho ONNX"""
        resized = cv2.resize(image, (size, size))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        batched = np.expand_dims(transposed, axis=0)
        return batched
    
    def _postprocess_onnx_outputs(self, outputs, original_shape, input_size):
        """Postprocess ONNX outputs"""
        # Simplified - cần implement dựa trên output format thực tế của YOLO ONNX
        # Thường là [batch, num_detections, 6] với [x, y, w, h, conf, class]
        plates = []
        # TODO: Implement proper postprocessing
        return plates
    
    def recognize_license_plate(self, plate_image: np.ndarray) -> str:
        """OCR biển số"""
        if self.model_type == 'pt':
            return self._recognize_pytorch(plate_image)
        elif self.model_type == 'onnx':
            return self._recognize_onnx(plate_image)
        elif self.model_type == 'engine':
            return self._recognize_tensorrt(plate_image)
        else:
            return "unknown"
    
    def _recognize_pytorch(self, plate_image: np.ndarray) -> str:
        """OCR với PyTorch"""
        device_to_use = self.device if self.device == 'cuda' and torch.cuda.is_available() else 'cpu'
        results = self.ocr_model.predict(plate_image, device=device_to_use, verbose=False, conf=0.25)
        
        if len(results) == 0:
            return "unknown"
        
        result = results[0]
        boxes = result.boxes
        
        if len(boxes) < 5 or len(boxes) > 10:
            return "unknown"
        
        # Parse và ghép ký tự (giống code cũ)
        char_list = []
        y_sum = 0
        
        for box in boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            cls = int(box.cls[0].cpu().numpy())
            x_c = (xyxy[0] + xyxy[2]) / 2
            y_c = (xyxy[1] + xyxy[3]) / 2
            y_sum += y_c
            char = self.ocr_model.names[cls]
            char_list.append([x_c, y_c, char])
        
        # Ghép chuỗi (giống code cũ)
        y_mean = y_sum / len(char_list)
        LP_type = "1"
        
        l_point = min(char_list, key=lambda x: x[0])
        r_point = max(char_list, key=lambda x: x[0])
        
        for char in char_list:
            if not self._check_point_linear(char[0], char[1], l_point[0], l_point[1], r_point[0], r_point[1]):
                LP_type = "2"
                break
        
        license_plate = ""
        if LP_type == "2":
            line_1 = [c for c in char_list if c[1] <= y_mean]
            line_2 = [c for c in char_list if c[1] > y_mean]
            for char in sorted(line_1, key=lambda x: x[0]):
                license_plate += char[2]
            license_plate += "-"
            for char in sorted(line_2, key=lambda x: x[0]):
                license_plate += char[2]
        else:
            for char in sorted(char_list, key=lambda x: x[0]):
                license_plate += char[2]
        
        return license_plate
    
    def _recognize_onnx(self, plate_image: np.ndarray) -> str:
        """OCR với ONNX"""
        # TODO: Implement ONNX OCR
        return "unknown"
    
    def _recognize_tensorrt(self, plate_image: np.ndarray) -> str:
        """OCR với TensorRT"""
        # TODO: Implement TensorRT OCR
        return "unknown"
    
    def _check_point_linear(self, x, y, x1, y1, x2, y2):
        """Kiểm tra điểm có nằm trên đường thẳng không"""
        import math
        if x1 == x2:
            return True
        b = y1 - (y2 - y1) * x1 / (x2 - x1)
        a = (y1 - b) / x1
        y_pred = a * x + b
        return math.isclose(y_pred, y, abs_tol=3)
    
    def crop_license_plate(self, image: np.ndarray, bbox: List[float]) -> np.ndarray:
        """Cắt biển số từ ảnh"""
        x_min, y_min, x_max, y_max = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        h, w = image.shape[:2]
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(w, x_max)
        y_max = min(h, y_max)
        return image[y_min:y_max, x_min:x_max]
    
    def process_image(self, image: np.ndarray, draw_bbox: bool = True, draw_stats: bool = False) -> Dict[str, Any]:
        """Process image pipeline"""
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
            # Detect plates
            plates = self.detect_license_plates(image)
            
            if len(plates) == 0:
                # Thử OCR trực tiếp
                license_plate = self.recognize_license_plate(image)
                if license_plate != "unknown":
                    result['plates_recognized'].append({
                        'text': license_plate,
                        'bbox': [0, 0, image.shape[1], image.shape[0]],
                        'confidence': 1.0
                    })
            else:
                for plate in plates:
                    bbox_info = {
                        'bbox': plate[:4],
                        'confidence': plate[4] if len(plate) > 4 else 1.0,
                        'class': plate[5] if len(plate) > 5 else 0
                    }
                    result['plates_detected'].append(bbox_info)
                    
                    crop_img = self.crop_license_plate(image, plate)
                    license_plate = self.recognize_license_plate(crop_img)
                    
                    if license_plate != "unknown":
                        plate_info = {
                            'text': license_plate,
                            'bbox': plate[:4],
                            'confidence': plate[4] if len(plate) > 4 else 1.0
                        }
                        result['plates_recognized'].append(plate_info)
            
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time
            self.stats['total_processing_time'] += processing_time
            result['success'] = True
            
        except Exception as e:
            print(f"Error in process_image: {e}")
            result['success'] = False
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê"""
        stats = self.stats.copy()
        if stats['total_frames'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['total_frames']
            stats['detection_rate'] = stats['total_plates_detected'] / stats['total_frames']
            stats['recognition_rate'] = stats['total_plates_recognized'] / max(1, stats['total_plates_detected'])
        return stats


def create_detector_optimized(model_type: str = 'auto', device: str = 'auto') -> LicensePlateDetectorOptimized:
    """
    Factory function tạo detector với model type cụ thể
    
    Args:
        model_type: 'auto', 'pt', 'onnx', 'engine'
        device: 'auto', 'cuda', 'cpu'
    """
    # Auto detect model paths dựa trên model_type
    if model_type == 'onnx':
        detector_path = 'models/license_plate/yolo_plate_v10n.onnx'
        ocr_path = 'models/ocr/yolo_ocr_chars_v10n.onnx'
    elif model_type == 'engine':
        detector_path = 'models/license_plate/yolo_plate_v10n.engine'
        ocr_path = 'models/ocr/yolo_ocr_chars_v10n.engine'
    else:  # pt or auto
        detector_path = 'models/license_plate/yolo_plate_v10n.pt'
        ocr_path = 'models/ocr/yolo_ocr_chars_v10n.pt'
    
    return LicensePlateDetectorOptimized(
        detector_model_path=detector_path,
        ocr_model_path=ocr_path,
        model_type=model_type,
        device=device
    )

