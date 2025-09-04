#!/usr/bin/env python3
"""
PV Finder with Ophyd Devices - Extract Relevant Process Variables for Experiments

This script uses AI to analyze user queries and extract relevant PV (Process Variable)
addresses from Ophyd device definitions. It's designed to help users identify
which EPICS PVs are needed for their experimental plans.

Usage:
    python pv_finder_ophyd.py "scan sample from 0 to 10 degrees"
    python pv_finder_ophyd.py --interactive
"""

import argparse
import json
import sys
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

# Add the src directory to the path to import from framework
sys.path.insert(0, 'src')

from framework.models.completion import get_chat_completion

# Ophyd device definitions
from ophyd import Component, Device, EpicsSignal, EpicsSignalRO, EpicsMotor
from ophyd.areadetector.plugins import PluginBase
from ophyd.areadetector import AreaDetector, ADComponent, ImagePlugin, JPEGPlugin, TIFFPlugin
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.areadetector.trigger_mixins import SingleTrigger


class ProcessVariable(BaseModel):
    """Model for a single Process Variable."""
    
    pv_name: str = Field(description="The EPICS PV address")
    description: str = Field(description="Description of what this PV controls")
    category: str = Field(description="Category of the PV (motor, detector, etc.)")
    units: Optional[str] = Field(default=None, description="Units of measurement")


class PVFinderResult(BaseModel):
    """Structured output model for PV finder results."""
    
    relevant_pvs: List[ProcessVariable] = Field(description="List of relevant PVs for the query")
    reasoning: str = Field(description="Explanation of why these PVs were selected")
    suggested_plan_type: str = Field(description="Suggested type of Bluesky plan (scan, count, etc.)")
    additional_notes: Optional[str] = Field(default=None, description="Additional notes or recommendations")


# Custom PVA Plugin for Area Detector
class PvaPlugin(PluginBase):
    _suffix = 'Pva1:'
    _plugin_type = 'NDPluginPva'
    _default_read_attrs = ['enable']
    _default_configuration_attrs = ['enable']
    array_callbacks = ADComponent(EpicsSignal, 'ArrayCallbacks')

# Device definitions (not instantiated to avoid connection timeouts)
DEVICE_DEFINITIONS = {
    "motors": [
        {"prefix": "DMC01:A", "name": "rotation_motor", "type": "EpicsMotor"},
        {"prefix": "DMC01:D", "name": "linear_stage", "type": "EpicsMotor"},
    ],
    "camera": {
        "prefix": "13ARV1:",
        "name": "camera",
        "type": "MyCamera",
        "components": {
            "cam": "cam1:",
            "image": "image1:",
            "tiff": "TIFF1:",
            "pva": "Pva1:"
        }
    },
    "signals": [
        {"prefix": "13ARV1:cam1:Acquire", "name": "acquire_signal", "type": "EpicsSignal"},
    ]
}


def get_available_pvs():
    """Extract PV information from device definitions."""
    pvs = []
    
    # Extract motor PVs from device definitions
    for motor_def in DEVICE_DEFINITIONS["motors"]:
        pvs.append(ProcessVariable(
            pv_name=motor_def["prefix"],
            description=f"{motor_def['name']} - {motor_def['type']}",
            category="motor",
            units="mm"  # Default units for motors
        ))
    
    # Extract camera PVs - key signals that would be used in experiments
    camera_prefix = DEVICE_DEFINITIONS["camera"]["prefix"]
    camera_pvs = [
        ("Acquire", "Camera acquire signal - starts/stops image acquisition", "detector", "state"),
        ("ImageMode", "Camera image mode - single, multiple, or continuous", "detector", "mode"),
        ("NumImages", "Number of images to acquire in multiple mode", "detector", "count"),
        ("AcquireTime", "Camera exposure time per image", "detector", "seconds"),
        ("AcquirePeriod", "Time between acquisitions", "detector", "seconds"),
        ("ArrayData", "Raw image data from camera", "detector", "pixels"),
        ("ArraySize0_RBV", "Image width in pixels", "detector", "pixels"),
        ("ArraySize1_RBV", "Image height in pixels", "detector", "pixels"),
    ]
    
    # Add camera component PVs
    for component, suffix in DEVICE_DEFINITIONS["camera"]["components"].items():
        if component == "cam":
            # Camera control PVs
            for pv_suffix, description, category, units in camera_pvs:
                pv_name = f"{camera_prefix}{suffix}{pv_suffix}"
                pvs.append(ProcessVariable(
                    pv_name=pv_name,
                    description=description,
                    category=category,
                    units=units
                ))
        else:
            # Plugin PVs
            plugin_pvs = [
                ("EnableCallbacks", f"{component} plugin enable", "detector", "state"),
                ("ArrayData", f"{component} plugin data", "detector", "pixels"),
            ]
            for pv_suffix, description, category, units in plugin_pvs:
                pv_name = f"{camera_prefix}{suffix}{pv_suffix}"
                pvs.append(ProcessVariable(
                    pv_name=pv_name,
                    description=description,
                    category=category,
                    units=units
                ))
    
    # Add standalone signals
    for signal_def in DEVICE_DEFINITIONS["signals"]:
        pvs.append(ProcessVariable(
            pv_name=signal_def["prefix"],
            description=f"{signal_def['name']} - {signal_def['type']}",
            category="detector",
            units="state"
        ))
    
    return pvs


# Get the PV table from Ophyd devices
HARDCODED_PV_TABLE = {
    "motors": [pv for pv in get_available_pvs() if pv.category == "motor"],
    "detectors": [pv for pv in get_available_pvs() if pv.category == "detector"]
}


def find_relevant_pvs(query: str, provider: str = "cborg", model_id: str = "anthropic/claude-sonnet") -> PVFinderResult:
    """
    Find relevant PVs for a given experimental query.
    
    Args:
        query: User query describing the experimental task
        provider: AI provider to use (default: cborg)
        model_id: Model ID to use (default: anthropic/claude-sonnet)
    
    Returns:
        PVFinderResult: Structured result with relevant PVs and reasoning
    """
    
    # Flatten the PV table for the prompt
    all_pvs = []
    for category, pvs in HARDCODED_PV_TABLE.items():
        all_pvs.extend(pvs)
    
    # Create a formatted string of all available PVs
    pv_list = "\n".join([
        f"- {pv.pv_name}: {pv.description} ({pv.category}, {pv.units})"
        for pv in all_pvs
    ])
    
    prompt = f"""
You are an expert in synchrotron radiation experiments and EPICS process variables (PVs). 
Your task is to analyze a user's experimental query and identify which PVs from the available 
list are relevant for executing that experiment.

Available PVs:
{pv_list}

User Query: "{query}"

Please analyze the query and identify all relevant PVs that would be needed to execute 
this experiment. Consider:

1. **Motors**: Which motors need to be moved or positioned?
2. **Detectors**: Which detectors need to be read or configured?
3. **Camera Controls**: Which camera settings need to be adjusted?

For each relevant PV, provide:
- The exact PV name
- Description of what it controls
- Category (motor, detector)
- Units of measurement

Also provide:
- Clear reasoning for why each PV was selected
- Suggested type of Bluesky plan (scan, count, fly_scan, etc.)
- Any additional notes or recommendations

Focus on PVs that are directly involved in the experimental procedure described in the query.
Don't include PVs that are only peripherally related or not essential for the core experiment.

Note: The available devices include:
- rotation_motor (DMC01:A): For rotating samples or detectors
- linear_stage (DMC01:D): For linear positioning
- camera (13ARV1:): Area detector camera with image acquisition capabilities
"""
    
    try:
        result = get_chat_completion(
            message=prompt,
            provider=provider,
            model_id=model_id,
            max_tokens=2000,
            output_model=PVFinderResult
        )
        return result
    except Exception as e:
        print(f"Error finding PVs: {e}")
        raise


def print_pv_result(result: PVFinderResult):
    """Print the PV finder result in a formatted way."""
    print("=" * 80)
    print("RELEVANT PROCESS VARIABLES")
    print("=" * 80)
    
    print(f"Suggested Plan Type: {result.suggested_plan_type}")
    print()
    
    print("Reasoning:")
    print(result.reasoning)
    print()
    
    if result.relevant_pvs:
        print("Relevant PVs:")
        print("-" * 40)
        
        # Group PVs by category
        categories = {}
        for pv in result.relevant_pvs:
            if pv.category not in categories:
                categories[pv.category] = []
            categories[pv.category].append(pv)
        
        for category, pvs in categories.items():
            print(f"\n{category.upper().replace('_', ' ')}:")
            for pv in pvs:
                print(f"  • {pv.pv_name}")
                print(f"    {pv.description}")
                if pv.units:
                    print(f"    Units: {pv.units}")
                print()
    else:
        print("No relevant PVs found.")
    
    if result.additional_notes:
        print("Additional Notes:")
        print(result.additional_notes)
        print()


def interactive_mode():
    """Run in interactive mode for multiple queries."""
    print("PV Finder with Ophyd Devices - Interactive Mode")
    print("Type 'quit' or 'exit' to stop")
    print("-" * 50)
    
    while True:
        try:
            query = input("\nEnter your experimental query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not query:
                print("Please enter a query.")
                continue
            
            print(f"\nFinding relevant PVs for: '{query}'...")
            result = find_relevant_pvs(query)
            print_pv_result(result)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Find relevant Process Variables for experimental queries using Ophyd devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "scan sample from 0 to 10 degrees using rotation motor"
  %(prog)s "take a single image with the camera"
  %(prog)s "perform a 2D scan with rotation and linear motors while taking images"
  %(prog)s "acquire 10 images with 1 second exposure time"
  %(prog)s --interactive
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Query describing the experimental task"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--provider",
        default="cborg",
        choices=["anthropic", "openai", "google", "ollama", "cborg"],
        help="AI provider to use (default: cborg)"
    )
    
    parser.add_argument(
        "--model-id",
        default="anthropic/claude-sonnet",
        help="Model ID to use (default: anthropic/claude-sonnet)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output file to save the results (JSON format)"
    )
    
    parser.add_argument(
        "--list-pvs",
        action="store_true",
        help="List all available PVs and exit"
    )
    
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List all Ophyd devices and their PVs"
    )
    
    args = parser.parse_args()
    
    if args.list_pvs:
        print("Available Process Variables:")
        print("=" * 50)
        for category, pvs in HARDCODED_PV_TABLE.items():
            print(f"\n{category.upper().replace('_', ' ')}:")
            for pv in pvs:
                print(f"  {pv.pv_name}: {pv.description} ({pv.units})")
        return
    
    if args.list_devices:
        print("Available Ophyd Devices:")
        print("=" * 50)
        print("Motors:")
        for motor in DEVICE_DEFINITIONS["motors"]:
            print(f"  - {motor['name']}: {motor['prefix']} ({motor['type']})")
        print(f"\nDetectors:")
        camera = DEVICE_DEFINITIONS["camera"]
        print(f"  - {camera['name']}: {camera['prefix']} ({camera['type']})")
        print(f"    Components: {', '.join(camera['components'].keys())}")
        print("Signals:")
        for signal in DEVICE_DEFINITIONS["signals"]:
            print(f"  - {signal['name']}: {signal['prefix']} ({signal['type']})")
        return
    
    if args.interactive:
        interactive_mode()
        return
    
    if not args.query:
        parser.error("Query is required unless using --interactive, --list-pvs, or --list-devices mode")
    
    try:
        print(f"Finding relevant PVs for: '{args.query}'")
        print(f"Using provider: {args.provider}")
        
        # Find relevant PVs
        result = find_relevant_pvs(
            query=args.query,
            provider=args.provider,
            model_id=args.model_id
        )
        
        # Print the result
        print_pv_result(result)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result.model_dump(), f, indent=2)
            print(f"\nResults saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
