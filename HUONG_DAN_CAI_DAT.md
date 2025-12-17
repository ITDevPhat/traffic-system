# Hướng Dẫn Cài Đặt Chi Tiết - LVTN

## 1. Cài Đặt Môi Trường Python

### Tạo môi trường Anaconda
```bash
conda create -n LVTN python=3.11
conda activate LVTN
```

### Cài đặt PyTorch với CUDA (nếu có GPU)
```bash
# Cho GPU CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Hoặc CPU only
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Cài đặt các thư viện Python
```bash
pip install -r requirements.txt
```

## 2. Cài Đặt Node.js Dependencies

```bash
npm install
# hoặc
yarn install
```

## 3. Cấu Hình Database

### Cài đặt PostgreSQL
- Tải và cài đặt PostgreSQL từ https://www.postgresql.org/download/
- Tạo database mới: `traffic_db`

### Cấu hình kết nối
Tạo file `.env` trong thư mục `traffic-server/`:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/traffic_db
SECRET_KEY=your-secret-key-here
DEVICE=cuda:0
STATIC_DIR=static
VIDEOS_DIR=videos
EVIDENCE_DIR=evidence
```

## 4. Chạy Ứng Dụng

### Backend (Terminal 1)
```bash
cd traffic-server
conda activate LVTN
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Terminal 2)
```bash
npm run dev
```

## 5. Truy Cập Ứng Dụng

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 6. Kiểm Tra GPU (Tùy chọn)

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"Current device: {torch.cuda.current_device()}")
    print(f"Device name: {torch.cuda.get_device_name()}")
```

## Lưu Ý

- Đảm bảo có đủ dung lượng ổ cứng (ít nhất 10GB cho models)
- GPU khuyến nghị: RTX 3050 trở lên
- RAM khuyến nghị: 8GB trở lên