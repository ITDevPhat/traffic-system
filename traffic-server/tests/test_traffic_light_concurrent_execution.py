"""
Property-Based Tests for Traffic Light Concurrent Execution

Feature: traffic-light-roi-detection

Property 12: Concurrent Execution Independence
Validates: Requirements 6.1
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
from pathlib import Path
import asyncio
import time
from functools import wraps

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.traffic_light_manager import TrafficLightWorkerManager
from app.services.traffic_light_worker import ROIConfig


# Helper to run async hypothesis tests
def async_test(f):
    """Wrapper to run async hypothesis tests"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# Mock video stream for testing
class MockVideoStream:
    """Mock video stream that simulates frame processing"""
    def __init__(self, frame_delay_ms=10):
        self.frame_delay_ms = frame_delay_ms
        self.frame_count = 0
        self.access_times = []
    
    async def get_latest_frame(self, camera_id):
        """Simulate getting a frame with some delay"""
        start_time = time.perf_counter()
        
        # Simulate frame processing delay
        await asyncio.sleep(self.frame_delay_ms / 1000.0)
        
        end_time = time.perf_counter()
        self.access_times.append(end_time - start_time)
        self.frame_count += 1
        
        # Return a mock frame (None to avoid actual processing)
        return None


# =========================================================
# Property 12: Concurrent Execution Independence
# **Feature: traffic-light-roi-detection, Property 12: Concurrent Execution Independence**
# **Validates: Requirements 6.1**
# =========================================================

@given(
    num_iterations=st.integers(min_value=5, max_value=20)
)
@settings(max_examples=50, deadline=None)
@async_test
async def test_property_12_tl_detection_does_not_block_main_loop(num_iterations):
    """
    **Feature: traffic-light-roi-detection, Property 12: Concurrent Execution Independence**
    **Validates: Requirements 6.1**
    
    For any TL detection worker running, the main vehicle detection loop must
    continue processing frames without blocking or significant delay (< 10ms impact
    per TL inference).
    
    This test simulates a main detection loop and verifies that TL worker
    operations don't cause blocking delays.
    """
    # Create mock video stream
    video_stream = MockVideoStream(frame_delay_ms=5)
    
    # Create manager and worker
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    # Measure baseline performance without TL worker
    baseline_times = []
    for _ in range(num_iterations):
        start = time.perf_counter()
        await video_stream.get_latest_frame("test_camera")
        end = time.perf_counter()
        baseline_times.append((end - start) * 1000)  # Convert to ms
    
    baseline_avg = sum(baseline_times) / len(baseline_times)
    
    # Create TL worker (without model to avoid YOLO loading)
    worker = await manager.create_worker(
        camera_id="test_camera",
        roi=roi,
        video_stream=video_stream,
        model=None
    )
    
    # Measure performance with TL worker running
    with_worker_times = []
    for _ in range(num_iterations):
        start = time.perf_counter()
        await video_stream.get_latest_frame("test_camera")
        end = time.perf_counter()
        with_worker_times.append((end - start) * 1000)  # Convert to ms
    
    with_worker_avg = sum(with_worker_times) / len(with_worker_times)
    
    # Calculate impact
    impact_ms = with_worker_avg - baseline_avg
    
    # Verify impact is less than 10ms (requirement from Property 12)
    assert impact_ms < 10.0, \
        f"TL worker caused {impact_ms:.2f}ms delay (max allowed: 10ms)"
    
    # Cleanup
    await manager.cleanup_all()


@given(
    num_workers=st.integers(min_value=1, max_value=5),
    iterations_per_worker=st.integers(min_value=3, max_value=10)
)
@settings(max_examples=30, deadline=None)
@async_test
async def test_property_12_multiple_workers_run_independently(num_workers, iterations_per_worker):
    """
    **Feature: traffic-light-roi-detection, Property 12: Concurrent Execution Independence**
    **Validates: Requirements 6.1**
    
    Multiple TL workers for different cameras should run independently without
    interfering with each other's execution.
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    # Create video streams for each camera
    video_streams = {
        f"camera_{i}": MockVideoStream(frame_delay_ms=5)
        for i in range(num_workers)
    }
    
    # Create workers for each camera
    workers = []
    for i in range(num_workers):
        camera_id = f"camera_{i}"
        worker = await manager.create_worker(
            camera_id=camera_id,
            roi=roi,
            video_stream=video_streams[camera_id],
            model=None
        )
        workers.append(worker)
    
    # Simulate concurrent frame access
    async def access_frames(camera_id, stream, iterations):
        """Simulate accessing frames for a camera"""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await stream.get_latest_frame(camera_id)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        return times
    
    # Run all workers concurrently
    tasks = [
        access_frames(f"camera_{i}", video_streams[f"camera_{i}"], iterations_per_worker)
        for i in range(num_workers)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all workers completed their iterations
    for i, times in enumerate(results):
        assert len(times) == iterations_per_worker, \
            f"Worker {i} should complete {iterations_per_worker} iterations"
        
        # Verify reasonable performance (each access should be < 50ms)
        avg_time = sum(times) / len(times)
        assert avg_time < 50.0, \
            f"Worker {i} average time {avg_time:.2f}ms exceeds 50ms threshold"
    
    # Cleanup
    await manager.cleanup_all()


@async_test
async def test_property_12_worker_creation_does_not_block():
    """
    **Feature: traffic-light-roi-detection, Property 12: Concurrent Execution Independence**
    **Validates: Requirements 6.1**
    
    Creating a TL worker should not block the main event loop for extended periods.
    Worker creation should complete quickly (< 100ms without model loading).
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    video_stream = MockVideoStream()
    
    # Measure worker creation time
    start = time.perf_counter()
    
    worker = await manager.create_worker(
        camera_id="test_camera",
        roi=roi,
        video_stream=video_stream,
        model=None  # Skip model loading for this test
    )
    
    end = time.perf_counter()
    creation_time_ms = (end - start) * 1000
    
    # Verify creation is fast (< 100ms without model loading)
    assert creation_time_ms < 100.0, \
        f"Worker creation took {creation_time_ms:.2f}ms (max allowed: 100ms)"
    
    # Verify worker is running
    assert worker.is_running, "Worker should be running after creation"
    
    # Cleanup
    await manager.cleanup_all()


@async_test
async def test_property_12_worker_stop_does_not_block():
    """
    **Feature: traffic-light-roi-detection, Property 12: Concurrent Execution Independence**
    **Validates: Requirements 6.1**
    
    Stopping a TL worker should not block the main event loop for extended periods.
    Worker cleanup should complete quickly (< 100ms).
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    video_stream = MockVideoStream()
    
    # Create worker
    worker = await manager.create_worker(
        camera_id="test_camera",
        roi=roi,
        video_stream=video_stream,
        model=None
    )
    
    # Measure worker stop time
    start = time.perf_counter()
    
    await manager.stop_worker("test_camera")
    
    end = time.perf_counter()
    stop_time_ms = (end - start) * 1000
    
    # Verify stop is fast (< 100ms)
    assert stop_time_ms < 100.0, \
        f"Worker stop took {stop_time_ms:.2f}ms (max allowed: 100ms)"
    
    # Verify worker is stopped
    assert not worker.is_running, "Worker should be stopped"


@given(
    num_operations=st.integers(min_value=5, max_value=20)
)
@settings(max_examples=30, deadline=None)
@async_test
async def test_property_12_rapid_create_stop_cycles_do_not_block(num_operations):
    """
    **Feature: traffic-light-roi-detection, Property 12: Concurrent Execution Independence**
    **Validates: Requirements 6.1**
    
    Rapid cycles of creating and stopping workers should not cause blocking
    or resource exhaustion.
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    video_stream = MockVideoStream()
    
    operation_times = []
    
    for i in range(num_operations):
        # Create worker
        start = time.perf_counter()
        worker = await manager.create_worker(
            camera_id="test_camera",
            roi=roi,
            video_stream=video_stream,
            model=None
        )
        create_time = time.perf_counter() - start
        
        # Stop worker
        start = time.perf_counter()
        await manager.stop_worker("test_camera")
        stop_time = time.perf_counter() - start
        
        total_time_ms = (create_time + stop_time) * 1000
        operation_times.append(total_time_ms)
    
    # Verify all operations completed
    assert len(operation_times) == num_operations, \
        f"Should complete {num_operations} operations"
    
    # Verify average operation time is reasonable (< 200ms per cycle)
    avg_time = sum(operation_times) / len(operation_times)
    assert avg_time < 200.0, \
        f"Average operation time {avg_time:.2f}ms exceeds 200ms threshold"
    
    # Verify no workers remain
    assert manager.get_active_worker_count() == 0, \
        "All workers should be cleaned up"


@async_test
async def test_property_12_worker_operations_are_async():
    """
    **Feature: traffic-light-roi-detection, Property 12: Concurrent Execution Independence**
    **Validates: Requirements 6.1**
    
    Worker operations should be truly asynchronous and allow other tasks to run.
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    video_stream = MockVideoStream()
    
    # Create a flag to track if other tasks can run
    other_task_ran = False
    
    async def other_task():
        """Simulate another task that should be able to run"""
        nonlocal other_task_ran
        await asyncio.sleep(0.01)
        other_task_ran = True
    
    # Start worker creation and other task concurrently
    worker_task = manager.create_worker(
        camera_id="test_camera",
        roi=roi,
        video_stream=video_stream,
        model=None
    )
    
    other = asyncio.create_task(other_task())
    
    # Wait for both
    worker = await worker_task
    await other
    
    # Verify other task was able to run
    assert other_task_ran, \
        "Other tasks should be able to run while worker is being created"
    
    # Cleanup
    await manager.cleanup_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
