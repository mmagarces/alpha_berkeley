"""
Bluesky Plan Execution Capability for BOLT Beamline System.

This capability generates and executes Bluesky plans based on user requests.
It uses AI to analyze user intent, select appropriate plans, and execute them
on the queue server.
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

from applications.bolt.context_classes import CurrentGenerateBlueskyExecContext
from applications.bolt.bolt_api import bolt_api

logger = get_logger("bolt", "generate_bluesky_exec")
registry = get_registry()

@capability_node
class GenerateBlueskyExecCapability(BaseCapability):
    """Generate and execute Bluesky plans based on user requests."""
    
    # Required class attributes for registry configuration
    name = "generate_bluesky_exec"
    description = "Generate and execute Bluesky plans based on user requests"
    provides = ["BLUESKY_PLAN"]
    requires = []
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute Bluesky plan generation and execution workflow."""
        step = StateManager.get_current_step(state)
        streamer = get_streamer("bolt", "generate_bluesky_exec", state)
        
        try:
            user_query = StateManager.get_current_task(state)
            streamer.status("Analyzing user request...")
            streamer.status("Generating and executing Bluesky plan...")
            execution_result = bolt_api.execute_bluesky_plan(user_query)
            
            # Create context object
            context = CurrentGenerateBlueskyExecContext(
                bluesky_plan=execution_result.msg,  # Use the message as the plan identifier
                condition=execution_result.condition,
                timestamp=execution_result.timestamp
            )
            
            # Store context in framework state
            context_updates = StateManager.store_context(
                state, 
                registry.context_types.BLUESKY_PLAN, 
                step.get("context_key"), 
                context
            )
            
            streamer.status("Bluesky plan executed successfully!")
            return context_updates
            
        except Exception as e:
            logger.error(f"Bluesky plan execution error: {e}")
            raise
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify Bluesky plan execution errors for intelligent retry coordination."""

        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                metadata={
                    "user_message": "Bluesky plan execution communication timeout, retrying...",
                    "technical_details": str(exc)
                }
            )
        
        return ErrorClassification(
            severity=ErrorSeverity.CRITICAL,
            metadata={
                "user_message": f"Bluesky plan execution error: {str(exc)}",
                "technical_details": f"Error: {type(exc).__name__}"
            }
        )
    
    @staticmethod
    def get_retry_policy() -> Dict[str, Any]:
        """Define retry policy configuration for Bluesky plan execution operations."""

        return {
            "max_attempts": 3,
            "delay_seconds": 0.5,
            "backoff_factor": 1.5
        }
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for Bluesky plan execution in BOLT beamline."""

        example = OrchestratorExample(
            step=PlannedStep(
                context_key="generate_bluesky_exec",
                capability="generate_bluesky_exec",
                task_objective="Execute Bluesky plan",
                expected_output=registry.context_types.BLUESKY_PLAN,
                success_criteria="Bluesky plan successfully executed",
                inputs=[]
            ),
            scenario_description="Bluesky plan execution for motor movements, scans, and acquisitions",
            notes=f"Output stored as {registry.context_types.BLUESKY_PLAN}. Use for motor control, scanning, and data acquisition."
        )
        
        return OrchestratorGuide(
            instructions=f"""**When to plan "generate_bluesky_exec" steps:**
- User asks to move motors or execute scans
- For running data collection plans
- When executing camera acquisitions
- For motor positioning and control

**BOLT Beamline Context:**
- Bluesky plan execution
- Used for motor movements, scans, and acquisitions
- Essential for experimental data collection

**Plan Types:**
- Motor movements (move_motor)
- Rotation scans (rotation_scan)
- Camera acquisitions (camera_acquire)
- Linear scans and measurements

**Output: Stored in Queue Server**
- Contains: execution results, plan details, timestamp
- Available for monitoring and analysis

**Typical Workflow Position:**
- After system initialization
- For data collection operations
- Motor control and positioning""",
            examples=[example],
            order=2  # Early in workflow for control operations
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide task classification guidance for Bluesky plan execution."""
        return TaskClassifierGuide(
            instructions="""Determine if the user wants to EXECUTE a Bluesky plan in the BOLT beamline system.

BOLT CONTEXT: This is a beamline where Bluesky plans control motors, detectors, and data collection. Users may request:
- Motor movements and positioning
- Data collection scans
- Camera acquisitions
- Experimental measurements""",
            examples=[
                ClassifierExample(
                    query="Move the motor to 45 degrees",
                    result=True,
                    reason="Direct request for motor movement."
                ),
                ClassifierExample(
                    query="Run a scan from 0 to 180 degrees",
                    result=True,
                    reason="Request for rotation scan execution."
                ),
                ClassifierExample(
                    query="Execute a camera acquisition",
                    result=True,
                    reason="Request for camera data collection."
                ),
                ClassifierExample(
                    query="Take a measurement",
                    result=True,
                    reason="Request for data collection plan."
                ),
                ClassifierExample(
                    query="Position the sample at 90 degrees",
                    result=True,
                    reason="Request for motor positioning."
                ),
                ClassifierExample(
                    query="Start a linear scan",
                    result=True,
                    reason="Request for scanning operation."
                ),
                ClassifierExample(
                    query="What is the current motor position?",
                    result=False,
                    reason="This is a read request, not plan execution."
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