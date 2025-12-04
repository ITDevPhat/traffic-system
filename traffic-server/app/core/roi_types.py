# ROI type definitions and defaults for backend
# Colors are defined in BGR for OpenCV, expose hex for API
from typing import Dict, Any, Tuple

ROI_TYPES: Dict[str, Dict[str, Any]] = {
    "detection_zone": {"shape": "polygon", "color_bgr": (255, 255, 0),   "label": "Detection Zone"},  # cyan (BGR)
    "lane_car":       {"shape": "polygon", "color_bgr": (0, 200, 0),     "label": "Lane (Car)"},
    "lane_bike":      {"shape": "polygon", "color_bgr": (255, 0, 0),     "label": "Lane (Bike)"},   # blue (BGR)
    "direction_zone": {"shape": "polygon", "color_bgr": (0, 165, 255),   "label": "Direction Zone"},
    "stopline":       {"shape": "line",    "color_bgr": (0, 0, 255),     "label": "Stop Line"},
    "solid_line":     {"shape": "line",    "color_bgr": (0, 0, 255),     "label": "Solid Line"},      # Red
    "dashed_line":    {"shape": "line",    "color_bgr": (255, 255, 255), "label": "Dashed Line"},    # White
    "forbidden_area": {"shape": "polygon", "color_bgr": (180, 0, 180),   "label": "Forbidden"},
    "opposite_lane":  {"shape": "polygon", "color_bgr": (0, 0, 128),     "label": "Opposite Lane"},  # Dark Red
    "crosswalk":      {"shape": "polygon", "color_bgr": (0, 255, 255),   "label": "Crosswalk"},    # yellow (BGR)
    "traffic_light":  {"shape": "rect",    "color_bgr": (255, 255, 255), "label": "Traffic Light"},
}


def bgr_to_hex(bgr: Tuple[int, int, int]) -> str:
    b, g, r = bgr
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)


def roi_types_public() -> Dict[str, Dict[str, Any]]:
    # Expose shape and color (hex) for clients
    out = {}
    for k, v in ROI_TYPES.items():
        out[k] = {
            "shape": v["shape"],
            "label": v.get("label", k),
            "color": bgr_to_hex(v["color_bgr"]),
        }
    return out
