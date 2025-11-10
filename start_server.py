#!/usr/bin/env python3
"""
🚀 Traffic Detection Server - One-Click Startup
RTX 3050 Optimized with ONNX FP32 Support

Usage:
    python start_server.py

This will automatically:
- Change to traffic-server directory
- Apply ONNX FP32 patches
- Start uvicorn server on 0.0.0.0:8000
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    traffic_server_dir = script_dir / "traffic-server"
    
    print("🚀 Starting Traffic Detection Server...")
    print(f"📁 Script location: {script_dir}")
    print(f"📁 Server directory: {traffic_server_dir}")
    
    # Check if traffic-server directory exists
    if not traffic_server_dir.exists():
        print(f"❌ Error: traffic-server directory not found at {traffic_server_dir}")
        sys.exit(1)
    
    # Change to traffic-server directory
    os.chdir(traffic_server_dir)
    print(f"📂 Changed to: {os.getcwd()}")
    
    # Set environment variables for ONNX FP32
    os.environ['FORCE_FP32_ONNX'] = '1'
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    print("🔧 Environment configured for RTX 3050 + ONNX FP32")
    print("⚡ Starting uvicorn server...")
    print("=" * 60)
    
    # Start uvicorn server
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
