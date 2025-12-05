"""
Property-Based Tests for Traffic Light Worker Manager

Feature: traffic-light-roi-detection

Property 10: Worker Lifecycle Cleanup
Validates: Requirements 5.2

Property 14: Worker Count Limit Enforcement
Validates: Requirements 6.5
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
from pathlib import Path
import asyncio
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


# =========================================================
# Property 10: Worker Lifecycle Cleanup
# **Feature: traffic-light-roi-detection, Property 10: Worker Lifecycle Cleanup**
# **Validates: Requirements 5.2**
# =========================================================

@given(
    camera_id=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
        min_size=1,
        max_size=20
    ),
    x=st.floats(min_value=0.0, max_value=0.8, allow_nan=False, allow_infinity=False),
    y=st.floats(min_value=0.0, max_value=0.8, allow_nan=False, allow_infinity=False),
    width=st.floats(min_value=0.02, max_value=0.2, allow_nan=False, allow_infinity=False),
    height=st.floats(min_value=0.02, max_value=0.2, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
@async_test
async def test_property_10_worker_lifecycle_cleanup(camera_id, x, y, width, height):
    """
    **Feature: traffic-light-roi-detection, Property 10: Worker Lifecycle Cleanup**
    **Validates: Requirements 5.2**
    
    For any stop request with valid camera_id, the corresponding worker must
    transition to stopped state and be removed from the active workers registry.
    """
    # Ensure ROI doesn't extend beyond frame
    assume(x + width <= 1.0)
    assume(y + height <= 1.0)
    
    # Create manager
    manager = TrafficLightWorkerManager()
    
    # Create ROI config
    roi = ROIConfig(x=x, y=y, width=width, height=height)
    
    # Create worker (without model to avoid loading YOLO)
    worker = await manager.create_worker(
        camera_id=camera_id,
        roi=roi,
        video_stream=None,
        model=None
    )
    
    # Verify worker is registered
    assert camera_id in manager.workers, \
        f"Worker for {camera_id} should be registered"
    assert manager.get_worker(camera_id) is not None, \
        f"get_worker should return worker for {camera_id}"
    assert manager.get_active_worker_count() == 1, \
        "Should have exactly 1 active worker"
    
    # Stop worker
    await manager.stop_worker(camera_id)
    
    # Verify worker is removed from registry
    assert camera_id not in manager.workers, \
        f"Worker for {camera_id} should be removed from registry"
    assert manager.get_worker(camera_id) is None, \
        f"get_worker should return None after stop"
    assert manager.get_active_worker_count() == 0, \
        "Should have 0 active workers after stop"
    
    # Verify worker is stopped
    assert not worker.is_running, \
        "Worker should be in stopped state (is_running=False)"


@async_test
async def test_property_10_stop_nonexistent_worker_raises_error():
    """
    **Feature: traffic-light-roi-detection, Property 10: Worker Lifecycle Cleanup**
    **Validates: Requirements 5.2**
    
    Attempting to stop a non-existent worker should raise KeyError.
    """
    manager = TrafficLightWorkerManager()
    
    # Try to stop non-existent worker
    with pytest.raises(KeyError, match="No worker found"):
        await manager.stop_worker("nonexistent_camera")


@given(
    num_workers=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=None)
@async_test
async def test_property_10_cleanup_all_removes_all_workers(num_workers):
    """
    **Feature: traffic-light-roi-detection, Property 10: Worker Lifecycle Cleanup**
    **Validates: Requirements 5.2**
    
    cleanup_all() must stop and remove all active workers, regardless of count.
    """
    manager = TrafficLightWorkerManager()
    
    # Create multiple workers
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    for i in range(num_workers):
        camera_id = f"camera_{i}"
        await manager.create_worker(
            camera_id=camera_id,
            roi=roi,
            video_stream=None,
            model=None
        )
    
    # Verify all workers are registered
    assert manager.get_active_worker_count() == num_workers, \
        f"Should have {num_workers} active workers"
    
    # Cleanup all
    await manager.cleanup_all()
    
    # Verify all workers are removed
    assert manager.get_active_worker_count() == 0, \
        "Should have 0 active workers after cleanup_all"
    assert len(manager.workers) == 0, \
        "Workers registry should be empty"


@async_test
async def test_property_10_worker_cleanup_releases_resources():
    """
    **Feature: traffic-light-roi-detection, Property 10: Worker Lifecycle Cleanup**
    **Validates: Requirements 5.2**
    
    Worker cleanup must release resources (clear subscribers, set model to None).
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    # Create worker
    worker = await manager.create_worker(
        camera_id="test_camera",
        roi=roi,
        video_stream=None,
        model=None
    )
    
    # Add some subscribers to simulate active connections
    worker.subscribers.append(asyncio.Queue())
    worker.subscribers.append(asyncio.Queue())
    
    # Stop worker
    await manager.stop_worker("test_camera")
    
    # Verify resources are released
    assert len(worker.subscribers) == 0, \
        "Subscribers should be cleared"
    assert worker.model is None, \
        "Model reference should be None"
    assert not worker.is_running, \
        "Worker should not be running"


# =========================================================
# Property 14: Worker Count Limit Enforcement
# **Feature: traffic-light-roi-detection, Property 14: Worker Count Limit Enforcement**
# **Validates: Requirements 6.5**
# =========================================================

@given(
    camera_id=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
        min_size=1,
        max_size=20
    ),
    num_attempts=st.integers(min_value=2, max_value=10)
)
@settings(max_examples=100, deadline=None)
@async_test
async def test_property_14_worker_count_limit_enforcement(camera_id, num_attempts):
    """
    **Feature: traffic-light-roi-detection, Property 14: Worker Count Limit Enforcement**
    **Validates: Requirements 6.5**
    
    For any camera_id, the number of active TL workers for that camera must
    never exceed 1 (enforced by worker manager).
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    # Try to create multiple workers for same camera
    for i in range(num_attempts):
        worker = await manager.create_worker(
            camera_id=camera_id,
            roi=roi,
            video_stream=None,
            model=None
        )
        
        # Verify only 1 worker exists for this camera
        assert manager.get_active_worker_count() == 1, \
            f"Should have exactly 1 worker, got {manager.get_active_worker_count()}"
        
        assert camera_id in manager.workers, \
            f"Worker for {camera_id} should be registered"
        
        # Verify it's the latest worker
        assert manager.get_worker(camera_id) is worker, \
            "get_worker should return the latest worker instance"
    
    # Cleanup
    await manager.cleanup_all()


@given(
    num_cameras=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=None)
@async_test
async def test_property_14_multiple_cameras_allowed(num_cameras):
    """
    **Feature: traffic-light-roi-detection, Property 14: Worker Count Limit Enforcement**
    **Validates: Requirements 6.5**
    
    Multiple cameras can have workers simultaneously (limit is per-camera, not global).
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    # Create workers for different cameras
    camera_ids = [f"camera_{i}" for i in range(num_cameras)]
    
    for camera_id in camera_ids:
        await manager.create_worker(
            camera_id=camera_id,
            roi=roi,
            video_stream=None,
            model=None
        )
    
    # Verify all workers are registered
    assert manager.get_active_worker_count() == num_cameras, \
        f"Should have {num_cameras} active workers"
    
    # Verify each camera has exactly 1 worker
    for camera_id in camera_ids:
        assert manager.get_worker(camera_id) is not None, \
            f"Camera {camera_id} should have a worker"
    
    # Cleanup
    await manager.cleanup_all()


@async_test
async def test_property_14_replacing_worker_stops_old_worker():
    """
    **Feature: traffic-light-roi-detection, Property 14: Worker Count Limit Enforcement**
    **Validates: Requirements 6.5**
    
    When creating a new worker for a camera with existing worker,
    the old worker must be stopped before creating the new one.
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    # Create first worker
    worker1 = await manager.create_worker(
        camera_id="test_camera",
        roi=roi,
        video_stream=None,
        model=None
    )
    
    # Verify first worker is running
    assert worker1.is_running, "First worker should be running"
    
    # Create second worker for same camera
    worker2 = await manager.create_worker(
        camera_id="test_camera",
        roi=roi,
        video_stream=None,
        model=None
    )
    
    # Verify first worker is stopped
    assert not worker1.is_running, \
        "First worker should be stopped when replaced"
    
    # Verify second worker is running
    assert worker2.is_running, "Second worker should be running"
    
    # Verify only 1 worker in registry
    assert manager.get_active_worker_count() == 1, \
        "Should have exactly 1 worker"
    
    # Verify it's the second worker
    assert manager.get_worker("test_camera") is worker2, \
        "Registry should contain the second worker"
    
    # Cleanup
    await manager.cleanup_all()


@given(
    operations=st.lists(
        st.tuples(
            st.sampled_from(['create', 'stop']),
            st.text(
                alphabet=st.characters(min_codepoint=97, max_codepoint=122),
                min_size=1,
                max_size=10
            )
        ),
        min_size=5,
        max_size=20
    )
)
@settings(max_examples=50, deadline=None)
@async_test
async def test_property_14_worker_count_never_exceeds_one_per_camera(operations):
    """
    **Feature: traffic-light-roi-detection, Property 14: Worker Count Limit Enforcement**
    **Validates: Requirements 6.5**
    
    For any sequence of create/stop operations, each camera must never have
    more than 1 active worker at any time.
    """
    manager = TrafficLightWorkerManager()
    roi = ROIConfig(x=0.1, y=0.1, width=0.2, height=0.2)
    
    # Track expected state
    expected_cameras = set()
    
    for operation, camera_id in operations:
        if operation == 'create':
            await manager.create_worker(
                camera_id=camera_id,
                roi=roi,
                video_stream=None,
                model=None
            )
            expected_cameras.add(camera_id)
            
        elif operation == 'stop':
            try:
                await manager.stop_worker(camera_id)
                expected_cameras.discard(camera_id)
            except KeyError:
                # OK if worker doesn't exist
                pass
        
        # Verify invariant: each camera has at most 1 worker
        active_cameras = manager.get_active_cameras()
        
        # Check no duplicates
        assert len(active_cameras) == len(set(active_cameras)), \
            "Active cameras list should not contain duplicates"
        
        # Check count matches expected
        assert manager.get_active_worker_count() == len(expected_cameras), \
            f"Worker count mismatch: expected {len(expected_cameras)}, got {manager.get_active_worker_count()}"
        
        # Verify each expected camera has exactly 1 worker
        for cam_id in expected_cameras:
            worker = manager.get_worker(cam_id)
            assert worker is not None, \
                f"Camera {cam_id} should have a worker"
            assert worker.camera_id == cam_id, \
                f"Worker camera_id mismatch"
    
    # Cleanup
    await manager.cleanup_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
