#!/usr/bin/env python3
"""
Example usage of the Bluesky Plan Generator

This script demonstrates how to use the generate_bluesky_plan function
programmatically in your own code.
"""

import sys
sys.path.insert(0, 'src')

from generate_bluesky_plan import generate_bluesky_plan, print_plan


def main():
    """Example usage of the Bluesky plan generator."""
    
    # Example queries
    queries = [
        "scan sample from 0 to 10 in 0.1 steps using motor1 and detector1",
        "take a single measurement with detector1",
        "perform a 2D mesh scan from 0,0 to 10,10 with 20x20 points using motor1 and motor2",
        "perform a step scan with 5 points from 0 to 10 using motor1"
    ]
    
    print("Bluesky Plan Generator - Example Usage")
    print("=" * 50)
    
    for i, query in enumerate(queries, 1):
        print(f"\nExample {i}: {query}")
        print("-" * 50)
        
        try:
            # Generate the plan using CBORG provider
            plan = generate_bluesky_plan(query, provider="cborg")
            
            # Print the plan
            print_plan(plan)
            
        except Exception as e:
            print(f"Error generating plan: {e}")
        
        if i < len(queries):
            input("\nPress Enter to continue to next example...")


if __name__ == "__main__":
    main()
