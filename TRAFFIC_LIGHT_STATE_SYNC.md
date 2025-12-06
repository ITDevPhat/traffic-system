# Traffic Light State Synchronization Fix

## Vấn đề
Backend violation detection đang nhận traffic light state = "UNKNOWN" hoặc dùng color-based detection không chính xác, trong khi frontend có YOLO detection chính xác từ `/ws/traffic-light` WebSocket.

## Giải pháp đã implement (Backend)
✅ Backend `/realtime` WebSocket đã được update để:
1. Nhận command `update_traffic_light_state` từ frontend
2. Ưu tiên dùng state từ frontend YOLO (chính xác nhất)
3. Fallback về color-based detection nếu không có state từ frontend
4. Fallback về GREEN nếu không có detection nào

## Cần làm (Frontend)
Cập nhật file `src/app/(admin)/detection/traffic-light/page.jsx`:

### Bước 1: Thêm function gửi traffic light state
Thêm function này vào component (sau `stopTrafficLightWS`):

```javascript
// Send traffic light state to realtime WebSocket for violation detection
const sendTrafficLightStateToRealtime = (state, confidence) => {
  if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
    const cmd = {
      command: 'update_traffic_light_state',
      state: state,
      confidence: confidence || 0.0
    };
    wsRef.current.send(JSON.stringify(cmd));
    console.log('🚦 Sent TL state to realtime WS:', cmd);
  }
};
```

### Bước 2: Update traffic light WebSocket onmessage
Tìm dòng này trong `startTrafficLightWS()`:

```javascript
if (data.state) {
  setTrafficLightState(data.state);
}
```

Thay bằng:

```javascript
if (data.state) {
  setTrafficLightState(data.state);
  // Send to realtime WebSocket for violation detection
  sendTrafficLightStateToRealtime(data.state, data.confidence);
}
```

### Bước 3: Test
1. Start backend: `python start_server.py`
2. Start frontend: `npm run dev`
3. Mở Traffic Light Detection page
4. Bật cả 2 switches: "Traffic Light Detection" và "Violation Detection"
5. Kiểm tra console log:
   - Frontend: `🚦 Sent TL state to realtime WS: {command: 'update_traffic_light_state', state: 'RED', confidence: 0.95}`
   - Backend: `🚦 Received TL state from frontend: RED (conf=0.95)`
   - Backend: `🎯 Using frontend YOLO TL state: RED (conf=0.95)`
6. Khi đèn đỏ và xe vượt stopline → sẽ thấy log: `🚨 X violations detected! Light=RED`

## Kết quả mong đợi
✅ Backend violation detection nhận đúng traffic light state từ YOLO (RED/GREEN/YELLOW)
✅ Không còn log "light=UNKNOWN" hoặc "light=GREEN" khi đèn đỏ
✅ Violations được detect chính xác khi đèn đỏ
✅ Log sạch, không spam

## Kiến trúc hệ thống
```
Frontend
  ├─ WebSocket 1: /api/traffic-light/ws/traffic-light
  │    └─ Nhận: YOLO traffic light state (RED/GREEN/YELLOW)
  │
  └─ WebSocket 2: /api/traffic-light/realtime
       ├─ Nhận: Video stream + violations
       └─ Gửi: Traffic light state (từ WS1) → Violation detection
```

## Debug
Nếu vẫn thấy "light=UNKNOWN":
1. Check frontend console: có log "🚦 Sent TL state to realtime WS" không?
2. Check backend log: có log "🚦 Received TL state from frontend" không?
3. Check WebSocket connection: `wsRef.current.readyState === WebSocket.OPEN`?
4. Check traffic light detection có đang chạy không (switch bật)?
