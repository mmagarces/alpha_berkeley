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
    #FASTAPI_URL = "host.docker.internal"

    FASTAPI_URL = "localhost"
    
    def create_bluesky_plan(self, api_call: str) -> CurrentBlueskyPlanReading:
        """Create a Bluesky plan using the provided API call structure without executing it."""
        try:
            if (self.FASTAPI_URL == "localhost"):
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
                except Exception as e:
                    print(f"Error: {str(e)}")
                    return CurrentBlueskyPlanReading(
                        condition=f"Error: {str(e)}",
                        msg="Failed to create Bluesky plan",
                        timestamp=datetime.now()
                    )
            else:
                api_url = f"http://host.docker.internal:8004/create_bluesky_plan/{api_call}/"
                response = requests.get(api_url)
                print("Server response:", response.text)
                if response.status_code != 200:
                    raise Exception(f"API call failed: {response.status_code} - {response.text}")
                print(response.text)
                plan_code = response.text

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
                try:
                    import os
                    # Change to the correct directory where the script can find the framework
                    script_dir = os.path.join(os.path.dirname(__file__), "../../..")
                    cmd = ["python", "generate_contextual_bluesky_plan.py", api_call]
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir)
                    import re, json

                    m = re.search(r'API Call Structure:\s*-+\s*(\{.*?\})\s*-+', result.stdout, re.S)
                    api_str = m.group(1).strip()          # the JSON between the ---- lines
                    api_call = json.loads(api_str)         # turn it into a Python dict

                    import json
                    # Use the configurable FASTAPI_URL
                    queue_url = f"http://{self.FASTAPI_URL}:8003/api/queue/item/execute"

                    cmd = [
                        "curl",
                        "-X", "POST",
                        queue_url,
                        "-H", "accept: application/json",
                        "-H", "Authorization: Apikey test",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(api_call),
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        raise Exception(f"API call failed: {result.stderr}")
                    
                    response_data = json.loads(result.stdout)
                    item_uid = response_data["item"]["item_uid"]
                    
                    # Wait for execution to complete (similar to get_current_angle)
                    try:
                        count = 0
                        check = None
                        previous_run_list_uid = None  # Track the previous run_list_uid
                        while(count != 3):
                            queue_url = f"http://{self.FASTAPI_URL}:8003/api/re/runs/active"
                            
                            cmd = [
                                "curl",
                                "-X", "GET",
                                queue_url,
                                "-H", "accept: application/json",
                                "-H", "Authorization: Apikey test"
                            ]   
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            history_data = json.loads(result.stdout)
                            print(count)
                            for item in history_data:
                                check = item
                    
                            if check == "run_list" and api_call["item"]["name"] == "move_motor":
                                count += 0.3
                                count = round(count, 1)
                            elif check == "run_list" and  (api_call["item"]["name"] == "get_angle"):
                                count += 0.5
                            elif (len(history_data["run_list"]) == 0) and ((api_call["item"]["name"] == "rotation_scan" or api_call["item"]["name"] == "reconstruct_object")):
                                count += 1
                            elif api_call["item"]["name"] == "display_object_from_file":
                                current_run_list_uid = history_data["run_list_uid"]
                                # Only increment count if run_list_uid has changed (and it's not the first check)
                                if previous_run_list_uid is not None and current_run_list_uid != previous_run_list_uid:
                                    count += 3
                                    break
                                previous_run_list_uid = current_run_list_uid
                            elif check == "run_list" and api_call["item"]["name"] == "camera_acquire":
                                count += 1.5
                            time.sleep(1)
                        print("Run finished, processing...")
                    
                    except Exception as e:
                        print(f"Error waiting for execution: {e}")
            
                except Exception as e:
                    print(f"Error: {str(e)}")
                    return CurrentBlueskyPlanReading(
                        condition=f"Error: {str(e)}",
                        msg="Failed to execute Bluesky plan",
                        timestamp=datetime.now()
                    )
            
                try:
                    # Test GET method for history
                    queue_url = f"http://{self.FASTAPI_URL}:8003/api/history/get"
                    
                    # Use GET method (not POST)
                    cmd = [
                        "curl",
                        "-X", "GET",  # Changed from POST to GET
                        queue_url,
                        "-H", "accept: application/json",
                        "-H", "Authorization: Apikey test"
                    ]   

                    result = subprocess.run(cmd, capture_output=True, text=True)
                    history_data = json.loads(result.stdout)
                    
                    for item in history_data["items"]:
                        if item["item_uid"] == item_uid:
                            run_id_0 = (item["result"]["run_uids"][0])
                            try:
                                run_id_1 = (item["result"]["run_uids"][1])
                            except:
                                run_id_1 = None
                            break
                except Exception as e:
                    print(f"Error: {e}")
                
                from tiled.client import from_uri
                tiled_server_url = f"http://{self.FASTAPI_URL}:8000"
                tiled_api_key = "ca6ae384c9f944e1465176b7e7274046b710dc7e2703dc33369f7c900d69bd64"
                # Connect to the Tiled server
                tiled_client = from_uri(
                    tiled_server_url,
                    api_key=tiled_api_key
                )

                run_data_0 = tiled_client[run_id_0]
                run_data_1 = tiled_client[run_id_1] if run_id_1 is not None else None
                msg=f"Plan executed with UID: {item_uid}",

                #This is mostly dependant on the call itself, as the plan will be different based on the call
                #These plans are custom, and are predefined
                if (api_call["item"]["name"] == "get_angle"):
                    angle = run_data_0.metadata['start']['angle_degrees']
                    msg = "Angle result from run: " + str(angle)

                elif (api_call["item"]["name"] == "camera_acquire"):
                    run_id = run_id_1 if run_id_1 is not None else run_id_0
                    msg = "Camera acquire result from run: " + "http://localhost:8000/ui/browse/" + run_id + "_" + " (IMPORTANT: URL must end with underscore right next to run_id)"
                elif (api_call["item"]["name"] == "move_motor"):
                    result = run_data_0.metadata['stop']['exit_status']
                    if (result == "success"):
                        msg = "Motor movement successful"
                    else:
                        msg = "Motor movement failed"


                elif (api_call["item"]["name"] == "rotation_scan"):
                    dir = api_call["item"]["kwargs"]["save_dir"]
                    msg = "Rotation scan completed: http://localhost:8000/ui/browse/" + dir

                elif (api_call["item"]["name"] == "reconstruct_object"):
                    if run_data_1 is not None:
                        uuid = run_data_1.metadata['start']['rotation_views_uuid']
                        msg = "Object reconstructed from folder: http://localhost:8000/ui/browse/" + uuid
                    else:
                        msg = "Object reconstruction failed - no run data available"
                elif (api_call["item"]["name"] == "display_object_from_file"):
                    uuid =  run_data_0.metadata['start']['tiled_array_uuid']
                    msg = "Object displayed from file: http://localhost:8000/ui/browse/" + uuid

                print(msg)
                return CurrentBlueskyPlanReading(
                    condition="Bluesky plan executed successfully",
                    msg=msg,
                    timestamp=datetime.now()
                )
            
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
