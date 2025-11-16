#!/usr/bin/env python3
# coding: utf-8
"""
big_main.py
Unified entry point for:
 - Face GUI + AI (chatbot / voice)
 - Camera modes (color, face, gesture, object, license plate)
 - Rock Paper Scissors game mode
 - IR remote control
 - Mode management & clean shutdown

Customize IR button codes in the CONFIG SECTION below.
"""

import os
import sys
import threading
import time
import tkinter as tk
import traceback
from typing import Optional

# Ensure CameraLib (and sibling loose modules) are importable even if their
# internal files use bare imports like `import color_tracking_lib`.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMERA_LIB_PATH = os.path.join(BASE_DIR, "CameraLib")
if CAMERA_LIB_PATH not in sys.path:
    sys.path.insert(0, CAMERA_LIB_PATH)

# Existing modules
from face_gui import MarichFaceApp, Config  # type: ignore
from chatbot_logic import run_chatbot, request_stop  # type: ignore
from CameraLib.camera_master_lib import CameraMaster  # type: ignore
from Raspbot_Lib import Raspbot  # type: ignore
# MODIFIED: Added trigger_beep
from robot_hardware import set_emotion_led, turn_off_led, stop as motor_stop, trigger_beep  # type: ignore
from rock_paper_scissors import run_rps_game, request_stop as rps_request_stop  # type: ignore
# --- NEW: Import presentation sequence ---
from presentation_sequence import run_presentation, request_stop as pres_request_stop # type: ignore
# --- END NEW ---


# ===================== CONFIG SECTION (EDIT THESE) =====================

# IR address register already used: read_data_array(0x0c,1)
# Assign HEX codes matching your remote.
IR_COLOR_RED = 0x01
IR_COLOR_BLUE = 0x04
IR_COLOR_GREEN = 0x06
IR_COLOR_YELLOW = 0x09
IR_FACE_MODE = 0x10
IR_GESTURE_MODE = 0x11
IR_OBJECT_MODE = 0x12
IR_PLATE_MODE = 0x14
IR_RPS_GAME = 0x19  # Rock Paper Scissors game mode
IR_PRESENTATION = 0x15 # --- NEW: Presentation Mode button ---
IR_AI_TOGGLE = 0x02  # Toggle AI (voice/chatbot) on/off
IR_STOP_ALL = 0x05  # Stop all camera modes + motors
IR_EXIT_APP = 0x00  # Exit whole application (remapped from 0x1A)

# Optional: debounce (seconds) to ignore repeated same code too fast
IR_DEBOUNCE_SEC = 0.4
IR_DEBUG = False  # Set True to log every non-zero IR code for mapping


# ======================================================================

class BigMainApp:
    def __init__(self):
        """Initialize lightweight shell; defer heavy subsystems until first IR command."""
        # Tk root & Face GUI (but don't start animation loops yet)
        self.root = tk.Tk()

        # --- FIX 1: Startup Crash ---
        # The MarichFaceApp __init__ in face_gui.py only takes `root` as an argument.
        # Passing width and height here was causing a TypeError on startup.
        # self.face_app = MarichFaceApp(self.root, Config.CANVAS_WIDTH, Config.CANVAS_HEIGHT)
        self.face_app = MarichFaceApp(self.root)
        # --- END FIX 1 ---

        # Hide the face GUI at startup - only show when AI is enabled
        try:
            self.face_app.suspend()
        except Exception:
            pass

        # Camera manager (lazy). Create on first mode activation.
        self.camera = None  # type: Optional[CameraMaster]
        self._camera_initialized = False
        self._camera_shutting_down = False

        # Animation lazy flag
        self._animations_started = False

        # Hardware (IR + servos + motors)
        self.bot = Raspbot()
        self.bot.Ctrl_IR_Switch(1)  # Enable IR receiver

        # State
        self.active_mode = None  # 'color','face','gesture','object','plate','rps','presentation'
        self.active_color = None  # Current color when in color mode
        self.ai_enabled = False  # Start with AI OFF; toggle via IR
        self.chatbot_thread = None
        self._chatbot_stop_event = None
        self._chatbot_started = False
        self.rps_thread = None  # Rock Paper Scissors game thread
        self._rps_stop_event = None
        self._rps_started = False
        
        # --- NEW: Presentation state ---
        self.presentation_thread = None
        self._presentation_stop_event = None
        self._presentation_started = False
        # --- END NEW ---
        
        self._stop_flag = threading.Event()
        self._ir_thread = None
        self._last_ir_code = 0
        self._last_ir_time = 0.0

        # Chatbot not started yet (lazy on IR toggle)

        # IR listener thread (lightweight)
        self._ir_thread = threading.Thread(target=self._ir_loop, daemon=True)
        self._ir_thread.start()

        # Periodic camera frame display loop (will be idle until camera created)
        self.root.after(200, self._camera_ui_loop)

        print("BigMainApp initialized. Idle (no camera, no animations, AI off). Awaiting IR commands...")
        self._print_help()

    # --------------- Chatbot Control ---------------
    def _start_chatbot_if_needed(self, suppress_greeting: bool = False):
        if self.ai_enabled and not self._chatbot_started:
            from threading import Event
            self._chatbot_stop_event = Event()
            self.chatbot_thread = threading.Thread(
                target=run_chatbot,
                args=(self.face_app, self._chatbot_stop_event, suppress_greeting),
                daemon=True,
                name="ChatbotThread"
            )
            self.chatbot_thread.start()
            self._chatbot_started = True
            print("[AI] Chatbot thread launched.")
        elif not self.ai_enabled:
            print("[AI] Chatbot remains disabled.")

    def _stop_chatbot_if_running(self):
        if self._chatbot_started and self._chatbot_stop_event:
            print("[AI] Stopping chatbot thread...")
            request_stop(self._chatbot_stop_event)
            # Give it a short grace period
            if self.chatbot_thread:
                self.chatbot_thread.join(timeout=2.0)
            self._chatbot_started = False
            self.chatbot_thread = None
            self._chatbot_stop_event = None
            print("[AI] Chatbot stopped.")

    # --------------- RPS Game Control ---------------
    def _start_rps_if_needed(self):
        """Start the Rock Paper Scissors game if not already running."""

        # --- FIX 2: AI vs RPS Conflict ---
        # Prevent starting RPS if AI mode is active.
        if self.ai_enabled or self._presentation_started: # MODIFIED: Also check presentation
            print("[MODE] Cannot start RPS game while AI or Presentation is enabled. Disable AI first.")
            return
        # --- END FIX 2 ---

        if not self._rps_started:
            # Stop any other modes first
            self._stop_all_camera_modes()

            # Ensure camera is initialized for RPS
            if not self._ensure_camera():
                print("[RPS] Cannot start game - camera unavailable.")
                return

            # --- FIX: Start gesture detection, but explicitly disable robot actions ---
            try:
                assert self.camera is not None
                # This creates the gesture_follower object needed for detection,
                # but passes enable_actions=False to prevent motors from moving.
                self.camera.start_gesture_following(enable_actions=False) 
                # We set active_mode so it can be correctly stopped later
                self.active_mode = 'gesture' 
            except Exception as e:
                print(f"[RPS] Warning: Could not start gesture following: {e}")
            # --- END FIX ---

            # Ensure animations are started for the face
            self._ensure_animations()

            # --- FIX 3: Face Not Showing in RPS ---
            # The face GUI is hidden (suspended) by default.
            # We must resume it here for it to be visible.
            try:
                self.face_app.resume()
                print("[RPS] Face GUI resumed.")
            except Exception as e:
                print(f"[RPS] Could not resume face GUI: {e}")
            # --- END FIX 3 ---

            from threading import Event
            self._rps_stop_event = Event()
            self.rps_thread = threading.Thread(
                target=run_rps_game,
                args=(self.face_app, self.camera, self._rps_stop_event),
                daemon=True,
                name="RPSGameThread"
            )
            self.rps_thread.start()
            self._rps_started = True
            self.active_mode = 'rps'
            print("[RPS] Rock Paper Scissors game thread launched.")

    def _stop_rps_if_running(self):
        """Stop the Rock Paper Scissors game if running."""
        if self._rps_started and self._rps_stop_event:
            print("[RPS] Stopping Rock Paper Scissors game...")
            rps_request_stop(self._rps_stop_event)
            # Give it a short grace period
            if self.rps_thread:
                self.rps_thread.join(timeout=2.0)
            self._rps_started = False
            self.rps_thread = None
            self._rps_stop_event = None
            if self.active_mode == 'rps' or self.active_mode == 'gesture':
                self.active_mode = None
            print("[RPS] Rock Paper Scissors game stopped.")

    # --- NEW: Presentation Mode Control ---
    def _start_presentation_mode(self):
        """Starts the Marich self-introduction sequence."""
        if self.ai_enabled or self._rps_started:
            print("[MODE] Cannot start presentation while AI or RPS is active.")
            return
        if self._presentation_started:
            print("[MODE] Presentation already running.")
            return

        self._stop_all_camera_modes() # Stop camera modes
        
        # We don't need the camera, but we need the face GUI and bot
        self._ensure_animations()
        try:
            self.face_app.resume()
            print("[Presentation] Face GUI resumed.")
        except Exception as e:
            print(f"[Presentation] Could not resume face GUI: {e}")

        from threading import Event
        self._presentation_stop_event = Event()
        self.presentation_thread = threading.Thread(
            target=run_presentation,
            # Pass the app, bot, and stop event
            args=(self.face_app, self.bot, self._presentation_stop_event),
            daemon=True,
            name="PresentationThread"
        )
        self.presentation_thread.start()
        self._presentation_started = True
        self.active_mode = 'presentation' # Set new active mode
        print("[Presentation] Presentation thread launched.")

    def _stop_presentation_if_running(self):
        """Stops the presentation sequence if it is running."""
        if self._presentation_started and self._presentation_stop_event:
            print("[Presentation] Stopping presentation...")
            pres_request_stop(self._presentation_stop_event)
            if self.presentation_thread:
                self.presentation_thread.join(timeout=2.0) # Wait for thread to cleanup
            self._presentation_started = False
            self.presentation_thread = None
            self._presentation_stop_event = None
            if self.active_mode == 'presentation':
                self.active_mode = None
            print("[Presentation] Presentation stopped.")
    # --- END NEW ---

    def _toggle_ai(self):
        self.ai_enabled = not self.ai_enabled
        if self.ai_enabled:
            print("[AI] Enabling AI - releasing camera if active and starting face/chatbot...")
            # Stop RPS game if it's running
            if self._rps_started:
                self._stop_rps_if_running()
            # --- NEW: Stop presentation if it's running ---
            if self._presentation_started:
                self._stop_presentation_if_running()
            # --- END NEW ---
                
            # Only release camera if it's actually running - AI and camera are mutually exclusive
            if self.camera is not None or self._camera_initialized:
                # Schedule camera release on main thread to avoid Qt threading issues
                self.root.after(10, self._release_camera_completely)
            else:
                # No camera to release, proceed directly
                self._start_ai_components()
        else:
            print("[AI] Disabling AI - stopping face/chatbot only...")
            self._stop_chatbot_if_running()
            # Hide GUI to save resources
            try:
                self.face_app.suspend()
            except Exception:
                pass
            self.face_app.set_emotion('neutral')
            # --- QoL SUGGESTION: Set LED for AI state ---
            turn_off_led()
            # --- END QoL SUGGESTION ---

    def _start_ai_components(self):
        """Start AI components after camera has been released"""
        print("[AI] Freeing up system memory for AI...")

        # Import subprocess at the beginning
        import subprocess

        # STEP 1: Ensure swap space is available for AI model loading
        print("[MEMORY] Ensuring swap space is available for AI model...")
        try:
            # Check current swap status
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            swap_available = False
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('Swap:'):
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] != '0B':
                            swap_available = True
                            print(f"[MEMORY] Swap already available: {parts[1]}")
                            break

            # If no swap available, create it automatically
            if not swap_available:
                print("[MEMORY] No swap detected - creating 4GB swap file...")

                # Create 4GB swap file if it doesn't exist
                if not os.path.exists('/swapfile'):
                    print("[MEMORY] Creating swap file...")
                    subprocess.run(['sudo', 'fallocate', '-l', '4G', '/swapfile'],
                                   check=False, capture_output=True)
                    subprocess.run(['sudo', 'chmod', '600', '/swapfile'],
                                   check=False, capture_output=True)
                    subprocess.run(['sudo', 'mkswap', '/swapfile'],
                                   check=False, capture_output=True)

                # Activate swap
                print("[MEMORY] Activating swap...")
                subprocess.run(['sudo', 'swapon', '/swapfile'],
                               check=False, capture_output=True)

                # Add to fstab if not already there
                try:
                    with open('/etc/fstab', 'r') as f:
                        fstab_content = f.read()
                    if '/swapfile' not in fstab_content:
                        print("[MEMORY] Making swap permanent...")
                        subprocess.run(['sudo', 'sh', '-c', "echo '/swapfile none swap sw 0 0' >> /etc/fstab"],
                                       check=False, capture_output=True)
                except Exception:
                    pass

                # Verify swap is now active
                result = subprocess.run(['free', '-h'], capture_output=True, text=True)
                if result.returncode == 0:
                    print("[MEMORY] Swap status after setup:")
                    print(result.stdout)

        except Exception as e:
            print(f"[MEMORY] Warning: Swap setup failed: {e}")
            print("[MEMORY] Continuing without swap (may cause memory issues)")

        # STEP 2: Free up system memory before starting AI
        try:
            import subprocess

            # Show memory before cleanup
            print("[MEMORY] Optimizing system memory...")
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    mem_line = lines[1].split()
                    if len(mem_line) >= 7:
                        print(f"[MEMORY] Available before cleanup: {mem_line[6]}")

            # Kill VS Code and other non-essential memory-heavy processes
            try:
                # Get all processes and find memory-heavy instances
                result = subprocess.run(['ps', '-eo', 'pid,comm,%mem', '--sort=-%mem', '--no-headers'],
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    processes_to_kill = []
                    current_python_pid = str(os.getpid())  # Don't kill our own process

                    # CRITICAL: Processes that should NEVER be killed (essential system processes)
                    protected_processes = {
                        'systemd', 'kthreadd', 'ksoftirqd', 'migration', 'rcu_', 'watchdog',
                        'sshd', 'ssh', 'NetworkManager', 'networkd', 'wpa_supplicant',
                        'dbus', 'dbus-daemon', 'systemd-', 'udev', 'rsyslog', 'cron',
                        'init', 'kernel', 'kworker', 'ksoftirq', 'migration', 'rcu_gp', 'rcu_par_gp',
                        'wayvnc', 'vnc', 'tigervnc', 'x11vnc', 'vncserver',  # VNC servers - KEEP THESE!
                        'Xwayland', 'labwc', 'weston', 'sway', 'wayfire',  # Display servers - KEEP THESE!
                        'pulseaudio', 'pipewire', 'wireplumber',  # Audio systems
                        'gdm', 'lightdm', 'sddm', 'login',  # Login managers
                        'bash', 'zsh', 'fish', 'sh',  # Shells - keep active shells
                        'getty', 'agetty',  # TTY processes
                        'dhcpcd', 'dhclient',  # Network DHCP
                        'avahi-daemon'  # Network discovery (might be needed)
                    }

                    killed_count = 0
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 3:
                            pid, comm, mem_percent = parts[0], parts[1], parts[2]
                            try:
                                mem_val = float(mem_percent)

                                # Skip our own Python process
                                if pid == current_python_pid:
                                    continue

                                # Check if process is protected (NEVER kill these)
                                is_protected = False
                                for protected in protected_processes:
                                    if protected in comm.lower():
                                        is_protected = True
                                        break

                                if is_protected:
                                    continue  # Skip protected processes

                                # Target ONLY specific safe memory-consuming processes
                                should_kill = False

                                # SAFE to kill: VS Code processes (development tool)
                                if comm == 'code':
                                    should_kill = True
                                # SAFE to kill: Web browsers (if running)
                                elif comm in ['chrome', 'firefox', 'chromium', 'brave']:
                                    should_kill = True
                                # SAFE to kill: Electron apps (often development tools)
                                elif comm in ['electron', 'atom', 'slack', 'discord']:
                                    should_kill = True
                                # SAFE to kill: Other Python processes ONLY if they use significant memory
                                elif comm == 'python3' and mem_val > 5.0:  # Higher threshold for python3
                                    should_kill = True
                                # SAFE to kill: Jupyter (development tool)
                                elif 'jupyter' in comm.lower():
                                    should_kill = True
                                # SAFE to kill: Docker (if running)
                                elif comm in ['docker', 'containerd']:
                                    should_kill = True
                                # SAFE to kill: Snap applications
                                elif comm.startswith('snap-') or '/snap/' in comm:
                                    should_kill = True
                                # SAFE to kill: Ollama server (can be restarted later)
                                elif comm == 'ollama' and mem_val > 3.0:
                                    should_kill = True

                                if should_kill:
                                    subprocess.run(['sudo', 'kill', '-15', pid], check=False, capture_output=True)
                                    time.sleep(0.1)
                                    subprocess.run(['sudo', 'kill', '-9', pid], check=False, capture_output=True)
                                    killed_count += 1

                            except ValueError:
                                continue

                    if killed_count > 0:
                        print(f"[MEMORY] Stopped {killed_count} memory-heavy processes")

                # Also try to stop VS Code service if it exists
                try:
                    subprocess.run(['sudo', 'systemctl', 'stop', 'code'], check=False, capture_output=True)
                    subprocess.run(['sudo', 'systemctl', 'disable', 'code'], check=False, capture_output=True)
                except Exception:
                    pass

            except Exception as e:
                print(f"[MEMORY] Process optimization: {e}")

            # Stop only non-essential services (NOT NetworkManager!)
            safe_services_to_stop = [
                #'bluetooth',  # Bluetooth - safe to stop temporarily
                'cups',  # Printing service - safe to stop
            ]

            stopped_services = 0
            for service in safe_services_to_stop:
                try:
                    # Check if service is active first
                    result = subprocess.run(['systemctl', 'is-active', service],
                                            capture_output=True, text=True)
                    if result.returncode == 0 and 'active' in result.stdout:
                        subprocess.run(['sudo', 'systemctl', 'stop', service],
                                       check=False, capture_output=True)
                        stopped_services += 1
                except Exception:
                    pass

            if stopped_services > 0:
                print(f"[MEMORY] Stopped {stopped_services} non-essential services")

            # System memory cleanup
            subprocess.run(['sudo', 'sync'], check=False, capture_output=True)
            subprocess.run(['sudo', 'sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'],
                           check=False, capture_output=True)

            # Additional memory optimizations
            try:
                subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /proc/sys/vm/compact_memory'],
                               check=False, capture_output=True)
                subprocess.run(['sudo', 'swapoff', '-a'], check=False, capture_output=True)
                time.sleep(0.5)
                subprocess.run(['sudo', 'swapon', '-a'], check=False, capture_output=True)
            except Exception:
                pass

            # Python garbage collection
            import gc
            for i in range(5):
                collected = gc.collect()
                if collected > 0 and i == 0:  # Only print first round
                    print(f"[MEMORY] Garbage collection freed {collected} objects")

            # Smart Python module management
            try:
                import sys
                safe_modules_patterns = [
                    'numpy', 'matplotlib', 'pandas', 'scipy', 'sklearn',
                    'requests', 'urllib3', 'certifi', 'chardet',
                    'PIL', 'Pillow', 'json', 'xml', 'html',
                    'argparse', 'configparser', 'logging'
                ]

                unloaded_count = 0
                for module_name in list(sys.modules.keys()):
                    if any(pattern in module_name.lower() for pattern in safe_modules_patterns):
                        if not any(
                                x in module_name.lower() for x in ['face_gui', 'chatbot', 'camera', 'tkinter', 'cv2']):
                            try:
                                if module_name in sys.modules:
                                    del sys.modules[module_name]
                                    unloaded_count += 1
                            except Exception:
                                pass
                            if unloaded_count >= 10:  # Limit to first 10
                                break

                if unloaded_count > 0:
                    print(f"[MEMORY] Unloaded {unloaded_count} unused modules")

            except Exception:
                pass

            # Smart GUI cleanup
            try:
                if hasattr(self.face_app, 'canvas') and self.face_app.canvas:
                    try:
                        items = self.face_app.canvas.find_all()
                        if len(items) > 20:
                            items_to_clear = []
                            for item in items:
                                tags = self.face_app.canvas.gettags(item)
                                if tags and 'star' not in str(tags).lower():
                                    items_to_clear.append(item)

                            for item in items_to_clear:
                                self.face_app.canvas.delete(item)

                            if len(items_to_clear) > 0:
                                print(f"[MEMORY] Cleaned {len(items_to_clear)} canvas items, preserved stars")
                    except Exception:
                        pass

                # Temporary window withdrawal
                self.root.withdraw()
                self.root.update_idletasks()
                time.sleep(0.2)

                # Light GUI cleanup
                self.root.tk.call('update')
                gc.collect()

            except Exception:
                pass

            # Conservative system tuning
            try:
                subprocess.run(['sudo', 'sh', '-c', 'echo 60 > /proc/sys/vm/vfs_cache_pressure'],
                               check=False, capture_output=True)
                subprocess.run(['sudo', 'sh', '-c', 'echo 8 > /proc/sys/vm/swappiness'],
                               check=False, capture_output=True)
                subprocess.run(['sudo', 'sync'], check=False, capture_output=True)
                subprocess.run(['sudo', 'sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'],
                               check=False, capture_output=True)
            except Exception:
                pass

            # Show final memory
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    mem_line = lines[1].split()
                    if len(mem_line) >= 7:
                        print(f"[MEMORY] Available after cleanup: {mem_line[6]}")

            time.sleep(0.5)  # Brief stabilization

        except Exception as e:
            print(f"[AI] Memory optimization warning: {e}")

        print("[AI] Starting AI components with maximum available memory...")

        # Pre-load the AI model for faster responses
        from chatbot_logic import preload_model
        preload_model()

        # Temporarily disable face animations to save memory during AI startup
        print("[MEMORY] Deferring face animations until after AI model loads...")

        # Show memory status after model preload
        print("[MEMORY] Final memory check after model preload:")
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)

        # Check available memory and suggest model alternatives
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    mem_line = lines[1].split()
                    if len(mem_line) >= 7:
                        available_mb = int(mem_line[6])
                        print(f"[AI] Available memory: {available_mb}MB")

                        if available_mb < 2900:  # Less than 2.9GB
                            print(f"[AI] WARNING: Only {available_mb}MB available, but AI model needs ~2900MB")
                            print("[AI] Attempting to start with available memory...")
        except Exception:
            pass

        # Start chatbot with conservative approach
        # Suppress greeting if already shown earlier in this session
        if not hasattr(self.face_app, 'suppress_initial_greeting'):
            # First activation: allow greeting (attribute created dynamically)
            setattr(self.face_app, 'suppress_initial_greeting', False)  # type: ignore[attr-defined]
        else:
            # Subsequent toggles skip greeting
            setattr(self.face_app, 'suppress_initial_greeting', True)  # type: ignore[attr-defined]

        print("[AI] Starting chatbot thread (model already loaded)...")

        self._start_chatbot_if_needed(suppress_greeting=getattr(self.face_app, 'suppress_initial_greeting', False))

        # Brief wait for chatbot thread to start
        time.sleep(0.5)

        # Start face animations more carefully
        print("[AI] Starting face animations...")
        self._ensure_animations()

        # Resume GUI window gently
        try:
            print("[AI] Restoring GUI...")
            self.root.deiconify()  # Restore the window
            self.root.update()
            # Try to resume face GUI, but catch any errors from missing canvas elements
            try:
                self.face_app.resume()
            except ValueError as e:
                if "not enough values to unpack" in str(e):
                    print("[AI] Canvas needs reinitialization, recreating face elements...")
                    # Reinitialize the face canvas elements
                    try:
                        self.face_app.suspend()
                        time.sleep(0.1)
                        self.face_app.resume()
                    except Exception:
                        print("[AI] Face GUI initialization issue - continuing with basic functionality")
                else:
                    raise
        except Exception as e:
            print(f"[AI] GUI restoration: {e}")
            try:
                self.face_app.resume()
            except Exception:
                pass

        self.face_app.set_emotion('happy')
        # --- QoL SUGGESTION: Set LED for AI state ---
        set_emotion_led('happy') # Happy = Green
        # --- END QoL SUGGESTION ---

    # --------------- Lazy Ensures ---------------
    def _ensure_camera(self):
        if not self._camera_initialized:
            try:
                # Kill any existing camera processes before starting new one
                self._kill_camera_processes()
                self.camera = CameraMaster(show_windows=True)
                self._camera_initialized = True
                print("[LAZY] Camera subsystem initialized.")
            except Exception:
                traceback.print_exc()
                print("[ERROR] Could not initialize camera.")
                self.camera = None
                self._camera_initialized = False
        return self.camera is not None

    def _kill_camera_processes(self):
        """Kill any existing camera processes to prevent conflicts"""
        try:
            import subprocess
            print("[CAMERA] Checking for existing camera processes...")

            # Check and kill processes using video devices
            for video_dev in ['/dev/video0', '/dev/video1']:
                try:
                    # Check if device exists
                    if os.path.exists(video_dev):
                        # Check processes using this video device
                        result = subprocess.run(['fuser', '-v', video_dev],
                                                capture_output=True, text=True)
                        if result.returncode == 0 and result.stderr.strip():
                            print(f"[CAMERA] Found processes using {video_dev}, killing them...")
                            # Kill processes using the video device
                            subprocess.run(['sudo', 'fuser', '-k', video_dev],
                                           check=False, capture_output=True)
                            time.sleep(0.2)  # Brief delay for cleanup
                except Exception as e:
                    print(f"[CAMERA] Cleanup {video_dev}: {e}")

        except Exception as e:
            print(f"[CAMERA] Process cleanup warning: {e}")

    def _ensure_animations(self):
        if not self._animations_started:
            try:
                # --- PREVIOUS FIX: Correct function name ---
                # This fixes the AttributeError from your original log
                # self.face_app.start_idle_loop()
                self.face_app.start_animation_loops()
                # --- END PREVIOUS FIX ---
                self._animations_started = True
                print("[LAZY] Face animations started.")
            except Exception:
                traceback.print_exc()
                print("[WARN] Could not start animations.")

    # --------------- Camera UI Loop ---------------
    def _camera_ui_loop(self):
        try:
            if self.camera is None or self._camera_shutting_down:
                # Still idle or shutting down; reschedule at a slower rate
                if not self._stop_flag.is_set():
                    self.root.after(300, self._camera_ui_loop)
                return
            key = self.camera.display_frame()
            if key == ord('q'):
                print('[KEY] q pressed - shutting down')
                self.shutdown()
                return
        except Exception:
            pass
        if not self._stop_flag.is_set():
            self.root.after(50, self._camera_ui_loop)

    # --------------- Mode Management ---------------
    def _stop_all_camera_modes(self):
        print("[MODE] Stopping all camera modes...")

        # Stop RPS game if running
        if self._rps_started:
            self._stop_rps_if_running()
            
        # --- NEW: Stop presentation if running ---
        if self._presentation_started:
            self._stop_presentation_if_running()
        # --- END NEW ---

        if self.camera:
            try:
                self.camera.stop_color_tracking()
            except Exception:
                pass
            try:
                self.camera.stop_face_tracking()
            except Exception:
                pass
            try:
                self.camera.stop_gesture_following()
            except Exception:
                pass
            try:
                self.camera.stop_object_recognition()
            except Exception:
                pass
            try:
                self.camera.stop_license_plate_recognition()
            except Exception:
                pass
        self.active_mode = None
        self.active_color = None
        motor_stop()
        
        # --- QoL FIX: Turn off LEDs completely when stopping a mode ---
        turn_off_led()
        # set_emotion_led('neutral') # Replaced with turn_off_led()
        # --- END QoL FIX ---
        
        # Only change face emotion if AI is enabled
        if self.ai_enabled:
            try:
                self.face_app.set_emotion('neutral')
            except Exception:
                pass  # Face may not be initialized

        # --- FIX 4: Hide Face on Mode Stop ---
        # If AI is not enabled, hide the face GUI again
        if not self.ai_enabled:
            try:
                self.face_app.suspend()
                print("[MODE] Face GUI suspended.")
            except Exception:
                pass
        # --- END FIX 4 ---

        print("[MODE] All camera modes stopped.")
        # --- QoL FIX: Show help menu after stopping a mode ---
        self._print_help()
        # --- END QoL FIX ---


    def _release_camera_completely(self):
        """Completely release and close the camera to free up memory"""
        print("[CAMERA] Releasing camera completely...")

        # Stop RPS game first if it's running
        if self._rps_started:
            self._stop_rps_if_running()
            
        # --- NEW: Stop presentation if running ---
        if self._presentation_started:
            self._stop_presentation_if_running()
        # --- END NEW ---

        # Set a flag to prevent new camera operations during shutdown
        self._camera_shutting_down = True

        # First stop all modes safely
        if self.camera is not None:
            print("Stopping camera modes...")
            try:
                self.camera.stop_color_tracking()
                print("Color tracker stopped")
            except Exception as e:
                print(f"Color tracker stop error: {e}")
            try:
                self.camera.stop_face_tracking()
                print("Face tracker stopped")
            except Exception as e:
                print(f"Face tracker stop error: {e}")
            try:
                self.camera.stop_gesture_following()
                print("Gesture tracker stopped")
            except Exception as e:
                print(f"Gesture tracker stop error: {e}")
            try:
                self.camera.stop_object_recognition()
                print("Object recognition stopped")
            except Exception as e:
                print(f"Object recognition stop error: {e}")
            try:
                self.camera.stop_license_plate_recognition()
                print("License plate recognition stopped")
            except Exception as e:
                print(f"License plate stop error: {e}")

            # Give a longer delay for processes to clean up properly
            time.sleep(0.3)

            # Now release the camera completely
            try:
                print("Releasing camera resources...")
                self.camera.release_all()
                print("Camera resources released")
            except Exception as e:
                print(f"Camera release error: {e}")

        # Reset camera state
        self.camera = None
        self._camera_initialized = False
        self.active_mode = None
        self.active_color = None
        self._camera_shutting_down = False

        # Stop motors and reset LEDs
        motor_stop()
        turn_off_led() # MODIFIED: Was set_emotion_led('neutral')

        # Only change face emotion if AI is enabled
        if self.ai_enabled:
            try:
                self.face_app.set_emotion('neutral')
            except Exception as e:
                print(f"Face emotion set error: {e}")

        # Force garbage collection to free memory
        import gc
        gc.collect()

        # Additional memory cleanup and camera process killing when switching to AI mode
        if self.ai_enabled:
            try:
                import subprocess
                print("[MEMORY] Aggressive memory cleanup for AI startup...")

                # Kill any remaining camera processes
                print("[CAMERA] Checking for camera processes...")
                # Check available video devices
                result = subprocess.run(['ls', '/dev/video*'], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    print(f"[CAMERA] Available video devices: {result.stdout.strip()}")

                # Kill processes using video devices
                for video_dev in ['/dev/video0', '/dev/video1']:
                    try:
                        # Check processes using this video device
                        result = subprocess.run(['fuser', '-v', video_dev],
                                                capture_output=True, text=True)
                        if result.returncode == 0 and result.stderr.strip():
                            print(f"[CAMERA] Processes using {video_dev}:")
                            print(result.stderr)
                            # Kill processes using the video device
                            subprocess.run(['sudo', 'fuser', '-k', video_dev],
                                           check=False, capture_output=True)
                            print(f"[CAMERA] Killed processes using {video_dev}")
                    except Exception as e:
                        print(f"[CAMERA] Video device {video_dev} cleanup: {e}")

                # Show memory before cache clear
                print("[MEMORY] Memory before cache clear:")
                result = subprocess.run(['free', '-h'], capture_output=True, text=True)
                if result.returncode == 0:
                    print(result.stdout)

                # Sync and clear caches
                subprocess.run(['sudo', 'sync'], check=False, capture_output=True)
                subprocess.run(['sudo', 'sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'],
                               check=False, capture_output=True)

                # Show memory after cache clear
                print("[MEMORY] Memory after cache clear:")
                result = subprocess.run(['free', '-h'], capture_output=True, text=True)
                if result.returncode == 0:
                    print(result.stdout)

                # Additional garbage collection
                for _ in range(2):
                    gc.collect()

            except Exception as e:
                print(f"[MEMORY] Cache clear warning: {e}")

        print("[CAMERA] Camera completely released and memory freed.")

        # If AI was just enabled, start AI components after camera release
        if self.ai_enabled:
            self._start_ai_components()

    def _start_color_mode(self, color_name):
        if self.ai_enabled or self._presentation_started: # MODIFIED
            print("[MODE] Cannot start camera modes while AI or Presentation is enabled. Disable AI first.")
            return
        if self.active_mode != 'color' or self.active_color != color_name:
            self._stop_all_camera_modes()
            print(f"[MODE] Starting color tracking: {color_name}")
            if not self._ensure_camera():
                print("[ERROR] Camera unavailable.")
                return
            try:
                assert self.camera is not None
                self.camera.start_color_tracking(color_name)
                self.active_mode = 'color'
                self.active_color = color_name
                # Only show emotions and animations if AI is enabled
                if self.ai_enabled:
                    self.face_app.set_emotion('happy')
                
                # --- QoL FIX: Set LED to tracking color ---
                # Raspbot color codes: Red:0, Green:1, Blue:2, Yellow:3
                color_index_map = {'red': 0, 'green': 1, 'blue': 2, 'yellow': 3}
                # Default to White (6) if color_name is not in our map
                color_index = color_index_map.get(color_name.lower(), 6) 
                try:
                    self.bot.Ctrl_WQ2812_ALL(1, color_index)
                except Exception as e:
                    print(f"[LED] Failed to set color: {e}")
                # --- END QoL FIX ---

            except Exception:
                traceback.print_exc()
                print("[ERROR] Could not start color tracking.")

    def _start_face_mode(self):
        if self.ai_enabled or self._presentation_started: # MODIFIED
            print("[MODE] Cannot start camera modes while AI or Presentation is enabled. Disable AI first.")
            return
        if self.active_mode != 'face':
            self._stop_all_camera_modes()
            print("[MODE] Starting face tracking & recognition")
            if not self._ensure_camera():
                print("[ERROR] Camera unavailable.")
                return
            try:
                assert self.camera is not None
                self.camera.start_face_tracking()
                self.active_mode = 'face'
                # Only show emotions and animations if AI is enabled
                if self.ai_enabled:
                    self.face_app.set_emotion('happy')
                set_emotion_led('happy')
            except Exception:
                traceback.print_exc()
                print("[ERROR] Could not start face mode.")

    def _start_gesture_mode(self):
        if self.ai_enabled or self._presentation_started: # MODIFIED
            print("[MODE] Cannot start camera modes while AI or Presentation is enabled. Disable AI first.")
            return
        if self.active_mode != 'gesture':
            self._stop_all_camera_modes()
            print("[MODE] Starting gesture following")
            if not self._ensure_camera():
                print("[ERROR] Camera unavailable.")
                return
            try:
                assert self.camera is not None
                self.camera.start_gesture_following(enable_actions=True) # MODIFIED: Explicitly enable actions
                self.active_mode = 'gesture'
                # Only show emotions and animations if AI is enabled
                if self.ai_enabled:
                    self.face_app.set_emotion('happy')
                set_emotion_led('happy')
            except Exception:
                traceback.print_exc()
                print("[ERROR] Could not start gesture mode.")

    def _start_object_mode(self):
        if self.ai_enabled or self._presentation_started: # MODIFIED
            print("[MODE] Cannot start camera modes while AI or Presentation is enabled. Disable AI first.")
            return
        if self.active_mode != 'object':
            self._stop_all_camera_modes()
            print("[MODE] Starting object recognition")
            if not self._ensure_camera():
                print("[ERROR] Camera unavailable.")
                return
            
            # --- FIX: Use BASE_DIR for reliable model paths ---
            global BASE_DIR # Access the global variable defined at the top of the file
            model_path = os.path.join(BASE_DIR, 'CameraLib', '04.Tensorflow_object_recognition',
                                      'ssdlite_mobilenet_v2_coco_2018_05_09', 'frozen_inference_graph.pb')
            label_map_path = os.path.join(BASE_DIR, 'CameraLib', '04.Tensorflow_object_recognition', 'data',
                                          'mscoco_label_map.pbtxt')
            # --- END FIX ---
            
            abs_model = os.path.abspath(model_path)
            abs_labels = os.path.abspath(label_map_path)
            model_ok = os.path.exists(model_path)
            labels_ok = os.path.exists(label_map_path)
            if not (model_ok and labels_ok):
                print("[ERROR] Object model resources missing.")
                if not model_ok:
                    print(f"  Missing model: {abs_model}")
                if not labels_ok:
                    print(f"  Missing label map: {abs_labels}")
                print("  Expected directory layout:")
                print("    04.Tensorflow_object_recognition/")
                print("      ssdlite_mobilenet_v2_coco_2018_05_09/frozen_inference_graph.pb")
                print("      data/mscoco_label_map.pbtxt")
                print("  Download COCO SSD Lite model from:")
                print(
                    "    https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/tf1_detection_zoo.md")
                print("  (Note: heavy for Raspberry Pi; consider skipping object mode.)")
                return
            try:
                assert self.camera is not None
                self.camera.start_object_recognition(model_path, label_map_path)
                self.active_mode = 'object'
                # Only show emotions and animations if AI is enabled
                if self.ai_enabled:
                    self.face_app.set_emotion('neutral')
                set_emotion_led('neutral')
            except Exception:
                traceback.print_exc()
                print("[ERROR] Could not start object recognition.")

    def _start_plate_mode(self):
        if self.ai_enabled or self._presentation_started: # MODIFIED
            print("[MODE] Cannot start camera modes while AI or Presentation is enabled. Disable AI first.")
            return
        if self.active_mode != 'plate':
            self._stop_all_camera_modes()
            print("[MODE] Starting license plate recognition")
            if not self._ensure_camera():
                print("[ERROR] Camera unavailable.")
                return
            font_path = '07.Camera-Based_License_plate_recognition/platech.ttf'
            try:
                assert self.camera is not None
                self.camera.start_license_plate_recognition(font_path=font_path, detect_level='low')
                self.active_mode = 'plate'
                # Only show emotions and animations if AI is enabled
                if self.ai_enabled:
                    self.face_app.set_emotion('neutral')
                set_emotion_led('neutral')
            except Exception:
                traceback.print_exc()
                print("[ERROR] Could not start license plate mode.")

    # --------------- IR Loop ---------------
    def _ir_loop(self):
        print("[IR] Listening for IR codes...")
        while not self._stop_flag.is_set():
            try:
                data = self.bot.read_data_array(0x0c, 1)
                if data and isinstance(data, list):
                    code = data[0]
                    now = time.time()
                    if code != 0 and code < 0xFF:
                        # Debounce
                        if not IR_DEBUG:
                            if code == self._last_ir_code and (now - self._last_ir_time) < IR_DEBOUNCE_SEC:
                                time.sleep(0.05)
                                continue
                        self._last_ir_code = code
                        self._last_ir_time = now
                        print(f"[IR] Code: 0x{code:02X}")
                        self._handle_ir_code(code)
                time.sleep(0.05)
            except Exception:
                time.sleep(0.1)

    def _handle_ir_code(self, code):
        if code == IR_COLOR_RED:
            self._start_color_mode('red')
        elif code == IR_COLOR_BLUE:
            self._start_color_mode('blue')
        elif code == IR_COLOR_GREEN:
            self._start_color_mode('green')
        elif code == IR_COLOR_YELLOW:
            self._start_color_mode('yellow')
        elif code == IR_FACE_MODE:
            self._start_face_mode()
        elif code == IR_GESTURE_MODE:
            self._start_gesture_mode()
        elif code == IR_OBJECT_MODE:
            self._start_object_mode()
        elif code == IR_PLATE_MODE:
            self._start_plate_mode()
        elif code == IR_RPS_GAME:
            self.root.after(0, self._start_rps_if_needed)  # Schedule on main thread
        # --- NEW: Handle presentation button ---
        elif code == IR_PRESENTATION:
            self.root.after(0, self._start_presentation_mode)
        # --- END NEW ---
        elif code == IR_AI_TOGGLE:
            self.root.after(0, self._toggle_ai)  # Schedule on main thread
        elif code == IR_STOP_ALL:
            # Schedule camera release on main thread to avoid Qt threading issues
            self.root.after(10, self._release_camera_completely)
        elif code == IR_EXIT_APP:
            print("[IR] Exit command received.")
            self.shutdown()
        
        else:
            if IR_DEBUG:
                print(f"[IR] Unmapped code: 0x{code:02X}")
        trigger_beep()

    # --------------- Helper ---------------
    def _print_help(self):
        print("\n=== IR COMMAND MAP ===")
        print(f"Red Color Mode      : 0x{IR_COLOR_RED:02X}")
        print(f"Blue Color Mode     : 0x{IR_COLOR_BLUE:02X}")
        print(f"Green Color Mode    : 0x{IR_COLOR_GREEN:02X}")
        print(f"Yellow Color Mode   : 0x{IR_COLOR_YELLOW:02X}")
        print(f"Face Tracking Mode  : 0x{IR_FACE_MODE:02X}")
        print(f"Gesture Mode        : 0x{IR_GESTURE_MODE:02X}")
        print(f"Object Recognition  : 0x{IR_OBJECT_MODE:02X}")
        print(f"License Plate Mode  : 0x{IR_PLATE_MODE:02X}")
        print(f"RPS Game Mode       : 0x{IR_RPS_GAME:02X}")
        print(f"Presentation Mode   : 0x{IR_PRESENTATION:02X}") # --- NEW ---
        print(f"AI Toggle           : 0x{IR_AI_TOGGLE:02X}")
        print(f"Stop All            : 0x{IR_STOP_ALL:02X}")
        print(f"Exit App            : 0x{IR_EXIT_APP:02X}")
        print("=================================================================\n")

    # --------------- Shutdown ---------------
    def shutdown(self):
        if self._stop_flag.is_set():
            return
        print("[SYS] Shutting down...")
        self._stop_flag.set()
        try:
            self.bot.Ctrl_IR_Switch(0)
        except Exception:
            pass
        # Ensure chatbot stopped
        self._stop_chatbot_if_running()
        
        # --- NEW: Stop presentation ---
        self._stop_presentation_if_running()
        # --- END NEW ---
        
        # Stop RPS (was already in your logic, just confirming)
        self._stop_rps_if_running()
        
        self._stop_all_camera_modes()
        if self.camera:
            try:
                self.camera.release_all()
            except Exception:
                pass
        motor_stop()
        turn_off_led()

        # --- FIX: Schedule GUI destruction on the main thread ---
        try:
            # self.root.quit()   <--- REMOVE
            # self.root.destroy() <--- REMOVE

            # Post the destroy() command to the main thread's event
            # queue. This is the only thread-safe way to close Tkinter.
            self.root.after(10, self.root.destroy)
        except Exception as e:
            # This might fail if the root is already in a bad state
            print(f"[SYS] Error scheduling GUI shutdown: {e}")
        # --- END FIX ---
        
        print("[SYS] Shutdown complete.")

    # --------------- Run ---------------
    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()
        except Exception:
            traceback.print_exc()
            self.shutdown()


def validate_setup():
    required_paths = [
        Config.VOSK_MODEL_PATH,
        Config.PIPER_PATH,
        Config.PIPER_MODEL,
        Config.PIPER_CONFIG
    ]
    ok = True
    for path in required_paths:
        if not os.path.exists(path):
            print(f"[WARN] Missing: {path}")
            ok = False
    if not ok:
        print("[INFO] You can still run camera modes without voice/AI.")
    return True  # Allow run anyway


if __name__ == "__main__":
    validate_setup()
    app = BigMainApp()
    app.run()