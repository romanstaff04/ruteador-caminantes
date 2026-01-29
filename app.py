import subprocess
import sys
import os

BASE_DIR = os.path.dirname(__file__)
APP_REAL = os.path.join(BASE_DIR, "ruteoprueba.py")

subprocess.run([
    sys.executable,
    "-m", "streamlit", "run", APP_REAL,
])
