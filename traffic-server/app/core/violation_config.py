"""
Violation Detection Configuration
Centralized config for enabling/disabling violation detection
"""

# =========================================================
# 🚨 VIOLATION DETECTION MASTER SWITCH
# =========================================================
# Set to True when traffic rules are implemented and ready
ENABLE_VIOLATIONS = False

# =========================================================
# 📋 VIOLATION TYPES CONFIGURATION
# =========================================================
VIOLATION_RULES = {
    # Demo violations (for testing UI)
    "enable_demo_violations": False,
    
    # Real violation types (disabled until rules are ready)
    "enable_red_light_violations": False,
    "enable_stopline_violations": False,
    "enable_speed_violations": False,
    "enable_wrong_direction_violations": False,
    "enable_no_entry_violations": False,
    "enable_solid_line_violations": False,
}

# =========================================================
# ⚙️ VIOLATION DETECTION SETTINGS
# =========================================================
VIOLATION_SETTINGS = {
    # Speed limit for speeding violations (km/h)
    "speed_limit_kmh": 50.0,
    
    # Confidence thresholds for different violation types
    "confidence_thresholds": {
        "red_light": 0.95,
        "stopline_crossing": 0.95,
        "speed_violation": 0.8,
        "wrong_direction": 0.85,
        "no_entry_zone": 0.9,
        "solid_line_crossing": 0.85,
    },
    
    # Violation persistence settings
    "violation_cooldown_seconds": 5.0,  # Prevent duplicate violations
    "max_violations_per_object": 10,    # Limit violations per track
}

# =========================================================
# 📝 VIOLATION MESSAGES
# =========================================================
VIOLATION_MESSAGES = {
    "system_disabled": "⚠️ Violation detection is currently DISABLED. Traffic rules are being developed.",
    "demo_mode": "🧪 Demo violation mode enabled for testing purposes.",
    "rules_ready": "✅ Traffic violation rules are active and monitoring.",
}

def get_violation_status():
    """Get current violation detection status"""
    return {
        "enabled": ENABLE_VIOLATIONS,
        "rules": VIOLATION_RULES,
        "settings": VIOLATION_SETTINGS,
        "message": VIOLATION_MESSAGES["rules_ready"] if ENABLE_VIOLATIONS else VIOLATION_MESSAGES["system_disabled"]
    }

def is_violation_type_enabled(violation_type: str) -> bool:
    """Check if a specific violation type is enabled"""
    if not ENABLE_VIOLATIONS:
        return False
    
    rule_key = f"enable_{violation_type}_violations"
    return VIOLATION_RULES.get(rule_key, False)