#!/usr/bin/env python3
"""
FlowBooks launcher – run this file to start the application.
Uses the system Python 3 which ships with tkinter on macOS.
"""
import subprocess
import sys
import os

app_main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "main.py")

# Try homebrew Python 3.13 first (has python-tk@3.13), then others
for py in ["/opt/homebrew/bin/python3.13", "/opt/homebrew/bin/python3.12",
           "/opt/homebrew/bin/python3.11", "/usr/bin/python3", sys.executable]:
    try:
        result = subprocess.run([py, "-c", "import tkinter"], capture_output=True)
        if result.returncode == 0:
            os.execv(py, [py, app_main])
    except Exception:
        continue

print("ERROR: Could not find a Python installation with tkinter support.")
print("On macOS: tkinter comes with the system Python at /usr/bin/python3")
print("On Windows: install Python from python.org (includes tkinter by default)")
sys.exit(1)
