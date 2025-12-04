# ROI type definitions and defaults

ROI_TYPES = {
    "detection_zone": {"shape": "polygon", "color": (255, 255, 0),   "label": "Detection Zone"},  # cyan (BGR)
    "lane_car":       {"shape": "polygon", "color": (0, 200, 0),     "label": "Lane (Car)"},      # green
    "lane_bike":      {"shape": "polygon", "color": (255, 0, 0),     "label": "Lane (Bike)"},     # blue (BGR)
    "direction_zone": {"shape": "polygon", "color": (0, 165, 255),   "label": "Direction Zone"},  # orange
    "stopline":       {"shape": "line",    "color": (0, 0, 255),     "label": "Stop Line"},       # red
    "forbidden_area": {"shape": "polygon", "color": (180, 0, 180),   "label": "Forbidden"},       # purple
    "crosswalk":      {"shape": "polygon", "color": (0, 255, 255),   "label": "Crosswalk"},       # yellow (BGR)
    "traffic_light":  {"shape": "rect",    "color": (255, 255, 255), "label": "Traffic Light"},   # white
}

# Helper to convert BGR to hex string

def bgr_to_hex(bgr):
    b, g, r = bgr
    return f"#{r:02X}{g:02X}{b:02X}"
