import cv2
import numpy as np
import math
from tkinter import *
from tkinter import filedialog, ttk, messagebox, StringVar, IntVar
from PIL import Image, ImageTk
import threading
import traceback
import time
import copy
import pymcprotocol
import sys  # For sys.platform


# --- CalibrationWindow Class (from boccia15.py) ---
# This class remains largely unchanged (assuming it's the same as provided before)
class CalibrationWindow(Toplevel):
    def __init__(self, main_app):
        super().__init__(main_app.root)
        self.main_app = main_app
        self.title("Advanced Calibration")
        self.geometry("850x850")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.calib_params = copy.deepcopy(self.main_app.active_detection_params)
        self.img_to_process = None
        if self.main_app.img is not None:
            self.img_to_process = self.main_app.img.copy()

        self.preview_size = (500, 350)
        self.color_vars = {}

        self.create_widgets()
        self.load_params_to_ui()
        self.refresh_all_mask_displays()

    def create_widgets(self):
        main_frame = Frame(self)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        global_settings_frame = LabelFrame(
            main_frame, text="Global Detection Settings", padx=5, pady=5
        )
        global_settings_frame.pack(fill=X, pady=(0, 10))

        Label(global_settings_frame, text="Gaussian Blur Kernel (odd, 3-21):").grid(
            row=0, column=0, sticky=W, padx=2, pady=2
        )
        self.color_vars["blur_kernel_scale"] = Scale(
            global_settings_frame,
            from_=3,
            to=21,
            orient=HORIZONTAL,
            resolution=2,
            command=lambda x: self.update_param_and_refresh_all("blur_kernel", int(x)),
        )
        self.color_vars["blur_kernel_scale"].grid(
            row=0, column=1, sticky=EW, padx=2, pady=2
        )
        global_settings_frame.grid_columnconfigure(1, weight=1)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=BOTH, expand=True, pady=5)

        colors_to_calibrate = ["white", "red", "blue"]
        for color_name in colors_to_calibrate:
            color_tab_frame = Frame(self.notebook)
            self.notebook.add(color_tab_frame, text=color_name.capitalize())
            self.setup_color_controls(color_tab_frame, color_name)

        action_frame = Frame(main_frame)
        action_frame.pack(fill=X, pady=10)
        Button(
            action_frame,
            text="Apply to Main",
            command=self.apply_changes,
            bg="lightgreen",
        ).pack(side=LEFT, padx=5)

        Button(
            action_frame,
            text="Reset Current Tab to Defaults",
            command=self.reset_current_tab_to_defaults,
        ).pack(side=LEFT, padx=5)
        Button(
            action_frame,
            text="Refresh Previews",
            command=self.refresh_all_mask_displays_from_button,
        ).pack(side=LEFT, padx=5)
        Button(action_frame, text="Close", command=self.on_closing, bg="salmon").pack(
            side=RIGHT, padx=5
        )

    def setup_color_controls(self, parent_frame, color_name):
        left_panel = Frame(parent_frame)
        left_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))

        right_panel = Frame(parent_frame, width=self.preview_size[0] + 20)
        right_panel.pack(side=RIGHT, fill=Y, padx=(5, 0))
        right_panel.pack_propagate(False)

        hsv_frame = LabelFrame(left_panel, text="HSV Ranges", padx=5, pady=5)
        hsv_frame.pack(fill=X, pady=3)
        if color_name not in self.color_vars:
            self.color_vars[color_name] = {}
        self.color_vars[color_name]["hsv_scales"] = {}
        hsv_params = [
            ("H Min", 0, 179),
            ("S Min", 0, 255),
            ("V Min", 0, 255),
            ("H Max", 0, 179),
            ("S Max", 0, 255),
            ("V Max", 0, 255),
        ]
        for i, (text, min_val, max_val) in enumerate(hsv_params):
            r, c = i % 3, (i // 3) * 2
            Label(hsv_frame, text=text + ":").grid(
                row=r, column=c, sticky=W, padx=2, pady=1
            )
            scale = Scale(
                hsv_frame,
                from_=min_val,
                to=max_val,
                orient=HORIZONTAL,
                length=150,
                command=lambda val, cn=color_name, p_idx=i: self.update_hsv_param_and_refresh(
                    cn, p_idx, int(val)
                ),
            )
            scale.grid(row=r, column=c + 1, sticky=EW, padx=2, pady=1)
            self.color_vars[color_name]["hsv_scales"][
                text.replace(" ", "_").lower()
            ] = scale
            hsv_frame.grid_columnconfigure(c + 1, weight=1)

        morph_frame = LabelFrame(
            left_panel, text="Morphological Operations", padx=5, pady=5
        )
        morph_frame.pack(fill=X, pady=3)
        morph_ops = [
            ("morph_open_k", "Open Kernel (odd, >=3):", 3, 21, 2),
            ("morph_open_iter", "Open Iterations:", 0, 5, 1),
            ("morph_close_k", "Close Kernel (odd, >=3):", 3, 21, 2),
            ("morph_close_iter", "Close Iterations:", 0, 5, 1),
        ]
        if color_name in ["red", "blue"]:
            morph_ops.extend(
                [
                    ("morph_dilate_k", "Dilate Kernel (odd, >=3):", 3, 21, 2),
                    ("morph_dilate_iter", "Dilate Iterations:", 0, 5, 1),
                ]
            )
        for r_idx, (param_key, text, from_val, to_val, res) in enumerate(morph_ops):
            Label(morph_frame, text=text).grid(
                row=r_idx, column=0, sticky=W, padx=2, pady=1
            )
            scale = Scale(
                morph_frame,
                from_=from_val,
                to=to_val,
                orient=HORIZONTAL,
                resolution=res,
                command=lambda val, cn=color_name, pk=param_key: self.update_param_and_refresh(
                    f"colors.{cn}.{pk}", int(val), cn
                ),
            )
            scale.grid(row=r_idx, column=1, sticky=EW, padx=2, pady=1)
            self.color_vars[color_name][f"{param_key}_scale"] = scale
            morph_frame.grid_columnconfigure(1, weight=1)

        detection_params_frame = LabelFrame(
            left_panel, text="Detection Parameters", padx=5, pady=5
        )
        detection_params_frame.pack(fill=X, pady=3)
        det_entries = [
            ("area_min", "Min Area:", 0, 10000, int),
            ("area_max", "Max Area:", 0, 50000, int),
        ]
        for r_idx, (param_key, text, _, _, type_func) in enumerate(det_entries):
            Label(detection_params_frame, text=text).grid(
                row=r_idx, column=0, sticky=W, padx=2, pady=1
            )
            entry = Entry(detection_params_frame, width=8)
            entry.grid(row=r_idx, column=1, sticky=W, padx=2, pady=1)
            entry.bind(
                "<FocusOut>",
                lambda e, cn=color_name, pk=param_key, ent=entry, tf=type_func: self.update_entry_param_and_refresh(
                    f"colors.{cn}.{pk}", ent.get(), cn, type_func=tf
                ),
            )
            entry.bind(
                "<Return>",
                lambda e, cn=color_name, pk=param_key, ent=entry, tf=type_func: self.update_entry_param_and_refresh(
                    f"colors.{cn}.{pk}", ent.get(), cn, type_func=tf
                ),
            )
            self.color_vars[color_name][f"{param_key}_entry"] = entry

        det_scales = [
            ("circularity", "Circularity (0-100%):", 0, 100, float, 100.0),
            ("solidity", "Solidity (0-100%):", 0, 100, float, 100.0),
        ]
        for r_idx_offset, (param_key, text, from_val, to_val, _, divisor) in enumerate(
            det_scales
        ):
            r_idx = r_idx_offset + len(det_entries)
            Label(detection_params_frame, text=text).grid(
                row=r_idx, column=0, sticky=W, padx=2, pady=1
            )
            scale = Scale(
                detection_params_frame,
                from_=from_val,
                to=to_val,
                orient=HORIZONTAL,
                command=lambda val, cn=color_name, pk=param_key, div=divisor: self.update_param_and_refresh(
                    f"colors.{cn}.{pk}", float(val) / div, cn
                ),
            )
            scale.grid(row=r_idx, column=1, sticky=EW, padx=2, pady=1)
            self.color_vars[color_name][f"{param_key}_scale"] = scale
        detection_params_frame.grid_columnconfigure(1, weight=1)

        Label(right_panel, text=f"{color_name.capitalize()} Mask Preview:").pack(
            pady=(0, 5)
        )
        mask_label = Label(
            right_panel,
            background="lightgrey",
            width=self.preview_size[0],
            height=self.preview_size[1],
        )
        mask_label.pack()
        self.color_vars[f"{color_name}_mask_label"] = mask_label
        self.color_vars[f"{color_name}_mask_photo"] = None

    def update_param_and_refresh(self, param_path, value, color_to_refresh=None):
        keys = param_path.split(".")
        d = self.calib_params
        try:
            for key in keys[:-1]:
                d = d[key]
            if keys[-1] in [
                "morph_open_k",
                "morph_close_k",
                "morph_dilate_k",
                "blur_kernel",
            ]:
                if value < 3:
                    value = 3
                if value % 2 == 0:
                    value = value + 1 if value > 0 else 3
            d[keys[-1]] = value
            if color_to_refresh:
                self.refresh_mask_display(color_to_refresh)
        except KeyError:
            print(f"Error: Invalid parameter path '{param_path}' during update.")
            traceback.print_exc()

    def update_param_and_refresh_all(self, param_path, value):
        keys = param_path.split(".")
        d = self.calib_params
        try:
            for key in keys[:-1]:
                d = d[key]
            if keys[-1] == "blur_kernel":
                if value < 3:
                    value = 3
                if value % 2 == 0:
                    value = value + 1 if value > 0 else 3
            d[keys[-1]] = value
            self.refresh_all_mask_displays()
        except KeyError:
            print(f"Error: Invalid parameter path '{param_path}' during update.")

    def update_entry_param_and_refresh(
        self, param_path, str_value, color_to_refresh, type_func=int
    ):
        try:
            value = type_func(str_value)
            self.update_param_and_refresh(param_path, value, color_to_refresh)
        except ValueError:
            print(
                f"Invalid input for {param_path}: {str_value}. Not a valid {type_func.__name__}."
            )

    def update_hsv_param_and_refresh(self, color_name, param_index_flat, value):
        if not self.calib_params["colors"][color_name][
            "hsv_ranges"
        ]:  # Should not happen if params are well-defined
            self.calib_params["colors"][color_name]["hsv_ranges"].append(
                (np.array([0, 0, 0]), np.array([179, 255, 255]))
            )  # Add a default if somehow empty
        current_lower, current_upper = self.calib_params["colors"][color_name][
            "hsv_ranges"
        ][0]
        temp_lower = current_lower.copy()
        temp_upper = current_upper.copy()
        param_map_to_channel_idx = {
            0: 0,
            1: 1,
            2: 2,
            3: 0,
            4: 1,
            5: 2,
        }  # H,S,V min then H,S,V max
        is_lower = param_index_flat < 3
        channel_idx = param_map_to_channel_idx[param_index_flat]
        if is_lower:
            temp_lower[channel_idx] = value
        else:
            temp_upper[channel_idx] = value
        self.calib_params["colors"][color_name]["hsv_ranges"][0] = (
            temp_lower,
            temp_upper,
        )
        self.refresh_mask_display(color_name)

    def load_params_to_ui(self):
        blur_k_val = self.calib_params.get("blur_kernel", 11)
        if blur_k_val % 2 == 0:
            blur_k_val = max(3, blur_k_val - 1)
        if (
            "blur_kernel_scale" in self.color_vars
            and self.color_vars["blur_kernel_scale"].winfo_exists()
        ):
            self.color_vars["blur_kernel_scale"].set(blur_k_val)

        for color_name in ["white", "red", "blue"]:
            color_data = self.calib_params["colors"].get(color_name, {})
            if color_data.get("hsv_ranges") and self.color_vars[color_name].get(
                "hsv_scales"
            ):
                if not all(
                    k in self.color_vars[color_name]["hsv_scales"]
                    for k in ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"]
                ):
                    continue
                lower, upper = color_data["hsv_ranges"][0]  # Assumes first range for UI
                self.color_vars[color_name]["hsv_scales"]["h_min"].set(lower[0])
                self.color_vars[color_name]["hsv_scales"]["s_min"].set(lower[1])
                self.color_vars[color_name]["hsv_scales"]["v_min"].set(lower[2])
                self.color_vars[color_name]["hsv_scales"]["h_max"].set(upper[0])
                self.color_vars[color_name]["hsv_scales"]["s_max"].set(upper[1])
                self.color_vars[color_name]["hsv_scales"]["v_max"].set(upper[2])

            morph_params_keys = [
                "morph_open_k",
                "morph_open_iter",
                "morph_close_k",
                "morph_close_iter",
            ]
            if color_name in ["red", "blue"]:
                morph_params_keys.extend(["morph_dilate_k", "morph_dilate_iter"])
            for param_key in morph_params_keys:
                if (
                    f"{param_key}_scale" in self.color_vars[color_name]
                    and self.color_vars[color_name][f"{param_key}_scale"].winfo_exists()
                ):
                    val = color_data.get(
                        param_key,
                        self.main_app.default_detection_params["colors"][
                            color_name
                        ].get(param_key, 3 if "_k" in param_key else 1),
                    )
                    if "_k" in param_key and val % 2 == 0:
                        val = max(3, val - 1)
                    self.color_vars[color_name][f"{param_key}_scale"].set(val)

            if (
                "area_min_entry" in self.color_vars[color_name]
                and self.color_vars[color_name]["area_min_entry"].winfo_exists()
            ):
                self.color_vars[color_name]["area_min_entry"].delete(0, END)
                self.color_vars[color_name]["area_min_entry"].insert(
                    0, str(color_data.get("area_min", 100))
                )
            if (
                "area_max_entry" in self.color_vars[color_name]
                and self.color_vars[color_name]["area_max_entry"].winfo_exists()
            ):
                self.color_vars[color_name]["area_max_entry"].delete(0, END)
                self.color_vars[color_name]["area_max_entry"].insert(
                    0, str(color_data.get("area_max", 10000))
                )
            if (
                "circularity_scale" in self.color_vars[color_name]
                and self.color_vars[color_name]["circularity_scale"].winfo_exists()
            ):
                self.color_vars[color_name]["circularity_scale"].set(
                    int(color_data.get("circularity", 0.7) * 100)
                )
            if (
                "solidity_scale" in self.color_vars[color_name]
                and self.color_vars[color_name]["solidity_scale"].winfo_exists()
            ):
                self.color_vars[color_name]["solidity_scale"].set(
                    int(color_data.get("solidity", 0.7) * 100)
                )

    def generate_mask_for_color(self, color_name, image_to_process):
        if image_to_process is None or image_to_process.size == 0:
            return np.zeros(
                (self.preview_size[1], self.preview_size[0]), dtype=np.uint8
            )

        params = self.calib_params["colors"].get(color_name, {})
        hsv_ranges = params.get("hsv_ranges", [])
        blur_k = self.calib_params.get("blur_kernel", 11)
        if blur_k < 3:
            blur_k = 3
        if blur_k % 2 == 0:
            blur_k = max(3, blur_k - 1)

        blurred_img = cv2.GaussianBlur(image_to_process, (blur_k, blur_k), 0)
        hsv_img = cv2.cvtColor(blurred_img, cv2.COLOR_BGR2HSV)
        combined_mask = np.zeros(hsv_img.shape[:2], dtype=np.uint8)

        for lower_hsv_np, upper_hsv_np in hsv_ranges:
            temp_lower = np.array(lower_hsv_np, dtype=np.uint8)
            temp_upper = np.array(upper_hsv_np, dtype=np.uint8)

            # Validate and adjust HSV range values (similar to detect_balls_in_frame)
            if not (
                color_name == "red" and temp_lower[0] > temp_upper[0]
            ):  # if not red wrap
                if temp_upper[0] < temp_lower[0]:
                    temp_upper[0] = temp_lower[0]  # hue
            if temp_upper[1] < temp_lower[1]:
                temp_upper[1] = temp_lower[1]  # saturation
            if temp_upper[2] < temp_lower[2]:
                temp_upper[2] = temp_lower[2]  # value

            individual_mask_segment = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
            if color_name == "red" and temp_lower[0] > temp_upper[0]:  # Red wrap-around
                mask1 = cv2.inRange(
                    hsv_img, np.array([0, temp_lower[1], temp_lower[2]]), temp_upper
                )  # From 0 to upper H
                mask2 = cv2.inRange(
                    hsv_img, temp_lower, np.array([179, temp_upper[1], temp_upper[2]])
                )  # From lower H to 179
                individual_mask_segment = cv2.bitwise_or(mask1, mask2)
            else:
                individual_mask_segment = cv2.inRange(hsv_img, temp_lower, temp_upper)
            combined_mask = cv2.bitwise_or(combined_mask, individual_mask_segment)

        open_k = params.get("morph_open_k", 5)
        open_iter = params.get("morph_open_iter", 1)
        close_k = params.get("morph_close_k", 5)
        dilate_k = params.get("morph_dilate_k", 5)  # Default for red/blue
        dilate_iter = params.get("morph_dilate_iter", 1)  # Default for red/blue
        close_iter_val = params.get(
            "morph_close_iter", 2 if color_name == "white" else 1
        )

        if open_k < 3:
            open_k = 3
        if open_k % 2 == 0:
            open_k += 1
        if close_k < 3:
            close_k = 3
        if close_k % 2 == 0:
            close_k += 1
        if dilate_k < 3:
            dilate_k = 3
        if dilate_k % 2 == 0:
            dilate_k += 1

        morph_mask = combined_mask
        if open_iter > 0:
            morph_mask = cv2.morphologyEx(
                morph_mask,
                cv2.MORPH_OPEN,
                np.ones((open_k, open_k), np.uint8),
                iterations=open_iter,
            )
        if color_name in ["red", "blue"] and dilate_iter > 0:
            morph_mask = cv2.dilate(
                morph_mask,
                np.ones((dilate_k, dilate_k), np.uint8),
                iterations=dilate_iter,
            )
        if close_iter_val > 0:
            morph_mask = cv2.morphologyEx(
                morph_mask,
                cv2.MORPH_CLOSE,
                np.ones((close_k, close_k), np.uint8),
                iterations=close_iter_val,
            )
        return morph_mask

    def refresh_mask_display(self, color_name):
        if self.img_to_process is None and self.main_app.img is not None:
            self.img_to_process = self.main_app.img.copy()
        elif self.main_app.img is None and self.img_to_process is not None:
            self.img_to_process = None

        if self.img_to_process is None or self.img_to_process.size == 0:
            mask_pil = Image.fromarray(
                np.zeros((self.preview_size[1], self.preview_size[0]), dtype=np.uint8),
                mode="L",
            )
        else:
            mask = self.generate_mask_for_color(color_name, self.img_to_process)
            mask_resized = cv2.resize(
                mask, self.preview_size, interpolation=cv2.INTER_NEAREST
            )
            mask_pil = Image.fromarray(mask_resized, mode="L")

        try:
            photo_img = ImageTk.PhotoImage(image=mask_pil)
            self.color_vars[f"{color_name}_mask_photo"] = photo_img
            if (
                f"{color_name}_mask_label" in self.color_vars
                and self.color_vars[f"{color_name}_mask_label"].winfo_exists()
            ):
                self.color_vars[f"{color_name}_mask_label"].config(image=photo_img)
        except Exception:
            pass

    def refresh_all_mask_displays(self):
        if self.main_app.img is not None:
            if (
                self.img_to_process is None
                or self.img_to_process.shape != self.main_app.img.shape
                or (
                    self.img_to_process.size > 0
                    and self.main_app.img.size > 0
                    and np.any(self.img_to_process != self.main_app.img)
                )
            ):
                self.img_to_process = self.main_app.img.copy()
        elif self.img_to_process is not None:
            self.img_to_process = None

        for color_name in ["white", "red", "blue"]:
            self.refresh_mask_display(color_name)

    def refresh_all_mask_displays_from_button(self):
        if self.main_app.img is None:
            messagebox.showwarning(
                "Refresh Previews", "No image loaded in the main application."
            )
            self.img_to_process = None
        else:
            self.img_to_process = self.main_app.img.copy()
        self.refresh_all_mask_displays()

    def apply_changes(self):
        self.main_app.active_detection_params = copy.deepcopy(self.calib_params)
        print("Info: Calibration parameters applied to main application.")
        if self.main_app.img is not None:
            self.main_app.run_full_detection_cycle(show_results_window=False)
        self.main_app.update_main_ui_detection_params_display()

    def reset_current_tab_to_defaults(self):
        try:
            current_tab_index = self.notebook.index(self.notebook.select())
            color_name_map = {0: "white", 1: "red", 2: "blue"}
            color_name = color_name_map.get(current_tab_index)

            if (
                color_name
                and color_name in self.main_app.default_detection_params["colors"]
            ):
                if color_name == "white":
                    self.calib_params["blur_kernel"] = copy.deepcopy(
                        self.main_app.default_detection_params.get("blur_kernel", 11)
                    )

                self.calib_params["colors"][color_name] = copy.deepcopy(
                    self.main_app.default_detection_params["colors"][color_name]
                )
                self.load_params_to_ui()
                self.refresh_mask_display(color_name)

                if color_name == "white":
                    self.refresh_all_mask_displays()

                print(
                    f"Info: Parameters for {color_name} reset to defaults in calibration window."
                )
            elif color_name:
                pass
        except Exception as e:
            traceback.print_exc()

    def on_closing(self):
        self.main_app.calibration_window_open = False
        self.main_app.calibration_window = None
        self.destroy()


# --- Main Application Class ---
class FieldMeasureApp:
    PREVIEW_SCALE = 1.0
    LOUPE_SCALE = 2.0
    LOUPE_DIM = 180
    LOUPE_BORDER = 2
    LOUPE_BORDER_COLOR = (0, 255, 0)
    TARGET_COLOR = (0, 0, 255)
    TARGET_RADIUS = 2
    FIELD_W_CM = 400.0
    FIELD_H_CM = 598.0

    PLC_IP = "192.168.0.200"
    PLC_PORT = 2001
    PLC_RECONNECT_INTERVAL = 5000

    DEFAULT_DETECTION_PARAMS = {  # From boccia16.py
        "blur_kernel": 11,
        "colors": {
            "white": {
                "hsv_ranges": [(np.array([0, 0, 170]), np.array([180, 65, 255]))],
                "circularity": 0.65,
                "solidity": 0.75,
                "area_min": 100,
                "area_max": 1500,
                "morph_open_k": 5,
                "morph_open_iter": 1,
                "morph_close_k": 5,
                "morph_close_iter": 2,
                "primary_min_radius": 6,
                "primary_circularity": 0.65,
            },
            "red": {
                "hsv_ranges": [
                    (np.array([0, 70, 70]), np.array([10, 255, 255])),
                    (np.array([170, 70, 70]), np.array([179, 255, 255])),
                ],
                "circularity": 0.7,
                "solidity": 0.65,
                "area_min": 100,
                "area_max": 700,
                "morph_open_k": 5,
                "morph_open_iter": 1,
                "morph_dilate_k": 5,
                "morph_dilate_iter": 1,
                "morph_close_k": 5,
                "morph_close_iter": 1,
            },
            "blue": {
                "hsv_ranges": [(np.array([100, 70, 70]), np.array([140, 255, 255]))],
                "circularity": 0.65,
                "solidity": 0.65,
                "area_min": 100,
                "area_max": 700,
                "morph_open_k": 5,
                "morph_open_iter": 1,
                "morph_dilate_k": 5,
                "morph_dilate_iter": 1,
                "morph_close_k": 5,
                "morph_close_iter": 1,
            },
        },
        "detection_threshold_nms": 0.01,
        "nms_overlap_threshold": 0.4,
    }
    STATUS_CLICK_COLOR_INFO_MODE = False
    last_known_plc_distance = None
    last_known_plc_angle = None
    last_known_plc_swing_speed = None
    last_known_plc_release_speed = 800
    has_last_known_plc_data = False
    sent_last_data_after_disappearance = False

    current_hsv_combined_mask_display = None  # For the new colored HSV combined mask

    MIN_16BIT_SIGNED = -32768
    MAX_16BIT_SIGNED = 32767
    DEFAULT_COLOR_PICK_PATCH_SIZE = 5

    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title("Field Measurement Tool (Enhanced v2.2 - Combined HSV Mask)")

        self.img = None
        self.preview = None
        self.cap = None
        self.camera_mode = False
        self.field_pts = []
        self.ball_pt1 = None
        self.ball_all = []
        self.cursor_preview = (0, 0)
        self.ball_detected = False
        self.running = True
        self.camera_thread = None

        self.canvas_photo = None
        self.loupe_photo = None
        self.combined_mask_photo = (
            None  # For the Tkinter label displaying the combined HSV mask
        )

        self.pymc3e = None
        self.plc_connected = False
        self.plc_connecting = False
        self.plc_attempt_reconnect = True

        self.default_detection_params = copy.deepcopy(self.DEFAULT_DETECTION_PARAMS)
        self.active_detection_params = copy.deepcopy(self.default_detection_params)

        self.calibration_window = None
        self.calibration_window_open = False
        self.picked_color_info_list = []

        self.target_x_cm_str = StringVar(value="155.0")
        self.target_y_cm_str = StringVar(value="750.0")
        self.distance_display_str = StringVar(value="Distance: N/A")
        self.angle_display_str = StringVar(value="Angle: N/A")
        self.ball_status_str = StringVar(value="Ball: Not detected")
        self.color_pick_patch_size_var = IntVar(
            value=self.DEFAULT_COLOR_PICK_PATCH_SIZE
        )
        self.white_solidity_var = IntVar(
            value=int(self.active_detection_params["colors"]["white"]["solidity"] * 100)
        )
        self.white_circularity_var = IntVar(
            value=int(
                self.active_detection_params["colors"]["white"]["circularity"] * 100
            )
        )
        self.white_min_radius_var = IntVar(
            value=self.active_detection_params["colors"]["white"].get(
                "primary_min_radius", 12
            )
        )

        self.current_hsv_combined_mask_display = np.zeros(
            (self.LOUPE_DIM, self.LOUPE_DIM, 3), dtype=np.uint8
        )

        self.create_widgets()
        self._initialize_plc()
        self.update_main_ui_detection_params_display()

        self.root.after(self.PLC_RECONNECT_INTERVAL, self._check_and_reconnect_plc_job)

    def _initialize_plc(self):
        self.pymc3e = pymcprotocol.Type3E()
        self.pymc3e.setaccessopt(commtype="binary")
        self.plc_attempt_reconnect = True
        self._attempt_connect_plc()

    def _update_plc_gui_status(self, status_text, lamp_color):
        if (
            hasattr(self, "plc_status_label_widget")
            and self.plc_status_label_widget.winfo_exists()
        ):
            self.plc_status_label_widget.config(text=f"PLC Status: {status_text}")
        if hasattr(self, "plc_lamp_canvas") and self.plc_lamp_canvas.winfo_exists():
            self.plc_lamp_canvas.itemconfig(self.plc_lamp_indicator, fill=lamp_color)

    def _attempt_connect_plc(self):
        if self.plc_connecting or not self.pymc3e:
            return False
        self.plc_connecting = True
        self._update_plc_gui_status("Connecting...", "orange")
        if hasattr(self.root, "update_idletasks") and self.root.winfo_exists():
            self.root.update_idletasks()
        try:
            if self.plc_connected:
                try:
                    self.pymc3e.close()
                except:
                    pass
            self.pymc3e.connect(self.PLC_IP, self.PLC_PORT)
            self.plc_connected = True
            self.plc_connecting = False
            self._update_plc_gui_status("Connected", "green")
            print(f"INFO: PLC Connected to {self.PLC_IP}:{self.PLC_PORT}")
            return True
        except Exception as e:
            self.plc_connected = False
            self.plc_connecting = False
            self._update_plc_gui_status(f"Failed", "red")
            return False

    def _check_and_reconnect_plc_job(self):
        if not self.running:
            return
        if (
            not self.plc_connected
            and self.plc_attempt_reconnect
            and not self.plc_connecting
        ):
            self._attempt_connect_plc()
        if hasattr(self.root, "after") and self.root.winfo_exists():
            self.root.after(
                self.PLC_RECONNECT_INTERVAL, self._check_and_reconnect_plc_job
            )

    def create_widgets(self):
        self.image_frame = Frame(self.root)
        self.image_frame.pack(side=LEFT, padx=10, pady=10, fill=BOTH, expand=True)

        self.control_frame = Frame(self.root, width=320)
        self.control_frame.pack(side=RIGHT, padx=10, pady=10, fill=Y)
        self.control_frame.pack_propagate(False)

        self.canvas = Canvas(self.image_frame, background="lightgrey")
        self.canvas.pack(fill=BOTH, expand=True)
        self.canvas.bind("<Motion>", self.update_loupe_and_coords)
        self.canvas.bind("<Button-1>", self.handle_canvas_click)

        self.info_display_frame = Frame(self.image_frame)
        self.info_display_frame.pack(fill=X, pady=(5, 2))

        self.combined_mask_label = Label(
            self.info_display_frame,
            background="black",
            width=self.LOUPE_DIM,
            height=self.LOUPE_DIM,
        )
        self.combined_mask_label.pack(side=LEFT, padx=5, pady=2, expand=True, fill=BOTH)
        blank_img_mask = Image.new(
            "RGB", (self.LOUPE_DIM, self.LOUPE_DIM), color="black"
        )  # RGB for colored mask
        self.combined_mask_photo = ImageTk.PhotoImage(image=blank_img_mask)
        self.combined_mask_label.config(image=self.combined_mask_photo)

        self.loupe_label = Label(
            self.info_display_frame,
            background="lightgrey",
            width=self.LOUPE_DIM,
            height=self.LOUPE_DIM,
        )
        self.loupe_label.pack(side=LEFT, padx=5, pady=2, expand=True, fill=BOTH)
        blank_img_loupe = Image.new(
            "RGB", (self.LOUPE_DIM, self.LOUPE_DIM), color="lightgrey"
        )
        self.loupe_photo = ImageTk.PhotoImage(image=blank_img_loupe)
        self.loupe_label.config(image=self.loupe_photo)

        self.coord_label = Label(self.image_frame, text="Cursor (Preview): X: -, Y: -")
        self.coord_label.pack(pady=2, side=BOTTOM, fill=X)

        input_mode_frame = LabelFrame(
            self.control_frame, text="Input Mode", font=("Arial", 10, "bold")
        )
        input_mode_frame.pack(fill=X, padx=5, pady=5)

        Button(
            input_mode_frame, text="Open Image File", command=self.open_image_file
        ).pack(fill=X, pady=2)

        Button(input_mode_frame, text="Open Camera", command=self.open_camera).pack(
            fill=X, pady=2
        )

        #Red REd RED red reD
        red_team_frame = LabelFrame(self.control_frame, text="Team Status", font=("Arial", 10, "bold"))
        red_team_frame.pack(fill=X, padx=5, pady=5)

        red_team_frame = LabelFrame(self.control_frame, text="Red Team Input", font=("Arial", 10, "bold"))
        red_team_frame.pack(fill=X, padx=5, pady=5)

        Label(red_team_frame, text="X (cm):").grid(row=0, column=0, sticky=W, padx=5)
        self.red_team_x_entry = Entry(red_team_frame, width=10)
        self.red_team_x_entry.grid(row=0, column=1, sticky=W, padx=5)

        Label(red_team_frame, text="Y (cm):").grid(row=1, column=0, sticky=W, padx=5)
        self.red_team_y_entry = Entry(red_team_frame, width=10)
        self.red_team_y_entry.grid(row=1, column=1, sticky=W, padx=5)

        Button(
            red_team_frame,
            text="Confirm",
            command=self.red_team,
            bg="red",
            fg="white",
            font=("Arial", 10, "bold"),
        ).grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        Button(
            red_team_frame,
            text="Check Red Team",
            command=self.red_team,
            bg="red",
            fg="white",
            font=("Arial", 10, "bold"),
        ).grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")


        self.capture_btn = Button(
            input_mode_frame,
            text="Capture Frame",
            command=self.capture_frame,
            state=DISABLED,
        )
        self.capture_btn.pack(fill=X, pady=2)

        corners_frame = LabelFrame(
            self.control_frame, text="Field Corners", font=("Arial", 10, "bold")
        )
        corners_frame.pack(fill=X, padx=5, pady=5)
        Label(
            corners_frame,
            text="Click order: TL, BL, TR, BR",
            font=("Arial", 8, "italic"),
        ).pack(fill=X)
        self.corner_listbox = Listbox(corners_frame, height=4, width=30)
        self.corner_listbox.pack(fill=X, pady=2)
        corner_buttons_frame = Frame(corners_frame)
        corner_buttons_frame.pack(fill=X)
        Button(
            corner_buttons_frame, text="Remove Last", command=self.remove_last_point
        ).pack(side=LEFT, expand=True, fill=X, pady=2, padx=1)
        Button(corner_buttons_frame, text="Clear All", command=self.clear_points).pack(
            side=LEFT, expand=True, fill=X, pady=2, padx=1
        )

        ball_detect_frame = LabelFrame(
            self.control_frame,
            text="Ball Detection & Params",
            font=("Arial", 10, "bold"),
        )
        ball_detect_frame.pack(fill=X, padx=5, pady=5)
        Button(
            ball_detect_frame,
            text="Detect Balls",
            command=lambda: self.run_full_detection_cycle(show_results_window=False),
        ).pack(fill=X, pady=2)
        self.ball_status_label = Label(
            ball_detect_frame, textvariable=self.ball_status_str
        )
        self.ball_status_label.pack(fill=X, pady=2)

        pick_params_frame = Frame(ball_detect_frame)
        pick_params_frame.pack(fill=X, pady=(5, 2))
        Button(
            pick_params_frame,
            text="Pick White (Set)",
            command=lambda: self.initiate_hsv_color_pick_for_params("white"),
            bg="#E0E0FF",
        ).pack(side=LEFT, expand=True, fill=X, padx=1)
        Button(
            pick_params_frame,
            text="Pick Red (Set)",
            command=lambda: self.initiate_hsv_color_pick_for_params("red"),
            bg="#FFE0E0",
        ).pack(side=LEFT, expand=True, fill=X, padx=1)
        Button(
            pick_params_frame,
            text="Pick Blue (Set)",
            command=lambda: self.initiate_hsv_color_pick_for_params("blue"),
            bg="#E0FFE0",
        ).pack(side=LEFT, expand=True, fill=X, padx=1)

        Button(
            ball_detect_frame,
            text="Pick Color (Info Only)",
            command=self.toggle_info_color_pick_mode,
        ).pack(fill=X, pady=2)
        Button(
            ball_detect_frame,
            text="Advanced HSV/Detection Params",
            command=self.open_calibration_window,
            bg="lightblue",
        ).pack(fill=X, pady=2)

        patch_size_frame_main = Frame(ball_detect_frame)
        patch_size_frame_main.pack(fill=X, pady=(5, 0))
        Label(patch_size_frame_main, text="Param Pick Patch (px):").pack(
            side=LEFT, padx=(0, 5)
        )
        self.color_pick_patch_scale_main_ui = Scale(
            patch_size_frame_main,
            from_=3,
            to=21,
            orient=HORIZONTAL,
            resolution=2,
            variable=self.color_pick_patch_size_var,
        )
        self.color_pick_patch_scale_main_ui.pack(side=LEFT, fill=X, expand=True)

        det_params_frame = LabelFrame(
            self.control_frame,
            text="Primary White Ball Params (Main UI)",
            font=("Arial", 10, "bold"),
        )
        det_params_frame.pack(fill=X, padx=5, pady=5)
        Label(det_params_frame, text="Solidity (0-100%):").grid(
            row=0, column=0, sticky=W
        )
        self.white_solidity_scale = Scale(
            det_params_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            variable=self.white_solidity_var,
            command=self.update_white_ball_detection_params_from_main_ui,
        )
        self.white_solidity_scale.grid(row=0, column=1, sticky=EW)
        Label(det_params_frame, text="Circularity (0-100%):").grid(
            row=1, column=0, sticky=W
        )
        self.white_circularity_scale = Scale(
            det_params_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            variable=self.white_circularity_var,
            command=self.update_white_ball_detection_params_from_main_ui,
        )
        self.white_circularity_scale.grid(row=1, column=1, sticky=EW)
        Label(det_params_frame, text="Min Radius (px):").grid(row=2, column=0, sticky=W)
        self.white_min_radius_scale = Scale(
            det_params_frame,
            from_=1,
            to=50,
            orient=HORIZONTAL,
            variable=self.white_min_radius_var,
            command=self.update_white_ball_detection_params_from_main_ui,
        )
        self.white_min_radius_scale.grid(row=2, column=1, sticky=EW)
        det_params_frame.grid_columnconfigure(1, weight=1)

        target_measure_frame = LabelFrame(
            self.control_frame, text="Target & Measurement", font=("Arial", 10, "bold")
        )

        target_measure_frame.pack(fill=X, padx=5, pady=5)
        Label(target_measure_frame, text="Target X (cm):").grid(
            row=0, column=0, sticky=W, padx=5
        )
        self.x_entry = Entry(
            target_measure_frame, width=10, textvariable=self.target_x_cm_str
        )
        self.x_entry.grid(row=0, column=1, sticky=W, padx=5)
        Label(target_measure_frame, text="Target Y (cm):").grid(
            row=1, column=0, sticky=W, padx=5
        )
        self.y_entry = Entry(
            target_measure_frame, width=10, textvariable=self.target_y_cm_str
        )
        self.y_entry.grid(row=1, column=1, sticky=W, padx=5)
        Button(
            target_measure_frame,
            text="Set Target Position",
            command=self.set_target_position_action,
        ).grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        Button(
            target_measure_frame,
            text="Calculate & Show Detail",
            command=lambda: self.run_full_detection_cycle(show_results_window=True),
            bg="lightgreen",
            font=("Arial", 10, "bold"),
        ).grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        self.distance_display_label = Label(
            target_measure_frame,
            textvariable=self.distance_display_str,
            font=("Arial", 14),
        )
        self.distance_display_label.grid(
            row=4, column=0, columnspan=2, pady=2, sticky="w"
        )
        self.angle_display_label = Label(
            target_measure_frame,
            textvariable=self.angle_display_str,
            font=("Arial", 14),
        )
        self.angle_display_label.grid(row=5, column=0, columnspan=2, pady=2, sticky="w")
        target_measure_frame.grid_columnconfigure(1, weight=1)

        plc_status_frame_outer = LabelFrame(
            self.control_frame, text="PLC Connection", font=("Arial", 10, "bold")
        )
        plc_status_frame_outer.pack(fill=X, padx=5, pady=5)
        plc_lamp_text_frame = Frame(plc_status_frame_outer)
        plc_lamp_text_frame.pack(pady=(5, 0), fill=X, expand=True)
        self.plc_lamp_canvas = Canvas(plc_lamp_text_frame, width=20, height=20)
        self.plc_lamp_canvas.pack(side=LEFT, padx=(10, 5))
        self.plc_lamp_indicator = self.plc_lamp_canvas.create_oval(
            2, 2, 18, 18, fill="grey", outline="black"
        )
        self.plc_status_label_widget = Label(
            plc_lamp_text_frame, text="PLC Status: Initializing...", font=("Arial", 12)
        )
        self.plc_status_label_widget.pack(side=LEFT, expand=True, fill=X)

        self._update_plc_gui_status("Initializing...", "grey")

    def _generate_hsv_combined_mask_for_display(self):
        """Generates a colored BGR mask representing active HSV ranges for display."""
        if self.img is None or self.img.size == 0:
            # Return a black BGR image of LOUPE_DIM for consistency if no source image
            return np.zeros((self.LOUPE_DIM, self.LOUPE_DIM, 3), dtype=np.uint8)

        # Use the original self.img for this HSV range visualization, not blurred
        hsv_image_orig = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)
        # Create a BGR canvas to draw colored masks onto
        colored_mask_preview_full_res = np.zeros_like(self.img)

        # Define colors for display (BGR format)
        # Order can matter if masks overlap; last drawn is on top.
        colors_to_draw_ordered = [  # Process in this order
            (
                "white",
                {"params_key": "white", "display_color": [0, 255, 0]},
            ),  # White areas -> Green
            (
                "blue",
                {"params_key": "blue", "display_color": [255, 0, 0]},
            ),  # Blue areas -> Blue
            (
                "red",
                {"params_key": "red", "display_color": [0, 0, 255]},
            ),  # Red areas -> Red
        ]

        for color_name_key, color_info in colors_to_draw_ordered:
            color_params = self.active_detection_params["colors"].get(
                color_info["params_key"]
            )
            if not color_params or not color_params.get("hsv_ranges"):
                continue

            hsv_ranges_list = color_params["hsv_ranges"]
            # This mask will be for the current color (e.g., white, then blue, then red)
            current_color_binary_mask_aggregated = np.zeros(
                hsv_image_orig.shape[:2], dtype=np.uint8
            )

            for lower_hsv_np, upper_hsv_np in hsv_ranges_list:
                temp_lower = np.array(lower_hsv_np, dtype=np.uint8)
                temp_upper = np.array(upper_hsv_np, dtype=np.uint8)

                # Basic validation for HSV ranges (non-hue channels)
                for i in range(1, 3):  # S, V
                    if temp_upper[i] < temp_lower[i]:
                        temp_upper[i] = temp_lower[i]

                # Hue validation (handle non-red wrap case)
                if not (
                    color_info["params_key"] == "red" and temp_lower[0] > temp_upper[0]
                ):
                    if temp_upper[0] < temp_lower[0]:
                        temp_upper[0] = temp_lower[0]

                individual_mask_segment = np.zeros(
                    hsv_image_orig.shape[:2], dtype=np.uint8
                )
                if (
                    color_info["params_key"] == "red" and temp_lower[0] > temp_upper[0]
                ):  # Red wrap-around
                    # Mask for lower hue range (e.g., 0 to H_max)
                    mask1 = cv2.inRange(
                        hsv_image_orig,
                        np.array([0, temp_lower[1], temp_lower[2]]),
                        temp_upper,
                    )
                    # Mask for upper hue range (e.g., H_min to 179)
                    mask2 = cv2.inRange(
                        hsv_image_orig,
                        temp_lower,
                        np.array([179, temp_upper[1], temp_upper[2]]),
                    )
                    individual_mask_segment = cv2.bitwise_or(mask1, mask2)
                else:
                    individual_mask_segment = cv2.inRange(
                        hsv_image_orig, temp_lower, temp_upper
                    )

                current_color_binary_mask_aggregated = cv2.bitwise_or(
                    current_color_binary_mask_aggregated, individual_mask_segment
                )

            # Apply the display color to the full resolution preview canvas
            # where the current color's aggregated mask is active
            colored_mask_preview_full_res[
                current_color_binary_mask_aggregated == 255
            ] = color_info["display_color"]

        return colored_mask_preview_full_res

    def update_white_ball_detection_params_from_main_ui(self, event=None):
        if "white" in self.active_detection_params["colors"]:
            self.active_detection_params["colors"]["white"]["solidity"] = (
                float(self.white_solidity_var.get()) / 100.0
            )
            self.active_detection_params["colors"]["white"]["circularity"] = (
                float(self.white_circularity_var.get()) / 100.0
            )
            self.active_detection_params["colors"]["white"]["primary_circularity"] = (
                float(self.white_circularity_var.get()) / 100.0
            )
            self.active_detection_params["colors"]["white"][
                "primary_min_radius"
            ] = self.white_min_radius_var.get()

            if (
                self.calibration_window_open
                and self.calibration_window
                and self.calibration_window.winfo_exists()
            ):
                self.calibration_window.calib_params["colors"]["white"]["solidity"] = (
                    self.active_detection_params["colors"]["white"]["solidity"]
                )
                self.calibration_window.calib_params["colors"]["white"][
                    "circularity"
                ] = self.active_detection_params["colors"]["white"]["circularity"]
                self.calibration_window.calib_params["colors"]["white"][
                    "primary_circularity"
                ] = self.active_detection_params["colors"]["white"][
                    "primary_circularity"
                ]
                self.calibration_window.calib_params["colors"]["white"][
                    "primary_min_radius"
                ] = self.active_detection_params["colors"]["white"][
                    "primary_min_radius"
                ]
                self.calibration_window.load_params_to_ui()
                self.calibration_window.refresh_mask_display("white")

            if self.img is not None and not self.camera_mode:
                self.run_full_detection_cycle(show_results_window=False)
            elif (
                self.img is not None and self.camera_mode
            ):  # For camera, just update the combined mask display
                self.current_hsv_combined_mask_display = (
                    self._generate_hsv_combined_mask_for_display()
                )
                # The main camera loop will call update_main_canvas_display which uses this

    def update_main_ui_detection_params_display(self):
        if hasattr(self, "white_solidity_var"):
            white_params = self.active_detection_params["colors"].get(
                "white", self.default_detection_params["colors"]["white"]
            )
            self.white_solidity_var.set(int(white_params.get("solidity", 0.75) * 100))
            self.white_circularity_var.set(
                int(white_params.get("circularity", 0.65) * 100)
            )
            self.white_min_radius_var.set(white_params.get("primary_min_radius", 12))

    def toggle_info_color_pick_mode(self):
        if self.img is None:
            messagebox.showwarning(
                "Pick Color", "Please open an image or camera first."
            )
            return
        self.STATUS_CLICK_COLOR_INFO_MODE = not self.STATUS_CLICK_COLOR_INFO_MODE
        if self.STATUS_CLICK_COLOR_INFO_MODE:
            self.canvas.config(cursor="crosshair")
            messagebox.showinfo(
                "Pick Color Mode",
                "Informational color pick mode ON. Click on image for BGR/HSV console output. Click button again for OFF.",
            )
            if (
                hasattr(self, "picking_hsv_for_color")
                and self.picking_hsv_for_color is not None
            ):
                self.picking_hsv_for_color = None
        else:
            self.canvas.config(cursor="")
            messagebox.showinfo("Pick Color Mode", "Informational color pick mode OFF.")

    def get_color_info_from_click(self, event):
        if self.img is None:
            return
        if self.preview is None or not (
            0 <= event.x < self.preview.shape[1]
            and 0 <= event.y < self.preview.shape[0]
        ):
            return
        img_x = int(event.x / self.PREVIEW_SCALE)
        img_y = int(event.y / self.PREVIEW_SCALE)
        if not (0 <= img_x < self.img.shape[1] and 0 <= img_y < self.img.shape[0]):
            return
        bgr_color = self.img[img_y, img_x]
        hsv_color = cv2.cvtColor(np.uint8([[bgr_color]]), cv2.COLOR_BGR2HSV)[0][0]
        print(
            f"--- Color Info at ({img_x},{img_y}) --- BGR: {bgr_color}, HSV: {hsv_color} ---"
        )
        self.picked_color_info_list.append(
            {"bgr": bgr_color, "hsv": hsv_color, "coords": (img_x, img_y)}
        )

    def set_target_position_action(self):
        try:
            x_val = float(self.target_x_cm_str.get())
            y_val = float(self.target_y_cm_str.get())
            messagebox.showinfo(
                "Target Set", f"Target noted as X: {x_val} cm, Y: {y_val} cm."
            )
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter valid numbers for X and Y target."
            )

    def handle_canvas_click(self, event):
        if self.STATUS_CLICK_COLOR_INFO_MODE:
            self.get_color_info_from_click(event)
        elif (
            hasattr(self, "picking_hsv_for_color")
            and self.picking_hsv_for_color is not None
        ):
            self.process_hsv_color_pick(event)
        else:
            self.add_point(event)

    def open_image_file(self):
        self.stop_camera_if_running()
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            try:
                self.img = cv2.imread(file_path)
                if self.img is None:
                    raise ValueError(f"Could not read image file: {file_path}")
                self.reset_state_for_new_image_or_camera()  # Resets field points, ball detections
                self._dynamic_scale_and_set_preview()
                self.current_hsv_combined_mask_display = (
                    self._generate_hsv_combined_mask_for_display()
                )  # Generate initial combined mask
                if (
                    self.calibration_window_open
                    and self.calibration_window
                    and self.calibration_window.winfo_exists()
                ):
                    self.calibration_window.refresh_all_mask_displays()
                self.run_full_detection_cycle(show_results_window=False)
            except Exception as e:
                messagebox.showerror(
                    "Image Error", f"Could not open or process image: {str(e)}"
                )
                self.img = None
                self.preview = None
                self.current_hsv_combined_mask_display = (
                    self._generate_hsv_combined_mask_for_display()
                )  # Generate blank
                self.update_main_canvas_display()

    def _dynamic_scale_and_set_preview(self):
        if self.img is None:
            self.preview = None
            self.PREVIEW_SCALE = 1.0
            return
        if not hasattr(self.root, "winfo_exists") or not self.root.winfo_exists():
            return
        self.root.update_idletasks()
        available_w = self.image_frame.winfo_width()
        available_h = self.image_frame.winfo_height()
        info_display_h_estimate = self.LOUPE_DIM + 10
        coord_h_estimate = 25
        target_canvas_h = available_h - info_display_h_estimate - coord_h_estimate - 20
        target_canvas_w = available_w - 20
        if target_canvas_w <= 1:
            target_canvas_w = 640
        if target_canvas_h <= 1:
            target_canvas_h = 480
        img_h_orig, img_w_orig = self.img.shape[:2]
        if img_w_orig == 0 or img_h_orig == 0:
            self.preview = self.img.copy()
            self.PREVIEW_SCALE = 1.0
            return
        scale_w = target_canvas_w / img_w_orig
        scale_h = target_canvas_h / img_h_orig
        self.PREVIEW_SCALE = min(scale_w, scale_h, 1.0)
        self.PREVIEW_SCALE = max(0.1, self.PREVIEW_SCALE)
        preview_w = max(1, int(img_w_orig * self.PREVIEW_SCALE))
        preview_h = max(1, int(img_h_orig * self.PREVIEW_SCALE))
        if preview_w > 0 and preview_h > 0:
            self.preview = cv2.resize(
                self.img, (preview_w, preview_h), interpolation=cv2.INTER_AREA
            )
        else:
            self.preview = None

    def open_camera(self):
        self.stop_camera_if_running()
        try:
            camera_indices_to_try = [0, 1, 2, 3, 4]
            opened_camera_index = -1
            self.cap = None
            for i in camera_indices_to_try:
                backend = cv2.CAP_DSHOW if sys.platform == "win32" else i
                temp_cap = cv2.VideoCapture(backend)
                if not temp_cap.isOpened() and backend != i:
                    temp_cap.release()
                    temp_cap = cv2.VideoCapture(i)
                if temp_cap.isOpened():
                    self.cap = temp_cap
                    opened_camera_index = i
                    break
                else:
                    if temp_cap:
                        temp_cap.release()
            if not self.cap or not self.cap.isOpened():
                raise ValueError("Could not open any camera.")

            # Attempt to set the highest possible resolution first
            desired_resolutions = [
                (3840, 2160),  # 4K UHD
                (2560, 1440),  # QHD (1440p)
                (1920, 1080),  # Full HD (1080p)
                (1600, 900),  # HD+
                (1280, 720),  # HD (720p)
                (1024, 768),  # XGA
                (800, 600),  # SVGA
                (640, 480),  # VGA
            ]

            successfully_set_resolution = False
            for w_d, h_d in desired_resolutions:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w_d)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h_d)
                # Allow some time for the camera to apply settings
                time.sleep(0.2)  # You might need to adjust this delay
                actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Check if the resolution was set successfully (some cameras might round or slightly adjust)
                # Allow a small tolerance, e.g., if the camera sets 1920x1088 instead of 1920x1080
                if abs(actual_w - w_d) <= 10 and abs(actual_h - h_d) <= 10:
                    print(
                        f"INFO: Camera resolution set to {actual_w}x{actual_h} (attempted {w_d}x{h_d})"
                    )
                    successfully_set_resolution = True
                    break  # Resolution set, exit loop
                else:
                    print(
                        f"INFO: Failed to set {w_d}x{h_d}. Current resolution: {actual_w}x{actual_h}"
                    )

            if not successfully_set_resolution:
                print(
                    f"WARNING: Could not set any of the preferred resolutions. Using default: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
                )

            self.camera_mode = True
            self.reset_state_for_new_image_or_camera()  #
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.img = frame.copy()
                if self.img is None or self.img.size == 0:
                    raise ValueError("Failed to get valid initial frame.")
                self.running = True
                self._dynamic_scale_and_set_preview()  #
                self.current_hsv_combined_mask_display = (
                    self._generate_hsv_combined_mask_for_display()
                )  # Initial mask
                self.camera_thread = threading.Thread(
                    target=self.update_camera_feed, daemon=True
                )  #
                self.camera_thread.start()
                if hasattr(self, "capture_btn"):
                    self.capture_btn.config(state=NORMAL)  #
            else:
                raise ValueError("Could not grab initial frame from camera.")
        except Exception as e:
            print(f"Error opening camera: {e}")
            traceback.print_exc()
            if self.cap:
                self.cap.release()
                self.cap = None
            self.running = False
            self.camera_mode = False
            if hasattr(self, "capture_btn"):
                self.capture_btn.config(state=DISABLED)  #
            messagebox.showerror(
                "Camera Error", f"Could not open/configure camera: {str(e)}"
            )
            self.img = None
            self.preview = None
            self.current_hsv_combined_mask_display = (
                self._generate_hsv_combined_mask_for_display()
            )  # Blank
            self.update_main_canvas_display()  #

    def update_camera_feed(self):
        last_error_report_time = 0
        error_report_interval = 5
        try:
            while self.running:
                if not (self.cap and self.cap.isOpened() and self.camera_mode):
                    break
                ret, frame = self.cap.read()
                if not self.running:
                    break
                if ret and frame is not None:
                    self.img = frame.copy()
                    if self.img is None or self.img.size == 0:
                        time.sleep(0.01)
                        continue
                    if (
                        not hasattr(self.root, "winfo_exists")
                        or not self.root.winfo_exists()
                    ):
                        break
                    self._dynamic_scale_and_set_preview()

                    ball_count = self.pymc3e.batchread_wordunits(headdevice="D130", readsize=2)

                    wordunits_values = self.pymc3e.batchread_wordunits(headdevice="M300", readsize=2)

                    if wordunits_values[0] != 0:
                        if ball_count[0] == 0:
                            self.red_team()
                        else:
                            self.detect_balls_in_frame()
                    else:
                        self.detect_balls_in_frame()

                    current_measurement_data = None
                    if len(self.field_pts) == 4:
                        if self.ball_detected and self.ball_pt1 is not None:
                            current_measurement_data = (
                                self.process_measurements_for_realtime()
                            )
                            if current_measurement_data:
                                if (
                                    hasattr(self.root, "after")
                                    and self.root.winfo_exists()
                                ):
                                    self.root.after(
                                        0,
                                        self.update_measurement_display,
                                        current_measurement_data,
                                    )
                                self.last_known_plc_distance = current_measurement_data[
                                    "distance_cm"
                                ]
                                self.last_known_plc_angle = current_measurement_data[
                                    "angle_degrees"
                                ]
                                current_swing = (
                                    self.last_known_plc_distance * 24.096
                                ) + 5900
                                current_swing = max(0, min(current_swing, 23000))
                                self.last_known_plc_swing_speed = current_swing
                                self.last_known_plc_release_speed = 800
                                self.has_last_known_plc_data = True
                                self.sent_last_data_after_disappearance = False
                                if self.plc_connected:
                                    self.send_data_to_plc(
                                        self.last_known_plc_distance,
                                        self.last_known_plc_angle,
                                        self.last_known_plc_swing_speed,
                                        self.last_known_plc_release_speed,
                                    )
                        else:
                            if hasattr(self.root, "after") and self.root.winfo_exists():
                                self.root.after(
                                    0, self.update_measurement_display_default
                                )
                            if (
                                self.has_last_known_plc_data
                                and not self.sent_last_data_after_disappearance
                            ):
                                if self.plc_connected:
                                    self.send_data_to_plc(
                                        self.last_known_plc_distance,
                                        self.last_known_plc_angle,
                                        self.last_known_plc_swing_speed,
                                        self.last_known_plc_release_speed,
                                    )
                                    self.sent_last_data_after_disappearance = True
                    else:
                        if hasattr(self.root, "after") and self.root.winfo_exists():
                            self.root.after(0, self.update_measurement_display_default)
                    if hasattr(self.root, "after") and self.root.winfo_exists():
                        self.root.after(0, self.update_main_canvas_display_from_thread)
                else:
                    current_time = time.time()
                    if current_time - last_error_report_time > error_report_interval:
                        last_error_report_time = current_time
                    time.sleep(0.05)
                time.sleep(0.02)
        except Exception as e_outer:
            if (
                self.running
                and "application has been destroyed" not in str(e_outer).lower()
                and "invalid command name" not in str(e_outer).lower()
            ):
                print(f"CRITICAL ERROR in camera feed: {e_outer}")
                traceback.print_exc()
        finally:
            if (
                hasattr(self.root, "winfo_exists")
                and self.root.winfo_exists()
                and hasattr(self.root, "after")
            ):
                self.root.after(0, self.handle_camera_thread_exit)

    def stop_camera_if_running(self):
        self.running = False
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=0.5)
        self.camera_thread = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.camera_mode = False
        if hasattr(self, "capture_btn") and self.capture_btn.winfo_exists():
            self.capture_btn.config(state=DISABLED)

    def capture_frame(self):
        if self.camera_mode and self.img is not None:
            self.run_full_detection_cycle(show_results_window=True)
        elif not self.camera_mode and self.img is not None:
            self.run_full_detection_cycle(show_results_window=True)
        else:
            messagebox.showwarning(
                "Capture Frame", "Camera not active or no image loaded."
            )

    def update_main_canvas_display_from_thread(self):
        if (
            self.preview is not None
            and hasattr(self.canvas, "winfo_exists")
            and self.canvas.winfo_exists()
        ):
            self.update_main_canvas_display()
        elif (
            self.img is None
            and hasattr(self.canvas, "winfo_exists")
            and self.canvas.winfo_exists()
        ):
            self.update_main_canvas_display()

    def handle_camera_thread_exit(self):
        if hasattr(self, "capture_btn") and self.capture_btn.winfo_exists():
            self.capture_btn.config(state=DISABLED)
        self.update_measurement_display_default()

    def detect_balls_in_frame(self):
        if self.img is None or self.img.size == 0:
            self.ball_pt1 = None
            self.ball_all = []
            self.point_in_trapezoid(x, y, )
            self.ball_detected = False
            self.current_hsv_combined_mask_display = (
                self._generate_hsv_combined_mask_for_display()
            )  # Generate blank
            if hasattr(self, "ball_status_str"):
                self.ball_status_str.set("Ball: No image")
            return

        # Generate the colored HSV combined mask for display first
        self.current_hsv_combined_mask_display = (
            self._generate_hsv_combined_mask_for_display()
        )

        # Continue with actual ball detection logic
        img_for_detection = self.img.copy()
        field_mask_applied = False
        field_mask_cv = None
        if len(self.field_pts) == 4:
            field_mask_cv = np.zeros(self.img.shape[:2], dtype=np.uint8)
            try:
                pts_for_poly = np.array(
                    [
                        self.field_pts[0],
                        self.field_pts[1],
                        self.field_pts[3],
                        self.field_pts[2],
                    ],
                    dtype=np.int32,
                )
                cv2.fillPoly(field_mask_cv, [pts_for_poly], 255)
                img_for_detection = cv2.bitwise_and(
                    img_for_detection, img_for_detection, mask=field_mask_cv
                )
                field_mask_applied = True
            except Exception as e:
                print(f"Error creating field mask: {e}")

        self.ball_pt1 = None
        self.ball_detected = False
        all_detected_objects_for_nms = []
        blur_k = self.active_detection_params.get("blur_kernel", 11)
        if blur_k < 3:
            blur_k = 3
        if blur_k % 2 == 0:
            blur_k = max(3, blur_k - 1)

        blurred = cv2.GaussianBlur(img_for_detection, (blur_k, blur_k), 0)
        hsv_blurred = cv2.cvtColor(
            blurred, cv2.COLOR_BGR2HSV
        )  # Use blurred for detection

        best_hsv_white_ball_for_primary = None
        highest_primary_white_metric = -1.0
        wp = self.active_detection_params["colors"].get("white", {})
        primary_white_min_radius = wp.get("primary_min_radius", 7)
        primary_white_circularity_thresh = wp.get("primary_circularity", 0.65)

        for color_name_detect, color_params_dict in self.active_detection_params[
            "colors"
        ].items():
            hsv_ranges_list = color_params_dict.get("hsv_ranges", [])
            if not hsv_ranges_list:
                continue

            current_color_binary_mask_detect = np.zeros(
                hsv_blurred.shape[:2], dtype=np.uint8
            )
            for lower_hsv_np, upper_hsv_np in hsv_ranges_list:
                temp_lower_det = np.array(lower_hsv_np, dtype=np.uint8)
                temp_upper_det = np.array(upper_hsv_np, dtype=np.uint8)

                # Validate and adjust HSV range values for detection (like in CalibrationWindow)
                if not (
                    color_name_detect == "red" and temp_lower_det[0] > temp_upper_det[0]
                ):
                    if temp_upper_det[0] < temp_lower_det[0]:
                        temp_upper_det[0] = temp_lower_det[0]
                if temp_upper_det[1] < temp_lower_det[1]:
                    temp_upper_det[1] = temp_lower_det[1]
                if temp_upper_det[2] < temp_lower_det[2]:
                    temp_upper_det[2] = temp_lower_det[2]

                individual_mask_segment_det = np.zeros(
                    hsv_blurred.shape[:2], dtype=np.uint8
                )
                if color_name_detect == "red" and temp_lower_det[0] > temp_upper_det[0]:
                    m1_det = cv2.inRange(
                        hsv_blurred,
                        np.array([0, temp_lower_det[1], temp_lower_det[2]]),
                        temp_upper_det,
                    )
                    m2_det = cv2.inRange(
                        hsv_blurred,
                        temp_lower_det,
                        np.array([179, temp_upper_det[1], temp_upper_det[2]]),
                    )
                    individual_mask_segment_det = cv2.bitwise_or(m1_det, m2_det)
                else:
                    individual_mask_segment_det = cv2.inRange(
                        hsv_blurred, temp_lower_det, temp_upper_det
                    )
                current_color_binary_mask_detect = cv2.bitwise_or(
                    current_color_binary_mask_detect, individual_mask_segment_det
                )

            # Morphological operations for detection (from params)
            open_k = color_params_dict.get("morph_open_k", 5)
            open_iter = color_params_dict.get("morph_open_iter", 1)
            close_k = color_params_dict.get("morph_close_k", 5)
            dilate_k = color_params_dict.get("morph_dilate_k", 5)
            dilate_iter = color_params_dict.get("morph_dilate_iter", 1)
            close_iter_val = color_params_dict.get(
                "morph_close_iter", 2 if color_name_detect == "white" else 1
            )

            if open_k < 3:
                open_k = 3
            if open_k % 2 == 0:
                open_k += 1
            if close_k < 3:
                close_k = 3
            if close_k % 2 == 0:
                close_k += 1
            if dilate_k < 3:
                dilate_k = 3
            if dilate_k % 2 == 0:
                dilate_k += 1

            morph_mask_detect = current_color_binary_mask_detect
            if open_iter > 0:
                morph_mask_detect = cv2.morphologyEx(
                    morph_mask_detect,
                    cv2.MORPH_OPEN,
                    np.ones((open_k, open_k), np.uint8),
                    iterations=open_iter,
                )
            if color_name_detect in ["red", "blue"] and dilate_iter > 0:
                morph_mask_detect = cv2.dilate(
                    morph_mask_detect,
                    np.ones((dilate_k, dilate_k), np.uint8),
                    iterations=dilate_iter,
                )
            if close_iter_val > 0:
                morph_mask_detect = cv2.morphologyEx(
                    morph_mask_detect,
                    cv2.MORPH_CLOSE,
                    np.ones((close_k, close_k), np.uint8),
                    iterations=close_iter_val,
                )

            contours_hsv, _ = cv2.findContours(
                morph_mask_detect, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            min_area = color_params_dict.get("area_min", 100)
            max_area = color_params_dict.get("area_max", 50000)
            circ_thresh = color_params_dict.get("circularity", 0.7)
            solidity_thresh = color_params_dict.get("solidity", 0.7)

            for cnt in contours_hsv:
                area = cv2.contourArea(cnt)
                if not (min_area <= area <= max_area):
                    continue
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0
                if circularity >= circ_thresh and solidity >= solidity_thresh:
                    class_id = {"white": 1, "red": 2, "blue": 0}.get(
                        color_name_detect, -1
                    )
                    confidence = (
                        circularity * 0.5
                        + solidity * 0.3
                        + min(1.0, area / (max_area if max_area > 0 else area + 1))
                        * 0.2
                    )
                    current_detected_ball = {
                        "bbox": (
                            int(x - radius),
                            int(y - radius),
                            int(x + radius),
                            int(y + radius),
                        ),
                        "confidence": confidence,
                        "class": class_id,
                        "center": (int(x), int(y)),
                        "radius": int(radius),
                        "color_name": color_name_detect,
                        "circularity": circularity,
                        "solidity": solidity,
                        "area": area,
                    }
                    all_detected_objects_for_nms.append(current_detected_ball)
                    if color_name_detect == "white":
                        current_primary_white_circ_thresh = wp.get(
                            "primary_circularity", primary_white_circularity_thresh
                        )
                        current_primary_white_min_radius = wp.get(
                            "primary_min_radius", primary_white_min_radius
                        )
                        if (
                            circularity >= current_primary_white_circ_thresh
                            and radius >= current_primary_white_min_radius
                        ):
                            metric = circularity * 1000 + radius
                            if metric > highest_primary_white_metric:
                                highest_primary_white_metric = metric
                                best_hsv_white_ball_for_primary = current_detected_ball

        if best_hsv_white_ball_for_primary:
            self.ball_pt1 = best_hsv_white_ball_for_primary["center"]
            self.ball_detected = True
            if hasattr(self, "ball_status_str"):
                self.ball_status_str.set(
                    f"Ball: Found (C:{best_hsv_white_ball_for_primary['circularity']:.2f} S:{best_hsv_white_ball_for_primary['solidity']:.2f} R:{best_hsv_white_ball_for_primary['radius']})"
                )
        else:
            self.ball_pt1 = None
            self.ball_detected = False
            if hasattr(self, "ball_status_str"):
                self.ball_status_str.set("Ball: Not found")

        boxes_for_nms = []
        confidences_for_nms = []
        indices_orig = []
        for i, det in enumerate(all_detected_objects_for_nms):
            x1, y1, x2, y2 = det["bbox"]
            boxes_for_nms.append([x1, y1, x2 - x1, y2 - y1])
            confidences_for_nms.append(det["confidence"])
            indices_orig.append(i)
        self.ball_all = []
        if len(boxes_for_nms) > 0:
            nms_indices = cv2.dnn.NMSBoxes(
                boxes_for_nms,
                np.array(confidences_for_nms).astype(np.float32),
                score_threshold=self.active_detection_params.get(
                    "detection_threshold_nms", 0.01
                ),
                nms_threshold=self.active_detection_params.get(
                    "nms_overlap_threshold", 0.4
                ),
            )
            if isinstance(nms_indices, np.ndarray):
                if nms_indices.ndim > 1:
                    nms_indices = nms_indices.flatten()
                self.ball_all = [
                    all_detected_objects_for_nms[indices_orig[i]] for i in nms_indices
                ]
        if self.ball_detected and best_hsv_white_ball_for_primary:
            is_primary_in_all = any(
                b_all["center"] == best_hsv_white_ball_for_primary["center"]
                and b_all["color_name"] == "white"
                for b_all in self.ball_all
            )
            if not is_primary_in_all:
                self.ball_all.append(best_hsv_white_ball_for_primary)

    def update_main_canvas_display(self):
        if self.preview is None:  # Also handles self.img is None case
            if hasattr(self.canvas, "winfo_exists") and self.canvas.winfo_exists():
                self.canvas.delete("all")
                cv_w = self.canvas.winfo_width()
                cv_h = self.canvas.winfo_height()
                if cv_w <= 1 or cv_h <= 1:
                    try:
                        cv_w = int(self.canvas.cget("width"))
                        cv_h = int(self.canvas.cget("height"))
                    except:
                        cv_w, cv_h = 640, 480
                if cv_w > 1 and cv_h > 1:
                    self.canvas.create_text(
                        cv_w // 2,
                        cv_h // 2,
                        text="No image / Camera off",
                        font=("Arial", 16),
                    )

            # Clear combined_mask_label if no preview/image
            if (
                hasattr(self.combined_mask_label, "winfo_exists")
                and self.combined_mask_label.winfo_exists()
            ):
                # Use the current self.current_hsv_combined_mask_display which should be blank if img is None
                blank_mask_for_tk = cv2.resize(
                    self.current_hsv_combined_mask_display,
                    (self.LOUPE_DIM, self.LOUPE_DIM),
                    interpolation=cv2.INTER_NEAREST,
                )
                blank_mask_rgb = cv2.cvtColor(
                    blank_mask_for_tk, cv2.COLOR_BGR2RGB
                )  # Assuming it's BGR
                blank_pil = Image.fromarray(blank_mask_rgb)
                self.combined_mask_photo = ImageTk.PhotoImage(image=blank_pil)
                self.combined_mask_label.config(image=self.combined_mask_photo)
            return

        preview_to_draw_on = self.preview.copy()
        for i, pt_orig_coords in enumerate(self.field_pts):
            x_prev = int(pt_orig_coords[0] * self.PREVIEW_SCALE)
            y_prev = int(pt_orig_coords[1] * self.PREVIEW_SCALE)
            cv2.circle(preview_to_draw_on, (x_prev, y_prev), 5, (0, 255, 0), -1)
            cv2.putText(
                preview_to_draw_on,
                str(i + 1),
                (x_prev + 7, y_prev + 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )
        display_ball_colors = {
            "white": (230, 230, 230),
            "red": (0, 0, 255),
            "blue": (255, 100, 100),
            "default": (0, 255, 0),
        }
        for det_ball in self.ball_all:
            center_orig = det_ball["center"]
            radius_orig = det_ball["radius"]
            color_name = det_ball["color_name"]
            center_prev = (
                int(center_orig[0] * self.PREVIEW_SCALE),
                int(center_orig[1] * self.PREVIEW_SCALE),
            )
            radius_prev = int(max(3, radius_orig * self.PREVIEW_SCALE))
            draw_color = display_ball_colors.get(
                color_name, display_ball_colors["default"]
            )
            cv2.circle(preview_to_draw_on, center_prev, radius_prev, draw_color, 2)
            label_text = f"{color_name[0].upper()}"
            cv2.putText(
                preview_to_draw_on,
                label_text,
                (
                    center_prev[0] - radius_prev // 2 + 3,
                    center_prev[1] - radius_prev - 5,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                draw_color,
                1,
            )
        if self.ball_detected and self.ball_pt1:
            x_ball_prev = int(self.ball_pt1[0] * self.PREVIEW_SCALE)
            y_ball_prev = int(self.ball_pt1[1] * self.PREVIEW_SCALE)
            cv2.circle(
                preview_to_draw_on, (x_ball_prev, y_ball_prev), 10, (255, 255, 0), 2
            )
            cv2.putText(
                preview_to_draw_on,
                "P1",
                (x_ball_prev + 12, y_ball_prev - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 0),
                2,
            )
        preview_rgb = cv2.cvtColor(preview_to_draw_on, cv2.COLOR_BGR2RGB)
        img_pil_canvas = Image.fromarray(preview_rgb)
        self.canvas_photo = ImageTk.PhotoImage(image=img_pil_canvas)
        if hasattr(self.canvas, "winfo_exists") and self.canvas.winfo_exists():
            self.canvas.create_image(0, 0, anchor=NW, image=self.canvas_photo)

        # Update the combined_mask_label with the new colored HSV combined mask
        if (
            hasattr(self, "current_hsv_combined_mask_display")
            and self.current_hsv_combined_mask_display is not None
            and self.current_hsv_combined_mask_display.size > 0
        ):
            try:
                mask_resized_for_tk = cv2.resize(
                    self.current_hsv_combined_mask_display,
                    (self.LOUPE_DIM, self.LOUPE_DIM),
                    interpolation=cv2.INTER_NEAREST,
                )
                mask_rgb_for_tk = cv2.cvtColor(
                    mask_resized_for_tk, cv2.COLOR_BGR2RGB
                )  # Is BGR from generation
                mask_pil_for_tk = Image.fromarray(mask_rgb_for_tk)
                self.combined_mask_photo = ImageTk.PhotoImage(image=mask_pil_for_tk)
                if (
                    hasattr(self.combined_mask_label, "winfo_exists")
                    and self.combined_mask_label.winfo_exists()
                ):
                    self.combined_mask_label.config(image=self.combined_mask_photo)
            except Exception as e:
                if (
                    hasattr(self.combined_mask_label, "winfo_exists")
                    and self.combined_mask_label.winfo_exists()
                ):
                    blank_mask_img = Image.new(
                        "RGB", (self.LOUPE_DIM, self.LOUPE_DIM), color="grey"
                    )
                    self.combined_mask_photo = ImageTk.PhotoImage(image=blank_mask_img)
                    self.combined_mask_label.config(image=self.combined_mask_photo)
        else:
            if (
                hasattr(self.combined_mask_label, "winfo_exists")
                and self.combined_mask_label.winfo_exists()
            ):
                blank_mask_img = Image.new(
                    "RGB", (self.LOUPE_DIM, self.LOUPE_DIM), color="black"
                )
                self.combined_mask_photo = ImageTk.PhotoImage(image=blank_mask_img)
                self.combined_mask_label.config(image=self.combined_mask_photo)

    def add_point(self, event):
        if self.img is None or self.preview is None:
            messagebox.showwarning("Add Point", "No image loaded.")
            return
        if not (
            0 <= event.x < self.preview.shape[1]
            and 0 <= event.y < self.preview.shape[0]
        ):
            return
        if len(self.field_pts) < 4:
            X_orig = int(event.x / self.PREVIEW_SCALE)
            Y_orig = int(event.y / self.PREVIEW_SCALE)
            if not (
                0 <= X_orig < self.img.shape[1] and 0 <= Y_orig < self.img.shape[0]
            ):
                return
            self.field_pts.append((X_orig, Y_orig))
            self.corner_listbox.insert(
                END, f"P{len(self.field_pts)}: ({X_orig}, {Y_orig})"
            )
            if len(self.field_pts) == 4:
                self.has_last_known_plc_data = False
                self.sent_last_data_after_disappearance = False
                if self.img is not None and not self.camera_mode:
                    self.run_full_detection_cycle(show_results_window=False)
            else:
                self.update_main_canvas_display()
        else:
            messagebox.showinfo(
                "Add Point", "4 field corners already selected. Clear to reselect."
            )

    def remove_last_point(self):
        if self.field_pts:
            self.field_pts.pop()
            self.corner_listbox.delete(END)
            if len(self.field_pts) < 4:
                self.ball_pt1 = None
                self.ball_all = []
                self.ball_detected = False
                self.current_hsv_combined_mask_display = (
                    self._generate_hsv_combined_mask_for_display()
                )  # Update mask
                self.ball_status_str.set("Ball: Select 4 corners")
                self.update_measurement_display_default()
                self.has_last_known_plc_data = False
            self.update_main_canvas_display()
        else:
            messagebox.showinfo("Remove Point", "No points to remove.")

    def clear_points(self):
        if not self.field_pts:
            messagebox.showinfo("Clear Points", "No points to clear.")
            return
        if messagebox.askyesno("Confirm Clear", "Clear all field corner points?"):
            self.field_pts = []
            self.corner_listbox.delete(0, END)
            self.ball_pt1 = None
            self.ball_all = []
            self.ball_detected = False
            self.current_hsv_combined_mask_display = (
                self._generate_hsv_combined_mask_for_display()
            )  # Update mask
            self.ball_status_str.set("Ball: Select 4 corners")
            self.update_main_canvas_display()
            self.update_measurement_display_default()
            self.has_last_known_plc_data = False

    def _float_to_rounded_int_word_list(self, float_val, value_name="value"):
        try:
            if float_val is None or math.isnan(float_val) or math.isinf(float_val):
                return [0]
            rounded_int_val = int(round(float_val))
            if not (self.MIN_16BIT_SIGNED <= rounded_int_val <= self.MAX_16BIT_SIGNED):
                rounded_int_val = max(
                    self.MIN_16BIT_SIGNED, min(self.MAX_16BIT_SIGNED, rounded_int_val)
                )
            return [rounded_int_val]
        except (ValueError, TypeError):
            return [0]

    def send_data_to_plc(
        self, distance_val, angle_val, swing_speed_val, release_speed_val
    ):
        if not self.plc_connected or not self.pymc3e:
            return
        try:
            dist_s = self._float_to_rounded_int_word_list(distance_val, "distance")[0]
            angle_s = self._float_to_rounded_int_word_list(angle_val, "angle")[0]
            swing_s = self._float_to_rounded_int_word_list(
                swing_speed_val, "swing_speed"
            )[0]
            release_s = self._float_to_rounded_int_word_list(
                release_speed_val, "release_speed"
            )[0]

            # Corrected call to randomwrite:
            self.pymc3e.randomwrite(
                word_devices=["D1", "D120", "D106", "D108"],
                word_values=[dist_s, angle_s, swing_s, release_s],
                dword_devices=[],  # Provide empty list for dword_devices
                dword_values=[],
            )  # Provide empty list for dword_values

            self._update_plc_gui_status("Data Sent", "green")
        except Exception as e:
            print(f"ERROR: PLC write error: {e}")
            self.plc_connected = False
            self._update_plc_gui_status(f"Write Fail", "red")

    def process_measurements_for_realtime(self):

        if not self.ball_detected or self.ball_pt1 is None or len(self.field_pts) != 4:
            return None
        src_pts = np.float32(self.field_pts)
        dst_pts = np.float32(
            [
                [0, 0],
                [0, self.FIELD_H_CM],
                [self.FIELD_W_CM, 0],
                [self.FIELD_W_CM, self.FIELD_H_CM],
            ]
        )

        try:
            H_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            if H_matrix is None:
                return None
        except Exception:
            return None
        ball1_pixels_np = np.float32([self.ball_pt1]).reshape(-1, 1, 2)
        ball1_cm_transformed = cv2.perspectiveTransform(ball1_pixels_np, H_matrix)
        if ball1_cm_transformed is None or ball1_cm_transformed.size == 0:
            return None
        x1_cm, y1_cm = ball1_cm_transformed[0, 0]
        try:
            x2_cm_str = self.target_x_cm_str.get()
            y2_cm_str = self.target_y_cm_str.get()
            if not x2_cm_str or not y2_cm_str:
                x2_cm, y2_cm = 0.0, 0.0
            else:
                x2_cm = float(x2_cm_str)
                y2_cm = float(y2_cm_str)
        except ValueError:
            x2_cm, y2_cm = 0.0, 0.0
        delta_x_cm = x2_cm - x1_cm
        delta_y_cm = y2_cm - y1_cm
        distance_cm = math.sqrt(delta_x_cm**2 + delta_y_cm**2)
        angle_radians = math.atan2(delta_x_cm, delta_y_cm)
        angle_degrees = math.degrees(angle_radians)
        if angle_degrees < 0:
            angle_degrees += 360.0
        return {
            "x1_cm": x1_cm,
            "y1_cm": y1_cm,
            "x2_cm": x2_cm,
            "y2_cm": y2_cm,
            "distance_cm": distance_cm,
            "angle_degrees": angle_degrees,
            "ball1_original_px": self.ball_pt1,
        }

    def update_measurement_display(self, data):
        if data and isinstance(data, dict):
            dist_cm = data.get("distance_cm", None)
            angle_deg = data.get("angle_degrees", None)
            if dist_cm is not None:
                self.distance_display_str.set(f"Distance: {dist_cm:.1f} cm")
            else:
                self.distance_display_str.set("Distance: Error")
            if angle_deg is not None:
                self.angle_display_str.set(f"Angle: {angle_deg:.1f}°")
            else:
                self.angle_display_str.set("Angle: Error")
        else:
            self.update_measurement_display_default()

    def update_measurement_display_default(self):
        self.distance_display_str.set("Distance: N/A")
        self.angle_display_str.set("Angle: N/A")

    def run_full_detection_cycle(self, show_results_window=False):
        if self.img is None:
            if not show_results_window:
                messagebox.showwarning("Detection Error", "No image loaded.")
            self.ball_status_str.set("Ball: No Image")
            self.current_hsv_combined_mask_display = (
                self._generate_hsv_combined_mask_for_display()
            )  # Blank
            self.update_main_canvas_display()
            return
        self.detect_balls_in_frame()
        self.update_main_canvas_display()
        measurement_data = None
        if len(self.field_pts) == 4:
            if self.ball_detected and self.ball_pt1 is not None:
                measurement_data = self.process_measurements_for_realtime()
                if measurement_data:
                    self.update_measurement_display(measurement_data)
                    self.last_known_plc_distance = measurement_data["distance_cm"]
                    self.last_known_plc_angle = measurement_data["angle_degrees"]
                    current_swing = (self.last_known_plc_distance * 24.096) + 5900
                    current_swing = max(0, min(current_swing, 23000))
                    self.last_known_plc_swing_speed = current_swing
                    self.last_known_plc_release_speed = 800
                    self.has_last_known_plc_data = True
                    self.sent_last_data_after_disappearance = False
                    if self.plc_connected and not self.camera_mode:
                        self.send_data_to_plc(
                            self.last_known_plc_distance,
                            self.last_known_plc_angle,
                            self.last_known_plc_swing_speed,
                            self.last_known_plc_release_speed,
                        )
                else:
                    self.update_measurement_display_default()
            else:
                self.update_measurement_display_default()
                if (
                    self.has_last_known_plc_data
                    and not self.sent_last_data_after_disappearance
                ):
                    if self.plc_connected and not self.camera_mode:
                        self.send_data_to_plc(
                            self.last_known_plc_distance,
                            self.last_known_plc_angle,
                            self.last_known_plc_swing_speed,
                            self.last_known_plc_release_speed,
                        )
                        self.sent_last_data_after_disappearance = True
        else:
            self.update_measurement_display_default()
            if not self.camera_mode and not show_results_window:
                pass
        if show_results_window:
            if len(self.field_pts) != 4:
                messagebox.showwarning(
                    "Results Error",
                    "4 field corners must be selected to show detailed results.",
                )
                return
            if not self.ball_detected or self.ball_pt1 is None:
                messagebox.showwarning(
                    "Results Error",
                    "Primary white ball not detected. Cannot show detailed results.",
                )
                return
            if measurement_data is None:
                measurement_data = self.process_measurements_for_realtime()
            if measurement_data:
                self.show_detailed_results_window(measurement_data)
            else:
                messagebox.showerror(
                    "Results Error",
                    "Could not process measurements for detail view. Check target values and field setup.",
                )

    def show_detailed_results_window(self, measurement_data):
        if not measurement_data or not isinstance(measurement_data, dict):
            return
        x1_cm = measurement_data.get("x1_cm")
        y1_cm = measurement_data.get("y1_cm")
        x2_cm = measurement_data.get("x2_cm")
        y2_cm = measurement_data.get("y2_cm")
        dist_cm = measurement_data.get("distance_cm")
        angle_deg = measurement_data.get("angle_degrees")
        ball1_px = measurement_data.get("ball1_original_px")
        if any(
            v is None
            for v in [x1_cm, y1_cm, x2_cm, y2_cm, dist_cm, angle_deg, ball1_px]
        ):
            messagebox.showerror(
                "Results Data Error", "Incomplete data for detailed results view."
            )
            return
        src_pts = np.float32(self.field_pts)
        dst_pts = np.float32(
            [
                [0, 0],
                [0, self.FIELD_H_CM],
                [self.FIELD_W_CM, 0],
                [self.FIELD_W_CM, self.FIELD_H_CM],
            ]
        )
        try:
            H_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            if H_matrix is None:
                raise ValueError("H_matrix is None")
        except Exception as e:
            messagebox.showerror(
                "Perspective Error",
                f"Error creating perspective transform for results view: {e}",
            )
            return
        warp_w_px, warp_h_px = int(self.FIELD_W_CM), int(self.FIELD_H_CM)
        max_disp_dim = 600
        disp_scale_f = 1.0
        if warp_w_px <= 0 or warp_h_px <= 0:
            messagebox.showerror(
                "Field Error",
                "Field width/height in cm must be positive for results view.",
            )
            return
        if warp_w_px > max_disp_dim or warp_h_px > max_disp_dim:
            disp_scale_f = min(max_disp_dim / warp_w_px, max_disp_dim / warp_h_px)
        disp_w = max(1, int(warp_w_px * disp_scale_f))
        disp_h = max(1, int(warp_h_px * disp_scale_f))
        if self.img is None:
            messagebox.showerror(
                "Image Error", "Original image not available for results view."
            )
            return
        warped_native = cv2.warpPerspective(self.img, H_matrix, (warp_w_px, warp_h_px))
        if warped_native is None or warped_native.size == 0:
            messagebox.showerror("Warp Error", "Failed to warp image for results view.")
            return
        pt1_d = (int(x1_cm * disp_scale_f), int(y1_cm * disp_scale_f))
        pt2_d = (int(x2_cm * disp_scale_f), int(y2_cm * disp_scale_f))
        warped_disp_bgr = cv2.resize(
            warped_native, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR
        )
        cv2.circle(
            warped_disp_bgr, pt1_d, max(3, int(6 * disp_scale_f)), (0, 0, 255), -1
        )
        cv2.putText(
            warped_disp_bgr,
            "P1",
            (pt1_d[0] + 5, pt1_d[1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5 * disp_scale_f,
            (255, 255, 255),
            max(1, int(1 * disp_scale_f)),
        )
        cv2.circle(
            warped_disp_bgr, pt2_d, max(3, int(6 * disp_scale_f)), (0, 255, 0), -1
        )
        cv2.putText(
            warped_disp_bgr,
            "T",
            (pt2_d[0] + 5, pt2_d[1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5 * disp_scale_f,
            (255, 255, 255),
            max(1, int(1 * disp_scale_f)),
        )
        cv2.arrowedLine(
            warped_disp_bgr,
            pt1_d,
            pt2_d,
            (255, 255, 255),
            max(1, int(2 * disp_scale_f)),
        )
        res_win = Toplevel(self.root)
        res_win.title("Measurement Results & Top View")
        res_win.grab_set()
        warped_rgb_disp = cv2.cvtColor(warped_disp_bgr, cv2.COLOR_BGR2RGB)
        img_pil_res = Image.fromarray(warped_rgb_disp)
        res_win.top_view_photo_ref = ImageTk.PhotoImage(image=img_pil_res)
        Label(
            res_win, text="Field Top View (Scaled to Display)", font=("Arial", 12)
        ).pack(pady=5)
        Label(res_win, image=res_win.top_view_photo_ref).pack(pady=10, padx=10)
        res_frame = Frame(res_win)
        res_frame.pack(pady=10, padx=10, fill=X)
        Label(
            res_frame, text=f"P1 Original Pixel Coords: {ball1_px}", font=("Arial", 10)
        ).pack(anchor=W)
        Label(
            res_frame,
            text=f"P1 Field Coords (cm): ({x1_cm:.1f}, {y1_cm:.1f})",
            font=("Arial", 10, "bold"),
        ).pack(anchor=W)
        Label(
            res_frame,
            text=f"Target Field Coords (cm): ({x2_cm:.1f}, {y2_cm:.1f})",
            font=("Arial", 10),
        ).pack(anchor=W)
        ttk.Separator(res_frame, orient="horizontal").pack(fill="x", pady=5)
        Label(
            res_frame,
            text=f"Distance to Target: {dist_cm:.1f} cm",
            font=("Arial", 12, "bold"),
        ).pack(anchor=W)
        Label(
            res_frame,
            text=f"Angle to Target (from +Y, CW): {angle_deg:.1f}°",
            font=("Arial", 12, "bold"),
        ).pack(anchor=W)
        Button(res_win, text="Close", command=res_win.destroy, width=10).pack(pady=10)
        res_win.resizable(False, False)

    def open_calibration_window(self):
        if self.img is None:
            messagebox.showwarning(
                "Calibration", "Open an image or start camera feed first."
            )
            return
        if self.calibration_window_open and self.calibration_window:
            try:
                if self.calibration_window.winfo_exists():
                    self.calibration_window.lift()
                    self.calibration_window.refresh_all_mask_displays()
                    return
                else:
                    self.calibration_window_open = False
                    self.calibration_window = None
            except TclError:
                self.calibration_window_open = False
                self.calibration_window = None
        self.calibration_window = CalibrationWindow(self)
        self.calibration_window_open = True

    def initiate_hsv_color_pick_for_params(self, color_name):
        if self.img is None:
            messagebox.showwarning(
                "Color Pick", f"Open image/camera to pick {color_name} for parameters."
            )
            return
        if self.STATUS_CLICK_COLOR_INFO_MODE:
            self.toggle_info_color_pick_mode()
        current_picking_color = getattr(self, "picking_hsv_for_color", None)
        if current_picking_color is not None and current_picking_color == color_name:
            self.canvas.config(cursor="")
            self.picking_hsv_for_color = None
            return
        self.picking_hsv_for_color = color_name
        self.canvas.config(cursor="plus")
        messagebox.showinfo(
            "Pick Color for Params",
            f"Click on a {color_name} ball in the main image to set its HSV parameters for Advanced Calibration. Click the '{color_name.capitalize()}' button again to cancel.",
        )

    def process_hsv_color_pick(self, event):
        if (
            self.preview is None
            or not hasattr(self, "picking_hsv_for_color")
            or self.picking_hsv_for_color is None
        ):
            if hasattr(self, "picking_hsv_for_color") and self.picking_hsv_for_color:
                pass
            self.canvas.config(cursor="")
            self.picking_hsv_for_color = None
            return
        color_name_picked = self.picking_hsv_for_color
        self.canvas.config(cursor="")
        self.picking_hsv_for_color = None
        if not (
            0 <= event.x < self.preview.shape[1]
            and 0 <= event.y < self.preview.shape[0]
        ):
            messagebox.showwarning(
                "Color Pick Error", "Clicked outside of the image preview area."
            )
            return
        X_orig = int(event.x / self.PREVIEW_SCALE)
        Y_orig = int(event.y / self.PREVIEW_SCALE)
        if not (0 <= X_orig < self.img.shape[1] and 0 <= Y_orig < self.img.shape[0]):
            messagebox.showwarning(
                "Color Pick Error",
                "Clicked outside original image bounds after scaling.",
            )
            return
        patch_size = self.color_pick_patch_size_var.get()
        if patch_size % 2 == 0:
            patch_size = max(3, patch_size + 1)
        half_patch = patch_size // 2
        y_s = max(0, Y_orig - half_patch)
        y_e = min(self.img.shape[0], Y_orig + half_patch + 1)
        x_s = max(0, X_orig - half_patch)
        x_e = min(self.img.shape[1], X_orig + half_patch + 1)
        bgr_patch = self.img[y_s:y_e, x_s:x_e]
        if bgr_patch.size == 0:
            messagebox.showwarning("Color Pick Error", "Selected patch is empty.")
            return
        hsv_patch = cv2.cvtColor(bgr_patch, cv2.COLOR_BGR2HSV)
        h_p = int(np.median(hsv_patch[:, :, 0]))
        s_p = int(np.median(hsv_patch[:, :, 1]))
        v_p = int(np.median(hsv_patch[:, :, 2]))
        target_color_params = self.active_detection_params["colors"][color_name_picked]
        if color_name_picked == "white":
            picked_hsv_lower = np.array([0, 0, max(120, v_p - 50)])
            picked_hsv_upper = np.array([179, min(80, s_p + 40), 255])
            target_color_params["hsv_ranges"] = [(picked_hsv_lower, picked_hsv_upper)]
        elif color_name_picked == "red":
            h_delta = 10
            s_delta = 70
            v_delta = 70
            s_min_thresh, v_min_thresh = 50, 50
            if h_p < h_delta:
                lower1 = np.array(
                    [
                        0,
                        max(s_min_thresh, s_p - s_delta),
                        max(v_min_thresh, v_p - v_delta),
                    ]
                )
                upper1 = np.array(
                    [h_p + h_delta, min(255, s_p + s_delta), min(255, v_p + v_delta)]
                )
                lower2 = np.array(
                    [
                        max(0, 179 - (h_delta - h_p)),
                        max(s_min_thresh, s_p - s_delta),
                        max(v_min_thresh, v_p - v_delta),
                    ]
                )
                upper2 = np.array(
                    [179, min(255, s_p + s_delta), min(255, v_p + v_delta)]
                )
                target_color_params["hsv_ranges"] = [(lower1, upper1), (lower2, upper2)]
            elif h_p > (179 - h_delta):
                lower1 = np.array(
                    [
                        max(0, h_p - h_delta),
                        max(s_min_thresh, s_p - s_delta),
                        max(v_min_thresh, v_p - v_delta),
                    ]
                )
                upper1 = np.array(
                    [179, min(255, s_p + s_delta), min(255, v_p + v_delta)]
                )
                lower2 = np.array(
                    [
                        0,
                        max(s_min_thresh, s_p - s_delta),
                        max(v_min_thresh, v_p - v_delta),
                    ]
                )
                upper2 = np.array(
                    [
                        min(179, (h_p + h_delta) - 179),
                        min(255, s_p + s_delta),
                        min(255, v_p + v_delta),
                    ]
                )
                target_color_params["hsv_ranges"] = [(lower1, upper1), (lower2, upper2)]
            else:
                l_h = max(0, h_p - h_delta)
                u_h = min(179, h_p + h_delta)
                l_s = max(s_min_thresh, s_p - s_delta)
                u_s = min(255, s_p + s_delta)
                l_v = max(v_min_thresh, v_p - v_delta)
                u_v = min(255, v_p + v_delta)
                target_color_params["hsv_ranges"] = [
                    (np.array([l_h, l_s, l_v]), np.array([u_h, u_s, u_v]))
                ]
        else:
            h_d, s_d, v_d = 15, 70, 70
            s_min_t, v_min_t = 50, 50
            l_h = max(0, h_p - h_d)
            u_h = min(179, h_p + h_d)
            l_s = max(s_min_t, s_p - s_d)
            u_s = min(255, s_p + s_d)
            l_v = max(v_min_t, v_p - v_d)
            u_v = min(255, v_p + v_d)
            target_color_params["hsv_ranges"] = [
                (np.array([l_h, l_s, l_v]), np.array([u_h, u_s, u_v]))
            ]
        messagebox.showinfo(
            "Color Pick Success",
            f"HSV range for '{color_name_picked}' parameters updated in active settings. Open Advanced Calibration to fine-tune or see preview.",
        )
        if (
            self.calibration_window_open
            and self.calibration_window
            and self.calibration_window.winfo_exists()
        ):
            self.calibration_window.calib_params["colors"][color_name_picked] = (
                copy.deepcopy(target_color_params)
            )
            self.calibration_window.load_params_to_ui()
            self.calibration_window.refresh_mask_display(color_name_picked)
            self.calibration_window.lift()
        if self.img is not None:
            self.run_full_detection_cycle(show_results_window=False)

    def reset_state_for_new_image_or_camera(self):
        self.field_pts = []
        self.ball_pt1 = None
        self.ball_all = []
        self.ball_detected = False
        if hasattr(self, "ball_status_str"):
            self.ball_status_str.set("Ball: Not detected")
        if hasattr(self, "corner_listbox"):
            self.corner_listbox.delete(0, END)
        if hasattr(self, "capture_btn") and self.capture_btn.winfo_exists():
            self.capture_btn.config(state=NORMAL if self.camera_mode else DISABLED)
        self.update_measurement_display_default()
        self.has_last_known_plc_data = False
        self.sent_last_data_after_disappearance = False
        self.current_hsv_combined_mask_display = (
            self._generate_hsv_combined_mask_for_display()
        )  # Update to blank/new

    def update_loupe_and_coords(self, event):
        if self.img is None or self.preview is None or self.preview.size == 0:
            if hasattr(self.coord_label, "winfo_exists"):
                self.coord_label.config(text="Cursor (Preview): X: -, Y: -")
            if (
                hasattr(self.loupe_label, "winfo_exists")
                and self.loupe_label.winfo_exists()
            ):
                blank_loupe_img = Image.new(
                    "RGB", (self.LOUPE_DIM, self.LOUPE_DIM), color="lightgrey"
                )
                self.loupe_photo = ImageTk.PhotoImage(image=blank_loupe_img)
                self.loupe_label.config(image=self.loupe_photo)
            return
        prev_h, prev_w = self.preview.shape[:2]
        if 0 <= event.x < prev_w and 0 <= event.y < prev_h:
            self.cursor_preview = (event.x, event.y)
            if hasattr(self.coord_label, "winfo_exists"):
                self.coord_label.config(
                    text=f"Cursor (Preview): X:{event.x}, Y:{event.y}"
                )
            X_o = int(event.x / self.PREVIEW_SCALE)
            Y_o = int(event.y / self.PREVIEW_SCALE)
            if not (0 <= X_o < self.img.shape[1] and 0 <= Y_o < self.img.shape[0]):
                return
            h_loupe_o = int(self.LOUPE_DIM / (2 * self.LOUPE_SCALE))
            x1, y1 = max(0, X_o - h_loupe_o), max(0, Y_o - h_loupe_o)
            x2, y2 = min(self.img.shape[1], X_o + h_loupe_o), min(
                self.img.shape[0], Y_o + h_loupe_o
            )
            patch = self.img[y1:y2, x1:x2]
            if patch.size == 0:
                patch = np.full(
                    (
                        self.LOUPE_DIM // int(self.LOUPE_SCALE),
                        self.LOUPE_DIM // int(self.LOUPE_SCALE),
                        3,
                    ),
                    128,
                    dtype=np.uint8,
                )
            loupe_resized = cv2.resize(
                patch, (self.LOUPE_DIM, self.LOUPE_DIM), interpolation=cv2.INTER_NEAREST
            )
            c_loupe = self.LOUPE_DIM // 2
            cv2.circle(
                loupe_resized,
                (c_loupe, c_loupe),
                self.TARGET_RADIUS,
                self.TARGET_COLOR,
                -1,
            )
            cv2.rectangle(
                loupe_resized,
                (0, 0),
                (self.LOUPE_DIM - 1, self.LOUPE_DIM - 1),
                self.LOUPE_BORDER_COLOR,
                self.LOUPE_BORDER,
            )
            loupe_rgb = cv2.cvtColor(loupe_resized, cv2.COLOR_BGR2RGB)
            img_pil_loupe = Image.fromarray(loupe_rgb)
            self.loupe_photo = ImageTk.PhotoImage(image=img_pil_loupe)
            if (
                hasattr(self.loupe_label, "winfo_exists")
                and self.loupe_label.winfo_exists()
            ):
                self.loupe_label.config(
                    image=self.loupe_photo, width=self.LOUPE_DIM, height=self.LOUPE_DIM
                )
        else:
            if hasattr(self.coord_label, "winfo_exists"):
                self.coord_label.config(text="Cursor (Preview): X: -, Y: -")

    def on_closing(self):
        print("Closing application...")
        self.running = False
        self.plc_attempt_reconnect = False
        self.stop_camera_if_running()
        if self.pymc3e and self.plc_connected:
            try:
                self.pymc3e.close()
            except Exception as e:
                print(f"Error closing PLC: {e}")
        self.plc_connected = False
        if self.calibration_window_open and self.calibration_window:
            try:
                if self.calibration_window.winfo_exists():
                    self.calibration_window.destroy()
            except:
                pass
        self.calibration_window = None
        self.calibration_window_open = False
        if hasattr(self.root, "destroy") and self.root.winfo_exists():
            self.root.destroy()
        print("Application closed.")
    
    def red_team(self):
        if not self.pymc3e or not self.plc_connected:
            print("PLC is not connected. Cannot check Red Team status.")
            return

        try:
            # อ่านค่าจาก PLC
            wordunits_values = self.pymc3e.batchread_wordunits(headdevice="M300", readsize=2)

            print(wordunits_values[0])
            if wordunits_values[0] == 3:
                print("RED TEAM")

                ball_count = self.pymc3e.batchread_wordunits(headdevice="D130", readsize=2)

                if ball_count[0] == 0:
                    print(ball_count[0])
                        # ดึงค่าจากช่องกรอก X และ Y
                    x_str = self.red_team_x_entry.get()
                    y_str = self.red_team_y_entry.get()

                    if not x_str or not y_str:
                            raise ValueError("X and Y values are required.")

                    X = float(x_str)
                    Y = float(y_str)

                        # ตรวจสอบว่ามี 4 จุดใน self.field_pts
                    if len(self.field_pts) != 4:
                            raise ValueError("Field points must contain exactly 4 points.")

                        # แปลงข้อมูลให้เป็น float32
                    src_pts = np.float32(self.field_pts)
                    dst_pts = np.float32(
                        [
                                [0, 0],
                                [0, self.FIELD_H_CM],
                                [self.FIELD_W_CM, 0],
                                [self.FIELD_W_CM, self.FIELD_H_CM],
                            ]
                        )

                        # Get the perspective transformation matrix
                    H_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

                        # Transform the input point (X, Y) to the field coordinate system
                    input_point = np.float32([[X, Y]]).reshape(-1, 1, 2)
                    transformed_point = cv2.perspectiveTransform(input_point, H_matrix)
                        # Extract the transformed coordinates
                    transformed_x, transformed_y = transformed_point[0, 0]

                        # Calculate the distance from the origin (0, 0)
                    distance1 = math.sqrt(transformed_x**2 + transformed_y**2)

                        # Calculate the angle in degrees
                    degrees1 = math.degrees(math.atan2(transformed_x, transformed_y))

                        # Calculate swing speed
                    swing_speed = (distance1 * 24.096) + 5900

                        # Cap swing speed
                    swing_speed = min(swing_speed, 23000)

                    release_speed = 800

                        # เขียนค่าลงใน PLC
                    self.pymc3e.randomwrite(
                            word_devices=["D120", "D106", "D108"],
                            word_values=[
                                int(round(degrees1)),
                                int(round(swing_speed)),
                                int(round(release_speed))
                            ],
                            dword_devices=[],
                            dword_values=[]
                        )   
                    x_str = self.red_team_x_entry.get()
                    y_str = self.red_team_y_entry.get()

                    if not x_str or not y_str:
                            raise ValueError("X and Y values are required.")

                    X = float(x_str)
                    Y = float(y_str)

                        # ตรวจสอบว่ามี 4 จุดใน self.field_pts
                    if len(self.field_pts) != 4:
                            raise ValueError("Field points must contain exactly 4 points.")

                        # แปลงข้อมูลให้เป็น float32
                    src_pts = np.float32(self.field_pts)
                    dst_pts = np.float32(
                            [
                                [0, 0],
                                [0, self.FIELD_H_CM],
                                [self.FIELD_W_CM, 0],
                                [self.FIELD_W_CM, self.FIELD_H_CM],
                            ]
                        )

                        # Get the perspective transformation matrix
                    H_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

                        # Transform the input point (X, Y) to the field coordinate system
                    input_point = np.float32([[X, Y]]).reshape(-1, 1, 2)
                    transformed_point = cv2.perspectiveTransform(input_point, H_matrix)

                        # Extract the transformed coordinates
                    transformed_x, transformed_y = transformed_point[0, 0]

                        # Calculate the distance from the origin (0, 0)
                    distance1 = math.sqrt(transformed_x**2 + transformed_y**2)

                        # Calculate the angle in degrees
                    degrees1 = math.degrees(math.atan2(transformed_x, transformed_y))

                        # Calculate swing speed
                    swing_speed = (distance1 * 24.096) + 5900

                        # Cap swing speed
                    swing_speed = min(swing_speed, 23000)

                    release_speed = 800

                        # เขียนค่าลงใน PLC
                    self.pymc3e.randomwrite(
                            word_devices=["D120", "D106", "D108"],
                            word_values=[
                                int(round(degrees1)),
                                int(round(swing_speed)),
                                int(round(release_speed))
                            ],
                            dword_devices=[],
                            dword_values=[]
                        )
                else:
                    print("Not in Red Team.")
        except Exception as e:
            print(f"Error reading Red Team status: {e}")




if __name__ == "__main__":
    root = Tk()
    root.geometry("1500x1250")
    app = FieldMeasureApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
