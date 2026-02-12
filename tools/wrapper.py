
import subprocess
import threading
import time
import os
import sys

# Timeout in seconds
DEFAULT_TIMEOUT = 600  # 10 minutes for long generations

def run_script(script_name, args=None, timeout=DEFAULT_TIMEOUT):
    """
    Executes a script from the 'scripts' directory.
    Captures stdout/stderr and handles timeouts.
    """
    if args is None:
        args = []
    
    script_path = os.path.abspath(f"scripts/{script_name}")
    if not os.path.exists(script_path):
        return {"success": False, "output": f"Script not found: {script_name}", "error": "File missing"}

    cmd = [sys.executable, script_path] + args
    
    print(f"🔧 Wrapper: Executing {' '.join(cmd)}")
    
    try:
        # Using Popen to capture realtime output if needed, but for now run() is safer for atomic execution
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()  # Ensure it runs from project root
        )
        
        success = result.returncode == 0
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
            
        return {
            "success": success,
            "output": output,
            "returncode": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": f"Execution timed out after {timeout} seconds.",
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Execution failed: {str(e)}",
            "error": str(e)
        }

if __name__ == "__main__":
    # Test
    print(run_script("02_stills_inspect.py"))
