"""
Shared utilities for pipeline scripts.
"""

import subprocess
import time

def run_command(command: str, description: str) -> bool:
    """Run a shell command and report results."""
    print(f"\n{'='*50}")
    print(f"STEP: {description}")
    print(f"COMMAND: {command}")
    print(f"{'='*50}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        
        duration = time.time() - start_time
        print(f"✅ SUCCESS ({duration:.1f}s)")
        
        if result.stdout:
            print("OUTPUT:")
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        print(f"❌ FAILED ({duration:.1f}s)")
        print(f"Return code: {e.returncode}")
        
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        
        return False
