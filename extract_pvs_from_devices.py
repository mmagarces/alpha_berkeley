#!/usr/bin/env python3
"""
PV Extractor from Device Definitions

This script extracts Process Variables (PVs) from device definition files
like 01_devices.py and creates a structured output that can be used by
the PV finder system.
"""

import ast
import sys
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ProcessVariable(BaseModel):
    """Model for a single Process Variable."""
    
    pv_name: str = Field(description="The EPICS PV address")
    description: str = Field(description="Description of what this PV controls")
    category: str = Field(description="Category of the PV (motor, detector, etc.)")
    units: Optional[str] = Field(default=None, description="Units of measurement")
    device_name: str = Field(description="Name of the device this PV belongs to")
    device_type: str = Field(description="Type of device (EpicsMotor, EpicsSignal, etc.)")


def extract_pvs_from_file(file_path: str) -> List[ProcessVariable]:
    """
    Extract PVs from a Python device definition file.
    
    Args:
        file_path: Path to the Python file containing device definitions
    
    Returns:
        List of ProcessVariable objects
    """
    pvs = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Walk through the AST to find device definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Look for assignments like: motor = EpicsMotor("PV_NAME", name="motor_name")
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        
                        # Check if it's a device assignment
                        if isinstance(node.value, ast.Call):
                            call_node = node.value
                            
                            # Get the device type
                            if isinstance(call_node.func, ast.Name):
                                device_type = call_node.func.id
                            elif isinstance(call_node.func, ast.Attribute):
                                device_type = call_node.func.attr
                            else:
                                continue
                            
                            # Extract PV name and device name from arguments
                            pv_name = None
                            device_name = None
                            
                            # Look for positional arguments (PV name)
                            if call_node.args and len(call_node.args) > 0:
                                if isinstance(call_node.args[0], ast.Constant):
                                    pv_name = call_node.args[0].value
                            
                            # Look for keyword arguments (name parameter)
                            for keyword in call_node.keywords:
                                if keyword.arg == 'name' and isinstance(keyword.value, ast.Constant):
                                    device_name = keyword.value.value
                            
                            # If no explicit name, use the variable name
                            if not device_name:
                                device_name = var_name
                            
                            if pv_name:
                                # Determine category based on device type
                                category = "unknown"
                                units = None
                                
                                if "Motor" in device_type:
                                    category = "motor"
                                    units = "mm"  # Default for motors
                                elif "Signal" in device_type:
                                    category = "signal"
                                elif "Camera" in device_type or "AreaDetector" in device_type:
                                    category = "detector"
                                elif "Plugin" in device_type:
                                    category = "plugin"
                                
                                # Create description based on device type and name
                                description = f"{device_type} device: {device_name}"
                                if category == "motor":
                                    description = f"Motor device: {device_name} - controls position"
                                elif category == "detector":
                                    description = f"Detector device: {device_name} - captures images/data"
                                elif category == "signal":
                                    description = f"Signal device: {device_name} - controls/reads values"
                                
                                pv = ProcessVariable(
                                    pv_name=pv_name,
                                    description=description,
                                    category=category,
                                    units=units,
                                    device_name=device_name,
                                    device_type=device_type
                                )
                                pvs.append(pv)
    
    except Exception as e:
        print(f"Error extracting PVs from {file_path}: {e}")
        return []
    
    return pvs


def extract_pvs_from_camera_config(content: str) -> List[ProcessVariable]:
    """
    Extract PVs from camera configuration in the file.
    This looks for stage_sigs assignments that contain PV names.
    """
    pvs = []
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Look for camera.stage_sigs assignments
                if (isinstance(node.targets[0], ast.Subscript) and 
                    isinstance(node.targets[0].value, ast.Attribute) and
                    node.targets[0].value.attr == 'stage_sigs'):
                    
                    # Get the camera name
                    camera_name = node.targets[0].value.value.id
                    
                    # Get the PV name from the subscript
                    if isinstance(node.targets[0].slice, ast.Constant):
                        pv_name = node.targets[0].slice.value
                        
                        # Get the value to understand what it controls
                        value = None
                        if isinstance(node.value, ast.Constant):
                            value = node.value.value
                        
                        # Create description based on the PV name
                        description = f"Camera configuration: {pv_name}"
                        if "acquire" in pv_name.lower():
                            description = "Camera acquisition control"
                        elif "enable" in pv_name.lower():
                            description = "Camera enable/disable control"
                        elif "queue" in pv_name.lower():
                            description = "Camera queue size control"
                        elif "file" in pv_name.lower():
                            description = "Camera file writing control"
                        
                        pv = ProcessVariable(
                            pv_name=pv_name,
                            description=description,
                            category="camera_config",
                            units=None,
                            device_name=camera_name,
                            device_type="CameraConfig"
                        )
                        pvs.append(pv)
    
    except Exception as e:
        print(f"Error extracting camera config PVs: {e}")
    
    return pvs


def main():
    """Main function to extract PVs from 01_devices.py"""
    file_path = "01_devices.py"
    
    print(f"Extracting PVs from {file_path}...")
    
    # Extract device PVs
    device_pvs = extract_pvs_from_file(file_path)
    
    # Extract camera configuration PVs
    with open(file_path, 'r') as f:
        content = f.read()
    camera_pvs = extract_pvs_from_camera_config(content)
    
    # Combine all PVs
    all_pvs = device_pvs + camera_pvs
    
    print(f"Found {len(all_pvs)} PVs:")
    print("=" * 80)
    
    # Group by category
    categories = {}
    for pv in all_pvs:
        if pv.category not in categories:
            categories[pv.category] = []
        categories[pv.category].append(pv)
    
    for category, pvs in categories.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for pv in pvs:
            print(f"  • {pv.pv_name}")
            print(f"    {pv.description}")
            print(f"    Device: {pv.device_name} ({pv.device_type})")
            if pv.units:
                print(f"    Units: {pv.units}")
            print()
    
    # Save to JSON for use by pv_finder
    import json
    pv_data = {
        "motors": [pv.model_dump() for pv in all_pvs if pv.category == "motor"],
        "detectors": [pv.model_dump() for pv in all_pvs if pv.category == "detector"],
        "signals": [pv.model_dump() for pv in all_pvs if pv.category == "signal"],
        "camera_config": [pv.model_dump() for pv in all_pvs if pv.category == "camera_config"],
        "plugins": [pv.model_dump() for pv in all_pvs if pv.category == "plugin"],
    }
    
    with open("extracted_pvs.json", "w") as f:
        json.dump(pv_data, f, indent=2)
    
    print(f"PVs saved to extracted_pvs.json")
    print(f"Total PVs extracted: {len(all_pvs)}")


if __name__ == "__main__":
    main()
