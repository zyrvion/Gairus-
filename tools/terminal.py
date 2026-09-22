import subprocess


class TerminalTool:
    def run(self, command, timeout=60):
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
