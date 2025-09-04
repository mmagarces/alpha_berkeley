# src/applications/bolt/capabilities/ply_quality_assessment.py
"""
PLY Quality Assessment Capability for BOLT Beamline System.

This capability analyzes .ply files for reconstruction quality and provides
improvement recommendations for scan parameters and reconstruction settings.
"""

from typing import Dict, Any, Optional
import json
from pathlib import Path

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

from applications.bolt.context_classes import CurrentPlyQualityContext
from applications.bolt.bolt_api import bolt_api

logger = get_logger("bolt", "ply_quality_assessment")
registry = get_registry()

@capability_node
class PLYQualityAssessmentCapability(BaseCapability):
    """Analyze PLY file quality and provide improvement recommendations."""
    
    name = "ply_quality_assessment"
    description = "Analyze PLY file quality and provide improvement recommendations"
    provides = ["PLY_QUALITY_ASSESSMENT"]
    requires = []
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute PLY quality analysis workflow."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("bolt", "ply_quality_assessment", state)
        
        try:
            streamer.status("Parsing PLY file path from query...")
            
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
            
            streamer.status(f"Analyzing PLY files in folder: {folder_name}")
            print(folder_name)
            scan_data = bolt_api.analyze_ply_quality(folder_name)

            context = CurrentPlyQualityContext(
                condition=scan_data.condition,
                msg=scan_data.msg,
                timestamp=scan_data.timestamp
            )

            context_updates = StateManager.store_context(
                state, 
                registry.context_types.PLY_QUALITY_ASSESSMENT, 
                step.get("context_key"), 
                context
            )

            streamer.status("Quality analysis completed!")

            return context_updates
            
        except Exception as e:
            logger.error(f"PLY quality assessment error: {e}")
            raise
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify photogrammetry scan errors for intelligent retry coordination."""

        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                metadata={
                    "user_message": "Beamline communication timeout, retrying...",
                    "technical_details": str(exc)
                }
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                metadata={
                    "user_message": f"Invalid scan parameters: {str(exc)}",
                    "technical_details": str(exc)
                }
            )
        
        return ErrorClassification(
            severity=ErrorSeverity.CRITICAL,
            metadata={
                "user_message": f"Photogrammetry scan error: {str(exc)}",
                "technical_details": f"Error: {type(exc).__name__}"
            }
        )
    
    @staticmethod
    def get_retry_policy() -> Dict[str, Any]:
        """Define retry policy configuration for photogrammetry scan operations."""

        return {
            "max_attempts": 2,  # Fewer retries for long scans
            "delay_seconds": 2.0,  # Longer delay for beamline recovery
            "backoff_factor": 2.0
        }
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for photogrammetry scan execution in BOLT beamline."""

        example = OrchestratorExample(
            step=PlannedStep(
                context_key="ply_quality_analysis",
                capability="ply_quality_assessment",
                task_objective="Analyze PLY file quality and provide improvement recommendations",
                expected_output=registry.context_types.PLY_QUALITY_ASSESSMENT,
                success_criteria="PLY quality analysis completed with all recommendations provided",
                inputs=[
                    {"name": "start_angle", "type": "float", "description": "Starting angle of scan (default: 0)"},
                    {"name": "end_angle", "type": "float", "description": "Ending angle of scan (default: 180)"},
                    {"name": "num_projections", "type": "int", "description": "Number of projections (default: 10)"},
                    {"name": "output_folder", "type": "string", "description": "Folder path to save output (optional)"}
                ]      
            ),
            scenario_description="Executing complete PLY quality analysis",
            notes=f"Output stored as {registry.context_types.PLY_QUALITY_ASSESSMENT}. This is a complete experimental procedure."
        )
        
        return OrchestratorGuide(
            instructions=f"""**When to plan "ply_quality_assessment" steps:**
- User requests to analyze the quality of a PLY file
- User specifies the PLY file path
- For full experimental data collection and research
- When comprehensive sample characterization is needed

**BOLT Beamline Context:**
- Executes complete PLY quality analysis
- Coordinates motor rotation with detector imaging
- Generates datasets for 3D reconstruction
- Primary experimental capability for research

**Scan Parameters:**
- PLY file path: path to the PLY file to analyze

**Output: {registry.context_types.PLY_QUALITY_ASSESSMENT}**
- Contains: PLY file path, quality metrics, recommendations, quality summary
- Available for data analysis and 3D reconstruction

**Typical Workflow Position:**
- After photogrammetry scan is completed
- After reconstruction is completed
- Final step in experimental preparation sequence
- Usually requires prior sample positioning and beam alignment""",
            examples=[example],
            order=4  # Highest priority - main experimental capability
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide task classification guidance for photogrammetry scan execution."""
        return TaskClassifierGuide(
            instructions="""Determine if the user wants to EXECUTE a complete PLY quality analysis in the BOLT beamline system.

        BOLT CONTEXT: This is an imaging beamline for PLY quality analysis. Users may request:
        - Complete PLY quality analysis
        - PLY file path
        - Full experimental data collection procedures
        - Research-grade PLY quality analysis""",
            examples=[
                ClassifierExample(
                    query="Analyze the quality of the PLY file",
                    result=True,
                    reason="Complete PLY quality analysis request with specific parameters."
                ),
                ClassifierExample(
                    query="Analyze the quality of the PLY file in the folder",
                    result=True,
                    reason="Request for PLY quality analysis in the folder."
                ),
                ClassifierExample(
                    query="Analyze the quality of the PLY file in folder",
                    result=True,
                    reason="Request for PLY quality analysis in the folder."
                ),
                ClassifierExample(
                    query="Analyze the quality of the PLY file in the folder",
                    result=True,
                    reason="Request for PLY quality analysis in the folder."
                ),
                ClassifierExample(
                    query="Take a single image",
                    result=False,
                    reason="This is a single image request, not a multi-projection scan."
                ),
                ClassifierExample(
                    query="Move the motor to 45 degrees",
                    result=False,
                    reason="This is motor positioning, not scan execution."
                ),
                ClassifierExample(
                    query="What is the current motor angle?",
                    result=False,
                    reason="This is a position read request, not scan execution."
                ),
                ClassifierExample(
                    query="Take a test shot",
                    result=False,
                    reason="Test shot is single image capture, not complete scan."
                ),
                ClassifierExample(
                    query="What tools do you have?",
                    result=False,
                    reason="Request is for tool information, not scan execution."
                ),
            ],
            actions_if_true=ClassifierActions()
        )