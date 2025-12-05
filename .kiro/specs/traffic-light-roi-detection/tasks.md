# Implementation Plan - Traffic Light ROI Detection

- [x] 1. Backend: Setup API endpoints và data models




  - Tạo file `traffic-server/app/routers/traffic_light_router.py`
  - Implement Pydantic models: ROIRequest, StopRequest, TLState, WSMessage
  - Implement POST /traffic-light/roi endpoint với ROI validation
  - Implement POST /traffic-light/stop endpoint
  - Implement WebSocket endpoint /ws/traffic-light
  - _Requirements: 2.1, 7.1, 7.2, 7.3, 7.4_

- [x] 1.1 Write property test for ROI validation


  - **Property 15: ROI Validation Rejection**
  - **Validates: Requirements 7.1**

- [x] 1.2 Write property test for error responses


  - **Property 16: Invalid Input Error Response**
  - **Validates: Requirements 7.2**

- [x] 2. Backend: Implement Traffic Light Detection Worker





  - Tạo file `traffic-server/app/services/traffic_light_worker.py`
  - Implement ROIConfig dataclass với to_pixel_coords method
  - Implement TrafficLightWorker class với detection loop
  - Implement crop_roi, classify_state, apply_smoothing methods
  - Load YOLO TL model (ONNX) trong load_model method
  - Implement broadcast method cho WebSocket streaming
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 2.1 Write property test for coordinate transformation


  - **Property 3: Coordinate Round-Trip Preservation**
  - **Validates: Requirements 2.2**

- [x] 2.2 Write property test for state classification


  - **Property 5: State Classification Correctness**
  - **Validates: Requirements 3.3**

- [x] 2.3 Write property test for temporal smoothing


  - **Property 6: Temporal Smoothing Stability**
  - **Validates: Requirements 3.4**

- [x] 2.4 Write property test for WebSocket message format


  - **Property 7: WebSocket Message Completeness**
  - **Validates: Requirements 3.5**

- [x] 3. Backend: Implement Worker Manager





  - Tạo file `traffic-server/app/services/traffic_light_manager.py`
  - Implement TrafficLightWorkerManager class
  - Implement create_worker, get_worker, stop_worker methods
  - Implement worker limit enforcement (max 1 per camera)
  - Implement cleanup_all method cho shutdown
  - _Requirements: 2.3, 6.5_

- [x] 3.1 Write property test for worker lifecycle


  - **Property 10: Worker Lifecycle Cleanup**
  - **Validates: Requirements 5.2**

- [x] 3.2 Write property test for worker limit


  - **Property 14: Worker Count Limit Enforcement**
  - **Validates: Requirements 6.5**

- [x] 4. Backend: Integrate với main application





  - Import traffic_light_router trong `traffic-server/app/main.py`
  - Register router với app.include_router()
  - Initialize worker_manager global instance
  - Add cleanup handler cho app shutdown
  - _Requirements: 2.3, 6.1_

- [x] 4.1 Write property test for concurrent execution


  - **Property 12: Concurrent Execution Independence**
  - **Validates: Requirements 6.1**
-

- [x] 5. Backend: Implement error handling và resource management




  - Add try-catch trong detection_loop với error broadcasting
  - Implement lazy model loading trong load_model
  - Implement stream interruption handling (None frame check)
  - Implement WebSocket disconnect cleanup với 5s timeout
  - Add exception handling trong worker stop method
  - _Requirements: 10.2, 10.3, 10.5, 7.5_

- [x] 5.1 Write property test for lazy loading


  - **Property 23: Lazy Model Loading**
  - **Validates: Requirements 10.2**

- [x] 5.2 Write property test for exception handling


  - **Property 25: Exception Handling Completeness**
  - **Validates: Requirements 10.5**
-

- [x] 6. Checkpoint - Backend tests passing




  - Ensure all tests pass, ask the user if questions arise.
-

- [x] 7. Frontend: Create ROI Selector Component




  - Tạo file `src/components/TrafficLight/ROISelector.tsx`
  - Implement state: isDrawing, startPoint, endPoint, selectedROI
  - Implement mouse event handlers: handleMouseDown, handleMouseMove, handleMouseUp
  - Implement normalizeCoordinates function
  - Implement SVG overlay rendering với rectangle preview
  - Add visual feedback (crosshair cursor, snap circle)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 7.1 Write property test for coordinate normalization


  - **Property 1: Coordinate Normalization Bounds**
  - **Validates: Requirements 1.3**

- [x] 7.2 Write property test for ROI replacement


  - **Property 2: ROI Replacement Consistency**
  - **Validates: Requirements 1.5**

- [x] 7.3 Write unit tests for ROI Selector


  - Test mouse event handlers
  - Test coordinate normalization edge cases
  - Test ROI validation (minimum size)
  - _Requirements: 1.1, 1.2, 1.3_
-

- [ ] 8. Frontend: Create Traffic Light Panel Component



  - Tạo file `src/components/TrafficLight/TrafficLightPanel.tsx`
  - Implement state: TrafficLightPanelState interface
  - Implement responsive layout (flex-row desktop, flex-column mobile)
  - Implement state display với color mapping
  - Implement ROI preview image rendering
  - Add control buttons: Start Detection, Stop Detection
  - Add placeholder "No ROI selected" khi chưa có ROI
  - _Requirements: 4.3, 4.4, 4.5, 4.6, 4.7, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 8.1 Write property test for state-to-color mapping


  - **Property 9: State-to-Color Mapping Consistency**
  - **Validates: Requirements 4.4, 4.5, 4.6, 4.7**

- [ ] 8.2 Write property test for UI completeness
  - **Property 19: UI Component Completeness**
  - **Validates: Requirements 8.2**

- [ ] 8.3 Write unit tests for Traffic Light Panel
  - Test state rendering for each state
  - Test responsive layout breakpoints
  - Test button enable/disable logic
  - _Requirements: 4.4, 4.5, 4.6, 8.3, 8.4_
-

- [-] 9. Frontend: Implement WebSocket Client Manager


  - Tạo file `src/services/trafficLightWebSocket.ts`
  - Implement TrafficLightWSClient class
  - Implement connect, disconnect methods
  - Implement message parsing với type safety
  - Implement auto-reconnect với exponential backoff (max 5 attempts)
  - Implement event callbacks: onMessage, onError, onClose
  - _Requirements: 4.1, 4.2, 9.5_

- [-] 9.1 Write property test for JSON parsing

  - **Property 8: JSON Parsing Robustness**
  - **Validates: Requirements 4.2**

- [ ] 9.2 Write property test for connection loss feedback
  - **Property 22: Connection Loss Feedback**
  - **Validates: Requirements 9.5**

- [ ] 9.3 Write unit tests for WebSocket Client
  - Test connection lifecycle with mocked WebSocket
  - Test message parsing
  - Test auto-reconnect logic
  - Test error handling
  - _Requirements: 4.1, 4.2, 9.5_

- [ ] 10. Frontend: Integrate components vào detection page

  - Update `src/app/(admin)/detection/traffic-light/page.jsx`
  - Import ROISelector và TrafficLightPanel components
  - Implement state management cho TL detection
  - Wire up ROI selection → API call → WebSocket connection
  - Implement Start Detection button handler
  - Implement Stop Detection button handler
  - _Requirements: 2.1, 5.1, 8.1_

- [ ] 10.1 Write property test for API call triggering
  - **Property 20: Toast Notification Triggering**
  - **Validates: Requirements 9.1, 9.2, 9.3**

- [ ] 11. Frontend: Implement toast notifications

  - Add toast cho ROI selection success
  - Add toast cho detection start/stop
  - Add toast cho backend errors với error message
  - Add toast cho WebSocket connection loss
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 11.1 Write property test for error message propagation
  - **Property 21: Error Message Propagation**
  - **Validates: Requirements 9.4**

- [ ] 12. Frontend: Implement error handling và cleanup

  - Add WebSocket cleanup trong useEffect cleanup
  - Add API timeout handling (15s start, 5s stop)
  - Add client-side ROI validation (minimum 2% size)
  - Add loading states cho async operations
  - Prevent multiple simultaneous operations
  - _Requirements: 10.1, 5.4, 5.5_

- [ ] 12.1 Write property test for WebSocket closure cleanup
  - **Property 11: WebSocket Closure State Reset**
  - **Validates: Requirements 5.5**

- [ ] 13. Checkpoint - Frontend tests passing

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Integration: End-to-end flow testing

  - Test complete flow: Select ROI → Start → Receive frames → Stop
  - Verify WebSocket messages format và timing
  - Verify state updates trong UI
  - Verify cleanup sau stop
  - _Requirements: 1.1-10.5_

- [ ] 14.1 Write integration tests
  - Test ROI selection to detection flow
  - Test error recovery scenarios
  - Test concurrent vehicle + TL detection
  - _Requirements: 2.1, 3.1, 4.1, 5.1_

- [ ] 15. Documentation và deployment prep

  - Add README cho TL detection module
  - Document API endpoints trong OpenAPI/Swagger
  - Add environment variables documentation
  - Create deployment checklist
  - _Requirements: All_

- [ ] 16. Final checkpoint - All tests passing

  - Ensure all tests pass, ask the user if questions arise.
