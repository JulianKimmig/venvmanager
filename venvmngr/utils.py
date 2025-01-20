import os
import subprocess
from packaging.version import Version
import threading


def locate_system_pythons():
    try:
        # Use 'where' on Windows and 'which' on Unix-based systems
        command = "where" if os.name == "nt" else "which"
        result = subprocess.run([command, "python"], capture_output=True, text=True)
        pyths = []
        for line in result.stdout.strip().splitlines():
            try:
                versionresult = subprocess.run(
                    [line, "--version"], check=True, capture_output=True, text=True
                )
                vers_string = versionresult.stdout
                vers_string = Version(vers_string.split()[-1])

            except Exception:
                continue

            if not vers_string:
                continue
            dat = {
                "executable": line,
                "version": vers_string,
            }

            pyths.append(dat)
        return pyths
    except Exception as exc:
        raise ValueError("Failed to locate system Python.") from exc


def run_subprocess_with_streams(args, stdout_callback=None, stderr_callback=None):
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Define a function to read and forward each stream in a separate thread
    def read_stream(stream, callback):
        for line in iter(stream.readline, ""):
            if callback:
                callback(line)
        stream.close()

    # Start threads for stdout and stderr
    stdout_thread = threading.Thread(
        target=read_stream, args=(process.stdout, stdout_callback)
    )
    stderr_thread = threading.Thread(
        target=read_stream, args=(process.stderr, stderr_callback)
    )

    stdout_thread.start()
    stderr_thread.start()

    # Wait for both threads to complete
    stdout_thread.join()
    stderr_thread.join()

    # Wait for the process to complete
    process.wait()

    if process.returncode != 0:
        raise ValueError(
            f"Failed to call {' '.join(args)}"
        ) from subprocess.CalledProcessError(process.returncode, process.args)
