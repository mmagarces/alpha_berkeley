#!/bin/bash
# Script to activate the BOLT environment

echo "Activating BOLT environment..."

# Activate conda environment
conda activate bluesky-test

# Activate virtual environment
source venv/bin/activate

echo "Environment activated successfully!"
echo "Python version: $(python --version)"
echo "Virtual environment: $(which python)"

echo ""
echo "To run BOLT, you can now use:"
echo "  python src/applications/bolt/bolt_api.py"
echo ""
echo "To deactivate, run: deactivate"
