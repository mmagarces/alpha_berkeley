"""
Detector Image Capture Capability for BOLT Beamline System.

This capability captures single images from the area detector
in the BOLT imaging beamline. It's used for individual measurements,
test shots, and quality checks.
"""
from typing import Dict, Any, Optional

from framework.base import (
    BaseCapability, capability_node,
    OrchestratorGuide, OrchestratorExample, PlannedStep,
    ClassifierActions, ClassifierExample, TaskClassifierGuide
)
from framework.base.errors import ErrorClassification, ErrorSeverity
from framework.registry import get_registry
from framework.state import AgentState, StateManager
from configs.logger import get_logger
from configs.streaming import get_streamer

from applications.bolt.context_classes import CurrentDisplayObjectContext
from applications.bolt.bolt_api import bolt_api

logger = get_logger("bolt", "detector_image_capture")
registry = get_registry()

@capability_node
class DisplayObjectCapability(BaseCapability):
    """Display object in BOLT beamline."""
    
    # Required class attributes for registry configuration
    name = "display_object"
    description = "Display object"
    provides = ["DISPLAY_OBJECT"]
    requires = []
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute display object workflow."""
        step = StateManager.get_current_step(state)
        streamer = get_streamer("bolt", "display_object", state)
        
        try:
            query = StateManager.get_current_task(state).lower()
            
            # Extract folder name from query
            import re
            
            # Look for folder name patterns
            folder_match = re.search(r'in\s+(\S+)', query)
            if folder_match:
                folder_name = folder_match.group(1)
            else:
                # Extract the last word in the sentence
                words = query.split()
                folder_name = words[-1] if words else "."
            
            # Remove quotes from folder name if present
            folder_name = folder_name.strip('"\'')
            streamer.status("Preparing object...")
            
            streamer.status("Displaying object...")
            image_data = bolt_api.display_object(folder_name)
            
            # Create context object
            context = CurrentDisplayObjectContext(
                condition=image_data.condition,
                msg=image_data.msg,
                timestamp=image_data.timestamp
            )
            
            # Store context in framework state
            context_updates = StateManager.store_context(
                state, 
                registry.context_types.DETECTOR_IMAGE, 
                step.get("context_key"), 
                context
            )
            
            streamer.status("Object displayed successfully!")
            return context_updates
            
        except Exception as e:
            logger.error(f"Display object error: {e}")
            raise
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify display object errors for intelligent retry coordination."""

        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                metadata={
                    "user_message": "Display object communication timeout, retrying...",
                    "technical_details": str(exc)
                }
            )
        
        return ErrorClassification(
            severity=ErrorSeverity.CRITICAL,
            metadata={
                "user_message": f"Display object error: {str(exc)}",
                "technical_details": f"Error: {type(exc).__name__}"
            }
        )
    
    @staticmethod
    def get_retry_policy() -> Dict[str, Any]:
        """Define retry policy configuration for display object operations."""

        return {
            "max_attempts": 3,
            "delay_seconds": 0.5,
            "backoff_factor": 1.5
        }
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for display object in BOLT beamline."""

        example = OrchestratorExample(
            step=PlannedStep(
                context_key="display_object",
                capability="display_object",
                task_objective="Display object",
                expected_output=registry.context_types.DISPLAY_OBJECT,
                success_criteria="Object successfully displayed",
                inputs=[]
            ),
            scenario_description="Displaying object for measurement or quality check",
            notes=f"Output stored as {registry.context_types.DISPLAY_OBJECT}. Use for test shots and individual measurements."
        )
        
        return OrchestratorGuide(
            instructions=f"""**When to plan "display_object" steps:**
- User asks to take a single image or measurement
- For test shots before starting photogrammetry scans
- When checking sample alignment or positioning
- For quality control and beam verification

**BOLT Beamline Context:**
- Displays object
- Used for individual measurements and test shots
- Essential for experimental verification and setup

**Image Types:**
- Object
- Test shots for alignment
- Quality control measurements

**Output: Stored in Tiled**
- Contains: object_data, display_conditions, timestamp
- Available for analysis and experimental verification

**Typical Workflow Position:**
- After motor positioning
- Before full photogrammetry scans (for testing)
- For standalone measurements and quality checks""",
            examples=[example],
            order=3  # After positioning, before full scans
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide task classification guidance for display object."""
        return TaskClassifierGuide(
            instructions="""Determine if the user wants to DISPLAY a single image from the area detector in the BOLT beamline system.

BOLT CONTEXT: This is a beamline where area detectors capture images for analysis. Users may request:
- Object
- Test shots before scans
- Quality control images
- Alignment verification images""",
            examples=[
                ClassifierExample(
                    query="Display object in file",
                    result=True,
                    reason="Direct request for image capture."
                ),
                ClassifierExample(
                    query="Display object",
                    result=True,
                    reason="Request for single image capture."
                ),
                ClassifierExample(
                    query="Display object",
                    result=True,
                    reason="Request to capture detector image."
                ),
                ClassifierExample(
                    query="Display object",
                    result=True,
                    reason="Request for test image before experiments."
                ),
                ClassifierExample(
                    query="Get an image of the sample",
                    result=True,
                    reason="Request to capture sample image."
                ),
                ClassifierExample(
                    query="Check beam alignment with an image",
                    result=True,
                    reason="Request for alignment verification image."
                ),
                ClassifierExample(
                    query="Start a photogrammetry scan",
                    result=False,
                    reason="This is a full scan request, not single image capture."
                ),
                ClassifierExample(
                    query="Move the motor to 45 degrees",
                    result=False,
                    reason="This is a motor movement command, not image capture."
                ),
                ClassifierExample(
                    query="What is the current motor position?",
                    result=False,
                    reason="This is a position read request, not image capture."
                ),
                ClassifierExample(
                    query="Show me the previous image",
                    result=False,
                    reason="Request for historical data, not new image capture."
                ),
                ClassifierExample(
                    query="What tools do you have?",
                    result=False,
                    reason="Request is for tool information, not image capture."
                ),
            ],
            actions_if_true=ClassifierActions()
        )