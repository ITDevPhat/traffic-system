from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import sys

# Allow running as: python roi_editor/main.py
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from roi_canvas import ROICanvas
from roi_manager import ROIManager


class ROIEditorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ROI Editor - Traffic Violation System")
        self.root.geometry("1280x760")

        # State
        self.manager = ROIManager()
        self.canvas = ROICanvas(self.root, width=1280, height=720,
                                 on_save=self.on_save_clicked,
                                 on_load=self.on_load_clicked)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Menu
        self.build_menu()

        # Bottom buttons
        self.build_bottom_bar()

        # Hotkeys
        self.root.bind("<s>", lambda e: self.on_save_clicked())
        self.root.bind("<l>", lambda e: self.on_load_clicked())
        self.root.bind("<c>", lambda e: self.on_clear_clicked())
        self.root.bind("<d>", lambda e: self.on_toggle_debug())

    def build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open Image...", command=self.open_image)
        file_menu.add_command(label="Open Video...", command=self.open_video)
        file_menu.add_separator()
        file_menu.add_command(label="Load ROI (JSON)...", command=self.on_load_clicked)
        file_menu.add_command(label="Save ROI (JSON)...", command=self.on_save_clicked)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Hotkeys", command=self.show_hotkeys)
        menubar.add_cascade(label="Help", menu=help_menu)

    def build_bottom_bar(self):
        bar = tk.Frame(self.root)
        bar.pack(fill=tk.X, padx=8, pady=6)
        tk.Button(bar, text="Open Image", command=self.open_image).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="Open Video", command=self.open_video).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="Load JSON", command=self.on_load_clicked).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="Save JSON", command=self.on_save_clicked).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="Clear All", command=self.on_clear_clicked).pack(side=tk.LEFT, padx=12)

    def show_hotkeys(self):
        message = (
            "Hotkeys:\n"
            "S = Save JSON\n"
            "L = Load JSON\n"
            "C = Clear All\n"
            "D = Toggle Debug Mode (placeholder)\n"
            "Mouse Left = draw / edit\n"
            "Backspace = remove last point\n"
            "Enter = finish ROI\n"
            "ESC = cancel current ROI\n"
        )
        messagebox.showinfo("Hotkeys", message)

    # -------- File Actions --------
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Open Image",
            filetypes=[("Image", "*.jpg;*.jpeg;*.png;*.bmp;*.webp"), ("All", "*.*")],
        )
        if not path:
            return
        self.canvas.load_image(path)

    def open_video(self):
        path = filedialog.askopenfilename(
            title="Open Video",
            filetypes=[("Video", "*.mp4;*.avi;*.mov;*.mkv"), ("All", "*.*")],
        )
        if not path:
            return
        self.canvas.load_video(path)

    def on_load_clicked(self):
        path = filedialog.askopenfilename(
            title="Load ROI JSON",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        ok = self.manager.load(path)
        if not ok:
            messagebox.showerror("Load JSON", "Invalid ROI JSON file")
            return
        self.canvas.set_rois(self.manager.to_list())
        messagebox.showinfo("Load JSON", f"Loaded {len(self.manager.rois)} ROI(s)")

    def on_save_clicked(self):
        # Default to project root roi_config.json
        default = os.path.abspath("roi_config.json")
        path = filedialog.asksaveasfilename(
            title="Save ROI JSON",
            defaultextension=".json",
            initialfile=os.path.basename(default),
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        # Pull current ROIs from canvas and save
        self.manager.clear()
        for r in self.canvas.get_rois():
            self.manager.add_roi(r)
        ok = self.manager.save(path)
        if ok:
            messagebox.showinfo("Save JSON", f"Saved {len(self.manager.rois)} ROI(s) -> {path}")
        else:
            messagebox.showerror("Save JSON", "Failed to save file")

    def on_clear_clicked(self):
        if messagebox.askyesno("Clear All", "Clear all ROIs?"):
            self.canvas.set_rois([])

    def on_toggle_debug(self):
        # Placeholder for future debug overlay toggle
        messagebox.showinfo("Debug", "Debug mode toggled (placeholder)")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ROIEditorApp().run()
