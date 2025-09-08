"""
BOLT Beamline API Interface.

Provides interface to BOLT imaging beamline hardware systems
including motor control, detector imaging, and photogrammetry operations.
"""
import random
import requests #added requests
from datetime import datetime
from dataclasses import dataclass
import subprocess
import time
import json
@dataclass
class CurrentAngleReading:
    """Structured data model for motor angular position readings.
    """
    motor: str
    angle: float 
    condition: str
    timestamp: datetime

@dataclass
class CurrentMoveMotorReading:
    """Structured data model for motor movement operation results."""
    motor: str
    angle: float
    condition: str
    timestamp: datetime

@dataclass
class CurrentTakeCaptureReading:
    """Structured data model for detector image capture results."""
    condition: str
    message: str
    timestamp: datetime

@dataclass
class CurrentRunScanReading:
    """Structured data model for photogrammetry scan execution results."""
    condition: str
    message: str
    timestamp: datetime

@dataclass
class CurrentReconstructObjectReading:
    """Structured data model for reconstruction from folder execution results."""
    condition: str
    timestamp: datetime
"""
@dataclass
class CurrentPlyQualityReading:
    Structured data model for PLY quality assessment execution results.
    condition: str
    msg: str
    timestamp: datetime
"""
@dataclass
class CurrentDisplayObjectReading:
    """Structured data model for display object execution results."""
    condition: str
    msg: str
    timestamp: datetime

@dataclass
class CurrentBlueskyPlanReading:
    """Structured data model for bluesky plan execution results."""
    condition: str
    msg: str
    plan_code: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BoltAPI:
    """BOLT beamline hardware interface.
    
    Provides interface to BOLT imaging beamline systems including
    motor control, detector operations, and photogrammetry scan coordination.
    """
    
    # Motor configuration
    MOTOR_DATA = {
        "DMC01:A": {}
    }
    """Motor configuration for BOLT beamline motors."""

    #For WebUI Use
    FASTAPI_URL = "host.docker.internal"

    #FASTAPI_URL = "localhost"
    
    def create_bluesky_plan(self, api_call: str) -> CurrentBlueskyPlanReading:
        """Create a Bluesky plan using the provided API call structure without executing it."""
        try:
            # Call the generate_bluesky_plan.py script
            result = subprocess.run(
                ["python", "generate_bluesky_plan.py", api_call],
                capture_output=True,
                text=True,
                cwd="/Users/magarces/agenticAI_bolt-main/version-control/bolt-5/alpha_berkeley"
            )
            
            if result.returncode != 0:
                raise Exception(f"Script failed: {result.stderr}")
            
            # Parse the output to extract the plan code
            output_lines = result.stdout.strip().split('\n')
            plan_code = ""
            in_code_block = False
            
            for line in output_lines:
                if line.strip().startswith('```python'):
                    in_code_block = True
                    continue
                elif line.strip() == '```' and in_code_block:
                    break
                elif in_code_block:
                    plan_code += line + '\n'
            
            # If no code block found, use the entire output as plan code
            if not plan_code.strip():
                plan_code = result.stdout.strip()
            
            # Extract plan name and parameters from the generated code
            plan_name = "generated_plan"  # default
            kwargs = {}
            
            for line in plan_code.split('\n'):
                if line.strip().startswith('def '):
                    # Extract function name
                    plan_name = line.strip().split('(')[0].replace('def ', '').strip()
                    
                    # Extract parameters
                    if '(' in line and ')' in line:
                        params_str = line.split('(')[1].split(')')[0]
                        for param in params_str.split(','):
                            param = param.strip()
                            if '=' in param:
                                key, value = param.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"\'')
                                # Convert numeric values
                                if value.isdigit():
                                    value = int(value)
                                elif value.replace('.', '').isdigit():
                                    value = float(value)
                                kwargs[key] = value
                    break
            
            return CurrentBlueskyPlanReading(
                condition="Bluesky plan created successfully",
                msg="Generated bluesky plan",
                plan_code=plan_code,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return CurrentBlueskyPlanReading(
                condition=f"Error: {str(e)}",
                msg="Failed to create Bluesky plan",
                timestamp=datetime.now()
            )

    def execute_bluesky_plan(self, api_call: str) -> CurrentBlueskyPlanReading:
        """Execute a Bluesky plan using the provided API call structure."""
        try:
            import os
            # Change to the correct directory where the script can find the framework

            if (self.FASTAPI_URL == "localhost"):
                script_dir = os.path.join(os.path.dirname(__file__), "../../..")
                cmd = ["python", "generate_contextual_bluesky_plan.py", api_call]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir)
            else:
                # Make HTTP API call to the local server
                import requests
                api_url = f"http://host.docker.internal:8004/generate_contextual_bluesky_plan/{api_call}/"
                response = requests.get(api_url)
                print("Server response:", response.text)
                if response.status_code != 200:
                    raise Exception(f"API call failed: {response.status_code} - {response.text}")
                
                # Parse the JSON response
                response_data = response.json()
                message = response_data["message"]
                plan_name = response_data["plan_name"]
                            
            return CurrentBlueskyPlanReading(
                condition=f"Bluesky plan '{plan_name}' executed successfully",
                msg=message,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return CurrentBlueskyPlanReading(
                condition=f"Error somewhere else: {str(e)}",
                msg="Failed to execute Bluesky plan",
                timestamp=datetime.now()
            )
    
    
bolt_api = BoltAPI()
