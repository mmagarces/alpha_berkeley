#!/usr/bin/env python3
"""
Bluesky Plan API Execution Generator

A script that fetches available plans from the queue server and generates API calls
that execute those existing plans. The AI analyzes user requests (like "Run a scan from 0 to 180 degrees")
and determines which existing plan best fits their needs, then generates the appropriate API call
in the format used by bolt_api.py.

Usage:
    python generate_contextual_bluesky_plan.py "Run a scan from 0 to 180 degrees"
    python generate_contextual_bluesky_plan.py "Take a camera acquisition with rotation motor"
    python generate_contextual_bluesky_plan.py --interactive
    python generate_contextual_bluesky_plan.py --list-plans
"""

import argparse
import json
import re
import subprocess
import sys
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Add the src directory to the path to import from framework
sys.path.insert(0, 'src')

from framework.models.completion import get_chat_completion


class BlueskyAPIExecution(BaseModel):
    """Structured output model for Bluesky API execution calls."""
    
    execution_name: str = Field(description="Name of the execution sequence")
    execution_description: str = Field(description="Description of what the execution does")
    selected_plan: str = Field(description="The plan name that best fits the user's request")
    api_call: dict = Field(description="Complete API call structure matching bolt_api.py format")
    parameters_used: dict = Field(description="Dictionary of parameters and their values used in the API call")
    estimated_duration: Optional[str] = Field(default=None, description="Estimated execution time")
    execution_notes: Optional[str] = Field(default=None, description="Notes about plan selection and parameter mapping")


def fetch_available_plans(server_url: str = "http://localhost:8003") -> Dict[str, Any]:
    """
    Fetch available plans with their detailed parameters from the queue server.
    
    Args:
        server_url: Base URL of the queue server
    
    Returns:
        Dictionary of plans with their detailed parameter information
    """
    try:
        queue_url = f"{server_url}/api/plans/existing"
        
        cmd = [
            "curl",
            "-X", "GET",
            queue_url,
            "-H", "accept: application/json",
            "-H", "Authorization: Apikey test"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Warning: Failed to fetch plans from server. Error: {result.stderr}")
            return {}
        
        history_data = json.loads(result.stdout)
        return history_data.get("plans_existing", {})
        
    except Exception as e:
        print(f"Warning: Error fetching available plans: {e}")
        return {}


def format_available_plans_context(plans: Dict[str, Any]) -> str:
    """
    Format the available plans with their detailed parameters into a context string for the AI prompt.
    
    Args:
        plans: Dictionary of available plans with their parameter details from the server
    
    Returns:
        Formatted string describing available plans with their parameters
    """
    if not plans:
        return "No available plans found on the server. You may need to create plans from scratch."
    
    context = "Available plans on the queue server with their parameters:\n\n"
    
    for i, (plan_name, plan_data) in enumerate(plans.items(), 1):
        context += f"{i}. Plan: {plan_name}\n"
        
        if isinstance(plan_data, dict) and 'parameters' in plan_data:
            context += "   Parameters:\n"
            for param in plan_data['parameters']:
                param_name = param.get('name', 'Unknown')
                param_desc = param.get('description', 'No description')
                param_type = param.get('annotation', {}).get('type', 'Unknown type')
                param_default = param.get('default', 'No default')
                param_min = param.get('min')
                param_max = param.get('max')
                
                context += f"     - {param_name} ({param_type}): {param_desc}\n"
                if param_default != 'No default':
                    context += f"       Default: {param_default}\n"
                if param_min is not None:
                    context += f"       Min: {param_min}\n"
                if param_max is not None:
                    context += f"       Max: {param_max}\n"
        else:
            context += "   No parameter details available\n"
        
        context += "\n"
    
    return context


def extract_numeric_values(query: str) -> List[float]:
    """
    Extract numeric values from a user query.
    
    Args:
        query: User query string
    
    Returns:
        List of numeric values found in the query
    """
    # Find all numeric values (integers and floats)
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, query)
    return [float(match) for match in matches]


def identify_relevant_plans(query: str, available_plans: Dict[str, Any]) -> List[str]:
    """
    Identify which plans are most relevant to the user's query based on keywords.
    
    Args:
        query: User query string
        available_plans: Dictionary of available plans with parameter details
    
    Returns:
        List of plan names that are most relevant to the query
    """
    query_lower = query.lower()
    relevant_plans = []
    
    # Define keyword mappings for common plan types
    keyword_mappings = {
        'move': ['move_motor', 'motor_move'],
        'scan': ['scan', 'rotation_scan', 'linear_scan'],
        'camera': ['camera_acquire', 'camera_capture'],
        'count': ['count', 'measurement'],
        'acquire': ['camera_acquire', 'acquire'],
        'rotate': ['rotation_scan', 'rotate'],
        'position': ['move_motor', 'position'],
        'degrees': ['move_motor', 'rotation_scan'],
        'angle': ['move_motor', 'rotation_scan']
    }
    
    # Find plans that match keywords in the query
    for keyword, plan_candidates in keyword_mappings.items():
        if keyword in query_lower:
            for plan_name in plan_candidates:
                if plan_name in available_plans and plan_name not in relevant_plans:
                    relevant_plans.append(plan_name)
    
    # If no specific matches found, return all plans (fallback to original behavior)
    if not relevant_plans:
        relevant_plans = list(available_plans.keys())
    
    return relevant_plans


def validate_parameter_ranges(query: str, available_plans: Dict[str, Any]) -> None:
    """
    Validate that numeric values in the user query are within the allowed ranges
    for the most relevant plans. Raises a nicely formatted error if validation fails.
    
    Args:
        query: User query string
        available_plans: Dictionary of available plans with parameter details
    
    Raises:
        ValueError: If any numeric values are out of range
    """
    numeric_values = extract_numeric_values(query)
    
    if not numeric_values:
        return
    
    # Identify which plans are most relevant to the user's query
    relevant_plans = identify_relevant_plans(query, available_plans)
    
    errors = []
    
    # Only check relevant plans for min/max constraints
    for plan_name in relevant_plans:
        if plan_name not in available_plans:
            continue
            
        plan_data = available_plans[plan_name]
        if not isinstance(plan_data, dict) or 'parameters' not in plan_data:
            continue
            
        for param in plan_data['parameters']:
            param_name = param.get('name', '')
            param_min = param.get('min')
            param_max = param.get('max')
            
            if param_min is not None or param_max is not None:
                try:
                    min_val = float(param_min) if param_min is not None else None
                    max_val = float(param_max) if param_max is not None else None
                    
                    for value in numeric_values:
                        if min_val is not None and value < min_val:
                            errors.append(
                                f"❌ Value {value} is below the minimum ({min_val}) "
                                f"for parameter '{param_name}' in plan '{plan_name}'"
                            )
                        if max_val is not None and value > max_val:
                            errors.append(
                                f"❌ Value {value} exceeds the maximum ({max_val}) "
                                f"for parameter '{param_name}' in plan '{plan_name}'"
                            )
                except (ValueError, TypeError):
                    # Skip if min/max values can't be converted to float
                    continue
    
    if errors:
        error_message = "\n" + "="*80 + "\n"
        error_message += "PARAMETER VALIDATION ERROR\n"
        error_message += "="*80 + "\n"
        error_message += f"Your request '{query}' contains values that are out of range:\n\n"
        for error in errors:
            error_message += f"  {error}\n"
        error_message += "\nPlease adjust your values to be within the allowed ranges.\n"
        error_message += "Use --list-plans to see all available plans and their constraints.\n"
        error_message += "="*80
        raise ValueError(error_message)


def generate_bluesky_api_execution(
    query: str, 
    available_plans: Dict[str, Any],
    provider: str = "cborg", 
    model_id: str = "anthropic/claude-sonnet"
) -> BlueskyAPIExecution:
    """
    Generate API execution calls for existing Bluesky plans.
    
    Args:
        query: User query describing the desired execution (e.g., "Run a scan from 0 to 180 degrees")
        available_plans: Dictionary of available plans with their parameter details from the server
        provider: AI provider to use (default: cborg)
        model_id: Model ID to use (default: anthropic/claude-sonnet)
    
    Returns:
        BlueskyAPIExecution: Structured API execution object
    """
    
    plans_context = format_available_plans_context(available_plans)
    
    prompt = f"""
You are an expert in Bluesky data collection execution. Analyze the user's request and determine which existing plan best fits their needs, then generate the appropriate API call.

{plans_context}

User Query: "{query}"

IMPORTANT: You should:
1. Analyze the user's request to understand what they want to accomplish
2. Select the most appropriate existing plan from the list above that matches their needs
3. Extract parameters from their request and map them to the EXACT parameter names shown above
4. Use the actual parameter names, types, and default values provided in the plan details
5. Pay attention to min/max constraints shown in the parameter details
6. Generate a complete API call structure that matches the bolt_api.py format

The API call should follow this exact structure:
```json
{{
    "item": {{
        "name": "plan_name",
        "args": [],
        "kwargs": {{
            "parameter1": "value1",
            "parameter2": "value2"
        }},
        "item_type": "plan",
        "user": "UNAUTHENTICATED_SINGLE_USER",
        "user_group": "primary"
    }}
}}
```

Please provide a structured response with:
1. A descriptive name for the execution
2. A clear description of what the execution does
3. The selected plan name that best fits the user's request
4. Complete API call structure in the exact format shown above
5. Dictionary of parameters and their values used
6. Estimated execution time if applicable
7. Notes about plan selection and parameter mapping

Example analysis:
- User: "Run a scan from 0 to 180 degrees"
- Analysis: User wants a rotational scan
- Selected Plan: "rotation_scan" (from the available plans)
- Parameters: Use the exact parameter names from the plan details:
  - start_angle: "0" (mapped from user's "0 degrees")
  - end_angle: "180" (mapped from user's "180 degrees")
  - num_points: "10" (use default or reasonable value)
  - save_dir: "default" (use default)
- API Call: {{"item": {{"name": "rotation_scan", "kwargs": {{"start_angle": "0", "end_angle": "180", "num_points": "10", "save_dir": "default"}}, "item_type": "plan", "user": "UNAUTHENTICATED_SINGLE_USER", "user_group": "primary"}}}}

Focus on matching the user's intent to the best available plan and generating the correct API call format.
"""
    
    try:
        result = get_chat_completion(
            message=prompt,
            provider=provider,
            model_id=model_id,
            max_tokens=2000,
            output_model=BlueskyAPIExecution
        )
        return result
    except Exception as e:
        print(f"Error generating plan: {e}")
        raise


def print_api_execution(execution: BlueskyAPIExecution):
    """Print the generated API execution in a formatted way."""
    print("=" * 80)
    print(f"BLUESKY API EXECUTION: {execution.execution_name}")
    print("=" * 80)
    print(f"Description: {execution.execution_description}")
    print()
    
    print(f"Selected Plan: {execution.selected_plan}")
    print()
    
    if execution.estimated_duration:
        print(f"Estimated Duration: {execution.estimated_duration}")
        print()
    
    if execution.execution_notes:
        print(f"Execution Notes: {execution.execution_notes}")
        print()
    
    if execution.parameters_used:
        print("Parameters Used:")
        for param, value in execution.parameters_used.items():
            print(f"  - {param}: {value}")
        print()
    
    print("API Call Structure:")
    print("-" * 40)
    print(json.dumps(execution.api_call, indent=2))
    print("-" * 40)


def list_available_plans(server_url: str = "http://localhost:8003"):
    """List all available plans from the queue server."""
    print("Fetching available plans from queue server...")
    plans = fetch_available_plans(server_url)
    
    if not plans:
        print("No plans found or unable to connect to server.")
        return
    
    print(f"\nFound {len(plans)} available plans:")
    print("=" * 60)
    
    for i, (plan_name, plan_data) in enumerate(plans.items(), 1):
        print(f"{i}. {plan_name}")
        
        if isinstance(plan_data, dict) and 'parameters' in plan_data:
            print("   Parameters:")
            for param in plan_data['parameters']:
                param_name = param.get('name', 'Unknown')
                param_desc = param.get('description', 'No description')
                param_type = param.get('annotation', {}).get('type', 'Unknown type')
                param_default = param.get('default', 'No default')
                param_min = param.get('min')
                param_max = param.get('max')
                
                print(f"     - {param_name} ({param_type}): {param_desc}")
                if param_default != 'No default':
                    print(f"       Default: {param_default}")
                if param_min is not None:
                    print(f"       Min: {param_min}")
                if param_max is not None:
                    print(f"       Max: {param_max}")
        else:
            print("   No parameter details available")
        print()


def interactive_mode(server_url: str = "http://localhost:8003"):
    """Run in interactive mode for multiple queries."""
    print("Bluesky Plan API Execution Generator - Interactive Mode")
    print("Type 'quit' or 'exit' to stop, 'list' to see available plans")
    print("-" * 60)
    
    # Fetch available plans once at startup
    print("Fetching available plans...")
    available_plans = fetch_available_plans(server_url)
    print(f"Found {len(available_plans)} available plans on server.")
    print()
    
    while True:
        try:
            query = input("\nEnter what you want to accomplish: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if query.lower() == 'list':
                list_available_plans(server_url)
                continue
            
            if not query:
                print("Please enter a query.")
                continue
            
            print(f"\nGenerating API execution for: '{query}'...")
            
            # Validate parameter ranges (will raise error if validation fails)
            validate_parameter_ranges(query, available_plans)
            
            execution = generate_bluesky_api_execution(query, available_plans)
            print_api_execution(execution)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate API calls that execute existing Bluesky plans based on user requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Run a scan from 0 to 180 degrees"
  %(prog)s "Take a camera acquisition with rotation motor"
  %(prog)s "Perform a measurement sequence"
  %(prog)s --interactive
  %(prog)s --list-plans
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Query describing what you want to accomplish (e.g., 'Run a scan from 0 to 180 degrees')"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--list-plans", "-l",
        action="store_true",
        help="List available plans from the queue server"
    )
    
    parser.add_argument(
        "--server-url",
        default="http://localhost:8003",
        help="Base URL of the queue server (default: http://localhost:8003)"
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
    
    if args.list_plans:
        list_available_plans(args.server_url)
        return
    
    if args.interactive:
        interactive_mode(args.server_url)
        return
    
    if not args.query:
        parser.error("Query is required unless using --interactive or --list-plans mode")
    
    try:
        print(f"Fetching available plans from server...")
        available_plans = fetch_available_plans(args.server_url)
        print(f"Found {len(available_plans)} available plans.")
        
        print(f"\nGenerating Bluesky API execution for: '{args.query}'")
        print(f"Using provider: {args.provider}")
        
        # Validate parameter ranges (will raise error if validation fails)
        validate_parameter_ranges(args.query, available_plans)
        
        # Generate the API execution
        execution = generate_bluesky_api_execution(
            query=args.query,
            available_plans=available_plans,
            provider=args.provider,
            model_id=args.model_id
        )
        
        # Print the API execution
        print_api_execution(execution)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(execution.model_dump(), f, indent=2)
            print(f"\nAPI execution saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
