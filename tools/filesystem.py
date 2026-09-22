from pathlib import Path


class FileSystemTool:
    def read(self, path):
        return Path(path).read_text(encoding="utf-8")

    def write(self, path, content):
        Path(path).write_text(content, encoding="utf-8")
        return True

    def exists(self, path):
        return Path(path).exists()
