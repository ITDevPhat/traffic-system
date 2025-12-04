"""
New Rule Engine for stateful violation detection
Engine chính để phát hiện vi phạm giao thông với VehicleState
"""

from typing import List, Dict, Any, Optional, Callable
import logging

from .models import VehicleState, ViolationEvent, ViolationContext
from .rules import red_light_rule, solid_line_rule, forbidden_area_rule

logger = logging.getLogger(__name__)


class ViolationEngine:
    """
    New Rule Engine for stateful violation detection
    
    Uses VehicleState objects and pluggable rule functions
    """
    
    def __init__(self):
        """Initialize ViolationEngine with empty rule set"""
        # List of rule functions: (vehicle: VehicleState, ctx: ViolationContext) -> Optional[ViolationEvent]
        self._rules: List[Callable[[VehicleState, ViolationContext], Optional[ViolationEvent]]] = []
        
        logger.info("ViolationEngine initialized")
    
    def register_rule(self, rule_fn: Callable[[VehicleState, ViolationContext], Optional[ViolationEvent]]):
        """
        Register a rule function
        
        Args:
            rule_fn: Function that takes (vehicle: VehicleState, ctx: ViolationContext) -> Optional[ViolationEvent]
        """
        self._rules.append(rule_fn)
        logger.debug(f"Registered rule: {rule_fn.__name__}")
    
    def evaluate(
        self,
        vehicles: Dict[int, VehicleState],
        ctx: ViolationContext
    ) -> List[ViolationEvent]:
        """
        Evaluate all vehicles against all registered rules
        
        Args:
            vehicles: Dict mapping track_id -> VehicleState
            ctx: ViolationContext with frame info, traffic lights, ROIs
            
        Returns:
            List of ViolationEvent objects
        """
        violations: List[ViolationEvent] = []
        
        for vehicle in vehicles.values():
            # Clear previous violation
            vehicle.violation = None
            
            # Evaluate all rules for this vehicle
            for rule in self._rules:
                try:
                    evt = rule(vehicle, ctx)
                    if evt is not None:
                        vehicle.violation = evt
                        violations.append(evt)
                        # Option: break after first violation per vehicle
                        break
                except Exception as e:
                    logger.error(f"Error in rule {rule.__name__} for track {vehicle.track_id}: {e}")
        
        return violations
    

def create_default_violation_engine() -> ViolationEngine:
    """
    Create a ViolationEngine with default rules registered
    
    Returns:
        ViolationEngine with red_light_rule and other basic rules
    """
    engine = ViolationEngine()
    engine.register_rule(red_light_rule)
    engine.register_rule(solid_line_rule)
    engine.register_rule(forbidden_area_rule)
    # Add more rules here as needed
    return engine
