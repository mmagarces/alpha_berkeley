#!/usr/bin/env python3
"""
PV Finder - Extract Relevant Process Variables for Experiments

This script uses AI to analyze user queries and extract relevant PV (Process Variable)
addresses from a hardcoded table of available PVs. It's designed to help users identify
which EPICS PVs are needed for their experimental plans.

Usage:
    python pv_finder.py "scan sample from 0 to 10 degrees"
    python pv_finder.py --interactive
"""

import argparse
import json
import sys
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

# Add the src directory to the path to import from framework
sys.path.insert(0, 'src')

from framework.models.completion import get_chat_completion


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


# Hardcoded PV table with realistic ALS-style PVs
HARDCODED_PV_TABLE = {
    "motors": [
        ProcessVariable(
            pv_name="ALS:SR:ES:BM:01:Y",
            description="Random motor",
            category="motor",
            units="mm"
        ),
        ProcessVariable(
            pv_name="DMC01:A",
            description="Main bolt beamline motor - controls horizontal beam position", 
            category="motor",
            units="mm"
        ),
    ],
    "detectors": [
        ProcessVariable(
            pv_name="ALS:SR:ES:IC:01:VALUE",
            description="Ion chamber detector - measures beam intensity",
            category="detector",
            units="nA"
        ),
        ProcessVariable(
            pv_name="13ARV1:cam1",
            description="Main bolt beamline motor",
            category="detector",
            units="counts"
        ),
    ]
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
3. **Beamline Controls**: Which beamline elements need to be adjusted?
4. **Environmental**: What environmental conditions need to be controlled?

For each relevant PV, provide:
- The exact PV name
- Description of what it controls
- Category (motor, detector, beamline_control, environmental)
- Units of measurement

Also provide:
- Clear reasoning for why each PV was selected
- Suggested type of Bluesky plan (scan, count, fly_scan, etc.)
- Any additional notes or recommendations

Focus on PVs that are directly involved in the experimental procedure described in the query.
Don't include PVs that are only peripherally related or not essential for the core experiment.
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
    print("PV Finder - Interactive Mode")
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
        description="Find relevant Process Variables for experimental queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "scan sample from 0 to 10 degrees"
  %(prog)s "take a single measurement with the detector"
  %(prog)s "perform a 2D mesh scan from 0,0 to 10,10 with 20x20 points"
  %(prog)s "do a temperature scan from 100K to 300K"
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
    
    args = parser.parse_args()
    
    if args.list_pvs:
        print("Available Process Variables:")
        print("=" * 50)
        for category, pvs in HARDCODED_PV_TABLE.items():
            print(f"\n{category.upper().replace('_', ' ')}:")
            for pv in pvs:
                print(f"  {pv.pv_name}: {pv.description} ({pv.units})")
        return
    
    if args.interactive:
        interactive_mode()
        return
    
    if not args.query:
        parser.error("Query is required unless using --interactive or --list-pvs mode")
    
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
