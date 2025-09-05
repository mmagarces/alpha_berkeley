"""
Bluesky Plan Creation Capability for BOLT Beamline System.

This capability creates Bluesky plans based on user requests without executing them.
It uses AI to analyze user intent and generate appropriate plan structures
for later execution.
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

from applications.bolt.context_classes import CurrentCreateBlueskyPlanContext
from applications.bolt.bolt_api import bolt_api

logger = get_logger("bolt", "create_bluesky_plan")
registry = get_registry()

@capability_node
class CreateBlueskyPlanCapability(BaseCapability):
    """Create Bluesky plans based on user requests without executing them."""
    
    # Required class attributes for registry configuration
    name = "create_bluesky_plan"
    description = "Create Bluesky plans based on user requests without executing them"
    provides = ["BLUESKY_PLAN_CREATION"]
    requires = []
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute Bluesky plan creation workflow."""
        step = StateManager.get_current_step(state)
        streamer = get_streamer("bolt", "create_bluesky_plan", state)
        
        try:
            user_query = StateManager.get_current_task(state)
            streamer.status("Analyzing user request...")
            streamer.status("Creating Bluesky plan...")


            #API call to create the Bluesky plan, using bolt_api.py as the source
            creation_result = bolt_api.create_bluesky_plan(user_query)
            
            # Create context object, which is returned from the api call
            context = CurrentCreateBlueskyPlanContext(
                bluesky_plan=creation_result.msg,  # Use the message as the plan identifier
                condition=creation_result.condition,
                plan_code=creation_result.plan_code,  # Store the actual plan code
                timestamp=creation_result.timestamp
            )
            
            # Store context in framework state
            context_updates = StateManager.store_context(
                state, 
                registry.context_types.BLUESKY_PLAN_CREATION, 
                step.get("context_key"), 
                context
            )
            
            streamer.status("Bluesky plan created successfully!")
            return context_updates
            
        except Exception as e:
            logger.error(f"Bluesky plan creation error: {e}")
            raise
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify Bluesky plan execution errors for intelligent retry coordination."""

        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                metadata={
                    "user_message": "Bluesky plan creation communication timeout, retrying...",
                    "technical_details": str(exc)
                }
            )
        
        return ErrorClassification(
            severity=ErrorSeverity.CRITICAL,
            metadata={
                "user_message": f"Bluesky plan creation error: {str(exc)}",
                "technical_details": f"Error: {type(exc).__name__}"
            }
        )
    
    @staticmethod
    def get_retry_policy() -> Dict[str, Any]:
        """Define retry policy configuration for Bluesky plan creation operations."""

        return {
            "max_attempts": 3,
            "delay_seconds": 0.5,
            "backoff_factor": 1.5
        }
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for Bluesky plan creation in BOLT beamline."""

        example = OrchestratorExample(
            step=PlannedStep(
                context_key="create_bluesky_plan",
                capability="create_bluesky_plan",
                task_objective="Create Bluesky plan",
                expected_output=registry.context_types.BLUESKY_PLAN_CREATION,
                success_criteria="Bluesky plan successfully created",
                inputs=[]
            ),
            scenario_description="Bluesky plan creation for motor movements, scans, and acquisitions",
            notes=f"Output stored as {registry.context_types.BLUESKY_PLAN_CREATION}. Use for plan creation without execution."
        )
        
        return OrchestratorGuide(
            instructions=f"""**When to plan "create_bluesky_plan" steps:**
- User asks to create or design plans without executing them
- For planning motor movements or scans
- When preparing experimental sequences
- For plan validation and review

**BOLT Beamline Context:**
- Bluesky plan creation (without execution)
- Used for planning motor movements, scans, and acquisitions
- Essential for experimental planning and validation

**Plan Types:**
- Motor movements (move_motor)
- Rotation scans (rotation_scan)
- Camera acquisitions (camera_acquire)
- Linear scans and measurements

**Output: Plan Structure Only**
- Contains: plan details, timestamp
- Available for review and later execution

**Typical Workflow Position:**
- Early in workflow for planning
- Before actual execution
- For plan validation and review""",
            examples=[example],
            order=2  # Early in workflow for control operations
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide task classification guidance for Bluesky plan creation."""
        return TaskClassifierGuide(
            instructions="""Determine if the user wants to CREATE a Bluesky plan (without executing it) in the BOLT beamline system.

BOLT CONTEXT: This is a beamline where Bluesky plans control motors, detectors, and data collection. Users may request plan creation for:
- Motor movements and positioning
- Data collection scans
- Camera acquisitions
- Experimental measurements

NOTE: This is for PLAN CREATION only, not execution. Use generate_bluesky_exec for execution.""",
            examples=[
                ClassifierExample(
                    query="Create a plan to move the motor to 45 degrees",
                    result=True,
                    reason="Explicit request for plan creation."
                ),
                ClassifierExample(
                    query="Design a scan from 0 to 180 degrees",
                    result=True,
                    reason="Request for scan plan creation."
                ),
                ClassifierExample(
                    query="Create a camera acquisition plan",
                    result=True,
                    reason="Request for camera data collection plan creation."
                ),
                ClassifierExample(
                    query="Plan a measurement sequence",
                    result=True,
                    reason="Request for measurement plan creation."
                ),
                ClassifierExample(
                    query="Design a plan to position the sample at 90 degrees",
                    result=True,
                    reason="Request for positioning plan creation."
                ),
                ClassifierExample(
                    query="Create a linear scan plan",
                    result=True,
                    reason="Request for scanning plan creation."
                ),
                ClassifierExample(
                    query="What is the current motor position?",
                    result=False,
                    reason="This is a read request, not plan creation."
                ),
                ClassifierExample(
                    query="Show me the previous data",
                    result=False,
                    reason="Request for historical data, not new execution."
                ),
                ClassifierExample(
                    query="What tools do you have?",
                    result=False,
                    reason="Request is for tool information, not plan execution."
                ),
                ClassifierExample(
                    query="Help me understand the system",
                    result=False,
                    reason="Request for information, not plan execution."
                ),
            ],
            actions_if_true=ClassifierActions()
        )