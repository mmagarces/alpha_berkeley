#!/usr/bin/env python3
"""
Bluesky Plan Generator

A simple script that uses the chat completion function to generate Bluesky plans
based on user queries. This script demonstrates how to use the completion.py
module for structured output generation.

Usage:
    python generate_bluesky_plan.py "scan sample from 0 to 10 in 0.1 steps"
    python generate_bluesky_plan.py --interactive
"""

import argparse
import json
import sys
from typing import List, Optional
from pydantic import BaseModel, Field

# Add the src directory to the path to import from framework
sys.path.insert(0, 'src')

from framework.models.completion import get_chat_completion


class BlueskyPlan(BaseModel):
    """Structured output model for Bluesky plans."""
    
    plan_name: str = Field(description="Name of the Bluesky plan")
    plan_description: str = Field(description="Description of what the plan does")
    plan_code: str = Field(description="Python code for the Bluesky plan")
    required_devices: List[str] = Field(description="List of required device names")
    parameters: dict = Field(description="Dictionary of plan parameters and their descriptions")
    estimated_duration: Optional[str] = Field(default=None, description="Estimated execution time")


def generate_bluesky_plan(query: str, provider: str = "cborg", model_id: str = "anthropic/claude-sonnet") -> BlueskyPlan:
    """
    Generate a Bluesky plan using the chat completion function.
    
    Args:
        query: User query describing the desired Bluesky plan
        provider: AI provider to use (default: cborg)
        model_id: Model ID to use (default: anthropic/claude-sonnet)
    
    Returns:
        BlueskyPlan: Structured plan object
    """
    
    prompt = f"""
You are an expert in Bluesky data collection plans. Generate a complete Bluesky plan based on the following user query:

Query: "{query}"

Please provide a structured response with:
1. A descriptive name for the plan
2. A clear description of what the plan does
3. Complete Python code for the Bluesky plan using proper Bluesky syntax
4. List of required devices/motors
5. Plan parameters with descriptions
6. Estimated execution time if applicable

The plan should be production-ready and follow Bluesky best practices. Use proper imports, device definitions, and plan decorators.

Example of good Bluesky plan structure:
```python
from bluesky import RunEngine
from bluesky.plans import scan
from ophyd import EpicsMotor

# Device definitions
motor = EpicsMotor('prefix:motor', name='motor')
detector = EpicsSignal('prefix:detector', name='detector')

# Plan definition
@bpp.stage_decorator([motor, detector])
@bpp.run_decorator()
def my_scan_plan(motor, detector, start, stop, num_points):
    yield from scan([detector], motor, start, stop, num_points)
```

Make sure to include all necessary imports and device definitions in the plan code.
"""
    
    try:
        result = get_chat_completion(
            message=prompt,
            provider=provider,
            model_id=model_id,
            max_tokens=2000,
            output_model=BlueskyPlan
        )
        return result
    except Exception as e:
        print(f"Error generating plan: {e}")
        raise


def print_plan(plan: BlueskyPlan):
    """Print the generated plan in a formatted way."""
    print("=" * 80)
    print(f"BLUESKY PLAN: {plan.plan_name}")
    print("=" * 80)
    print(f"Description: {plan.plan_description}")
    print()
    
    if plan.estimated_duration:
        print(f"Estimated Duration: {plan.estimated_duration}")
        print()
    
    print("Required Devices:")
    for device in plan.required_devices:
        print(f"  - {device}")
    print()
    
    if plan.parameters:
        print("Parameters:")
        for param, description in plan.parameters.items():
            print(f"  - {param}: {description}")
        print()
    
    print("Plan Code:")
    print("-" * 40)
    print(plan.plan_code)
    print("-" * 40)


def interactive_mode():
    """Run in interactive mode for multiple queries."""
    print("Bluesky Plan Generator - Interactive Mode")
    print("Type 'quit' or 'exit' to stop")
    print("-" * 50)
    
    while True:
        try:
            query = input("\nEnter your Bluesky plan query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not query:
                print("Please enter a query.")
                continue
            
            print(f"\nGenerating plan for: '{query}'...")
            plan = generate_bluesky_plan(query)
            print_plan(plan)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate Bluesky plans using AI chat completion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "scan sample from 0 to 10 in 0.1 steps"
  %(prog)s "take a single measurement with detector"
  %(prog)s "perform a 2D mesh scan from 0,0 to 10,10 with 20x20 points"
  %(prog)s --interactive
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Query describing the desired Bluesky plan"
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
        help="Output file to save the plan (JSON format)"
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    if not args.query:
        parser.error("Query is required unless using --interactive mode")
    
    try:
        print(f"Generating Bluesky plan for: '{args.query}'")
        print(f"Using provider: {args.provider}")
        
        # Generate the plan
        plan = generate_bluesky_plan(
            query=args.query,
            provider=args.provider,
            model_id=args.model_id
        )
        
        # Print the plan
        print_plan(plan)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(plan.model_dump(), f, indent=2)
            print(f"\nPlan saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()



#make  acapability for the claude automatic generator
#pv finder, where it is fed a pv table that contains everything that is relevant
#which outpts a ideal pv's to use in the plan generator 
#