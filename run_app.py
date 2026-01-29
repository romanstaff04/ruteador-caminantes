import streamlit.web.cli as stcli
import sys
import os

def main():
    script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ruteoprueba.py"
    )

    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--server.headless=true",
        "--browser.serverAddress=localhost"
    ]

    stcli.main()

if __name__ == "__main__":
    main()
