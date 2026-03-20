#!/usr/bin/env python3
"""
Run script for Aubo Robot Controller Backend.
Usage: python run_backend.py
"""

import sys
import os

# Add the src directory to the path for imports
backend_src = os.path.join(os.path.dirname(__file__), 'backend', 'src')
sys.path.insert(0, backend_src)

# Set PYTHONPATH for module imports
os.environ['PYTHONPATH'] = backend_src

if __name__ == "__main__":
    from robot_controller.api.main import app
    import uvicorn

    # Check for config file
    config_path = os.path.join(backend_src, 'robot_controller', 'config.json')

    if os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
            host = config.get('api_host', '0.0.0.0')
            port = config.get('api_port', 8000)
    else:
        host = '0.0.0.0'
        port = 8000

    print("=" * 50)
    print("Aubo Robot Controller Backend")
    print(f"Starting server on http://{host}:{port}")
    print("=" * 50)

    uvicorn.run(app, host=host, port=port)
