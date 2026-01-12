import subprocess
from pathlib import Path

if __name__ == "__main__":
    files_path = str(Path(__file__).parent)
    try:
        server = subprocess.Popen(["poetry", "run", "python", "-m", "http.server", "3005", "--directory", files_path])
        print("Started Client server")
        server.wait()
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.terminate()
        server.wait()