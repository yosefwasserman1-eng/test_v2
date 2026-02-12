
import subprocess
import threading
import time
import os
import sys
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Timeout in seconds
DEFAULT_TIMEOUT = 600  # 10 minutes for long generations

def run_script(script_name: str, args: Optional[List[str]] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    Executes a script from the 'scripts' directory.
    Captures stdout/stderr and handles timeouts.
    """
    if args is None:
        args = []
    
    # Use independent path resolution relative to project root (assuming wrapper is in tools/)
    # Or rely on CWD being project root. Let's rely on CWD but verify.
    project_root = Path(os.getcwd())
    script_path = project_root / "scripts" / script_name
    
    if not script_path.exists():
        logger.error(f"Script not found at: {script_path}")
        return {"success": False, "output": f"Script not found: {script_name}", "error": "File missing"}

    cmd = [sys.executable, str(script_path)] + args
    
    logger.info(f"🔧 Wrapper: Executing {' '.join(cmd)}")
    
    try:
        # Using Popen to capture realtime output if needed, but for now run() is safer for atomic execution
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root)  # Ensure it runs from project root
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
        logger.error(f"Script {script_name} timed out after {timeout}s")
        return {
            "success": False,
            "output": f"Execution timed out after {timeout} seconds.",
            "error": "Timeout"
        }
    except Exception as e:
        logger.exception(f"Script execution failed: {e}")
        return {
            "success": False,
            "output": f"Execution failed: {str(e)}",
            "error": str(e)
        }

if __name__ == "__main__":
    # Test
    print(run_script("02_stills_inspect.py"))
