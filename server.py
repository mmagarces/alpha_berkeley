from fastapi import FastAPI, HTTPException
import os
import subprocess
import json
import re
import time


app = FastAPI()

@app.get("/generate_contextual_bluesky_plan/{user_query}/")
def generate_contextual_bluesky_plan(user_query: str):
    try:

        FASTAPI_URL = "localhost"
        # Run the generate_contextual_bluesky_plan.py script
        script_path = os.path.join(os.path.dirname(__file__), "../bolt-5/alpha_berkeley/generate_contextual_bluesky_plan.py")
        cmd = ["python", script_path, user_query]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(script_path))
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Script failed: {result.stderr}")
        
        # Parse the output to extract the API call structure
        m = re.search(r'API Call Structure:\s*-+\s*(\{.*?\})\s*-+', result.stdout, re.S)
        api_str = m.group(1).strip()          # the JSON between the ---- lines
        api_call = json.loads(api_str)         # turn it into a Python dict

        queue_url = f"http://{FASTAPI_URL}:8003/api/queue/item/execute"

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
        
        #The call generates this, which is the thumbprint of the plan being executed. Although this isnt
        #The UID related to the actual process, this lets us identify the plan being executed later.
        item_uid = response_data["item"]["item_uid"]
        
        # Wait for execution to complete
        try:
            count = 0
            check = None
            previous_run_list_uid = None  # Track the previous run_list_uid
            while(count != 3):
                queue_url = f"http://{FASTAPI_URL}:8003/api/re/runs/active"
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
                # These are custom, simply what worked during each call. This should be modified and fixed, 
                # Esepcially due to the lack of consitency and usage of the call itself.
                # They are what allow the plan to remain in the while loop, and the plan to be executed.
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
                elif (len(history_data["run_list"]) == 0) and api_call["item"]["name"] == "camera_acquire":
                    count += 1.5
                time.sleep(1)
                
        except Exception as e:
            print(f"Error waiting for execution: {e}")
        
        # Once done, we are grabbing the history of the run and using the previosuly generated item_uid to identify the run,
        # therefore helpoing us grab the correct run UID.
        try:
            # Test GET method for history
            queue_url = f"http://{FASTAPI_URL}:8003/api/history/get"
            
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
            
            # In the cae that there are multiple runs (some need it), we are trying to store both run_ids.
            for item in history_data["items"]:
                if item["item_uid"] == item_uid:    #Until found
                    run_id_0 = (item["result"]["run_uids"][0])
                    try:
                        run_id_1 = (item["result"]["run_uids"][1])
                    except:
                        run_id_1 = None
                    break
        except Exception as e:
            print(f"Error finding run_id: {e}")
        
        # Connect to the tiled server in order to grab the metadata of the run, or provide a link to the run's generated
        # data.
        print("Making it here")
        from tiled.client import from_uri
        tiled_server_url = f"http://{FASTAPI_URL}:8000"
        tiled_api_key = "ca6ae384c9f944e1465176b7e7274046b710dc7e2703dc33369f7c900d69bd64"
        # Connect to the Tiled server
        tiled_client = from_uri(
            tiled_server_url,
            api_key=tiled_api_key
        )
        
        #This is defined by the usage purpose of the call, where multiple runs require the second run_id in the call
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

        return {
             "success": True,
             "message": msg,
             "plan_name": api_call["item"]["name"]
         }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/create_bluesky_plan/{user_query}/")
def create_bluesky_plan(user_query: str):
    # Call the generate_bluesky_plan.py script
    result = subprocess.run(
        ["python", "generate_bluesky_plan.py", user_query],
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
        
    return plan_code