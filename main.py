"""
main.py

Entry point only: creates the pywebview window and starts it. All logic
lives in backend/ - this file should stay this short even as features grow.
"""

import os
import webview

from backend.api import AlphaBotAPI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(BASE_DIR, "web", "index.html")
ICON_PATH = os.path.join(BASE_DIR, "web", "assets", "logo.png")


def launch_desktop_bootloader():
    api =  AlphaBotAPI()

    window = webview.create_window(
        title="EZ-BOTIX Professional Workstation",
        url=INDEX_HTML,
        js_api=api,
        width=1200,
        height=800,
        resizable=True,
        maximized=True,
    )

    api.set_window(window)
    webview.start(gui="qt", icon=ICON_PATH)


if __name__ == "__main__":
    launch_desktop_bootloader()
