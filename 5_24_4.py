import cv2
import numpy as np
import math
from tkinter import *
from tkinter import filedialog, ttk, messagebox, StringVar, IntVar
from PIL import Image, ImageTk, ImageColor # Added ImageColor for safety, though not strictly needed for "lightgrey"
import threading
import traceback
import time
import copy
import pymcprotocol
import sys

# --- CalibrationWindow Class  ---
class CalibrationWindow(Toplevel):
    def __init__(self, main_app):
        super().__init__(main_app.root)
        self.main_app = main_app
        self.title("HSV Calibration")
        self.geometry("400x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.calib_params = copy.deepcopy(self.main_app.active_detection_params)
        # self.img_to_process = None
        # self.preview_size = (480, 320)
        self.color_vars = {}

        self.create_widgets()
        self.load_params_to_ui()
        # self.refresh_all_mask_displays()

    def _auto_apply_to_main_app(self):
        """Helper function to apply current calib_params to the main app and trigger updates."""
        self.main_app.active_detection_params = copy.deepcopy(self.calib_params)
        if self.main_app.img is not None:
            self.main_app.run_full_detection_cycle(show_results_window=False)
        self.main_app.update_main_ui_detection_params_display()
        if self.main_app.img is not None:
             self.main_app.current_hsv_combined_mask_display = self.main_app._generate_hsv_combined_mask_for_display()
             self.main_app.update_main_canvas_display()

    def create_widgets(self):
        main_frame = Frame(self)
        main_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        settings_container_frame = main_frame

        # --- Commented out Global Settings (e.g., Blur Kernel) ---
        # global_settings_frame = LabelFrame(settings_container_frame, text="Global Settings", padx=5, pady=5)
        # global_settings_frame.pack(fill=X, expand=False, pady=3, padx=3)
        # Label(global_settings_frame, text="Blur Kernel:").grid(row=0, column=0, sticky=W, padx=1, pady=1)
        # blur_scale = Scale(global_settings_frame, from_=3, to=31, orient=HORIZONTAL, length=200, resolution=2,
        #                    command=lambda val: self.update_param_and_auto_apply("blur_kernel", int(val)))
        # blur_scale.grid(row=0, column=1, sticky=EW, padx=1, pady=1)
        # self.blur_kernel_scale = blur_scale
        # global_settings_frame.grid_columnconfigure(1, weight=1)
        # --- End of Commented out Global Settings ---

        colors_to_calibrate = ["white", "red", "blue"]
        for color_name in colors_to_calibrate:
            color_specific_settings_frame = LabelFrame(settings_container_frame, text=f"{color_name.capitalize()} HSV Settings", padx=5, pady=5) # Title changed
            color_specific_settings_frame.pack(fill=X, expand=False, pady=3, padx=3)
            self.setup_color_controls(color_specific_settings_frame, color_name)

        # --- Action Frame and its buttons were already commented out in previous step ---

    def setup_color_controls(self, parent_frame, color_name):
        hsv_frame = LabelFrame(parent_frame, text="HSV Ranges", padx=3, pady=3)
        hsv_frame.pack(fill=X, pady=2) # Only HSV frame now directly in color_specific_settings_frame
        if color_name not in self.color_vars:
            self.color_vars[color_name] = {}
        self.color_vars[color_name]["hsv_scales"] = {}
        hsv_params = [
            ("H Min", 0, 179),("S Min", 0, 255),("V Min", 0, 255),
            ("H Max", 0, 179),("S Max", 0, 255),("V Max", 0, 255),
        ]
        for i, (text, min_val, max_val) in enumerate(hsv_params):
            r, c = i % 3, (i // 3) * 2
            Label(hsv_frame, text=text + ":").grid(row=r, column=c, sticky=W, padx=1, pady=1)
            scale = Scale(
                hsv_frame, from_=min_val, to=max_val, orient=HORIZONTAL, length=120,
                command=lambda val, cn=color_name, p_idx=i: self.update_hsv_param_and_auto_apply(cn, p_idx, int(val)),
            )
            scale.grid(row=r, column=c + 1, sticky=EW, padx=1, pady=1)
            self.color_vars[color_name]["hsv_scales"][text.replace(" ", "_").lower()] = scale
            hsv_frame.grid_columnconfigure(c + 1, weight=1)

        # --- Commented out Detection Params Frame and its contents ---
        # detection_params_frame = LabelFrame(parent_frame, text="Detection Params", padx=3, pady=3)
        # detection_params_frame.pack(fill=X, pady=2)

        # det_entries_config = [("area_min", "Min Area:", int), ("area_max", "Max Area:", int)]
        # if color_name in ["red", "blue"]:
        #     det_entries_config.extend([
        #         ("cluster_area_min", "Min Cluster Area:", int), ("cluster_area_max", "Max Cluster Area:", int),
        #     ])
        # current_row_det = 0
        # for param_key, text, type_func in det_entries_config:
        #     Label(detection_params_frame, text=text).grid(row=current_row_det, column=0, sticky=W, padx=1, pady=1)
        #     entry = Entry(detection_params_frame, width=7)
        #     entry.grid(row=current_row_det, column=1, sticky=W, padx=1, pady=1)
        #     entry.bind("<FocusOut>", lambda e, cn=color_name, pk=param_key, ent=entry, tf=type_func: self.update_entry_param_and_auto_apply(f"colors.{cn}.{pk}", ent.get(), type_func=tf))
        #     entry.bind("<Return>", lambda e, cn=color_name, pk=param_key, ent=entry, tf=type_func: self.update_entry_param_and_auto_apply(f"colors.{cn}.{pk}", ent.get(), type_func=tf))
        #     self.color_vars[color_name][f"{param_key}_entry"] = entry
        #     current_row_det +=1

        # det_scales_config = [("circularity", "Circularity (0-100%):", 100.0), ("solidity", "Solidity (0-100%):", 100.0)]
        # if color_name in ["red", "blue"]:
        #     det_scales_config.extend([
        #         ("cluster_min_aspect_ratio", "Min Clust. Aspect (0-100%):", 100.0),
        #         ("cluster_max_aspect_ratio", "Max Clust. Aspect (0-500%):", 100.0),
        #     ])
        # for param_key, text, divisor in det_scales_config:
        #     to_val = 500 if "max_aspect" in param_key else 100
        #     Label(detection_params_frame, text=text).grid(row=current_row_det, column=0, sticky=W, padx=1, pady=1)
        #     scale_det = Scale(
        #         detection_params_frame, from_=0, to=to_val, orient=HORIZONTAL, length=150,
        #         command=lambda val, cn=color_name, pk=param_key, div=divisor: self.update_param_and_auto_apply(f"colors.{cn}.{pk}", float(val)/div),
        #     )
        #     scale_det.grid(row=current_row_det, column=1, sticky=EW, padx=1, pady=1)
        #     self.color_vars[color_name][f"{param_key}_scale"] = scale_det
        #     current_row_det += 1
        # detection_params_frame.grid_columnconfigure(1, weight=1)
        # --- End of Commented out Detection Params Frame ---

    # --- Commented out update_param_and_auto_apply (was for detection params and global blur) ---
    # def update_param_and_auto_apply(self, param_path, value):
    #     keys = param_path.split(".")
    #     d = self.calib_params
    #     try:
    #         for key in keys[:-1]: d = d[key]
    #         if keys[-1] in ["morph_open_k", "morph_close_k", "morph_dilate_k", "blur_kernel"]: # blur_kernel was global
    #             if not isinstance(value, (int, float)): value = int(value)
    #             if value < 3: value = 3
    #             if value % 2 == 0: value = value + 1 if value > 0 else 3
    #         d[keys[-1]] = value
    #         self._auto_apply_to_main_app()
    #     except KeyError:
    #         print(f"Error: Invalid param path '{param_path}' during update.")
    #         traceback.print_exc()
    #     except Exception as e:
    #         print(f"Error in update_param_and_auto_apply for {param_path}={value}: {e}")
    #         traceback.print_exc()
    # --- End of Commented out method ---

    # --- Commented out update_entry_param_and_auto_apply (was for detection param entries) ---
    # def update_entry_param_and_auto_apply(self, param_path, str_value, type_func=int):
    #     try:
    #         value = type_func(str_value)
    #         # self.update_param_and_auto_apply(param_path, value) # Would call the above commented method
    #         # Since the target method is commented, this one is effectively non-functional for now
    #         # If a global non-HSV entry is added, this structure might be revived.
    #         print(f"Note: update_entry_param_and_auto_apply called for {param_path}, but its target logic is commented out.")
    #     except ValueError:
    #         print(f"Invalid input for {param_path}: {str_value}. Not a valid {type_func.__name__}.")
    # --- End of Commented out method ---

    def update_hsv_param_and_auto_apply(self, color_name, param_index_flat, value): # This remains for HSV
        if not self.calib_params["colors"][color_name].get("hsv_ranges"):
            default_hsv_lower, default_hsv_upper = self.main_app.DEFAULT_DETECTION_PARAMS["colors"][color_name]["hsv_ranges"][0]
            self.calib_params["colors"][color_name]["hsv_ranges"] = [(default_hsv_lower.copy(), default_hsv_upper.copy())]
        elif not self.calib_params["colors"][color_name]["hsv_ranges"][0]:
            default_hsv_lower, default_hsv_upper = self.main_app.DEFAULT_DETECTION_PARAMS["colors"][color_name]["hsv_ranges"][0]
            self.calib_params["colors"][color_name]["hsv_ranges"][0] = (default_hsv_lower.copy(), default_hsv_upper.copy())

        current_lower, current_upper = self.calib_params["colors"][color_name]["hsv_ranges"][0]
        temp_lower, temp_upper = current_lower.copy(), current_upper.copy()

        param_map_to_channel_idx = {0:0, 1:1, 2:2, 3:0, 4:1, 5:2}
        is_lower = param_index_flat < 3
        channel_idx = param_map_to_channel_idx[param_index_flat]

        if is_lower: temp_lower[channel_idx] = value
        else: temp_upper[channel_idx] = value

        self.calib_params["colors"][color_name]["hsv_ranges"][0] = (temp_lower, temp_upper)
        self._auto_apply_to_main_app()

    def load_params_to_ui(self):
        # --- Commented out Load Global Blur Kernel ---
        # if hasattr(self, "blur_kernel_scale") and self.blur_kernel_scale.winfo_exists():
        #      self.blur_kernel_scale.set(self.calib_params.get("blur_kernel", self.main_app.DEFAULT_DETECTION_PARAMS.get("blur_kernel", 11)))
        # --- End of Commented out Load Global Blur Kernel ---

        for color_name in ["white", "red", "blue"]:
            color_data = self.calib_params["colors"].get(color_name, {})
            if not color_data:
                 self.calib_params["colors"][color_name] = copy.deepcopy(self.main_app.DEFAULT_DETECTION_PARAMS["colors"][color_name])
                 color_data = self.calib_params["colors"][color_name]
            default_color_data = self.main_app.DEFAULT_DETECTION_PARAMS["colors"][color_name]

            # HSV Scales loading
            if self.color_vars.get(color_name) and self.color_vars[color_name].get("hsv_scales"):
                required_hsv_scales = ["h_min","s_min","v_min","h_max","s_max","v_max"]
                if not all(s_key in self.color_vars[color_name]["hsv_scales"] and \
                           self.color_vars[color_name]["hsv_scales"][s_key].winfo_exists() for s_key in required_hsv_scales):
                    pass
                else:
                    if not color_data.get("hsv_ranges") or not color_data["hsv_ranges"][0]:
                        def_lower, def_upper = default_color_data["hsv_ranges"][0]
                        color_data["hsv_ranges"] = [(def_lower.copy(), def_upper.copy())]
                    
                    lower, upper = color_data["hsv_ranges"][0]
                    self.color_vars[color_name]["hsv_scales"]["h_min"].set(lower[0])
                    self.color_vars[color_name]["hsv_scales"]["s_min"].set(lower[1])
                    self.color_vars[color_name]["hsv_scales"]["v_min"].set(lower[2])
                    self.color_vars[color_name]["hsv_scales"]["h_max"].set(upper[0])
                    self.color_vars[color_name]["hsv_scales"]["s_max"].set(upper[1])
                    self.color_vars[color_name]["hsv_scales"]["v_max"].set(upper[2])

            # --- Commented out Detection Parameter Entry loading ---
            # entry_pks = ["area_min", "area_max"]
            # if color_name in ["red", "blue"]: entry_pks.extend(["cluster_area_min", "cluster_area_max"])
            # for pk_entry in entry_pks:
            #     entry_widget_key = f"{pk_entry}_entry"
            #     if self.color_vars.get(color_name) and entry_widget_key in self.color_vars[color_name] and \
            #        self.color_vars[color_name][entry_widget_key].winfo_exists():
            #         self.color_vars[color_name][entry_widget_key].delete(0, END)
            #         def_val = default_color_data.get(pk_entry, 100 if "min" in pk_entry else (700 if "cluster" not in pk_entry else 5000))
            #         self.color_vars[color_name][entry_widget_key].insert(0, str(color_data.get(pk_entry, def_val)))
            # --- End of Commented out Detection Parameter Entry loading ---

            # --- Commented out Detection Parameter Scale loading ---
            # scale_pks_map = {"circularity":0.7, "solidity":0.7}
            # if color_name in ["red","blue"]:
            #     scale_pks_map["cluster_min_aspect_ratio"] = default_color_data.get("cluster_min_aspect_ratio", 0.2)
            #     scale_pks_map["cluster_max_aspect_ratio"] = default_color_data.get("cluster_max_aspect_ratio", 3.0)
            # for pk_scale, def_val_shape in scale_pks_map.items():
            #     scale_widget_key = f"{pk_scale}_scale"
            #     if self.color_vars.get(color_name) and scale_widget_key in self.color_vars[color_name] and \
            #        self.color_vars[color_name][scale_widget_key].winfo_exists():
            #         current_val = color_data.get(pk_scale, def_val_shape)
            #         self.color_vars[color_name][scale_widget_key].set(int(current_val * 100))
            # --- End of Commented out Detection Parameter Scale loading ---

    # --- All other methods (generate_mask_for_color, refresh_mask_display, etc.) were already commented out ---

    def on_closing(self):
        self.main_app.calibration_window_open = False
        self.main_app.calibration_window = None
        self.destroy()

# --- Main Application Class ---
class FieldMeasureApp:
    PREVIEW_SCALE = 1.0
    LOUPE_SCALE = 2.0
    LOUPE_DIM = 150
    COMBINDED_MASK_DIM = 350
    LOUPE_BORDER = 1
    LOUPE_BORDER_COLOR = (0, 255, 0); TARGET_COLOR = (0,0,255); TARGET_RADIUS = 2
    FIELD_W_CM = 400.0; FIELD_H_CM = 598.0
    PLC_IP = "192.168.0.200"; PLC_PORT = 2001; PLC_RECONNECT_INTERVAL = 5000

    DEFAULT_DETECTION_PARAMS = {
        "blur_kernel": 11,
        "colors": {
            "white": {"hsv_ranges":[(np.array([0,0,180]),np.array([180,65,255]))], "circularity":0.65,"solidity":0.75,
                      "area_min":100,"area_max":1500, "morph_open_k":5,"morph_open_iter":1,"morph_close_k":5,
                      "morph_close_iter":2, "primary_min_radius":6,"primary_circularity":0.65},
            "red": {"hsv_ranges":[(np.array([0,70,70]),np.array([10,255,255])),(np.array([170,70,70]),np.array([179,255,255]))],
                    "circularity":0.7,"solidity":0.65, "area_min":100,"area_max":700, "morph_open_k":5,"morph_open_iter":1,
                    "morph_dilate_k":5,"morph_dilate_iter":1,"morph_close_k":5,"morph_close_iter":1,
                    "cluster_area_min":600,"cluster_area_max":6000, "cluster_min_aspect_ratio":0.15,"cluster_max_aspect_ratio":6.0},
            "blue": {"hsv_ranges":[(np.array([100,70,70]),np.array([140,255,255]))], "circularity":0.65,"solidity":0.65,
                     "area_min":100,"area_max":700, "morph_open_k":5,"morph_open_iter":1,"morph_dilate_k":5,
                     "morph_dilate_iter":1,"morph_close_k":5,"morph_close_iter":1,
                     "cluster_area_min":600,"cluster_area_max":6000, "cluster_min_aspect_ratio":0.15,"cluster_max_aspect_ratio":6.0},
        },
        "detection_threshold_nms":0.01, "nms_overlap_threshold":0.3,
    }
    STATUS_CLICK_COLOR_INFO_MODE = False # Kept, though button is removed
    last_known_plc_distance=None; last_known_plc_angle=None; last_known_plc_swing_speed=None
    last_known_plc_release_speed=800; has_last_known_plc_data=False; sent_last_data_after_disappearance=False
    current_hsv_combined_mask_display = None
    MIN_16BIT_SIGNED = -32768; MAX_16BIT_SIGNED = 32767
    DEFAULT_COLOR_PICK_PATCH_SIZE = 7
    OBSTACLE_PROXIMITY_THRESHOLD_CM = 10.0
    OPPONENT_NEAR_JACK_THRESHOLD_CM = 10.0
    TEAM_NONE=0; TEAM_RED=1; TEAM_BLUE=2

    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title("Field Measurement Tool v6.2")

        self.img=None; self.preview=None; self.cap=None; self.camera_mode=False
        self.field_pts=[]; self.ball_pt1=None; self.ball_all=[]
        self.cursor_preview=(0,0); self.ball_detected=False; self.running=True
        self.camera_thread=None; self.canvas_photo=None; self.loupe_photo=None; self.combined_mask_photo=None
        self.pymc3e=None; self.plc_connected=False; self.plc_connecting=False; self.plc_attempt_reconnect=True
        self.default_detection_params=copy.deepcopy(self.DEFAULT_DETECTION_PARAMS)
        self.active_detection_params=copy.deepcopy(self.default_detection_params)
        self.calibration_window=None; self.calibration_window_open=False
        self.picked_color_info_list=[]

        self.target_x_cm_str=StringVar(value="153.0"); self.target_y_cm_str=StringVar(value="801.0")
        self.pulse_offset_var = StringVar(value="-200") # Added for pulse offset
        self.distance_display_str=StringVar(value="Distance: N/A"); self.angle_display_str=StringVar(value="Angle: N/A")
        self.swing_speed_display_str=StringVar(value="Swing speed: N/A"); self.release_position_display_str=StringVar(value="Release pos.: N/A")
        self.ball_status_str=StringVar(value="Ball: Not found"); self.color_pick_patch_size_var=IntVar(value=self.DEFAULT_COLOR_PICK_PATCH_SIZE)
        wp = self.active_detection_params["colors"]["white"]
        self.white_solidity_var=IntVar(value=int(wp["solidity"]*100)); self.white_circularity_var=IntVar(value=int(wp["circularity"]*100))
        self.white_min_radius_var=IntVar(value=wp.get("primary_min_radius",6))
        self.current_hsv_combined_mask_display=np.zeros((self.COMBINDED_MASK_DIM,self.COMBINDED_MASK_DIM,3),dtype=np.uint8)

        # For Red Team Jack Ball Throw
        self.selecting_red_team_point = False
        self.red_team_selected_point = None
        self.red_team_xy_var = StringVar(value="Red Jack Target X:-, Y:-")
        self.current_team = self.TEAM_NONE


        self.create_widgets()
        self._initialize_plc()
        self.update_main_ui_detection_params_display()
        self.root.after(self.PLC_RECONNECT_INTERVAL, self._check_and_reconnect_plc_job)

    def _initialize_plc(self):
        self.pymc3e = pymcprotocol.Type3E(); self.pymc3e.setaccessopt(commtype="binary")
        self.plc_attempt_reconnect = True; self._attempt_connect_plc()

    def _update_plc_gui_status(self, status_text, lamp_color):
        if hasattr(self,"plc_status_label_widget") and self.plc_status_label_widget.winfo_exists():
            self.plc_status_label_widget.config(text=f"PLC: {status_text}")
        if hasattr(self,"plc_lamp_canvas") and self.plc_lamp_canvas.winfo_exists():
            self.plc_lamp_canvas.itemconfig(self.plc_lamp_indicator, fill=lamp_color)

    def _generate_hsv_combined_mask_for_display(self):
        if self.img is None or self.img.size == 0:
            return np.zeros((self.COMBINDED_MASK_DIM, self.COMBINDED_MASK_DIM, 3), dtype=np.uint8)
        try:
            hsv_image_orig = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)
            colored_mask_preview_full_res = np.zeros_like(self.img)
            colors_to_draw_ordered = [
                ("white", {"params_key": "white", "display_color": [0,255,0]}),
                ("blue", {"params_key": "blue", "display_color": [255,0,0]}),
                ("red", {"params_key": "red", "display_color": [0,0,255]})
            ]
            for color_name_key, color_info in colors_to_draw_ordered:
                color_params = self.active_detection_params["colors"].get(color_info["params_key"])
                if not color_params or not color_params.get("hsv_ranges"): continue
                hsv_ranges_list = color_params["hsv_ranges"]
                current_color_binary_mask_aggregated = np.zeros(hsv_image_orig.shape[:2], dtype=np.uint8)
                for lower_hsv_np, upper_hsv_np in hsv_ranges_list:
                    temp_lower = np.array(lower_hsv_np, dtype=np.uint8)
                    temp_upper = np.array(upper_hsv_np, dtype=np.uint8)
                    for i in range(1,3):
                        if temp_upper[i] < temp_lower[i]: temp_upper[i] = temp_lower[i]
                    if not (color_info["params_key"] == "red" and temp_lower[0] > temp_upper[0]):
                        if temp_upper[0] < temp_lower[0]: temp_upper[0] = temp_lower[0]
                    individual_mask_segment = np.zeros(hsv_image_orig.shape[:2], dtype=np.uint8)
                    if color_info["params_key"] == "red" and temp_lower[0] > temp_upper[0]:
                        mask1 = cv2.inRange(hsv_image_orig, np.array([0, temp_lower[1], temp_lower[2]]), temp_upper)
                        mask2 = cv2.inRange(hsv_image_orig, temp_lower, np.array([179, temp_upper[1], temp_upper[2]]))
                        individual_mask_segment = cv2.bitwise_or(mask1, mask2)
                    else:
                        individual_mask_segment = cv2.inRange(hsv_image_orig, temp_lower, temp_upper)
                    current_color_binary_mask_aggregated = cv2.bitwise_or(current_color_binary_mask_aggregated, individual_mask_segment)
                colored_mask_preview_full_res[current_color_binary_mask_aggregated == 255] = color_info["display_color"]
            return colored_mask_preview_full_res
        except Exception as e:
            print(f"Error in _generate_hsv_combined_mask_for_display: {e}")
            traceback.print_exc()
            return np.zeros((self.COMBINDED_MASK_DIM, self.COMBINDED_MASK_DIM, 3), dtype=np.uint8)

    def _attempt_connect_plc(self):
        if self.plc_connecting or not self.pymc3e: return False
        self.plc_connecting = True; self._update_plc_gui_status("Connecting...", "orange")
        if hasattr(self.root,"update_idletasks") and self.root.winfo_exists(): self.root.update_idletasks()
        try:
            if self.plc_connected: self.pymc3e.close()
            self.pymc3e.connect(self.PLC_IP, self.PLC_PORT)
            self.plc_connected = True; self._update_plc_gui_status("Connected", "green")
            print(f"INFO: PLC Connected to {self.PLC_IP}:{self.PLC_PORT}")
            return True
        except Exception:
            self.plc_connected=False; self._update_plc_gui_status("Failed","red")
            return False
        finally: self.plc_connecting = False

    def _check_and_reconnect_plc_job(self):
        if not self.running: return
        if not self.plc_connected and self.plc_attempt_reconnect and not self.plc_connecting:
            self._attempt_connect_plc()
        if hasattr(self.root,"after") and self.root.winfo_exists():
            self.root.after(self.PLC_RECONNECT_INTERVAL, self._check_and_reconnect_plc_job)

    def create_widgets(self):
        self.image_frame = Frame(self.root)
        self.image_frame.pack(side=LEFT, padx=3, pady=3, fill=BOTH, expand=True)
        self.control_frame = Frame(self.root, width=310)
        self.control_frame.pack(side=RIGHT, padx=3, pady=3, fill=Y)
        self.control_frame.pack_propagate(False)
        self.canvas = Canvas(self.image_frame, background="lightgrey")
        self.canvas.pack(fill=BOTH, expand=True)
        self.canvas.bind("<Motion>", self.update_loupe_and_coords)
        self.canvas.bind("<Button-1>", self.handle_canvas_click)
        info_display_frame = Frame(self.image_frame)
        info_display_frame.pack(fill=X, pady=(2,0))
        # self.combined_mask_label = Label(info_display_frame, bg="black", width=self.COMBINDED_MASK_DIM, height=self.COMBINDED_MASK_DIM)
        self.combined_mask_label = Label(info_display_frame, bg="black")
        self.combined_mask_label.pack(side=LEFT, padx=1, pady=1, expand=True, fill=BOTH)
        _blank_l_img = Image.new("RGB",(self.COMBINDED_MASK_DIM,self.COMBINDED_MASK_DIM),"black");
        self.combined_mask_photo=ImageTk.PhotoImage(_blank_l_img)
        self.combined_mask_label.config(image=self.combined_mask_photo)
        # self.loupe_label = Label(info_display_frame, bg="lightgrey", width=self.LOUPE_DIM, height=self.LOUPE_DIM)
        # self.loupe_label.pack(side=LEFT, padx=1, pady=1, expand=True, fill=BOTH)
        # _blank_r_img = Image.new("RGB",(self.LOUPE_DIM,self.LOUPE_DIM),"lightgrey");
        # self.loupe_photo=ImageTk.PhotoImage(_blank_r_img)
        # self.loupe_label.config(image=self.loupe_photo)
        self.coord_label = Label(self.image_frame, text="Cursor: X: -, Y: -", font=("Arial", 10))
        self.coord_label.pack(pady=1, side=BOTTOM, fill=X)
        sfont = ("Arial", 10); sfont_bold = ("Arial", 10, "bold"); sfont_small = ("Arial", 9)
       
        f_plc = LabelFrame(self.control_frame, text="PLC Status", font=sfont_bold)
        f_plc.pack(fill=X, padx=2, pady=(5,1), side=TOP)
        f_plc_inner = Frame(f_plc)
        f_plc_inner.pack(pady=1,fill=X,expand=True)
        self.plc_lamp_canvas = Canvas(f_plc_inner, width=18, height=18)
        self.plc_lamp_canvas.pack(side=LEFT, padx=(3,2))
        self.plc_lamp_indicator = self.plc_lamp_canvas.create_oval(2,2,16,16,fill="grey",outline="black")
        self.plc_status_label_widget = Label(f_plc_inner, text="PLC: Init...", font=sfont)
        self.plc_status_label_widget.pack(side=LEFT, expand=True, fill=X)
        self._update_plc_gui_status("Initializing...", "grey")

        f_loupe = LabelFrame(self.control_frame, text="Loupe window", font=sfont_bold)
        f_loupe.pack(fill=X, padx=2, pady=1) # This will place it after f_target because f_target was packed first
        self.loupe_label = Label(f_loupe, bg="lightgrey", width=self.LOUPE_DIM, height=self.LOUPE_DIM) #
        self.loupe_label.pack(fill=BOTH, expand=True, padx=1, pady=1)
        _blank_r_img = Image.new("RGB",(self.LOUPE_DIM,self.LOUPE_DIM),"lightgrey"); #
        self.loupe_photo=ImageTk.PhotoImage(_blank_r_img) #
        self.loupe_label.config(image=self.loupe_photo) #     
       
        f_input = LabelFrame(self.control_frame,text="Input",font=sfont_bold); f_input.pack(fill=X,padx=2,pady=1)
        Button(f_input,text="Open Image",command=self.open_image_file,font=sfont).pack(fill=X,pady=1,ipady=0)
        Button(f_input,text="Open Camera",command=self.open_camera,font=sfont).pack(fill=X,pady=1,ipady=0)
        # self.capture_btn=Button(f_input,text="Capture Frame",command=self.capture_frame,state=DISABLED,font=sfont)
        # self.capture_btn.pack(fill=X,pady=1,ipady=0)

        f_red = LabelFrame(self.control_frame,text="Red Team Jack Cmd",font=sfont_bold); f_red.pack(fill=X,padx=2,pady=1)
        Button(f_red,text="Select Red Jack Target",command=self.start_red_team_select_mode,bg="#FFCCCC",font=sfont).pack(fill=X,pady=1,ipady=0)
        self.red_team_xy_label=Label(f_red,textvariable=self.red_team_xy_var,font=sfont_bold,bg="white"); self.red_team_xy_label.pack(fill=X,pady=1)
        Button(f_red,text="Send Red Jack Command",command=self.red_team,bg="#FFCCCC",font=sfont).pack(fill=X,pady=1,ipady=0)

        f_corners = LabelFrame(self.control_frame,text="Field Corners",font=sfont_bold); f_corners.pack(fill=X,padx=2,pady=1)
        Label(f_corners,text="Order: TL,BL,TR,BR",font=("Arial",7,"italic")).pack(fill=X)
        self.corner_listbox=Listbox(f_corners,height=2,font=("Arial",7,"italic")); self.corner_listbox.pack(fill=X,pady=1)
        cf_btns=Frame(f_corners); cf_btns.pack(fill=X)
        Button(cf_btns,text="Del Last",command=self.remove_last_point,font=sfont).pack(side=LEFT,expand=True,fill=X,padx=1,ipady=0)
        Button(cf_btns,text="Clear All",command=self.clear_points,font=sfont).pack(side=LEFT,expand=True,fill=X,padx=1,ipady=0)
        f_detect = LabelFrame(self.control_frame,text="Detection",font=sfont_bold); f_detect.pack(fill=X,padx=2,pady=1)
        # Button(f_detect,text="Detect Balls",command=lambda:self.run_full_detection_cycle(False),font=sfont).pack(fill=X,pady=1,ipady=0)
        self.ball_status_label=Label(f_detect,textvariable=self.ball_status_str,font=sfont); self.ball_status_label.pack(fill=X,pady=0)
        f_pick=Frame(f_detect); f_pick.pack(fill=X)
        Button(f_pick,text="Pick W",command=lambda:self.initiate_hsv_color_pick_for_params("white"),bg="#E0E0FF",font=sfont_small).pack(side=LEFT,expand=True,fill=X,padx=1,ipady=0)
        Button(f_pick,text="Pick R",command=lambda:self.initiate_hsv_color_pick_for_params("red"),bg="#FFE0E0",font=sfont_small).pack(side=LEFT,expand=True,fill=X,padx=1,ipady=0)
        Button(f_pick,text="Pick B",command=lambda:self.initiate_hsv_color_pick_for_params("blue"),bg="#E0FFE0",font=sfont_small).pack(side=LEFT,expand=True,fill=X,padx=1,ipady=0)
        # Button(f_detect,text="Pick Color (Info)",command=self.toggle_info_color_pick_mode,font=sfont).pack(fill=X,pady=1,ipady=0) # MODIFIED: Removed
        Button(f_detect,text="Advanced Params",command=self.open_calibration_window,bg="lightblue",font=sfont_bold).pack(fill=X,pady=1,ipady=0)
        f_patch=Frame(f_detect); f_patch.pack(fill=X,pady=(1,0))
        Label(f_patch,text="Pick Patch(px):",font=sfont_small).pack(side=LEFT,padx=(0,2))
        self.color_pick_patch_scale_main_ui=Scale(f_patch,from_=3,to=21,orient=HORIZONTAL,resolution=2,variable=self.color_pick_patch_size_var,length=70,font=sfont_small)
        self.color_pick_patch_scale_main_ui.pack(side=LEFT,fill=X,expand=True)
        f_wpri = LabelFrame(self.control_frame,text="Primary White (UI)",font=sfont_bold); f_wpri.pack(fill=X,padx=2,pady=1)
        Label(f_wpri,text="Solidity(%):",font=sfont_small).grid(row=0,column=0,sticky=W,pady=0)
        self.white_solidity_scale=Scale(f_wpri,from_=0,to=100,orient=HORIZONTAL,var=self.white_solidity_var,command=self.update_white_ball_detection_params_from_main_ui,length=60,font=sfont_small)
        self.white_solidity_scale.grid(row=0,column=1,sticky=EW,pady=0)
        Label(f_wpri,text="Circularity(%):",font=sfont_small).grid(row=1,column=0,sticky=W,pady=0)
        self.white_circularity_scale=Scale(f_wpri,from_=0,to=100,orient=HORIZONTAL,var=self.white_circularity_var,command=self.update_white_ball_detection_params_from_main_ui,length=60,font=sfont_small)
        self.white_circularity_scale.grid(row=1,column=1,sticky=EW,pady=0)
        Label(f_wpri,text="Min Radius(px):",font=sfont_small).grid(row=2,column=0,sticky=W,pady=0)
        self.white_min_radius_scale=Scale(f_wpri,from_=1,to=50,orient=HORIZONTAL,var=self.white_min_radius_var,command=self.update_white_ball_detection_params_from_main_ui,length=60,font=sfont_small)
        self.white_min_radius_scale.grid(row=2,column=1,sticky=EW,pady=0)
        f_wpri.grid_columnconfigure(1,weight=1)

        f_target = LabelFrame(self.control_frame,text="Target & Measure",font=sfont_bold); f_target.pack(fill=X,padx=2,pady=1)
        Label(f_target,text="Target X (cm):",font=sfont_small).grid(row=0,column=0,sticky=W,padx=2)
        self.x_entry=Entry(f_target,width=7,textvariable=self.target_x_cm_str,font=sfont_small); self.x_entry.grid(row=0,column=1,sticky=W,padx=2)
        Label(f_target,text="Target Y (cm):",font=sfont_small).grid(row=1,column=0,sticky=W,padx=2)
        self.y_entry=Entry(f_target,width=7,textvariable=self.target_y_cm_str,font=sfont_small); self.y_entry.grid(row=1,column=1,sticky=W,padx=2)

        # MODIFIED: Added Pulse Offset Entry
        Label(f_target,text="Pulse Offset:",font=sfont_small).grid(row=0,column=2,sticky=W,padx=2)
        Entry(f_target,width=7,textvariable=self.pulse_offset_var,font=sfont_small).grid(row=0,column=3,sticky=W,padx=2)

        # MODIFIED: Adjusted row numbers for subsequent widgets
        Button(f_target,text="Set Target",command=self.set_target_position_action,font=sfont).grid(row=3,column=0,columnspan=2,pady=1,sticky="ew",ipady=0) # Was row 2
        Button(f_target,text="Calc & Show Detail",command=lambda:self.run_full_detection_cycle(True),bg="lightgreen",font=sfont_bold).grid(row=3,column=2,columnspan=2,pady=1,sticky="ew",ipady=0)
        self.distance_display_label=Label(f_target,textvariable=self.distance_display_str,font=("Arial",10,"bold")); self.distance_display_label.grid(row=5,column=0,columnspan=2,pady=0,sticky="w")
        self.angle_display_label=Label(f_target,textvariable=self.angle_display_str,font=("Arial",10,"bold")); self.angle_display_label.grid(row=5,column=2,columnspan=2,pady=0,sticky="w")
        self.swing_speed_display_label=Label(f_target,textvariable=self.swing_speed_display_str,font=("Arial",10,"bold")); self.swing_speed_display_label.grid(row=6,column=0,columnspan=2,pady=0,sticky="w")
        self.release_position_display_label=Label(f_target,textvariable=self.release_position_display_str,font=("Arial",10,"bold")); self.release_position_display_label.grid(row=6,column=2,columnspan=2,pady=0,sticky="w")
        f_target.grid_columnconfigure(1,weight=1)

    def _get_current_team(self):
        return self.current_team

    def _is_opponent_near_jack(self, jack_cm, opponent_balls_cm_coords, threshold_cm):
        # Function from 5_23_7.py
        # print(f"DEBUG: _is_opponent_near_jack - Called with: jack_cm={jack_cm}, opponents={opponent_balls_cm_coords}, threshold={threshold_cm}")
        if not opponent_balls_cm_coords or jack_cm is None:
            return False
        jx, jy = jack_cm
        for i, (ox, oy) in enumerate(opponent_balls_cm_coords):
            distance = math.sqrt((jx - ox)**2 + (jy - oy)**2)
            if distance < threshold_cm:
                return True
        return False

    def _is_obstacle_on_path(self, jack_cm, target_cm, obstacle_balls_cm_coords, proximity_threshold_cm):
        # Function from 5_23_7.py
        if not obstacle_balls_cm_coords or jack_cm is None or target_cm is None:
            return False

        p1_x, p1_y = jack_cm
        t_x, t_y = target_cm

        if p1_x == t_x and p1_y == t_y:
            return False

        vec_p1_t_x, vec_p1_t_y = t_x - p1_x, t_y - p1_y
        len_sq_p1_t = vec_p1_t_x**2 + vec_p1_t_y**2

        for i, (obs_x, obs_y) in enumerate(obstacle_balls_cm_coords):
            line_A = p1_y - t_y
            line_B = t_x - p1_x
            line_C = (p1_x * t_y) - (t_x * p1_y)

            denominator = math.sqrt(line_A**2 + line_B**2)
            if denominator == 0:
                continue

            distance_to_line = abs(line_A * obs_x + line_B * obs_y + line_C) / denominator

            if distance_to_line < proximity_threshold_cm:
                dot_product = (obs_x - p1_x) * vec_p1_t_x + (obs_y - p1_y) * vec_p1_t_y
                epsilon = 1e-9
                if (dot_product > epsilon) and (dot_product < len_sq_p1_t - epsilon):
                    return True
        return False

    def update_white_ball_detection_params_from_main_ui(self, event=None):
        if "white" in self.active_detection_params["colors"]:
            wp = self.active_detection_params["colors"]["white"]
            wp["solidity"]=float(self.white_solidity_var.get())/100.0
            wp["circularity"]=float(self.white_circularity_var.get())/100.0
            wp["primary_circularity"]=wp["circularity"]
            wp["primary_min_radius"]=self.white_min_radius_var.get()
            if self.calibration_window_open and self.calibration_window and self.calibration_window.winfo_exists():
                calib_wp = self.calibration_window.calib_params["colors"]["white"]
                calib_wp.update(wp)
                self.calibration_window.load_params_to_ui()
                self.calibration_window.refresh_mask_display("white")
            if self.img is not None and not self.camera_mode: self.run_full_detection_cycle(False)
            elif self.img is not None and self.camera_mode:
                self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()

    def update_main_ui_detection_params_display(self):
        if hasattr(self, "white_solidity_var"):
            def_w = self.DEFAULT_DETECTION_PARAMS["colors"]["white"]
            act_w = self.active_detection_params["colors"].get("white", def_w)
            self.white_solidity_var.set(int(act_w.get("solidity",def_w["solidity"])*100))
            self.white_circularity_var.set(int(act_w.get("circularity",def_w["circularity"])*100))
            self.white_min_radius_var.set(act_w.get("primary_min_radius",def_w["primary_min_radius"]))

    def toggle_info_color_pick_mode(self): # Method kept even if button removed, in case of other uses
        if self.img is None: messagebox.showwarning("Pick Color", "Open image/camera first."); return
        self.STATUS_CLICK_COLOR_INFO_MODE = not self.STATUS_CLICK_COLOR_INFO_MODE
        cursor_val = "crosshair" if self.STATUS_CLICK_COLOR_INFO_MODE else ""
        self.canvas.config(cursor=cursor_val)
        msg = f"Informational color pick mode {'ON' if self.STATUS_CLICK_COLOR_INFO_MODE else 'OFF'}."
        # messagebox.showinfo("Pick Color Mode", msg) # Optional: can be re-enabled if needed
        print(msg) # Changed to print to avoid UI pop-up for a now-hidden feature
        if self.STATUS_CLICK_COLOR_INFO_MODE and getattr(self,"picking_hsv_for_color",None) is not None:
            self.picking_hsv_for_color = None

    def get_color_info_from_click(self, event):
        if self.img is None or self.preview is None: return
        if not (0<=event.x<self.preview.shape[1] and 0<=event.y<self.preview.shape[0]): return
        ix,iy=int(event.x/self.PREVIEW_SCALE),int(event.y/self.PREVIEW_SCALE)
        if not (0<=ix<self.img.shape[1] and 0<=iy<self.img.shape[0]): return
        bgr=self.img[iy,ix]; hsv=cv2.cvtColor(np.uint8([[bgr]]),cv2.COLOR_BGR2HSV)[0][0]
        print(f"--- Color Info ({ix},{iy}) BGR: {bgr}, HSV: {hsv} ---")
        self.picked_color_info_list.append({"bgr":bgr,"hsv":hsv,"coords":(ix,iy)})

    def set_target_position_action(self):
        try:
            x,y = float(self.target_x_cm_str.get()), float(self.target_y_cm_str.get())
            messagebox.showinfo("Target Set", f"Target: X:{x:.1f} cm, Y:{y:.1f} cm.")
            if self.img is not None and len(self.field_pts)==4: self.run_full_detection_cycle(False)
        except ValueError: messagebox.showerror("Invalid Input","Valid numbers for X,Y target.")

    def handle_canvas_click(self, event):
        if getattr(self,"selecting_red_team_point",False):
            X,Y=int(event.x/self.PREVIEW_SCALE),int(event.y/self.PREVIEW_SCALE)
            self.red_team_selected_point=(X,Y); self.red_team_xy_var.set(f"Red Jack Target X:{X}, Y:{Y}")
            self.selecting_red_team_point=False; self.canvas.config(cursor="")
            messagebox.showinfo("Red Jack Target", f"Selected Red Jack Target point: ({X},{Y})")
            return
        if self.STATUS_CLICK_COLOR_INFO_MODE: self.get_color_info_from_click(event)
        elif getattr(self,"picking_hsv_for_color",None) is not None: self.process_hsv_color_pick(event)
        else: self.add_point(event)

    def open_image_file(self):
        self.stop_camera_if_running()
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image files","*.jpg *.jpeg *.png *.bmp *.tiff"),("All files","*.*")]
        )
        if file_path:
            try:
                self.img = cv2.imread(file_path)
                if self.img is None: raise ValueError(f"Could not read image: {file_path}")
                self.reset_state_for_new_image_or_camera()
                self._dynamic_scale_and_set_preview()
                self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
                if self.calibration_window_open and self.calibration_window and self.calibration_window.winfo_exists():
                    self.calibration_window.refresh_all_mask_displays()
                self.update_main_canvas_display()
            except Exception as e:
                messagebox.showerror("Image Error", f"Error opening image: {str(e)}")
                traceback.print_exc()
                self.img=None; self.preview=None
                self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
                self.update_main_canvas_display()

    def _dynamic_scale_and_set_preview(self):
        if self.img is None: self.preview=None; self.PREVIEW_SCALE=1.0; return
        if not hasattr(self.root,"winfo_exists") or not self.root.winfo_exists(): return
        self.root.update_idletasks()
        avail_w=self.image_frame.winfo_width(); avail_h=self.image_frame.winfo_height()
        info_h_est=self.COMBINDED_MASK_DIM+10; coord_h_est=20
        target_h=avail_h-info_h_est-coord_h_est-5
        target_w=avail_w-5
        if target_w<=1: target_w=self.canvas.winfo_width()
        if target_h<=1: target_h=self.canvas.winfo_height()
        if target_w<=1: target_w=600
        if target_h<=1: target_h=400
        img_h,img_w = self.img.shape[:2]
        if img_w==0 or img_h==0: self.preview=self.img.copy() if self.img is not None else None; self.PREVIEW_SCALE=1.0; return
        scale_w = target_w/img_w; scale_h = target_h/img_h
        self.PREVIEW_SCALE = min(scale_w,scale_h,1.0); self.PREVIEW_SCALE=max(0.1,self.PREVIEW_SCALE)
        prev_w=max(1,int(img_w*self.PREVIEW_SCALE)); prev_h=max(1,int(img_h*self.PREVIEW_SCALE))
        if prev_w>0 and prev_h>0: self.preview=cv2.resize(self.img,(prev_w,prev_h),interpolation=cv2.INTER_AREA)
        else: self.preview = None

    def open_camera(self):
        self.stop_camera_if_running()
        try:
            indices_to_try=[0,1,2,-1]; self.cap=None
            for i in indices_to_try:
                backend = cv2.CAP_DSHOW if sys.platform=="win32" else i
                temp_cap = cv2.VideoCapture(backend)
                if not temp_cap.isOpened() and backend!=i: temp_cap.release(); temp_cap=cv2.VideoCapture(i)
                if temp_cap.isOpened(): self.cap=temp_cap; print(f"INFO: Cam @ index {i} (backend:{backend}) opened."); break
                else: temp_cap.release()
            if not self.cap or not self.cap.isOpened(): raise ValueError("Could not open any camera.")
            res_set=False
            for w,h in [(2560,1440),(1920,1080),(1280,720)]:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,w); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,h)
                time.sleep(0.2)
                aw,ah=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if abs(aw-w)<10 and abs(ah-h)<10: print(f"INFO: Cam res set to {aw}x{ah}"); res_set=True; break
            if not res_set: print(f"WARN: Using default cam res: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
            self.camera_mode=True; self.reset_state_for_new_image_or_camera()
            ret,frame=self.cap.read()
            if ret and frame is not None:
                self.img=frame.copy()
                if self.img is None or self.img.size==0: raise ValueError("Invalid initial cam frame.")
                self.running=True; self._dynamic_scale_and_set_preview()
                self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
                self.camera_thread=threading.Thread(target=self.update_camera_feed,daemon=True); self.camera_thread.start()
                # if hasattr(self,"capture_btn"): self.capture_btn.config(state=NORMAL)
            else: raise ValueError("Could not grab initial frame from cam.")
        except Exception as e:
            print(f"ERR opening cam: {e}"); traceback.print_exc()
            if self.cap: self.cap.release(); self.cap=None
            self.running=False; self.camera_mode=False
            # if hasattr(self,"capture_btn"): self.capture_btn.config(state=DISABLED)
            messagebox.showerror("Camera Error",f"Could not open/config cam: {e}")
            self.img=None;self.preview=None; self.current_hsv_combined_mask_display=self._generate_hsv_combined_mask_for_display()
            self.update_main_canvas_display()

# End of First Half
# --- Continuation of FieldMeasureApp Class ---

    def update_camera_feed(self):
        last_error_report_time = 0
        error_report_interval = 5
        detection_interval = 0.05
        last_detection_time = time.time()
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

                    if not hasattr(self.root, "winfo_exists") or not self.root.winfo_exists():
                        break
                    self._dynamic_scale_and_set_preview()

                    m300_value = 0
                    d130_value = -1

                    try:
                        if self.plc_connected and self.pymc3e:
                            read_m300_data = self.pymc3e.batchread_wordunits(headdevice="M300", readsize=1)
                            if read_m300_data:
                                m300_value = read_m300_data[0]

                            read_d130_data = self.pymc3e.batchread_wordunits(headdevice="D130", readsize=1)
                            if read_d130_data:
                                d130_value = read_d130_data[0]

                            if m300_value != 0:
                                self.current_team = self.TEAM_RED
                            elif m300_value == 0 : # Assuming M300 = 0 is the other team (e.g., Blue)
                                self.current_team = self.TEAM_BLUE
                            else: # Other M300 values or read failure
                                self.current_team = self.TEAM_NONE
                    except Exception as plc_e:
                        print(f"PLC read error in update_camera_feed: {plc_e}")
                        self.current_team = self.TEAM_NONE

                    current_time = time.time()
                    if (current_time - last_detection_time) > detection_interval:
                        last_detection_time = current_time

                        # --- Get pulse_offset_val --- Start MODIFIED
                        pulse_offset_val = 0
                        try:
                            if hasattr(self, 'pulse_offset_var') and isinstance(self.pulse_offset_var, StringVar):
                                pulse_offset_val = int(self.pulse_offset_var.get())
                            else:
                                print(f"Warning: pulse_offset_var not initialized correctly in update_camera_feed. Using 0.")
                        except ValueError:
                            if hasattr(self, 'pulse_offset_var') and isinstance(self.pulse_offset_var, StringVar):
                                print(f"Warning: Invalid pulse_offset value in update_camera_feed: '{self.pulse_offset_var.get()}'. Using 0.")
                            else:
                                print(f"Warning: Invalid pulse_offset value (pulse_offset_var not available) in update_camera_feed. Using 0.")
                            pass # Default to 0 if conversion fails
                        # --- Get pulse_offset_val --- End MODIFIED

                        execute_ball_detection = True
                        if self.current_team == self.TEAM_RED and d130_value == 0:
                            execute_ball_detection = False
                            self.ball_all, self.ball_detected, self.ball_pt1 = [], False, None
                            if hasattr(self.root, "after") and self.root.winfo_exists():
                                self.root.after(0, self.ball_status_str.set, "Ball: Red Jack (D130=0) - Pick Target")

                        if execute_ball_detection:
                            if len(self.field_pts) == 4:
                                try:
                                    self.detect_balls_in_frame()
                                except Exception as e_detect:
                                    print(f"ERROR in detect_balls_in_frame during camera feed: {e_detect}")
                                    traceback.print_exc()
                                    self.ball_all, self.ball_detected, self.ball_pt1 = [], False, None
                                    if hasattr(self.root, "after") and self.root.winfo_exists():
                                        self.root.after(0, self.ball_status_str.set, "Ball: Detect Error")
                            else:
                                self.ball_all, self.ball_detected, self.ball_pt1 = [], False, None
                                if hasattr(self.root, "after") and self.root.winfo_exists():
                                    self.root.after(0, self.ball_status_str.set, "Ball: Set 4 Corners")

                        if not (self.current_team == self.TEAM_RED and d130_value == 0):
                            if len(self.field_pts) == 4:
                                jack_cm_for_eval = None
                                dist_for_eval = None
                                angle_for_eval = None

                                current_jack_is_detected_visually = self.ball_detected and self.ball_pt1 is not None

                                if current_jack_is_detected_visually:
                                    measurement_data_current = self.process_measurements_for_realtime()
                                    if measurement_data_current:
                                        jack_cm_for_eval = (measurement_data_current["x1_cm"], measurement_data_current["y1_cm"])
                                        dist_for_eval = measurement_data_current["distance_cm"]
                                        angle_for_eval = measurement_data_current["angle_degrees"]

                                        self.last_known_jack_cm_coords = jack_cm_for_eval
                                        self.last_known_plc_distance = dist_for_eval
                                        self.last_known_plc_angle = angle_for_eval
                                        self.has_last_known_plc_data = True
                                        self.sent_last_data_after_disappearance = False
                                    else:
                                        current_jack_is_detected_visually = False

                                if not current_jack_is_detected_visually and self.has_last_known_plc_data and self.last_known_jack_cm_coords:
                                    jack_cm_for_eval = self.last_known_jack_cm_coords
                                    dist_for_eval = self.last_known_plc_distance
                                    angle_for_eval = self.last_known_plc_angle

                                if jack_cm_for_eval and dist_for_eval is not None and angle_for_eval is not None:
                                    target_cm_coords = None
                                    try:
                                        target_cm_coords = (float(self.target_x_cm_str.get()), float(self.target_y_cm_str.get()))
                                    except ValueError:
                                        if hasattr(self.root, "after") and self.root.winfo_exists():
                                            self.root.after(0, self.update_measurement_display_default)
                                        if self.plc_connected and self.pymc3e:
                                            try: # M190, M191, M192 OFF
                                                self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[0, 0, 0])
                                            except Exception: pass
                                        if hasattr(self.root, "after") and self.root.winfo_exists():
                                            self.root.after(0, self.update_main_canvas_display_from_thread)
                                        time.sleep(0.005)
                                        continue

                                    opponent_balls_cm_in_roi = []
                                    current_H_matrix = None
                                    src_h = np.float32(self.field_pts)
                                    dst_h = np.float32([[0,0],[0,self.FIELD_H_CM],[self.FIELD_W_CM,0],[self.FIELD_W_CM,self.FIELD_H_CM]])
                                    try: current_H_matrix = cv2.getPerspectiveTransform(src_h, dst_h)
                                    except Exception: pass

                                    if current_H_matrix is not None:
                                        for ball_info in self.ball_all:
                                            is_opponent = (self.current_team == self.TEAM_RED and ball_info["color_name"] == "blue") or \
                                                          (self.current_team == self.TEAM_BLUE and ball_info["color_name"] == "red")
                                            if is_opponent:
                                                ball_pixel_center = np.float32([ball_info["center"]]).reshape(-1,1,2)
                                                ball_cm_transformed = cv2.perspectiveTransform(ball_pixel_center, current_H_matrix)
                                                if ball_cm_transformed is not None and ball_cm_transformed.size > 0:
                                                    opponent_balls_cm_in_roi.append(tuple(ball_cm_transformed[0,0]))

                                    # --- Strategic conditions ---
                                    obstacle_on_path = self._is_obstacle_on_path(jack_cm_for_eval, target_cm_coords, opponent_balls_cm_in_roi, self.OBSTACLE_PROXIMITY_THRESHOLD_CM)
                                    opponent_near_jack = self._is_opponent_near_jack(jack_cm_for_eval, opponent_balls_cm_in_roi, self.OPPONENT_NEAR_JACK_THRESHOLD_CM)

                                    # --- Determine final speeds and angle based on conditions ---
                                    final_swing_speed = (dist_for_eval * 24.096) + 5900 + pulse_offset_val # MODIFIED: Base swing uses pulse_offset_val
                                    final_swing_speed = max(0, min(final_swing_speed, 23000))
                                    final_release_speed = 800 # Base release
                                    final_angle_deg = angle_for_eval # Base angle

                                    # --- PLC M-bit logic --- Start MODIFIED
                                    m190_val = 0 # Opponent near Jack
                                    m191_val = 0 # Opponent on path
                                    m192_val = 0 # Normal case

                                    if opponent_near_jack:
                                        m190_val = 1
                                        # if ball_cm_transformed <= 360 and final_angle_deg <= 349.1 :
                                            # This formula is different and not affected by pulse_offset directly
                                            # final_swing_speed = (dist_for_eval * 31.363) + 10864 - 1200
                                        final_swing_speed = (dist_for_eval * 24.096) + 5900 +pulse_offset_val +3850
                                        final_swing_speed = max(0, min(final_swing_speed, 23000))
                                        final_release_speed = 500

                                    if obstacle_on_path:
                                        m191_val = 1
                                        # If M190 is not already set (i.e., not opponent_near_jack), then apply obstacle-only throw adjustments
                                        if not opponent_near_jack: # only obstacle, NOT opponent near jack
                                            # Base swing speed (already includes pulse_offset) is kept.
                                            final_release_speed = 800 # Specific for this condition in camera feed
                                            if self.current_team == self.TEAM_RED:
                                                if final_angle_deg >=0 and final_angle_deg < 180: final_angle_deg -= 1.0
                                                else: final_angle_deg += 2.0
                                            elif self.current_team == self.TEAM_BLUE:
                                                if final_angle_deg >=0 and final_angle_deg < 180: final_angle_deg -= 1.0
                                                else: final_angle_deg += 2.0
                                    
                                    # M192 is ON (Normal) if neither M190 (opponent near jack) nor M191 (obstacle on path) are met
                                    if m190_val == 0 and m191_val == 0:
                                        m192_val = 1
                                    # --- PLC M-bit logic --- End MODIFIED
                                    
                                    final_swing_speed = max(0, min(final_swing_speed, 23000))
                                    final_angle_deg = (final_angle_deg + 360.0) % 360.0

                                    if current_jack_is_detected_visually:
                                        self.last_known_plc_swing_speed = final_swing_speed
                                        self.last_known_plc_release_speed = final_release_speed

                                    if self.plc_connected and self.pymc3e:
                                        self.send_data_to_plc(dist_for_eval, final_angle_deg, final_swing_speed, final_release_speed) # D registers
                                        try: 
                                            # MODIFIED: Write M190, M191, M192
                                            self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[m190_val, m191_val, m192_val])
                                            print(f"PLC M-Bits Sent: M190={m190_val}, M191={m191_val}, M192={m192_val}")
                                        except Exception as e: 
                                            print(f"ERROR writing M190-M192 (CamFeed): {e}")

                                    display_data = {
                                        "distance_cm_final": dist_for_eval, "angle_degrees_final": final_angle_deg,
                                        "x1_cm": jack_cm_for_eval[0], "y1_cm": jack_cm_for_eval[1],
                                        "x2_cm": target_cm_coords[0], "y2_cm": target_cm_coords[1]
                                    }
                                    if hasattr(self.root, "after") and self.root.winfo_exists():
                                        self.root.after(0, self.update_measurement_display, display_data)

                                    if not current_jack_is_detected_visually:
                                        self.sent_last_data_after_disappearance = True

                                else: # No Jack position (current or last known) for evaluation
                                    if hasattr(self.root, "after") and self.root.winfo_exists():
                                        self.root.after(0, self.update_measurement_display_default)
                                    if self.plc_connected and self.pymc3e:
                                        try: # MODIFIED: M190, M191, M192 OFF
                                            self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[0, 0, 0])
                                            print(f"PLC M-Bits Cleared (No Jack Eval): M190=0, M191=0, M192=0")
                                        except Exception as e: 
                                            print(f"ERROR writing M190-M192 OFF (No Jack Eval): {e}")
                            else: # Field points not defined
                                if hasattr(self.root, "after") and self.root.winfo_exists():
                                    self.root.after(0, self.update_measurement_display_default)
                                if self.plc_connected and self.pymc3e:
                                    try: # MODIFIED: M190, M191, M192 OFF
                                        self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[0, 0, 0])
                                        print(f"PLC M-Bits Cleared (No Field): M190=0, M191=0, M192=0")
                                    except Exception as e: 
                                        print(f"ERROR writing M190-M192 OFF (No Field): {e}")

                        if hasattr(self.root, "after") and self.root.winfo_exists():
                            self.root.after(0, self.update_main_canvas_display_from_thread)
                else: # Frame not retrieved or invalid
                    current_time_err = time.time()
                    if current_time_err - last_error_report_time > error_report_interval:
                        last_error_report_time = current_time_err
                    time.sleep(0.05)

                time.sleep(0.005)

        except Exception as e_outer:
            if self.running and \
               hasattr(self.root, "winfo_exists") and self.root.winfo_exists() and \
               ("application has been destroyed" not in str(e_outer).lower()) and \
               ("invalid command name" not in str(e_outer).lower()):
                print(f"CRITICAL ERROR in camera feed: {e_outer}")
                traceback.print_exc()
        finally:
            if hasattr(self.root, "winfo_exists") and self.root.winfo_exists() and hasattr(self.root, "after"):
                self.root.after(0, self.handle_camera_thread_exit)

    def run_full_detection_cycle(self, show_results_window=False):
        if self.img is None:
            if not show_results_window:
                messagebox.showwarning("Detection Error", "No image loaded.")
            self.ball_status_str.set("Ball: No Image")
            self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
            self.update_main_canvas_display()
            return

        m300_value = 0
        d130_is_zero = False
        try:
            if self.plc_connected and self.pymc3e:
                read_m300 = self.pymc3e.batchread_wordunits(headdevice="M300", readsize=1)
                if read_m300: m300_value = read_m300[0]

                if m300_value != 0:
                    self.current_team = self.TEAM_RED
                    read_d130_words = self.pymc3e.batchread_wordunits(headdevice="D130", readsize=1)
                    if read_d130_words and read_d130_words[0] == 0: d130_is_zero = True
                elif m300_value == 2 :
                    self.current_team = self.TEAM_BLUE
                else:
                    self.current_team = self.TEAM_NONE
        except Exception as plc_e:
            print(f"PLC Error in run_full_detection_cycle: {plc_e}")
            self.current_team = self.TEAM_NONE

        perform_visual_detection_full_cycle = True
        if self.current_team == self.TEAM_RED and d130_is_zero:
            perform_visual_detection_full_cycle = False
            self.ball_all = []
            self.ball_detected = False
            self.ball_pt1 = None
            self.ball_status_str.set("Ball: Red Jack (Manual Aim Mode / D130=0)")

        if perform_visual_detection_full_cycle:
            try:
                self.detect_balls_in_frame()
            except Exception as e_detect_full:
                print(f"ERROR in detect_balls_in_frame (full cycle): {e_detect_full}")
                traceback.print_exc()
                self.ball_all = []
                self.ball_detected = False
                self.ball_pt1 = None
                self.ball_status_str.set("Ball: Detection Error")
                self.update_main_canvas_display()
                return

        self.update_main_canvas_display()
        measurement_data_dict = None
        m190_value_to_set = 0

        # --- Get pulse_offset_val --- Start MODIFIED
        pulse_offset_val = 0
        try:
            if hasattr(self, 'pulse_offset_var') and isinstance(self.pulse_offset_var, StringVar):
                pulse_offset_val = int(self.pulse_offset_var.get())
            else:
                print(f"Warning: pulse_offset_var not initialized correctly in run_full_detection_cycle. Using 0.")
        except ValueError:
            if hasattr(self, 'pulse_offset_var') and isinstance(self.pulse_offset_var, StringVar):
                print(f"Warning: Invalid pulse_offset value in run_full_detection_cycle: '{self.pulse_offset_var.get()}'. Using 0.")
            else:
                print(f"Warning: Invalid pulse_offset value (pulse_offset_var not available) in run_full_detection_cycle. Using 0.")
            pass # Default to 0 if conversion fails
        # --- Get pulse_offset_val --- End MODIFIED

        if len(self.field_pts) == 4:
            if self.ball_detected and self.ball_pt1 is not None:
                measurement_data_dict = self.process_measurements_for_realtime()
                if measurement_data_dict:
                    final_dist_cm = measurement_data_dict["distance_cm"]
                    final_angle_deg = measurement_data_dict["angle_degrees"]
                    # MODIFIED: Base swing speed calculation includes pulse_offset_val
                    final_swing_speed = (final_dist_cm * 24.096) + 5900 + pulse_offset_val
                    final_release_speed = 800
                    H_matrix_local = measurement_data_dict.get("H_matrix")
                    jack_cm_coords = (measurement_data_dict["x1_cm"], measurement_data_dict["y1_cm"])
                    target_cm_coords = (measurement_data_dict["x2_cm"], measurement_data_dict["y2_cm"])
                    opponent_balls_cm_in_roi = []
                    if H_matrix_local is not None:
                        for ball_info in self.ball_all:
                            is_opponent = (self.current_team == self.TEAM_RED and ball_info["color_name"] == "blue") or \
                                          (self.current_team == self.TEAM_BLUE and ball_info["color_name"] == "red")
                            if is_opponent:
                                ball_pixel_center = np.float32([ball_info["center"]]).reshape(-1,1,2)
                                ball_cm_transformed = cv2.perspectiveTransform(ball_pixel_center, H_matrix_local)
                                if ball_cm_transformed is not None and ball_cm_transformed.size > 0:
                                    opponent_balls_cm_in_roi.append(tuple(ball_cm_transformed[0,0]))

                    obstacle_on_path = self._is_obstacle_on_path(jack_cm_coords, target_cm_coords, opponent_balls_cm_in_roi, self.OBSTACLE_PROXIMITY_THRESHOLD_CM)
                    if obstacle_on_path:
                        # MODIFIED: This re-assignment of base swing speed also includes pulse_offset_val
                        final_swing_speed = (final_dist_cm * 24.096) + 5900 + pulse_offset_val
                        final_release_speed = 800 # Keep original logic for release speed in this condition
                        if self.current_team == self.TEAM_RED:
                            if final_angle_deg >=0 and final_angle_deg < 180: final_angle_deg -= 1.0
                            elif final_angle_deg >= 180 and final_angle_deg <=360: final_angle_deg += 1.0
                        elif self.current_team == self.TEAM_BLUE:
                            if final_angle_deg >=0 and final_angle_deg < 180: final_angle_deg -= 1.0
                            elif final_angle_deg >= 180 and final_angle_deg <=360: final_angle_deg += 1.0

                    opponent_near_jack = self._is_opponent_near_jack(jack_cm_coords, opponent_balls_cm_in_roi, self.OPPONENT_NEAR_JACK_THRESHOLD_CM)
                    if opponent_near_jack: # This formula is different, not affected by pulse_offset
                        # final_swing_speed = (final_dist_cm * 31.363) + 10864 - 1200
                        final_swing_speed = (final_dist_cm * 24.096) + 5900  + pulse_offset_val +3850
                        final_release_speed = 500
                        m190_value_to_set = 1

                    final_angle_deg = (final_angle_deg + 360.0) % 360.0 
                    final_swing_speed = max(0, min(final_swing_speed, 23000))
                    self.last_known_plc_distance = final_dist_cm
                    self.last_known_plc_angle = final_angle_deg
                    self.last_known_plc_swing_speed = final_swing_speed
                    self.last_known_plc_release_speed = final_release_speed
                    self.has_last_known_plc_data = True
                    self.sent_last_data_after_disappearance = False
                    if self.plc_connected and self.pymc3e:
                        if not self.camera_mode:
                            self.send_data_to_plc(self.last_known_plc_distance, self.last_known_plc_angle,
                                                  self.last_known_plc_swing_speed, self.last_known_plc_release_speed)
                        try: self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[m190_value_to_set])
                        except Exception as e_plc_m190_fc: print(f"ERROR writing M190 to PLC (FullCycle): {e_plc_m190_fc}")
                    display_data = measurement_data_dict.copy()
                    display_data["distance_cm_final"] = self.last_known_plc_distance
                    display_data["angle_degrees_final"] = self.last_known_plc_angle
                    self.update_measurement_display(display_data)
                else:
                    self.update_measurement_display_default()
                    if self.plc_connected and self.pymc3e:
                        try: self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[0])
                        except Exception as e: print(f"Error M190 OFF (meas fail): {e}")
            else:
                self.update_measurement_display_default()
                if perform_visual_detection_full_cycle and self.has_last_known_plc_data and not self.sent_last_data_after_disappearance :
                    if self.plc_connected and self.pymc3e:
                         self.send_data_to_plc(self.last_known_plc_distance, self.last_known_plc_angle,
                                               self.last_known_plc_swing_speed, self.last_known_plc_release_speed)
                         try: self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[0])
                         except Exception as e: print(f"Error M190 OFF (jack gone): {e}")
                    self.sent_last_data_after_disappearance = True
                elif self.plc_connected and self.pymc3e:
                    try: self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[0])
                    except Exception as e: print(f"Error M190 OFF (no detection): {e}")
        else:
            self.update_measurement_display_default()
            if not self.camera_mode and not show_results_window:
                 if hasattr(self, "ball_status_str"): self.ball_status_str.set("Ball: Define 4 field corners")
            if self.plc_connected and self.pymc3e:
                try: self.pymc3e.batchwrite_bitunits(headdevice="M190", values=[0])
                except Exception as e: print(f"Error M190 OFF (no field): {e}")

        if show_results_window:
            if len(self.field_pts) != 4:
                messagebox.showwarning("Results Error", "4 field corners must be selected for detailed results.")
                return
            if not perform_visual_detection_full_cycle:
                 messagebox.showinfo("Results Info", "Red Team Jack (D130=0). Visual results based on auto-detection not applicable for this specific state.")
                 return
            if not self.ball_detected or self.ball_pt1 is None:
                messagebox.showwarning("Results Error", "Primary white ball not detected. Cannot show details.")
                return
            if measurement_data_dict is None:
                measurement_data_dict = self.process_measurements_for_realtime()
            if measurement_data_dict: self.show_detailed_results_window(measurement_data_dict)
            else: messagebox.showerror("Results Error","Could not process measurements for detail view.")


    def stop_camera_if_running(self):
        self.running = False
        if self.camera_thread and self.camera_thread.is_alive(): self.camera_thread.join(timeout=0.5)
        self.camera_thread = None
        if self.cap: self.cap.release(); self.cap = None
        self.camera_mode = False
        # if hasattr(self,"capture_btn") and self.capture_btn.winfo_exists(): self.capture_btn.config(state=DISABLED)

    def capture_frame(self):
        if self.img is None: messagebox.showwarning("Capture","No image/camera active."); return
        self.run_full_detection_cycle(show_results_window=True)

    def update_main_canvas_display_from_thread(self):
        if (self.preview is not None or self.img is None) and hasattr(self.canvas,"winfo_exists") and self.canvas.winfo_exists():
            self.update_main_canvas_display()

    def handle_camera_thread_exit(self):
        # if hasattr(self,"capture_btn") and self.capture_btn.winfo_exists(): self.capture_btn.config(state=DISABLED)
        print("Camera thread has exited.")

    def detect_balls_in_frame(self):
        if self.img is None or self.img.size == 0:
            self.ball_pt1, self.ball_all, self.ball_detected = None, [], False
            self.ball_status_str.set("Ball: No image")
            self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
            return
        if len(self.field_pts) != 4:
            self.ball_pt1, self.ball_all, self.ball_detected = None, [], False
            if hasattr(self,"ball_status_str"): self.ball_status_str.set("Ball: Define 4 corners")
            self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
            return
        self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
        img_for_detection = self.img.copy()
        field_mask_cv = np.zeros(self.img.shape[:2], dtype=np.uint8)
        try:
            pts_for_poly = np.array([self.field_pts[0],self.field_pts[1],self.field_pts[3],self.field_pts[2]], dtype=np.int32)
            cv2.fillPoly(field_mask_cv, [pts_for_poly], 255)
            img_for_detection = cv2.bitwise_and(img_for_detection,img_for_detection,mask=field_mask_cv)
        except Exception as e_mask: print(f"Error creating field mask: {e_mask}")
        self.ball_pt1 = None
        self.ball_detected = False
        all_detected_objects_for_nms = []
        blur_k = self.active_detection_params.get("blur_kernel", 11)
        blur_k = max(3, blur_k + (1 if blur_k % 2 == 0 else 0))
        try:
            blurred = cv2.GaussianBlur(img_for_detection, (blur_k, blur_k), 0)
            hsv_blurred = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        except Exception as e_blur:
            print(f"Error during blur/HSV conversion: {e_blur}")
            hsv_blurred = cv2.cvtColor(img_for_detection, cv2.COLOR_BGR2HSV)
        best_hsv_white_ball_for_primary = None
        highest_primary_white_metric = -1.0
        wp = self.active_detection_params["colors"].get("white", self.DEFAULT_DETECTION_PARAMS["colors"]["white"])
        if wp:
            hsv_ranges_list = wp.get("hsv_ranges", [])
            if hsv_ranges_list:
                mask_w = np.zeros(hsv_blurred.shape[:2],dtype=np.uint8)
                for lr, ur in hsv_ranges_list:
                    l=np.array(lr,dtype=np.uint8); u=np.array(ur,dtype=np.uint8)
                    for ch_idx in range(3):
                        if u[ch_idx] < l[ch_idx]: u[ch_idx] = l[ch_idx]
                    mask_w = cv2.bitwise_or(mask_w, cv2.inRange(hsv_blurred, l, u))
                op_k_w=max(3,wp.get("morph_open_k",5)+(1 if wp.get("morph_open_k",5)%2==0 else 0))
                op_i_w=wp.get("morph_open_iter",1)
                cl_k_w=max(3,wp.get("morph_close_k",5)+(1 if wp.get("morph_close_k",5)%2==0 else 0))
                cl_i_w=wp.get("morph_close_iter",2)
                if op_i_w>0: mask_w=cv2.morphologyEx(mask_w,cv2.MORPH_OPEN,np.ones((op_k_w,op_k_w),np.uint8),iterations=op_i_w)
                if cl_i_w>0: mask_w=cv2.morphologyEx(mask_w,cv2.MORPH_CLOSE,np.ones((cl_k_w,cl_k_w),np.uint8),iterations=cl_i_w)
                contours_w, _ = cv2.findContours(mask_w, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                min_a_w, max_a_w = wp.get("area_min",100), wp.get("area_max",1500)
                circ_t_w, sol_t_w = wp.get("circularity",0.65), wp.get("solidity",0.75)
                prim_circ_t, prim_rad_t = wp.get("primary_circularity",0.65), wp.get("primary_min_radius",6)
                for cnt in contours_w:
                    area = cv2.contourArea(cnt)
                    if not (min_a_w <= area <= max_a_w): continue
                    perimeter = cv2.arcLength(cnt,True);
                    if perimeter == 0: continue
                    circularity = 4 * np.pi * area / (perimeter**2)
                    (x,y),radius = cv2.minEnclosingCircle(cnt)
                    hull=cv2.convexHull(cnt); hull_a=cv2.contourArea(hull)
                    solidity = float(area)/hull_a if hull_a > 0 else 0
                    if circularity >= circ_t_w and solidity >= sol_t_w:
                        conf = circularity*0.5 + solidity*0.3 + min(1.0, area/max_a_w)*0.2
                        obj = {"bbox":(int(x-radius),int(y-radius),int(x+radius),int(y+radius)), "confidence":conf,
                               "center":(int(x),int(y)), "radius":int(radius), "color_name":"white", "shape_type":"circle",
                               "circularity":circularity, "solidity":solidity, "area":area, "is_primary_white": False}
                        all_detected_objects_for_nms.append(obj)
                        if circularity >= prim_circ_t and radius >= prim_rad_t:
                            metric = circularity*1000 + radius
                            if metric > highest_primary_white_metric:
                                highest_primary_white_metric = metric
                                best_hsv_white_ball_for_primary = obj
        primary_jack_center_px = None
        primary_jack_radius_px = 0
        if best_hsv_white_ball_for_primary:
            self.ball_detected = True
            best_hsv_white_ball_for_primary["is_primary_white"] = True
            primary_jack_center_px = best_hsv_white_ball_for_primary["center"]
            primary_jack_radius_px = best_hsv_white_ball_for_primary["radius"]
            self.ball_pt1 = (primary_jack_center_px[0], primary_jack_center_px[1] + primary_jack_radius_px)
            self.ball_status_str.set(f"W:Found (C:{best_hsv_white_ball_for_primary['circularity']:.2f} R:{primary_jack_radius_px})")
            ROI_RADIUS_FACTOR = 12.0
            search_radius_sq_px = (primary_jack_radius_px * ROI_RADIUS_FACTOR)**2
            for color_name in ["red", "blue"]:
                cp = self.active_detection_params["colors"].get(color_name, self.DEFAULT_DETECTION_PARAMS["colors"][color_name])
                hsv_ranges_list_rb = cp.get("hsv_ranges",[])
                if not hsv_ranges_list_rb: continue
                mask_rb = np.zeros(hsv_blurred.shape[:2],dtype=np.uint8)
                for lr,ur in hsv_ranges_list_rb:
                    l,u=np.array(lr,dtype=np.uint8),np.array(ur,dtype=np.uint8)
                    for ch_idx in range(1,3):
                        if u[ch_idx] < l[ch_idx]: u[ch_idx] = l[ch_idx]
                    if not(color_name=="red" and l[0]>u[0]):
                        if u[0] < l[0]: u[0] = l[0]
                    seg_mask_rb = np.zeros(hsv_blurred.shape[:2],dtype=np.uint8)
                    if color_name=="red" and l[0]>u[0]:
                        m1=cv2.inRange(hsv_blurred,np.array([0,l[1],l[2]]),u)
                        m2=cv2.inRange(hsv_blurred,l,np.array([179,u[1],u[2]]))
                        seg_mask_rb = cv2.bitwise_or(m1,m2)
                    else: seg_mask_rb = cv2.inRange(hsv_blurred,l,u)
                    mask_rb = cv2.bitwise_or(mask_rb, seg_mask_rb)
                op_k_rb=max(3,cp.get("morph_open_k",5)+(1 if cp.get("morph_open_k",5)%2==0 else 0))
                op_i_rb=cp.get("morph_open_iter",1)
                di_k_rb=max(3,cp.get("morph_dilate_k",5)+(1 if cp.get("morph_dilate_k",5)%2==0 else 0))
                di_i_rb=cp.get("morph_dilate_iter",1)
                cl_k_rb=max(3,cp.get("morph_close_k",5)+(1 if cp.get("morph_close_k",5)%2==0 else 0))
                cl_i_rb=cp.get("morph_close_iter",1)
                if op_i_rb>0: mask_rb=cv2.morphologyEx(mask_rb,cv2.MORPH_OPEN,np.ones((op_k_rb,op_k_rb),np.uint8),iterations=op_i_rb)
                if di_i_rb>0: mask_rb=cv2.dilate(mask_rb,np.ones((di_k_rb,di_k_rb),np.uint8),iterations=di_i_rb)
                if cl_i_rb>0: mask_rb=cv2.morphologyEx(mask_rb,cv2.MORPH_CLOSE,np.ones((cl_k_rb,cl_k_rb),np.uint8),iterations=cl_i_rb)
                contours_rb, _ = cv2.findContours(mask_rb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                min_a_rb,max_a_rb=cp.get("area_min",100),cp.get("area_max",700)
                circ_t_rb,sol_t_rb=cp.get("circularity",0.6),cp.get("solidity",0.6)
                c_min_a, c_max_a = cp.get("cluster_area_min",600), cp.get("cluster_area_max",6000)
                c_min_ar, c_max_ar = cp.get("cluster_min_aspect_ratio",0.15), cp.get("cluster_max_aspect_ratio",6.0)
                for cnt_rb in contours_rb:
                    M=cv2.moments(cnt_rb)
                    if M["m00"]==0: continue
                    cx_rb,cy_rb=int(M["m10"]/M["m00"]),int(M["m01"]/M["m00"])
                    if (cx_rb-primary_jack_center_px[0])**2 + (cy_rb-primary_jack_center_px[1])**2 > search_radius_sq_px: continue
                    area_rb = cv2.contourArea(cnt_rb)
                    is_single_ball = False
                    if min_a_rb <= area_rb <= max_a_rb:
                        perimeter_rb=cv2.arcLength(cnt_rb,True)
                        if perimeter_rb>0:
                            circ_rb=4*np.pi*area_rb/(perimeter_rb**2)
                            (x_rb,y_rb),rad_rb=cv2.minEnclosingCircle(cnt_rb)
                            hull_rb=cv2.convexHull(cnt_rb); hull_a_rb=cv2.contourArea(hull_rb)
                            sol_rb = float(area_rb)/hull_a_rb if hull_a_rb>0 else 0
                            if circ_rb >= circ_t_rb and sol_rb >= sol_t_rb:
                                conf_rb = circ_rb*0.5 + sol_rb*0.3 + min(1.0, area_rb/max_a_rb)*0.2
                                all_detected_objects_for_nms.append({
                                    "bbox":(int(x_rb-rad_rb),int(y_rb-rad_rb),int(x_rb+rad_rb),int(y_rb+rad_rb)),
                                    "confidence":conf_rb, "center":(int(x_rb),int(y_rb)), "radius":int(rad_rb),
                                    "color_name":color_name, "shape_type":"circle", "area":area_rb
                                })
                                is_single_ball = True
                    if not is_single_ball and c_min_a <= area_rb <= c_max_a:
                        x_br, y_br, w_br, h_br = cv2.boundingRect(cnt_rb)
                        aspect_ratio_br = float(w_br)/h_br if h_br > 0 else 0.0
                        inv_aspect_ratio_br = float(h_br)/w_br if w_br > 0 else 0.0
                        is_valid_aspect = (c_min_ar <= aspect_ratio_br <= c_max_ar) or \
                                          (c_min_ar <= inv_aspect_ratio_br <= c_max_ar)
                        if is_valid_aspect:
                            conf_cl = 0.4 + min(1.0, (area_rb - c_min_a) / (c_max_a - c_min_a + 1e-6)) * 0.6
                            all_detected_objects_for_nms.append({
                                "bbox":(x_br,y_br,x_br+w_br,y_br+h_br), "rect_coords": (x_br,y_br,w_br,h_br),
                                "confidence":conf_cl, "center":(cx_rb,cy_rb),
                                "color_name":color_name, "shape_type":"rectangle", "area":area_rb
                            })
        elif not self.ball_detected: self.ball_status_str.set("Ball: White not found")
        self.ball_all = []
        if all_detected_objects_for_nms:
            boxes_nms = []; confs_nms = []; orig_indices = []
            for i, obj in enumerate(all_detected_objects_for_nms):
                x1,y1,x2,y2 = obj["bbox"]; boxes_nms.append([x1,y1,x2-x1,y2-y1]); confs_nms.append(obj["confidence"]); orig_indices.append(i)
            if boxes_nms:
                try:
                    nms_idx = cv2.dnn.NMSBoxes(boxes_nms, np.array(confs_nms).astype(np.float32),
                                               self.active_detection_params.get("detection_threshold_nms",0.01),
                                               self.active_detection_params.get("nms_overlap_threshold",0.3))
                    if isinstance(nms_idx, np.ndarray):
                        if nms_idx.ndim > 1: nms_idx = nms_idx.flatten()
                        for idx_val in nms_idx: self.ball_all.append(all_detected_objects_for_nms[orig_indices[idx_val]])
                except Exception as e_nms: print(f"NMS Error: {e_nms}"); self.ball_all = all_detected_objects_for_nms
        if self.ball_detected and best_hsv_white_ball_for_primary:
            is_pri_in_list = any(b.get("is_primary_white",False) for b in self.ball_all)
            if not is_pri_in_list:
                for b_obj in self.ball_all:
                    if b_obj["color_name"]=="white" and b_obj.get("is_primary_white"): b_obj["is_primary_white"]=False
                self.ball_all.append(best_hsv_white_ball_for_primary)
        if not self.ball_all and not self.ball_detected and not self.ball_status_str.get().startswith("Ball: Define 4"):
             self.ball_status_str.set("Ball: None found")

    def update_main_canvas_display(self):
        # Define a default aspect ratio for placeholders (e.g., 3:4 for vertical if camera is usually vertical)
        # This is used when the actual mask's aspect ratio cannot be determined (e.g., mask is empty)
        default_placeholder_aspect_ratio = 3.0 / 4.0  # width / height, adjust as needed

        # Handle the main canvas (self.canvas)
        if self.preview is None or self.preview.size == 0:
            if hasattr(self.canvas, "winfo_exists") and self.canvas.winfo_exists():
                self.canvas.delete("all")
                cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
                if cw <= 1 or ch <= 1:  # Fallback
                    try:
                        cw = int(self.canvas.cget("width"))
                        ch = int(self.canvas.cget("height"))
                    except:
                        cw, ch = 600, 400 # Absolute fallback
                if cw > 1 and ch > 1:
                    self.canvas.create_text(cw // 2, ch // 2, text="No image / Camera off", font=("Arial", 14), fill="black")
            
            # Display placeholder for combined mask when no main preview
            if hasattr(self.combined_mask_label, "winfo_exists") and self.combined_mask_label.winfo_exists():
                target_display_height = self.COMBINDED_MASK_DIM
                placeholder_w = int(target_display_height * default_placeholder_aspect_ratio)
                if placeholder_w <= 0: placeholder_w = 1
                
                # Check if self.current_hsv_combined_mask_display exists and has valid shape to get its aspect ratio
                # Otherwise, use the default placeholder aspect ratio
                aspect_to_use = default_placeholder_aspect_ratio
                if hasattr(self, "current_hsv_combined_mask_display") and \
                   self.current_hsv_combined_mask_display is not None and \
                   self.current_hsv_combined_mask_display.ndim >= 2 and \
                   self.current_hsv_combined_mask_display.shape[0] > 0 and \
                   self.current_hsv_combined_mask_display.shape[1] > 0:
                    orig_h, orig_w = self.current_hsv_combined_mask_display.shape[:2]
                    aspect_to_use = orig_w / orig_h
                    placeholder_w = int(target_display_height * aspect_to_use)
                    if placeholder_w <= 0: placeholder_w = 1

                _blank_mask_img = Image.new("RGB", (placeholder_w, target_display_height), "black")
                self.combined_mask_photo = ImageTk.PhotoImage(image=_blank_mask_img)
                self.combined_mask_label.config(image=self.combined_mask_photo)
            return

        # If we have a preview image, draw it and its overlays
        draw_preview = self.preview.copy()

        # Draw field points (Your existing code for this is fine)
        for i, pt_orig in enumerate(self.field_pts):
            if pt_orig is None or len(pt_orig) != 2: continue
            x_prev, y_prev = int(pt_orig[0] * self.PREVIEW_SCALE), int(pt_orig[1] * self.PREVIEW_SCALE)
            cv2.circle(draw_preview, (x_prev, y_prev), 4, (0, 255, 0), -1)
            cv2.putText(draw_preview, str(i + 1), (x_prev + 5, y_prev + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # Draw all detected balls/objects (Your existing code for this is fine)
        ball_draw_colors = {"white": (230, 230, 230), "red": (0, 0, 255), "blue": (255, 100, 100), "default": (0, 200, 0)}
        for det_obj in self.ball_all:
            if not isinstance(det_obj, dict): continue
            center_orig = det_obj.get("center")
            if center_orig is None or len(center_orig) != 2: continue
            color_name = det_obj.get("color_name", "default")
            shape_type = det_obj.get("shape_type", "circle")
            center_prev = (int(center_orig[0] * self.PREVIEW_SCALE), int(center_orig[1] * self.PREVIEW_SCALE))
            draw_clr = ball_draw_colors.get(color_name, ball_draw_colors["default"])
            if shape_type == "circle":
                radius_orig = det_obj.get("radius", 5)
                radius_prev = int(max(2, radius_orig * self.PREVIEW_SCALE))
                cv2.circle(draw_preview, center_prev, radius_prev, draw_clr, 1)
                label_txt = f"{color_name[0].upper()}"
                if det_obj.get("is_primary_white"): label_txt = "Jack"
                cv2.putText(draw_preview, label_txt, (center_prev[0] - radius_prev // 2, center_prev[1] - radius_prev - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, draw_clr, 1)
            elif shape_type == "rectangle":
                rect_coords = det_obj.get("rect_coords")
                if rect_coords and len(rect_coords) == 4:
                    x_br, y_br, w_br, h_br = rect_coords
                    x1_p, y1_p = int(x_br * self.PREVIEW_SCALE), int(y_br * self.PREVIEW_SCALE)
                    x2_p, y2_p = int((x_br + w_br) * self.PREVIEW_SCALE), int((y_br + h_br) * self.PREVIEW_SCALE)
                    cv2.rectangle(draw_preview, (x1_p, y1_p), (x2_p, y2_p), draw_clr, 1)
                    cv2.putText(draw_preview, f"{color_name[0].upper()}Cl", (x1_p, y1_p - 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.3, draw_clr, 1)

        # Draw primary white ball marker (Jack) if detected (Your existing code is fine)
        if self.ball_detected and self.ball_pt1 and len(self.ball_pt1) == 2:
            p1_mx, p1_my = int(self.ball_pt1[0] * self.PREVIEW_SCALE), int(self.ball_pt1[1] * self.PREVIEW_SCALE)
            cv2.drawMarker(draw_preview, (p1_mx, p1_my), (255, 255, 0), markerType=cv2.MARKER_CROSS, markerSize=8, thickness=1)

        # Convert and display the main preview image
        try:
            img_pil_canvas = Image.fromarray(cv2.cvtColor(draw_preview, cv2.COLOR_BGR2RGB))
            self.canvas_photo = ImageTk.PhotoImage(image=img_pil_canvas)
            if hasattr(self.canvas, "winfo_exists") and self.canvas.winfo_exists():
                self.canvas.create_image(0, 0, anchor=NW, image=self.canvas_photo)
        except Exception as e:
            print(f"Error updating main canvas image: {e}")
            # traceback.print_exc()

        # MODIFIED SECTION: Handle the combined mask display with aspect ratio preservation
        if hasattr(self, "current_hsv_combined_mask_display") and \
           self.current_hsv_combined_mask_display is not None and \
           self.current_hsv_combined_mask_display.size > 0:
            try:
                orig_h, orig_w = self.current_hsv_combined_mask_display.shape[:2]
                
                target_display_height = self.COMBINDED_MASK_DIM  # Use as target height

                if orig_h > 0 and orig_w > 0: 
                    aspect_ratio = orig_w / orig_h 
                    target_display_width = int(target_display_height * aspect_ratio)
                    if target_display_width <= 0: target_display_width = 1 
                    
                    mask_disp_resized = cv2.resize(self.current_hsv_combined_mask_display, 
                                                 (target_display_width, target_display_height), 
                                                 interpolation=cv2.INTER_NEAREST)
                else:
                    # Fallback if original mask dimensions are invalid (e.g., corrupted)
                    placeholder_w = int(target_display_height * default_placeholder_aspect_ratio)
                    if placeholder_w <= 0: placeholder_w = 1
                    mask_disp_resized = np.zeros((target_display_height, placeholder_w, 3), dtype=np.uint8)

                mask_rgb = cv2.cvtColor(mask_disp_resized, cv2.COLOR_BGR2RGB)
                mask_pil_tk = Image.fromarray(mask_rgb)
                self.combined_mask_photo = ImageTk.PhotoImage(image=mask_pil_tk)
                
                if hasattr(self.combined_mask_label, "winfo_exists") and self.combined_mask_label.winfo_exists():
                    self.combined_mask_label.config(image=self.combined_mask_photo)
            except Exception as e:
                print(f"Error resizing/displaying combined mask: {e}")
                # traceback.print_exc()
                if hasattr(self.combined_mask_label, "winfo_exists") and self.combined_mask_label.winfo_exists():
                    placeholder_h = self.COMBINDED_MASK_DIM
                    placeholder_w = int(placeholder_h * default_placeholder_aspect_ratio)
                    if placeholder_w <= 0: placeholder_w = 1
                    _error_mask_img = Image.new("RGB", (placeholder_w, placeholder_h), "darkred")
                    self.combined_mask_photo = ImageTk.PhotoImage(image=_error_mask_img)
                    self.combined_mask_label.config(image=self.combined_mask_photo)
        elif hasattr(self.combined_mask_label, "winfo_exists") and self.combined_mask_label.winfo_exists():
            # Handle case where current_hsv_combined_mask_display is None or empty from the start
            placeholder_h = self.COMBINDED_MASK_DIM
            placeholder_w = int(placeholder_h * default_placeholder_aspect_ratio)
            if placeholder_w <= 0: placeholder_w = 1
            _blank_mask_img = Image.new("RGB", (placeholder_w, placeholder_h), "black")
            self.combined_mask_photo = ImageTk.PhotoImage(image=_blank_mask_img)
            self.combined_mask_label.config(image=self.combined_mask_photo)

    def add_point(self, event):
        if self.img is None or self.preview is None: messagebox.showwarning("Add Point","No image."); return
        if not (0<=event.x<self.preview.shape[1] and 0<=event.y<self.preview.shape[0]): return
        if len(self.field_pts) < 4:
            Xo,Yo=int(event.x/self.PREVIEW_SCALE),int(event.y/self.PREVIEW_SCALE)
            if not (0<=Xo<self.img.shape[1] and 0<=Yo<self.img.shape[0]): return
            self.field_pts.append((Xo,Yo))
            self.corner_listbox.insert(END,f"P{len(self.field_pts)}: ({Xo},{Yo})")
            if len(self.field_pts)==4: self.has_last_known_plc_data=False; self.run_full_detection_cycle(False)
            else: self.update_main_canvas_display()
        else: messagebox.showinfo("Add Point","4 corners already set. Clear to reselect.")

    def remove_last_point(self):
        if self.field_pts:
            self.field_pts.pop(); self.corner_listbox.delete(END)
            if len(self.field_pts)<4:
                self.ball_pt1,self.ball_all,self.ball_detected=None,[],False
                self.current_hsv_combined_mask_display=self._generate_hsv_combined_mask_for_display()
                self.ball_status_str.set("Ball: Define 4 corners")
                self.update_measurement_display_default(); self.has_last_known_plc_data=False
            self.update_main_canvas_display()
        else: messagebox.showinfo("Remove Point","No points to remove.")

    def clear_points(self):
        if not self.field_pts: messagebox.showinfo("Clear Points","No points to clear."); return
        if messagebox.askyesno("Confirm Clear","Clear all field corner points?"):
            self.field_pts=[]; self.corner_listbox.delete(0,END)
            self.ball_pt1,self.ball_all,self.ball_detected=None,[],False
            self.current_hsv_combined_mask_display=self._generate_hsv_combined_mask_for_display()
            self.ball_status_str.set("Ball: Define 4 corners")
            self.update_main_canvas_display(); self.update_measurement_display_default(); self.has_last_known_plc_data=False

    def _float_to_rounded_int_word_list(self, float_val, value_name="value"):
        try:
            if float_val is None or math.isnan(float_val) or math.isinf(float_val): return [0]
            rnd_int = int(round(float_val))
            return [max(self.MIN_16BIT_SIGNED, min(self.MAX_16BIT_SIGNED, rnd_int))]
        except: return [0]

    def send_data_to_plc(self, dist_val, angle_val, swing_val, release_val):
        if not self.plc_connected or not self.pymc3e: return
        try:
            d_val = self._float_to_rounded_int_word_list(dist_val)[0]
            a_val = self._float_to_rounded_int_word_list(angle_val)[0]
            s_val = self._float_to_rounded_int_word_list(swing_val)[0]
            r_val = self._float_to_rounded_int_word_list(release_val)[0]
            self.pymc3e.randomwrite(
                word_devices=["D1", "D120", "D106", "D108"],
                word_values=[d_val, a_val, s_val, r_val],
                dword_devices=[], dword_values=[]
            )
            self._update_plc_gui_status("Data Sent", "green")
        except Exception as e_plc_tx:
            print(f"ERR: PLC write error: {e_plc_tx}")
            self.plc_connected = False
            self._update_plc_gui_status(f"Write Fail", "red")

    def process_measurements_for_realtime(self):
        if not self.ball_detected or self.ball_pt1 is None or len(self.field_pts)!=4: return None
        src=np.float32(self.field_pts)
        dst=np.float32([[0,0],[0,self.FIELD_H_CM],[self.FIELD_W_CM,0],[self.FIELD_W_CM,self.FIELD_H_CM]])
        H_mat = None
        try: H_mat = cv2.getPerspectiveTransform(src,dst)
        except Exception: return None
        if H_mat is None: return None
        ball1_pix_np = np.float32([self.ball_pt1]).reshape(-1,1,2)
        ball1_cm_t = cv2.perspectiveTransform(ball1_pix_np,H_mat)
        if ball1_cm_t is None or ball1_cm_t.size==0: return None
        x1cm,y1cm = ball1_cm_t[0,0]
        try: x2cm,y2cm = float(self.target_x_cm_str.get()), float(self.target_y_cm_str.get())
        except ValueError: x2cm,y2cm = 0.0,0.0
        dx_cm,dy_cm = x2cm-x1cm, y2cm-y1cm
        dist_cm = math.sqrt(dx_cm**2 + dy_cm**2)
        ang_rad = math.atan2(dx_cm,dy_cm)
        ang_deg = math.degrees(ang_rad)
        if ang_deg < 0: ang_deg += 360.0
        return {"x1_cm":x1cm,"y1_cm":y1cm,"x2_cm":x2cm,"y2_cm":y2cm,
                "distance_cm":dist_cm,"angle_degrees":ang_deg,
                "ball1_original_px":self.ball_pt1,"H_matrix":H_mat}

    def update_measurement_display(self, data_dict):
        if data_dict and isinstance(data_dict, dict):
            dist_disp = data_dict.get("distance_cm_final", data_dict.get("distance_cm"))
            ang_disp = data_dict.get("angle_degrees_final", data_dict.get("angle_degrees"))
            if dist_disp is not None: self.distance_display_str.set(f"Dist: {dist_disp:.1f} cm")
            else: self.distance_display_str.set("Dist: Error")
            if ang_disp is not None: self.angle_display_str.set(f"Angle: {ang_disp:.1f}°")
            else: self.angle_display_str.set("Angle: Error")
        else: self.update_measurement_display_default()

    def update_measurement_display_default(self):
        self.distance_display_str.set("Distance: N/A"); self.angle_display_str.set("Angle: N/A")
        self.swing_speed_display_str.set("Swing speed: N/A"); self.release_position_display_str.set("Release pos.: N/A")

    def show_detailed_results_window(self, measurement_data):
        if not measurement_data or not isinstance(measurement_data,dict): return
        x1,y1,x2,y2,dist,angle,ball1_px,H_mat = (measurement_data.get(k) for k in ["x1_cm","y1_cm","x2_cm","y2_cm","distance_cm","angle_degrees","ball1_original_px","H_matrix"])
        if any(v is None for v in [x1,y1,x2,y2,dist,angle,ball1_px,H_mat]): messagebox.showerror("Results Data","Incomplete data."); return
        warp_w,warp_h=int(self.FIELD_W_CM),int(self.FIELD_H_CM)
        max_dim=500; scale_f=1.0
        if warp_w<=0 or warp_h<=0: messagebox.showerror("Field Err","Field dims must be positive."); return
        if warp_w>max_dim or warp_h>max_dim: scale_f=min(max_dim/warp_w,max_dim/warp_h)
        disp_w,disp_h=max(1,int(warp_w*scale_f)),max(1,int(warp_h*scale_f))
        if self.img is None: messagebox.showerror("Image Err","Original image not available."); return
        warped_nat = cv2.warpPerspective(self.img,H_mat,(warp_w,warp_h))
        if warped_nat is None or warped_nat.size==0: messagebox.showerror("Warp Err","Failed to warp image."); return
        pt1d=(int(x1*scale_f),int(y1*scale_f)); pt2d=(int(x2*scale_f),int(y2*scale_f))
        warped_disp = cv2.resize(warped_nat,(disp_w,disp_h),interpolation=cv2.INTER_LINEAR)
        cv2.circle(warped_disp,pt1d,max(2,int(5*scale_f)),(0,0,255),-1)
        cv2.putText(warped_disp,"Jack",(pt1d[0]+3,pt1d[1]-3),cv2.FONT_HERSHEY_SIMPLEX,0.4*scale_f,(255,255,255),max(1,int(1*scale_f)))
        cv2.circle(warped_disp,pt2d,max(2,int(5*scale_f)),(0,255,0),-1)
        cv2.putText(warped_disp,"T",(pt2d[0]+3,pt2d[1]-3),cv2.FONT_HERSHEY_SIMPLEX,0.4*scale_f,(255,255,255),max(1,int(1*scale_f)))
        cv2.arrowedLine(warped_disp,pt1d,pt2d,(255,255,255),max(1,int(1*scale_f)))
        res_win=Toplevel(self.root); res_win.title("Measurement Details"); res_win.grab_set()
        res_win.top_view_photo=ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(warped_disp,cv2.COLOR_BGR2RGB)))
        Label(res_win,text="Field Top View (Scaled)",font=("Arial",10)).pack(pady=3)
        Label(res_win,image=res_win.top_view_photo).pack(pady=5,padx=5)
        res_f=Frame(res_win); res_f.pack(pady=5,padx=5,fill=X)
        sfont=("Arial",9); sfont_bold = ("Arial", 9, "bold")
        Label(res_f,text=f"P1 (Jack) Original Pixel: {ball1_px}",font=sfont).pack(anchor=W)
        Label(res_f,text=f"P1 Field Coords (cm): ({x1:.1f}, {y1:.1f})",font=sfont_bold).pack(anchor=W)
        Label(res_f,text=f"Target Field Coords (cm): ({x2:.1f}, {y2:.1f})",font=sfont).pack(anchor=W)
        ttk.Separator(res_f,orient="horizontal").pack(fill="x",pady=3)
        Label(res_f,text=f"Distance to Target: {dist:.1f} cm",font=sfont_bold).pack(anchor=W)
        Label(res_f,text=f"Angle to Target (from +Y, CW): {angle:.1f}°",font=sfont_bold).pack(anchor=W)
        Button(res_win,text="Close",command=res_win.destroy,width=8).pack(pady=5)
        res_win.resizable(False,False)

    def open_calibration_window(self):
        if self.img is None: messagebox.showwarning("Calibration","Open image/camera first."); return
        if self.calibration_window_open and self.calibration_window:
            try:
                if self.calibration_window.winfo_exists():
                    self.calibration_window.lift(); self.calibration_window.refresh_all_mask_displays(); return
                else: self.calibration_window_open=False; self.calibration_window=None
            except TclError: self.calibration_window_open=False; self.calibration_window=None
        self.calibration_window = CalibrationWindow(self); self.calibration_window_open=True

    def initiate_hsv_color_pick_for_params(self, color_name):
        if self.img is None: messagebox.showwarning("Pick Color",f"Open image/camera to pick {color_name}."); return
        if self.STATUS_CLICK_COLOR_INFO_MODE: self.toggle_info_color_pick_mode() # Will print to console now
        current_picking = getattr(self, "picking_hsv_for_color", None)
        if current_picking == color_name:
            self.canvas.config(cursor=""); self.picking_hsv_for_color = None; return
        self.picking_hsv_for_color = color_name; self.canvas.config(cursor="plus")
        messagebox.showinfo("Pick Color for Params",f"Click on a {color_name} ball to set its HSV params. Click '{color_name.capitalize()}' button again to cancel.")

    def process_hsv_color_pick(self, event):
        color_name_picked = getattr(self, "picking_hsv_for_color", None)
        if self.preview is None or color_name_picked is None:
            if color_name_picked: pass
            self.canvas.config(cursor=""); self.picking_hsv_for_color=None; return
        self.canvas.config(cursor=""); self.picking_hsv_for_color=None
        if not (0<=event.x<self.preview.shape[1] and 0<=event.y<self.preview.shape[0]): messagebox.showwarning("Pick Error","Clicked outside preview."); return
        Xo,Yo=int(event.x/self.PREVIEW_SCALE),int(event.y/self.PREVIEW_SCALE)
        if not (0<=Xo<self.img.shape[1] and 0<=Yo<self.img.shape[0]): messagebox.showwarning("Pick Error","Clicked outside original image."); return
        patch_sz=self.color_pick_patch_size_var.get(); patch_sz=max(3,patch_sz+(1 if patch_sz%2==0 else 0))
        half_p=patch_sz//2
        ys,ye=max(0,Yo-half_p),min(self.img.shape[0],Yo+half_p+1)
        xs,xe=max(0,Xo-half_p),min(self.img.shape[1],Xo+half_p+1)
        bgr_patch=self.img[ys:ye,xs:xe]
        if bgr_patch.size==0: messagebox.showwarning("Pick Error","Selected patch empty."); return
        hsv_patch=cv2.cvtColor(bgr_patch,cv2.COLOR_BGR2HSV)
        hp,sp,vp = int(np.median(hsv_patch[:,:,0])),int(np.median(hsv_patch[:,:,1])),int(np.median(hsv_patch[:,:,2]))
        target_params = self.active_detection_params["colors"][color_name_picked]
        h_del,s_del,v_del = (10 if color_name_picked=="red" else 15), 70, 70
        s_min_th,v_min_th = 50,50
        if color_name_picked == "white":
            picked_hsv_lower = np.array([0, 0, max(100, vp - 60)])
            picked_hsv_upper = np.array([179, min(80, sp + 50), 255])
            target_params["hsv_ranges"] = [(picked_hsv_lower, picked_hsv_upper)]
        elif color_name_picked == "red":
            ranges = []
            lh1, uh1 = hp - h_del, hp + h_del
            ls, us = max(s_min_th, sp-s_del), min(255, sp+s_del)
            lv, uv = max(v_min_th, vp-v_del), min(255, vp+v_del)
            if lh1 < 0:
                ranges.append((np.array([max(0,179+lh1),ls,lv]), np.array([179,us,uv])))
                ranges.append((np.array([0,ls,lv]), np.array([min(179,uh1),us,uv])))
            elif uh1 > 179:
                ranges.append((np.array([max(0,lh1),ls,lv]), np.array([179,us,uv])))
                ranges.append((np.array([0,ls,lv]), np.array([min(179,uh1-179),us,uv])))
            else:
                ranges.append((np.array([max(0,lh1),ls,lv]), np.array([min(179,uh1),us,uv])))
            target_params["hsv_ranges"] = ranges
        else:
            lh,uh=max(0,hp-h_del),min(179,hp+h_del)
            ls,us=max(s_min_th,sp-s_del),min(255,sp+s_del)
            lv,uv=max(v_min_th,vp-v_del),min(255,vp+v_del)
            target_params["hsv_ranges"]=[(np.array([lh,ls,lv]),np.array([uh,us,uv]))]
        messagebox.showinfo("Pick Success",f"HSV for '{color_name_picked}' updated. Open Adv. Calib to fine-tune.")
        if self.calibration_window_open and self.calibration_window and self.calibration_window.winfo_exists():
            self.calibration_window.calib_params["colors"][color_name_picked]=copy.deepcopy(target_params)
            self.calibration_window.load_params_to_ui()
            self.calibration_window.refresh_mask_display(color_name_picked); self.calibration_window.lift()
        if self.img is not None: self.run_full_detection_cycle(False)

    def reset_state_for_new_image_or_camera(self):
        self.field_pts=[]; self.ball_pt1=None; self.ball_all=[]; self.ball_detected=False
        if hasattr(self,"ball_status_str"): self.ball_status_str.set("Ball: Not detected")
        if hasattr(self,"corner_listbox"): self.corner_listbox.delete(0,END)
        # if hasattr(self,"capture_btn") and self.capture_btn.winfo_exists():
            # self.capture_btn.config(state=NORMAL if self.camera_mode else DISABLED)
        self.update_measurement_display_default(); self.has_last_known_plc_data=False
        self.sent_last_data_after_disappearance=False
        self.current_hsv_combined_mask_display = self._generate_hsv_combined_mask_for_display()
        self.picked_color_info_list = []
        self.selecting_red_team_point = False
        self.red_team_selected_point = None
        self.red_team_xy_var.set("Red Jack Target X:-, Y:-")


    def update_loupe_and_coords(self, event):
        if self.img is None or self.preview is None or self.preview.size==0:
            if hasattr(self.coord_label,"winfo_exists"): self.coord_label.config(text="Cursor: X: -, Y: -")
            if hasattr(self.loupe_label,"winfo_exists") and self.loupe_label.winfo_exists():
                if not hasattr(self, "_blank_loupe_photo_ref"):
                    _b_loupe = Image.new("RGB",(self.LOUPE_DIM,self.LOUPE_DIM),"lightgrey") # LOUPE_DIM is now 240
                    self._blank_loupe_photo_ref = ImageTk.PhotoImage(image=_b_loupe)
                self.loupe_label.config(image=self._blank_loupe_photo_ref)
            return
        prev_h,prev_w=self.preview.shape[:2]
        if 0<=event.x<prev_w and 0<=event.y<prev_h:
            self.cursor_preview=(event.x,event.y)
            if hasattr(self.coord_label,"winfo_exists"): self.coord_label.config(text=f"Cursor: X:{event.x}, Y:{event.y}")
            Xo,Yo=int(event.x/self.PREVIEW_SCALE),int(event.y/self.PREVIEW_SCALE)
            if not(0<=Xo<self.img.shape[1] and 0<=Yo<self.img.shape[0]): return
            h_loupe_o = int(self.LOUPE_DIM/(2*self.LOUPE_SCALE)) # LOUPE_DIM is now 240
            x1,y1=max(0,Xo-h_loupe_o),max(0,Yo-h_loupe_o)
            x2,y2=min(self.img.shape[1],Xo+h_loupe_o),min(self.img.shape[0],Yo+h_loupe_o)
            patch = self.img[y1:y2,x1:x2]
            if patch.size==0: patch=np.full((self.LOUPE_DIM//int(self.LOUPE_SCALE),self.LOUPE_DIM//int(self.LOUPE_SCALE),3),128,dtype=np.uint8)
            loupe_res = cv2.resize(patch,(self.LOUPE_DIM,self.LOUPE_DIM),interpolation=cv2.INTER_NEAREST) # LOUPE_DIM is now 240
            cv2.circle(loupe_res,(self.LOUPE_DIM//2,self.LOUPE_DIM//2),self.TARGET_RADIUS,self.TARGET_COLOR,-1)
            cv2.rectangle(loupe_res,(0,0),(self.LOUPE_DIM-1,self.LOUPE_DIM-1),self.LOUPE_BORDER_COLOR,self.LOUPE_BORDER)
            self.loupe_photo=ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(loupe_res,cv2.COLOR_BGR2RGB)))
            if hasattr(self.loupe_label,"winfo_exists") and self.loupe_label.winfo_exists():
                self.loupe_label.config(image=self.loupe_photo)
        else:
            if hasattr(self.coord_label,"winfo_exists"): self.coord_label.config(text="Cursor: X: -, Y: -")

    def on_closing(self):
        print("Closing application...")
        self.running=False; self.plc_attempt_reconnect=False
        self.stop_camera_if_running()
        if self.pymc3e and self.plc_connected:
            try: self.pymc3e.close()
            except Exception as e_plc_close: print(f"Err closing PLC: {e_plc_close}")
        self.plc_connected=False
        if self.calibration_window_open and self.calibration_window:
            try:
                if self.calibration_window.winfo_exists(): self.calibration_window.destroy()
            except: pass
        self.calibration_window=None; self.calibration_window_open=False
        if hasattr(self.root,"destroy") and self.root.winfo_exists(): self.root.destroy()
        print("Application closed.")

    def start_red_team_select_mode(self):
        self.selecting_red_team_point = True
        messagebox.showinfo("Red Jack Target", "Click on the image to select the Red Team's Jack ball target point.")
        self.canvas.config(cursor="target")

    def red_team(self):
        if not self.pymc3e or not self.plc_connected:
            messagebox.showwarning("PLC Error", "PLC not connected. Cannot send Red Jack command.")
            print("PLC is not connected. Cannot process Red Jack command.")
            return

        try:
            # --- Get pulse_offset_val --- Start MODIFIED
            pulse_offset_val = 0
            try:
                if hasattr(self, 'pulse_offset_var') and isinstance(self.pulse_offset_var, StringVar):
                    pulse_offset_val = int(self.pulse_offset_var.get())
                else:
                    print(f"Warning: pulse_offset_var not initialized correctly in red_team. Using 0.")
            except ValueError:
                if hasattr(self, 'pulse_offset_var') and isinstance(self.pulse_offset_var, StringVar):
                    print(f"Warning: Invalid pulse_offset value in red_team: '{self.pulse_offset_var.get()}'. Using 0.")
                else:
                    print(f"Warning: Invalid pulse_offset value (pulse_offset_var not available) in red_team. Using 0.")
                pass # Default to 0 if conversion fails
            # --- Get pulse_offset_val --- End MODIFIED

            m300_read = self.pymc3e.batchread_wordunits(headdevice="M300", readsize=1)
            m300_value = m300_read[0] if m300_read else -1
            print(f"M300 Read for Red Jack: {m300_value}")

            if m300_value != 0:
                print("PLC indicates RED TEAM mode active for Jack throw (M300 indicates Red).")
                d130_read = self.pymc3e.batchread_wordunits(headdevice="D130", readsize=1)
                d130_value = d130_read[0] if d130_read else -1
                print(f"D130 Read for Red Jack: {d130_value}")

                if d130_value == 0:
                    print("PLC indicates ball count is 0 (D130 == 0). Proceeding with Red Jack command.")

                    if not self.red_team_selected_point:
                        messagebox.showerror("Red Jack Error", "Red Jack target point not selected on the image.")
                        print("Red Jack target point not selected on image.")
                        return

                    if len(self.field_pts) != 4:
                        messagebox.showerror("Field Error", "Field corners not defined. Cannot transform point for Red Jack command.")
                        print("Field corners not defined. Cannot transform point for Red Jack command.")
                        return

                    src_pts = np.float32(self.field_pts)
                    dst_pts = np.float32([[0, 0], [0, self.FIELD_H_CM], [self.FIELD_W_CM, 0], [self.FIELD_W_CM, self.FIELD_H_CM]])

                    H_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    if H_matrix is None:
                        messagebox.showerror("Transform Error", "Failed to get perspective transform for Red Jack command.")
                        print("Failed to get perspective transform for Red Jack command.")
                        return

                    rt_pixel_x, rt_pixel_y = self.red_team_selected_point
                    rt_pixel_np = np.float32([[rt_pixel_x, rt_pixel_y]]).reshape(-1, 1, 2)
                    rt_cm_transformed = cv2.perspectiveTransform(rt_pixel_np, H_matrix)

                    if rt_cm_transformed is None or rt_cm_transformed.size == 0:
                        messagebox.showerror("Transform Error", "Failed to transform Red Jack selected point to field coordinates.")
                        print("Failed to transform Red Jack selected point.")
                        return

                    x_rt_cm, y_rt_cm = rt_cm_transformed[0, 0]
                    print(f"Red Jack Picked Point (Pixel): ({rt_pixel_x},{rt_pixel_y}), Transformed to Field (cm): ({x_rt_cm:.1f}, {y_rt_cm:.1f})")

                    try:
                        robot_x_cm = float(self.target_x_cm_str.get())
                        robot_y_cm = float(self.target_y_cm_str.get())
                        print(f"Robot's Throwing Position (cm from UI): ({robot_x_cm:.1f}, {robot_y_cm:.1f})")
                    except ValueError:
                        messagebox.showerror("Input Error", "Invalid robot target (throwing origin) coordinates for Red Jack command.")
                        print("Invalid robot target coordinates for Red Jack command.")
                        return

                    delta_x = x_rt_cm - robot_x_cm
                    delta_y = y_rt_cm - robot_y_cm

                    distance_to_rt_pt = math.sqrt(delta_x**2 + delta_y**2)
                    angle_to_rt_pt_rad = math.atan2(delta_x, delta_y)
                    angle_to_rt_pt_deg = math.degrees(angle_to_rt_pt_rad)-180
                    print(angle_to_rt_pt_deg)
                    if angle_to_rt_pt_deg < 0:
                        angle_to_rt_pt_deg += 360.0

                    # MODIFIED: swing_plc calculation uses pulse_offset_val
                    swing_plc = (distance_to_rt_pt * 24.096) + 5900 + pulse_offset_val
                    swing_plc = max(0, min(swing_plc, 23000))
                    release_plc = 800

                    print(f"Red Jack Cmd Calculation: Dist Robot to PickedPt: {distance_to_rt_pt:.1f} cm, Angle: {angle_to_rt_pt_deg:.1f} deg")
                    print(f"Values for PLC - Angle(D120): {angle_to_rt_pt_deg:.0f}, Swing(D106): {swing_plc:.0f}, Release(D108): {release_plc:.0f}")

                    self.pymc3e.randomwrite(
                        word_devices=["D120", "D106", "D108"],
                        word_values=[
                            self._float_to_rounded_int_word_list(angle_to_rt_pt_deg)[0],
                            self._float_to_rounded_int_word_list(swing_plc)[0],
                            self._float_to_rounded_int_word_list(release_plc)[0]
                        ],
                        dword_devices=[], dword_values=[]
                    )
                    print(f"Red Jack command data sent to PLC: Angle={angle_to_rt_pt_deg:.1f}°, Swing={swing_plc:.0f}, Release={release_plc:.0f}")
                    self._update_plc_gui_status("Red Jack Cmd Sent", "cyan")
                    # messagebox.showinfo("Red Jack Cmd", "Red Jack command sent to PLC.")

                else:
                    msg = "Red Team mode active (M300 indicates Red), but conditions not met for Jack throw (D130 != 0 or PLC read fail)."
                    print(msg)
                    if d130_value != 0 :
                         messagebox.showwarning("Red Jack Info", "Red Team mode active (M300 indicates Red), but ball count (D130) is not 0.")
                    else:
                         messagebox.showwarning("Red Jack Info", "Red Team Jack conditions not fully met or PLC read issue.")
            else:
                print("Not in Red Team mode for Jack throw (M300 does not indicate Red or M300 read failed). No action taken.")
                messagebox.showinfo("Team Status", "Not in Red Team mode for Jack throw (M300 is not 3).") # Assuming 3 was the original check logic intent
        except ValueError as ve:
            err_msg = f"Red Jack command error (ValueError): {str(ve)}"
            print(err_msg)
            messagebox.showerror("Red Jack Error", err_msg)
        except Exception as e_rt:
            err_msg = f"Error during Red Jack command execution: {str(e_rt)}"
            print(err_msg)
            traceback.print_exc()
            messagebox.showerror("Red Jack Error", err_msg)
            self._update_plc_gui_status("Red Jack Cmd Fail", "orange")


if __name__ == "__main__":
    root = Tk()
    root.geometry("1000x970") # Window size might need adjustment depending on new LOUPE_DIM
    app = FieldMeasureApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
