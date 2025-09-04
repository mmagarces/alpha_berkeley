"""
BOLT Beamline Context Classes.

Context classes for storing and accessing data from BOLT beamline operations
including motor positions, detector images, and photogrammetry scan results.
"""


from datetime import datetime
from typing import Dict, Any, Optional, ClassVar
from pydantic import Field
from framework.context.base import CapabilityContext

class CurrentGenerateBlueskyExecContext(CapabilityContext):
    """Structured context for motor position data from BOLT beamline via Tiled.
    
    Stores current angular position retrieved from queue server execution and 
    extracted from Tiled metadata for experimental setup, status reporting, 
    and coordination with other beamline operations.
    """

    CONTEXT_TYPE: ClassVar[str] = "BLUESKY_PLAN"
    CONTEXT_CATEGORY: ClassVar[str] = "LIVE_DATA"
    
    # Motor position data
    bluesky_plan: str = Field(description="Bluesky plan identifier (e.g., DMC01:A)")
    condition: str = Field(description="Bluesky plan status and condition description")
    timestamp: datetime = Field(description="Timestamp when position was read")
    
    def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Provide structured access information for LLM consumption and templating."""
        key_ref = key_name if key_name else "key_name"
        
        return {
            "bluesky_plan_id": self.bluesky_plan,   
            "current_bluesky_plan": f"{self.bluesky_plan}°",
            "bluesky_plan_status": self.condition,
            "access_pattern": f"context.{self.CONTEXT_TYPE}.{key_ref}.bluesky_plan, context.{self.CONTEXT_TYPE}.{key_ref}.condition",
            "example_usage": f"Bluesky plan {self.bluesky_plan} is positioned at {{context.{self.CONTEXT_TYPE}.{key_ref}.bluesky_plan}}°",
            "available_fields": ["bluesky_plan", "condition", "timestamp"]
        }
    
    def get_human_summary(self, key: str) -> dict:
        """Generate human-readable summary of bluesky plan position data from Tiled."""
        return {
            "summary": f"Bluesky plan {self.bluesky_plan} positioned at {self.bluesky_plan}° (retrieved from Tiled data after executing through the queue serveron {self.timestamp.strftime('%Y-%m-%d')} at {self.timestamp.strftime('%H:%M')})"
        }
    