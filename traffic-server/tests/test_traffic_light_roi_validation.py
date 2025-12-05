"""
Property-Based Tests for Traffic Light ROI Validation

Feature: traffic-light-roi-detection
Property 15: ROI Validation Rejection
Validates: Requirements 7.1

Property 16: Invalid Input Error Response
Validates: Requirements 7.2
"""
import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.routers.traffic_light_router import router, ROI, ROIRequest
from fastapi import FastAPI

# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


# =========================================================
# Property 15: ROI Validation Rejection
# **Feature: traffic-light-roi-detection, Property 15: ROI Validation Rejection**
# **Validates: Requirements 7.1**
# =========================================================

@given(
    x=st.one_of(
        st.floats(min_value=-10.0, max_value=-0.001),  # Negative x
        st.floats(min_value=1.001, max_value=10.0)     # x > 1
    ),
    y=st.floats(min_value=0.0, max_value=1.0),
    width=st.floats(min_value=0.02, max_value=1.0),
    height=st.floats(min_value=0.02, max_value=1.0)
)
@settings(max_examples=100, deadline=None)
def test_property_15_roi_validation_rejects_invalid_x(x, y, width, height):
    """
    **Feature: traffic-light-roi-detection, Property 15: ROI Validation Rejection**
    **Validates: Requirements 7.1**
    
    For any ROI coordinates where x is outside [0, 1],
    the API must return HTTP 400 with an error message.
    """
    # Ensure other coordinates are valid
    y = max(0.0, min(0.98, y))
    width = max(0.02, min(1.0 - 0.0, width))
    height = max(0.02, min(1.0 - y, height))
    
    response = client.post(
        "/api/traffic-light/roi",
        json={
            "camera_id": "test_camera",
            "roi": {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }
        }
    )
    
    # Must return 400 or 422 for invalid x (422 is FastAPI's validation error code)
    assert response.status_code in [400, 422], f"Expected 400 or 422 for x={x}, got {response.status_code}"
    
    # Must contain error message
    detail = response.json().get("detail", {})
    if isinstance(detail, dict):
        assert "error" in detail or "message" in detail, "Response must contain error message"
    else:
        assert detail, "Response must contain error message"


@given(
    x=st.floats(min_value=0.0, max_value=1.0),
    y=st.one_of(
        st.floats(min_value=-10.0, max_value=-0.001),  # Negative y
        st.floats(min_value=1.001, max_value=10.0)     # y > 1
    ),
    width=st.floats(min_value=0.02, max_value=1.0),
    height=st.floats(min_value=0.02, max_value=1.0)
)
@settings(max_examples=100, deadline=None)
def test_property_15_roi_validation_rejects_invalid_y(x, y, width, height):
    """
    **Feature: traffic-light-roi-detection, Property 15: ROI Validation Rejection**
    **Validates: Requirements 7.1**
    
    For any ROI coordinates where y is outside [0, 1],
    the API must return HTTP 400 with an error message.
    """
    # Ensure other coordinates are valid
    x = max(0.0, min(0.98, x))
    width = max(0.02, min(1.0 - x, width))
    height = max(0.02, min(1.0 - 0.0, height))
    
    response = client.post(
        "/api/traffic-light/roi",
        json={
            "camera_id": "test_camera",
            "roi": {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }
        }
    )
    
    # Must return 400 or 422 for invalid y (422 is FastAPI's validation error code)
    assert response.status_code in [400, 422], f"Expected 400 or 422 for y={y}, got {response.status_code}"
    
    # Must contain error message
    detail = response.json().get("detail", {})
    if isinstance(detail, dict):
        assert "error" in detail or "message" in detail, "Response must contain error message"
    else:
        assert detail, "Response must contain error message"


@given(
    x=st.floats(min_value=0.0, max_value=1.0),
    y=st.floats(min_value=0.0, max_value=1.0),
    width=st.one_of(
        st.floats(min_value=-10.0, max_value=0.019),  # width < 0.02
        st.floats(min_value=1.001, max_value=10.0)    # width > 1
    ),
    height=st.floats(min_value=0.02, max_value=1.0)
)
@settings(max_examples=100, deadline=None)
def test_property_15_roi_validation_rejects_invalid_width(x, y, width, height):
    """
    **Feature: traffic-light-roi-detection, Property 15: ROI Validation Rejection**
    **Validates: Requirements 7.1**
    
    For any ROI coordinates where width is outside [0.02, 1],
    the API must return HTTP 400 with an error message.
    """
    # Ensure other coordinates are valid
    x = max(0.0, min(0.98, x))
    y = max(0.0, min(0.98, y))
    height = max(0.02, min(1.0 - y, height))
    
    response = client.post(
        "/api/traffic-light/roi",
        json={
            "camera_id": "test_camera",
            "roi": {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }
        }
    )
    
    # Must return 400 or 422 for invalid width (422 is FastAPI's validation error code)
    assert response.status_code in [400, 422], f"Expected 400 or 422 for width={width}, got {response.status_code}"
    
    # Must contain error message
    detail = response.json().get("detail", {})
    if isinstance(detail, dict):
        assert "error" in detail or "message" in detail, "Response must contain error message"
    else:
        assert detail, "Response must contain error message"


@given(
    x=st.floats(min_value=0.0, max_value=1.0),
    y=st.floats(min_value=0.0, max_value=1.0),
    width=st.floats(min_value=0.02, max_value=1.0),
    height=st.one_of(
        st.floats(min_value=-10.0, max_value=0.019),  # height < 0.02
        st.floats(min_value=1.001, max_value=10.0)    # height > 1
    )
)
@settings(max_examples=100, deadline=None)
def test_property_15_roi_validation_rejects_invalid_height(x, y, width, height):
    """
    **Feature: traffic-light-roi-detection, Property 15: ROI Validation Rejection**
    **Validates: Requirements 7.1**
    
    For any ROI coordinates where height is outside [0.02, 1],
    the API must return HTTP 400 with an error message.
    """
    # Ensure other coordinates are valid
    x = max(0.0, min(0.98, x))
    y = max(0.0, min(0.98, y))
    width = max(0.02, min(1.0 - x, width))
    
    response = client.post(
        "/api/traffic-light/roi",
        json={
            "camera_id": "test_camera",
            "roi": {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }
        }
    )
    
    # Must return 400 or 422 for invalid height (422 is FastAPI's validation error code)
    assert response.status_code in [400, 422], f"Expected 400 or 422 for height={height}, got {response.status_code}"
    
    # Must contain error message
    detail = response.json().get("detail", {})
    if isinstance(detail, dict):
        assert "error" in detail or "message" in detail, "Response must contain error message"
    else:
        assert detail, "Response must contain error message"


# =========================================================
# Property 16: Invalid Input Error Response
# **Feature: traffic-light-roi-detection, Property 16: Invalid Input Error Response**
# **Validates: Requirements 7.2**
# =========================================================

@given(
    x=st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100),
    y=st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100),
    width=st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100),
    height=st.floats(allow_nan=False, allow_infinity=False, min_value=-100, max_value=100)
)
@settings(max_examples=100, deadline=None)
def test_property_16_invalid_input_error_response(x, y, width, height):
    """
    **Feature: traffic-light-roi-detection, Property 16: Invalid Input Error Response**
    **Validates: Requirements 7.2**
    
    For any invalid API request (missing fields, wrong types, out-of-range values),
    the response must have status 400 or 422 and contain a non-empty error message
    describing the validation failure.
    """
    # Skip if all values are valid (we're testing invalid inputs)
    if (0 <= x <= 1 and 0 <= y <= 1 and 
        0.02 <= width <= 1 and 0.02 <= height <= 1 and
        x + width <= 1.0 and y + height <= 1.0):
        return
    
    try:
        response = client.post(
            "/api/traffic-light/roi",
            json={
                "camera_id": "test_camera",
                "roi": {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height
                }
            }
        )
    except (ValueError, TypeError) as e:
        # JSON encoding errors are also a form of validation failure
        # This is acceptable as the invalid data cannot even be sent
        return
    
    # Must return 400 or 422 for invalid input
    assert response.status_code in [400, 422], \
        f"Expected 400 or 422 for invalid input, got {response.status_code}"
    
    # Must contain non-empty error message
    response_json = response.json()
    assert response_json, "Response must not be empty"
    
    # Check for error message in detail
    detail = response_json.get("detail")
    assert detail, "Response must contain 'detail' field with error message"
    
    # Verify error message is non-empty
    if isinstance(detail, dict):
        # Structured error response
        assert detail.get("error") or detail.get("message"), \
            "Error response must contain 'error' or 'message' field"
    elif isinstance(detail, list):
        # FastAPI validation error format
        assert len(detail) > 0, "Error list must not be empty"
        assert detail[0].get("msg"), "Error must contain 'msg' field"
    else:
        # String error message
        assert len(str(detail)) > 0, "Error message must not be empty"


@pytest.mark.parametrize("invalid_camera_id", [
    "",  # Empty string
    "../etc/passwd",  # Path traversal
    "camera/with/slash",  # Contains slash
    "camera\\with\\backslash",  # Contains backslash
])
def test_property_16_invalid_camera_id_error_response(invalid_camera_id):
    """
    **Feature: traffic-light-roi-detection, Property 16: Invalid Input Error Response**
    **Validates: Requirements 7.2**
    
    For any invalid camera_id (empty, path traversal, illegal characters),
    the response must have status 400 or 422 and contain an error message.
    """
    response = client.post(
        "/api/traffic-light/roi",
        json={
            "camera_id": invalid_camera_id,
            "roi": {
                "x": 0.1,
                "y": 0.1,
                "width": 0.2,
                "height": 0.2
            }
        }
    )
    
    # Must return 400 or 422 for invalid camera_id
    assert response.status_code in [400, 422], \
        f"Expected 400 or 422 for invalid camera_id '{invalid_camera_id}', got {response.status_code}"
    
    # Must contain error message
    response_json = response.json()
    assert response_json, "Response must not be empty"
    detail = response_json.get("detail")
    assert detail, "Response must contain error message"


@pytest.mark.parametrize("missing_field", ["camera_id", "roi"])
def test_property_16_missing_required_field_error_response(missing_field):
    """
    **Feature: traffic-light-roi-detection, Property 16: Invalid Input Error Response**
    **Validates: Requirements 7.2**
    
    For any request missing required fields, the response must have status 422
    and contain an error message describing the missing field.
    """
    request_data = {
        "camera_id": "test_camera",
        "roi": {
            "x": 0.1,
            "y": 0.1,
            "width": 0.2,
            "height": 0.2
        }
    }
    
    # Remove the field to test
    del request_data[missing_field]
    
    response = client.post(
        "/api/traffic-light/roi",
        json=request_data
    )
    
    # Must return 422 for missing field
    assert response.status_code == 422, \
        f"Expected 422 for missing field '{missing_field}', got {response.status_code}"
    
    # Must contain error message
    response_json = response.json()
    assert response_json, "Response must not be empty"
    detail = response_json.get("detail")
    assert detail, "Response must contain error message about missing field"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
