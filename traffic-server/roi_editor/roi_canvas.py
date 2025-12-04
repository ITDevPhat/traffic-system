from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Callable
import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser
from PIL import Image, ImageTk

from .roi_types import ROI_TYPES, bgr_to_hex
from .utils import (
    draw_polygon, fill_polygon, draw_line, draw_rect, draw_circle, draw_text,
    point_in_polygon, point_on_line_segment, rect_from_points, near
)

Point = Tuple[int, int]


@dataclass
class Draft:
    roi_type: str
    shape: str
    points: List[Point] = field(default_factory=list)


class ROICanvas(tk.Frame):
    def __init__(self, master: tk.Tk, width: int = 1280, height: int = 720,
                 on_save: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
                 on_load: Optional[Callable[[], List[Dict[str, Any]]]] = None):
        super().__init__(master)
        self.master = master
        self.width = width
        self.height = height
        self.on_save = on_save
        self.on_load = on_load

        # Video/Image state
        self.cap: Optional[cv2.VideoCapture] = None
        self.image_frame: Optional[np.ndarray] = None  # BGR
        self.playing = False

        # ROI state
        self.rois: List[Dict[str, Any]] = []
        self.visible = True
        self.current_type: str = "detection_zone"
        self.current_color = ROI_TYPES[self.current_type]["color"]
        self.current_shape = ROI_TYPES[self.current_type]["shape"]

        # Draft drawing
        self.draft: Optional[Draft] = None
        self.hover_idx: Optional[int] = None
        self.preview_click_mode = False  # For test object preview

        # UI widgets
        self.canvas = tk.Canvas(self, width=self.width, height=self.height, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.photo = None  # for Tk image

        # Events
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.master.bind("<BackSpace>", self.on_backspace)
        self.master.bind("<Escape>", self.on_escape)
        self.master.bind("<Return>", self.on_return)

        # Toolbar (top)
        self.toolbar = tk.Frame(self)
        self.toolbar.place(x=8, y=8)
        self.play_btn = tk.Button(self.toolbar, text="▶ Play", command=self.toggle_play)
        self.play_btn.grid(row=0, column=0, padx=2)
        self.pause_btn = tk.Button(self.toolbar, text="⏸ Pause", command=self.pause)
        self.pause_btn.grid(row=0, column=1, padx=2)
        self.show_chk_var = tk.BooleanVar(value=True)
        self.show_chk = tk.Checkbutton(self.toolbar, text="Show ROI", var=self.show_chk_var, command=self.toggle_show)
        self.show_chk.grid(row=0, column=2, padx=6)
        self.preview_btn = tk.Button(self.toolbar, text="🧪 Preview Object", command=self.toggle_preview)
        self.preview_btn.grid(row=0, column=3, padx=2)

        # ROI type buttons
        self.type_bar = tk.Frame(self)
        self.type_bar.place(x=8, y=42)
        for i, (key, meta) in enumerate(ROI_TYPES.items()):
            def mkcmd(k=key):
                return lambda: self.select_type(k)
            btn = tk.Button(self.type_bar, text=key, command=mkcmd(), relief=tk.RIDGE)
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)

        # Info label
        self.info_var = tk.StringVar(value="Left-click to draw. Enter=finish, ESC=cancel, Backspace=undo")
        self.info = tk.Label(self, textvariable=self.info_var, fg="white", bg="#222")
        self.info.place(x=8, y=self.height - 28)

        # Main loop
        self.after(20, self.render_loop)

    # -------------------- Public API --------------------
    def load_video(self, path: str):
        try:
            self.cap = cv2.VideoCapture(path)
            self.playing = True
        except Exception as e:
            messagebox.showerror("Video Error", str(e))

    def load_image(self, path: str):
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Image Error", f"Cannot open image: {path}")
            return
        self.image_frame = img
        self.playing = False
        self.update()

    def set_rois(self, rois: List[Dict[str, Any]]):
        self.rois = rois or []

    def get_rois(self) -> List[Dict[str, Any]]:
        return list(self.rois)

    # -------------------- UI Actions --------------------
    def select_type(self, roi_type: str):
        if roi_type not in ROI_TYPES:
            return
        self.current_type = roi_type
        meta = ROI_TYPES[roi_type]
        self.current_shape = meta["shape"]
        self.current_color = meta["color"]
        self.info_var.set(f"Selected: {roi_type} ({self.current_shape}). Click to draw. Enter=finish, ESC=cancel")

    def toggle_play(self):
        if self.cap is None:
            return
        self.playing = not self.playing
        self.play_btn.config(text="⏸ Pause" if self.playing else "▶ Play")

    def pause(self):
        self.playing = False
        self.play_btn.config(text="▶ Play")

    def toggle_show(self):
        self.visible = self.show_chk_var.get()

    def toggle_preview(self):
        self.preview_click_mode = not self.preview_click_mode
        self.preview_btn.config(relief=tk.SUNKEN if self.preview_click_mode else tk.RAISED)
        self.info_var.set("Preview ON: click on frame to test object location" if self.preview_click_mode else "Preview OFF")

    # -------------------- Drawing Events --------------------
    def on_left_click(self, event):
        x, y = int(event.x), int(event.y)
        if self.preview_click_mode:
            self.handle_preview_click((x, y))
            return

        # Click on ROI to edit/delete
        idx = self.pick_roi((x, y))
        if idx is not None and self.draft is None:
            self.edit_roi_dialog(idx)
            return

        # Start or continue draft
        if self.draft is None:
            self.draft = Draft(roi_type=self.current_type, shape=self.current_shape, points=[])
        d = self.draft

        if d.shape == "polygon":
            # Snap to first point
            if len(d.points) >= 3 and near((x, y), d.points[0], 10):
                # close polygon
                self.finish_draft()
                return
            d.points.append((x, y))
        elif d.shape == "line":
            if len(d.points) == 0:
                d.points.append((x, y))
            elif len(d.points) == 1:
                d.points.append((x, y))
                self.finish_draft()
        elif d.shape == "rect":
            if len(d.points) == 0:
                d.points.append((x, y))
            elif len(d.points) == 1:
                d.points.append((x, y))
                self.finish_draft()

    def on_mouse_move(self, event):
        x, y = int(event.x), int(event.y)
        # Hover for existing rois
        self.hover_idx = self.pick_roi((x, y))

    def on_backspace(self, _):
        if self.draft and self.draft.points:
            self.draft.points.pop()

    def on_escape(self, _):
        self.draft = None

    def on_return(self, _):
        if self.draft:
            self.finish_draft()

    # -------------------- ROI Operations --------------------
    def finish_draft(self):
        if not self.draft:
            return
        d = self.draft
        if d.shape == "polygon" and len(d.points) < 3:
            messagebox.showwarning("Polygon", "Polygon needs at least 3 points")
            return
        if d.shape in ("line", "rect") and len(d.points) < 2:
            return

        # Normalize rect
        if d.shape == "rect":
            p1, p2 = rect_from_points(d.points[0], d.points[1])
            points = [p1, (p2[0], p1[1]), p2, (p1[0], p2[1])]  # clockwise
        else:
            points = list(d.points)

        # Default metadata
        name = simpledialog.askstring("ROI Name", "Enter ROI name:", parent=self.master) or f"{d.roi_type}_{len(self.rois)+1}"
        color = ROI_TYPES[d.roi_type]["color"]
        roi = {
            "name": name,
            "type": d.roi_type,
            "points": points,
            "color": bgr_to_hex(color),
        }

        # Extra fields for specific types
        if d.roi_type in ("lane_car", "lane_bike", "direction_zone"):
            # Ask heading range
            min_deg = simpledialog.askinteger("Heading Min", "Min heading (0-360):", minvalue=0, maxvalue=360, initialvalue=0)
            max_deg = simpledialog.askinteger("Heading Max", "Max heading (0-360):", minvalue=0, maxvalue=360, initialvalue=360)
            if min_deg is not None and max_deg is not None:
                roi["allowed_heading"] = [int(min_deg), int(max_deg)]

        self.rois.append(roi)
        self.draft = None

    def pick_roi(self, p: Point) -> Optional[int]:
        # Return index of ROI under point (polygon or rect) or near line
        for i in reversed(range(len(self.rois))):
            r = self.rois[i]
            pts = r.get("points", [])
            t = r.get("type")
            if t == "stopline" and len(pts) >= 2:
                if point_on_line_segment(p, pts[0], pts[1], tol=6.0):
                    return i
            else:
                if point_in_polygon(p, pts):
                    return i
        return None

    def edit_roi_dialog(self, idx: int):
        r = self.rois[idx]
        dlg = tk.Toplevel(self.master)
        dlg.title(f"Edit ROI: {r.get('name')}")
        dlg.geometry("320x320")
        # Name
        tk.Label(dlg, text="Name").pack(anchor="w", padx=8, pady=2)
        name_var = tk.StringVar(value=r.get("name", ""))
        tk.Entry(dlg, textvariable=name_var).pack(fill="x", padx=8)
        # Type (readonly)
        tk.Label(dlg, text=f"Type: {r.get('type')}").pack(anchor="w", padx=8, pady=2)
        # Color
        tk.Button(dlg, text="Pick Color", command=lambda: self._pick_color(r, dlg)).pack(padx=8, pady=4)
        # Allowed classes
        tk.Label(dlg, text="allowed_classes (comma)").pack(anchor="w", padx=8, pady=2)
        ac_var = tk.StringVar(value=",".join(r.get("allowed_classes", [])))
        tk.Entry(dlg, textvariable=ac_var).pack(fill="x", padx=8)
        # Related light
        tk.Label(dlg, text="related_light").pack(anchor="w", padx=8, pady=2)
        rl_var = tk.StringVar(value=r.get("related_light", ""))
        tk.Entry(dlg, textvariable=rl_var).pack(fill="x", padx=8)
        # Heading for lanes/direction
        if r.get("type") in ("lane_car", "lane_bike", "direction_zone"):
            tk.Label(dlg, text="Heading [min, max]").pack(anchor="w", padx=8, pady=2)
            h = r.get("allowed_heading", [0, 360])
            min_var = tk.IntVar(value=h[0])
            max_var = tk.IntVar(value=h[1])
            tk.Scale(dlg, from_=0, to=360, orient=tk.HORIZONTAL, variable=min_var, label="Min").pack(fill="x", padx=8)
            tk.Scale(dlg, from_=0, to=360, orient=tk.HORIZONTAL, variable=max_var, label="Max").pack(fill="x", padx=8)
        else:
            min_var = max_var = None

        # Actions
        btns = tk.Frame(dlg)
        btns.pack(fill="x", pady=8)
        def save_and_close():
            r["name"] = name_var.get().strip() or r["name"]
            ac = [c.strip() for c in ac_var.get().split(",") if c.strip()]
            if ac:
                r["allowed_classes"] = ac
            rl = rl_var.get().strip()
            if rl:
                r["related_light"] = rl
            if min_var is not None and max_var is not None:
                r["allowed_heading"] = [int(min_var.get()), int(max_var.get())]
            dlg.destroy()
        def delete_and_close():
            if messagebox.askyesno("Delete", "Delete this ROI?"):
                self.rois.pop(idx)
                dlg.destroy()
        tk.Button(btns, text="Save", command=save_and_close).pack(side=tk.LEFT, padx=8)
        tk.Button(btns, text="Delete", command=delete_and_close).pack(side=tk.LEFT, padx=8)
        tk.Button(btns, text="Close", command=dlg.destroy).pack(side=tk.RIGHT, padx=8)

    def _pick_color(self, r: Dict[str, Any], dlg: tk.Toplevel):
        # Current color hex or default
        cur = r.get("color", bgr_to_hex(ROI_TYPES[r.get("type", "detection_zone")]["color"]))
        rgb, hx = colorchooser.askcolor(title="Pick ROI Color", initialcolor=cur)
        if hx:
            r["color"] = hx

    def handle_preview_click(self, p: Point):
        idx = self.pick_roi(p)
        if idx is None:
            messagebox.showinfo("Preview", "Object does NOT lie in any ROI")
            return
        r = self.rois[idx]
        name = r.get("name")
        t = r.get("type")
        heading = None
        if t in ("lane_car", "lane_bike", "direction_zone"):
            h = r.get("allowed_heading", [0, 360])
            heading = f"heading=[{h[0]}°, {h[1]}°]"
        msg = f"Object nằm trong {name} ({t})"
        if heading:
            msg += f" ({heading})"
        messagebox.showinfo("Preview", msg)

    # -------------------- Rendering --------------------
    def read_frame(self) -> Optional[np.ndarray]:
        if self.cap is not None and self.playing:
            ok, frame = self.cap.read()
            if ok:
                self.image_frame = frame
            else:
                # loop video
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return self.image_frame

    def render_loop(self):
        frame = self.read_frame()
        if frame is None:
            # empty canvas
            img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        else:
            img = cv2.resize(frame, (self.width, self.height))

        # Draw overlays
        if self.visible:
            self.draw_overlays(img)

        # Convert to Tk image and show
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(rgb)
        self.photo = ImageTk.PhotoImage(image=im)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # HUD text
        self.canvas.create_text(8, self.height - 8, anchor=tk.SW, fill="white",
                                text=self.info_var.get())

        self.after(30, self.render_loop)

    def draw_overlays(self, img: np.ndarray):
        # Draw saved rois
        for i, r in enumerate(self.rois):
            pts = [(int(x), int(y)) for x, y in r.get("points", [])]
            if len(pts) == 0:
                continue
            color_hex = r.get("color")
            if color_hex and isinstance(color_hex, str) and color_hex.startswith("#") and len(color_hex) == 7:
                # convert hex to BGR
                rr = int(color_hex[1:3], 16)
                gg = int(color_hex[3:5], 16)
                bb = int(color_hex[5:7], 16)
                color = (bb, gg, rr)
            else:
                color = ROI_TYPES.get(r.get("type", "detection_zone"), {}).get("color", (0, 255, 255))

            highlight = (255, 255, 255) if i == self.hover_idx else color
            alpha = 0.25
            if r.get("type") == "stopline" and len(pts) >= 2:
                draw_line(img, pts[0], pts[1], highlight, 3)
            else:
                # fill and border
                fill_polygon(img, pts, color, alpha)
                draw_polygon(img, pts, highlight, 2, True)

            # label
            if pts:
                draw_text(img, r.get("name", "ROI"), (pts[0][0] + 6, pts[0][1] + 6), (255, 255, 255))

            # heading preview
            if r.get("type") in ("lane_car", "lane_bike", "direction_zone"):
                h = r.get("allowed_heading", [0, 360])
                center = np.mean(np.array(pts), axis=0).astype(int).tolist()
                cpt = (int(center[0]), int(center[1]))
                # draw two arrows for min/max
                from .utils import draw_heading
                draw_heading(img, cpt, float(h[0]), color)
                draw_heading(img, cpt, float(h[1]), color)

        # Draw draft
        if self.draft:
            d = self.draft
            color = ROI_TYPES[d.roi_type]["color"]
            if d.shape == "polygon":
                if len(d.points) >= 2:
                    draw_polygon(img, d.points, color, 2, False)
                for p in d.points:
                    draw_circle(img, p, 3, (255, 255, 255), 2)
                # snap circle
                if len(d.points) >= 3:
                    p0 = d.points[0]
                    draw_circle(img, p0, 8, (255, 255, 255), 2)
            elif d.shape == "line" and len(d.points) == 1:
                p1 = d.points[0]
                draw_line(img, p1, p1, color, 2)
            elif d.shape == "rect" and len(d.points) == 1:
                p1 = d.points[0]
                draw_rect(img, p1, p1, color, 2)
