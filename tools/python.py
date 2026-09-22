import subprocess
import sys


class PythonTool:
    def run(self, code):
        process = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )

        return {
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
