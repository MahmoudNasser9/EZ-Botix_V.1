"""
project_manager.py

Owns project file save/load through native OS dialogs. Knows nothing about
serial ports or the device - just reads and writes .ezb project files.
"""

import webview


class ProjectManager:
    FILE_TYPES = ("EZ BOTIX Projects (*.ezb)", "All files (*.*)")
    DEFAULT_FILENAME = "my_robot_code.ezb"

    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def save_project(self, project_data: str):
        """Opens a native save dialog and writes the visual blocks to a file."""
        if not self.window:
            return {"status": "error", "message": "Window not found"}

        save_path = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory="",
            save_filename=self.DEFAULT_FILENAME,
            file_types=self.FILE_TYPES,
        )

        if not save_path:
            return {"status": "cancelled"}

        try:
            with open(save_path[0], "w", encoding="utf-8") as f:
                f.write(project_data)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def load_project(self):
        """Opens a native file picker and reads the project data back."""
        if not self.window:
            return {"status": "error", "message": "Window not found"}

        open_path = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            directory="",
            file_types=self.FILE_TYPES,
        )

        if not open_path:
            return {"status": "cancelled"}

        try:
            with open(open_path[0], "r", encoding="utf-8") as f:
                data = f.read()
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}
