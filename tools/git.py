import subprocess


class GitTool:
    def run(self, args):
        process = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
        )

        return {
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
