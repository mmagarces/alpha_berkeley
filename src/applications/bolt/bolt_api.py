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
@dataclass
class CurrentAngleReading:
    """Structured data model for motor angular position readings.
    """
    motor: str
    angle: float  # Final motor angle position
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
    timestamp: datetime


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
    
    def execute_bluesky_plan(self, api_call: str) -> CurrentBlueskyPlanReading:
        """Execute a Bluesky plan using the provided API call structure."""
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
                    print(count)
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    history_data = json.loads(result.stdout)
                    for item in history_data:
                        check = item
                    
                    if check == "run_list_uid" and (api_call["item"]["name"] == "get_angle"):
                        count += 1
                    elif check == "run_list" and api_call["item"]["name"] == "move_motor":
                        count += 1
                    elif (len(history_data["run_list"]) == 0) and ((api_call["item"]["name"] == "rotation_scan" or api_call["item"]["name"] == "reconstruct_object")):
                        count += 1
                    elif api_call["item"]["name"] == "display_object_from_file":
                        current_run_list_uid = history_data["run_list_uid"]
                        # Only increment count if run_list_uid has changed (and it's not the first check)
                        if previous_run_list_uid is not None and current_run_list_uid != previous_run_list_uid:
                            count += 3
                            break
                        previous_run_list_uid = current_run_list_uid
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error waiting for execution: {e}")
            
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
            run_data_1 = tiled_client[run_id_1]
            print(run_data_0.metadata)
            msg=f"Plan executed with UID: {item_uid}",

            if (api_call["item"]["name"] == "get_angle"):
                angle = run_data_0.metadata['start']['angle_degrees']
                msg = "Angle result from run: " + str(angle)
            elif (api_call["item"]["name"] == "camera_acquire"):
                msg = "Camera acquire result from run: " + "http://localhost:8000/ui/browse/" + run_id_1 + "_"
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
                
                uuid = run_data_1.metadata['start']['rotation_views_uuid']

                print("Making it here")
                print(uuid)
                print(uuid)


                msg = "Object reconstructed from folder: http://localhost:8000/ui/browse/" + uuid
            elif (api_call["item"]["name"] == "display_object_from_file"):
                uuid =  run_data_0.metadata['start']['tiled_array_uuid']
                msg = "Object displayed from file: http://localhost:8000/ui/browse/" + uuid


            return CurrentBlueskyPlanReading(
                condition="Bluesky plan executed successfully",
                msg=msg,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return CurrentBlueskyPlanReading(
                condition=f"Error: {str(e)}",
                msg="Failed to execute Bluesky plan",
                timestamp=datetime.now()
            )
    
    
bolt_api = BoltAPI()
