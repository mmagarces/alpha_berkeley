#!/usr/bin/env python3
"""
Example usage of the PV Finder

This script demonstrates how to use the pv_finder function
programmatically in your own code.
"""

import sys
sys.path.insert(0, 'src')

from pv_finder import find_relevant_pvs, print_pv_result


def main():
    """Example usage of the PV finder."""
    
    # Example queries
    queries = [
        "scan sample from 0 to 10 degrees using theta motor",
        "take a single measurement with the ion chamber detector",
        "perform a 2D mesh scan from 0,0 to 10,10 with 20x20 points using X and Y motors",
        "do a temperature scan from 100K to 300K while measuring with the CCD camera",
        "perform a crystallography measurement with chi and omega rotations",
        "measure beam intensity with the scintillation counter while adjusting the monochromator energy",
        "take an image with the CCD detector at different sample heights"
    ]
    
    print("PV Finder - Example Usage")
    print("=" * 50)
    
    for i, query in enumerate(queries, 1):
        print(f"\nExample {i}: {query}")
        print("-" * 50)
        
        try:
            # Find relevant PVs using CBORG provider
            result = find_relevant_pvs(query, provider="cborg")
            
            # Print the result
            print_pv_result(result)
            
        except Exception as e:
            print(f"Error finding PVs: {e}")
        
        if i < len(queries):
            input("\nPress Enter to continue to next example...")


if __name__ == "__main__":
    main()
