"""System utilities - browse folder dialog."""
import subprocess
import sys
from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/browse-folder")
def browse_folder() -> dict:
    """Open a native folder dialog and return the selected path."""
    dialog_script = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
folder = filedialog.askdirectory(title="Select Project Folder")
print(folder, end="")
root.destroy()
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", dialog_script],
            capture_output=True,
            text=True,
            timeout=60,
        )
        folder = result.stdout.strip()
        if folder:
            return {"folder": folder, "success": True}
        return {"folder": "", "success": False, "message": "No folder selected"}
    except Exception as e:
        return {"folder": "", "success": False, "error": str(e)}
