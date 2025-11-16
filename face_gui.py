# face_gui.py
#
# This module handles all aspects of the graphical user interface,
# including the face's drawing, state, and animations.

import tkinter as tk
import os
import math
import random
import time
from typing import Optional

# NEW: Added PIL for image display on Tkinter canvas
try:
    from PIL import Image, ImageTk
except ImportError:
    print("Warning: Pillow (PIL) is not installed. Game images will not display.")
    class Image: # type: ignore
        @staticmethod
        def open(path): return None
        class Resampling: # type: ignore
            LANCZOS = 1
    class ImageTk: # type: ignore
        @staticmethod
        def PhotoImage(img): return None

# --- Configuration ---
class Config:
    """Stores all application-wide configuration settings."""
    # Get the directory where this script is located
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    VOSK_MODEL_PATH = os.path.join(_BASE_DIR, "vosk-model-small-en-us-0.15")
    LLM_MODEL = "gemma2:2b" 
    PIPER_PATH = os.path.join(_BASE_DIR, "piper", "piper")
    PIPER_MODEL = os.path.join(_BASE_DIR, "piper", "en_US-amy-medium.onnx")
    PIPER_CONFIG = os.path.join(_BASE_DIR, "piper", "en_US-amy-medium.onnx.json")
    AUDIO_DEVICE = "default" # TODO: Verify this with `arecord -l`
    TEMP_WAV_FILE = "piper_output.wav"
    CANVAS_WIDTH = 300
    CANVAS_HEIGHT = 300
    STAR_COLOR = "#e0e0e0"
    NUM_STARS = 75
    EMOTION_COLORS = {
        'neutral': "#1a1a2e",
        'happy': "#16a085",
        'angry': "#4a1a1a",
        'shy': "#ffb6c1",  # A light pink for the shy/blushing emotion
        'confused': "#f39c12", # NEW: Added confused emotion color
        'scared': "#2a2a3e"
    }
    FACE_COLOR = "#ffffff"
    PUPIL_COLOR = "#1e272e"
    MOUTH_COLOR = "#ffffff"
    CHEEK_COLOR = "#ff7979"
    EYEBROW_COLOR = "#ffffff"
    
    # --- NEW: Game Image Paths ---
    RPS_ROCK_PATH = os.path.join(_BASE_DIR, "rock.png")
    RPS_PAPER_PATH = os.path.join(_BASE_DIR, "paper.png")
    RPS_SCISSORS_PATH = os.path.join(_BASE_DIR, "scissors.png")


# --- Main GUI Application Class ---
class MarichFaceApp:
    """
    Manages the Tkinter GUI for the chatbot's animated face.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Marich Chatbot")
        self.canvas = tk.Canvas(root, width=Config.CANVAS_WIDTH, height=Config.CANVAS_HEIGHT, bg=Config.EMOTION_COLORS['neutral'])
        self.canvas.pack()

        # Animation state
        self.current_emotion = 'neutral'
        self.animation_active = False
        self.animation_step = 0
        self.idle_step = 0
        self.eyes_open = True
        self.blink_ticks_remaining = 0
        self.next_blink_in = random.randint(25, 80)

        # Touch interaction state
        self.touch_enabled = False
        self.pat_callback = None
        self.tap_callback = None 
        self.last_pat_time = 0
        self.canvas.bind("<Button-1>", self._handle_tap)
        self.canvas.bind("<B1-Motion>", self._handle_pat)

        # Canvas item references and their initial positions
        self.face_parts = {}
        self.initial_coords = {}
        self.background_stars = []
        
        # --- NEW: Game Image State ---
        self.current_game_image: Optional[tk.PhotoImage] = None
        # Cache PhotoImage objects to prevent garbage collection
        self.image_cache: dict = {}

        self._define_face_coords()
        self._create_starfield()
        self.draw_face()

    def _define_face_coords(self):
        """Defines the coordinates for all facial features for each emotion."""
        self.base_coords = {
            'neutral': {
                'left_eye': (75, 100, 125, 150), 'right_eye': (175, 100, 225, 150),
                'mouth': (110, 200, 190, 220)
            },
            'happy': {
                'left_eye': (75, 100, 125, 150), 'right_eye': (175, 100, 225, 150),
                'mouth': (100, 190, 200, 240),
                'left_cheek': (50, 155, 80, 175), 'right_cheek': (220, 155, 250, 175)
            },
            'angry': {
                'left_eye': (75, 110, 125, 160), 'right_eye': (175, 110, 225, 160),
                'mouth': (110, 220, 190, 250),
                'left_eyebrow': (75, 95, 125, 115), 'right_eyebrow': (175, 115, 225, 95)
            },
            'shy': {
                'left_eye': (75, 100, 125, 150), 'right_eye': (175, 100, 225, 150),
                'mouth': (120, 200, 180, 220), # A smaller, gentle smile
                'left_cheek': (50, 155, 80, 175), 'right_cheek': (220, 155, 250, 175)
            },
            # NEW: Add a definition for 'confused'
            'confused': {
                'left_eye': (75, 100, 125, 150), 'right_eye': (175, 100, 225, 150),
                'mouth': (110, 200, 190, 220)
            },
            'scared': {
                'left_eye': (70, 90, 130, 160),  # Bigger eye
                'right_eye': (170, 90, 230, 160), # Bigger eye
                'mouth': (130, 210, 170, 240)  # Small 'O' mouth
            }
        }

    def _create_starfield(self):
        """Populates the background with stars for a dynamic effect."""
        for _ in range(Config.NUM_STARS):
            x = random.uniform(0, Config.CANVAS_WIDTH)
            y = random.uniform(0, Config.CANVAS_HEIGHT)
            size = random.uniform(0.5, 2)
            star = self.canvas.create_oval(x, y, x + size, y + size, fill=Config.STAR_COLOR, outline="")
            self.background_stars.append(star)

    def draw_face(self):
        """Clears and redraws all facial features based on the current emotion."""
        self.canvas.delete("face_part", "game_image") # MODIFIED: Also clear game images
        self.face_parts.clear()
        self.initial_coords.clear()
        
        # NEW: If a game image is set, display it and stop drawing the face
        if self.current_game_image:
            self.canvas.create_image(Config.CANVAS_WIDTH/2, Config.CANVAS_HEIGHT/2,
                                     anchor=tk.CENTER, image=self.current_game_image, tags="game_image")
            return

        coords = self.base_coords.get(self.current_emotion, self.base_coords['neutral'])

        # Eyes and Pupils
        for eye_type in ['left_eye', 'right_eye']:
            L = coords[eye_type]
            pupil_size = 15
            px, py = (L[0] + L[2]) / 2, (L[1] + L[3]) / 2
            
            eye_id = self.canvas.create_oval(*L, fill=Config.FACE_COLOR, outline="", tags="face_part")
            pupil_id = self.canvas.create_oval(px-pupil_size/2, py-pupil_size/2, px+pupil_size/2, py+pupil_size/2,
                                               fill=Config.PUPIL_COLOR, outline="", tags="face_part")
            self.face_parts[eye_type] = eye_id
            self.face_parts[f'{eye_type}_pupil'] = pupil_id

        # Mouth, Eyebrows, Cheeks
        if self.current_emotion in ['happy', 'shy']:
            self.face_parts['mouth'] = self.canvas.create_arc(*coords['mouth'], start=0, extent=-180, style=tk.CHORD, fill=Config.MOUTH_COLOR, outline="", tags="face_part")
            self.face_parts['left_cheek'] = self.canvas.create_oval(*coords['left_cheek'], fill=Config.CHEEK_COLOR, outline="", tags="face_part")
            self.face_parts['right_cheek'] = self.canvas.create_oval(*coords['right_cheek'], fill=Config.CHEEK_COLOR, outline="", tags="face_part")
        elif self.current_emotion == 'angry':
            self.face_parts['mouth'] = self.canvas.create_arc(*coords['mouth'], start=0, extent=180, style=tk.ARC, outline=Config.MOUTH_COLOR, width=6, tags="face_part")
            self.face_parts['left_eyebrow'] = self.canvas.create_line(*coords['left_eyebrow'], fill=Config.EYEBROW_COLOR, width=8, tags="face_part")
            self.face_parts['right_eyebrow'] = self.canvas.create_line(*coords['right_eyebrow'], fill=Config.EYEBROW_COLOR, width=8, tags="face_part")
        elif self.current_emotion == 'scared':
            self.face_parts['mouth'] = self.canvas.create_oval(*coords['mouth'], fill=Config.MOUTH_COLOR, outline="", tags="face_part")
        else: # Neutral or Confused
            self.face_parts['mouth'] = self.canvas.create_line(coords['mouth'][0], coords['mouth'][1], coords['mouth'][2], coords['mouth'][1], fill=Config.MOUTH_COLOR, width=6, capstyle=tk.ROUND, tags="face_part")
        
        # Store initial coordinates for all created parts for drift-free animation
        for name, part_id in self.face_parts.items():
            self.initial_coords[name] = self.canvas.coords(part_id)

        self._set_eyes_open(self.eyes_open, force_redraw=True)

    def set_emotion(self, emotion):
        """Sets the current emotion and redraws the face."""
        if emotion != self.current_emotion:
            self.current_emotion = emotion
            new_bg = Config.EMOTION_COLORS.get(emotion, Config.EMOTION_COLORS['neutral'])
            self.canvas.config(bg=new_bg)
            self.draw_face()

    def _set_eyes_open(self, is_open, force_redraw=False):
        """Toggles the eyes between open (oval) and closed (line)."""
        if self.eyes_open == is_open and not force_redraw:
            return
        self.eyes_open = is_open
        
        for eye_type in ['left_eye', 'right_eye']:
            eye, pupil = self.face_parts.get(eye_type), self.face_parts.get(f'{eye_type}_pupil')
            if not eye or not pupil: continue
            
            self.canvas.itemconfig(pupil, state=tk.NORMAL if is_open else tk.HIDDEN)
            self.canvas.itemconfig(eye, state=tk.NORMAL if is_open else tk.HIDDEN)

            if f'{eye_type}_lid' in self.face_parts:
                self.canvas.delete(self.face_parts[f'{eye_type}_lid'])
            
            if not is_open:
                coords = self.canvas.coords(eye)
                y_center = (coords[1] + coords[3]) / 2
                lid_id = self.canvas.create_line(coords[0], y_center, coords[2], y_center, fill=Config.PUPIL_COLOR, width=6, tags="face_part")
                self.face_parts[f'{eye_type}_lid'] = lid_id
                self.initial_coords[f'{eye_type}_lid'] = self.canvas.coords(lid_id)

    def start_animation_loops(self):
        """Starts the idle and talking animation loops."""
        self._idle_loop()
        self._animation_loop()

    def suspend(self):
        """Temporarily hide GUI and stop animations to save CPU."""
        try:
            self.animation_active = False
            self.root.withdraw()
        except Exception:
            pass

    def resume(self):
        """Show GUI again and restart idle loops if needed."""
        try:
            self.root.deiconify()
            # Restart loops only if not already scheduled
            self._idle_loop()
            self._animation_loop()
        except Exception:
            pass

    def _animation_loop(self):
        """Handles the mouth animation when the chatbot is talking."""
        if self.animation_active:
            self._animate_mouth()
        self.root.after(25, self._animation_loop)

    def _animate_mouth(self):
        """Changes the mouth shape based on the current emotion and animation step."""
        mouth_id = self.face_parts.get('mouth')
        if not mouth_id: return
        
        f = (math.sin(math.pi * self.animation_step / 10) + 1) / 2
        base_coords = self.base_coords.get(self.current_emotion, self.base_coords['neutral'])
        base_M = base_coords.get('mouth')
        if not base_M: return
        
        if self.current_emotion in ['happy', 'shy']:
            widen = 15 * f
            self.canvas.coords(mouth_id, base_M[0] - widen, base_M[1], base_M[2] + widen, base_M[3])
        elif self.current_emotion == 'angry':
            y_quiver = (10 * f) + random.uniform(-2, 2)
            self.canvas.coords(mouth_id, base_M[0], base_M[1] - y_quiver, base_M[2], base_M[3] + y_quiver)
        elif self.current_emotion == 'scared':
            # Make the 'O' mouth quiver rapidly
            y_quiver = random.uniform(-2, 2)
            x_quiver = random.uniform(-2, 2)
            self.canvas.coords(mouth_id, base_M[0] + x_quiver, base_M[1] + y_quiver, base_M[2] + x_quiver, base_M[3] + y_quiver)
        else: # neutral, confused
            y_open = 15 * f
            self.canvas.coords(mouth_id, base_M[0], base_M[1] - y_open, base_M[2], base_M[1] + y_open)

        self.animation_step = (self.animation_step + 1) % 20

    def _idle_loop(self):
        """Handles all idle animations, including starfield and facial drift."""
        # --- Starfield Scrolling ---
        for star in self.background_stars:
            self.canvas.move(star, -0.2, -0.1)
            x1, y1, _, _ = self.canvas.coords(star)
            if x1 < 0: self.canvas.move(star, Config.CANVAS_WIDTH, 0)
            if y1 < 0: self.canvas.move(star, 0, Config.CANVAS_HEIGHT)

        if not self.animation_active:
            # --- Blinking Logic ---
            if self.blink_ticks_remaining > 0:
                self.blink_ticks_remaining -= 1
                if self.blink_ticks_remaining == 0:
                    self._set_eyes_open(True)
                    self.next_blink_in = random.randint(50, 150)
            else:
                self.next_blink_in -= 1
                if self.next_blink_in <= 0:
                    self.blink_ticks_remaining = 3
                    self._set_eyes_open(False)

            # --- Facial Drift ---
            bob_y = 1.5 * math.sin(self.idle_step / 10)
            bob_x = 1.0 * math.cos(self.idle_step / 10)
            
            for name, part_id in self.face_parts.items():
                initial = self.initial_coords.get(name)
                if not initial: continue

                if 'pupil' in name:
                    eye_name = name.replace('_pupil', '')
                    eye_initial = self.initial_coords.get(eye_name)
                    if not eye_initial: continue
                    
                    eye_radius_x = (eye_initial[2] - eye_initial[0]) / 2
                    pupil_radius_x = (initial[2] - initial[0]) / 2
                    max_pupil_offset = eye_radius_x - pupil_radius_x - 2

                    pupil_x_offset = max_pupil_offset * math.sin(self.idle_step / 15)
                    pupil_y_offset = max_pupil_offset * math.cos(self.idle_step / 20) * 0.7

                    new_coords = [
                        initial[0] + bob_x + pupil_x_offset, initial[1] + bob_y + pupil_y_offset,
                        initial[2] + bob_x + pupil_x_offset, initial[3] + bob_y + pupil_y_offset
                    ]
                else: # All other parts just bob
                    new_coords = [c + (bob_x if i % 2 == 0 else bob_y) for i, c in enumerate(initial)]

                try:
                    self.canvas.coords(part_id, *new_coords)
                except tk.TclError:
                    # This can happen if a part was deleted mid-animation
                    pass
            
            self.idle_step += 1

        self.root.after(50, self._idle_loop)
        
    def start_talking(self):
        """Starts the mouth animation."""
        self.animation_active = True
        self.draw_face()
        if not self.eyes_open: self._set_eyes_open(True)

    def stop_talking(self):
        """Stops the mouth animation."""
        self.animation_active = False
        self.draw_face()

    # --- NEW: Game Image Methods ---

    def display_game_image(self, image_path: str):
        """Displays a specific image (Rock/Paper/Scissors) on the canvas."""
        if image_path not in self.image_cache:
            try:
                img = Image.open(image_path)
                # --- FIX: Check if image loaded before resizing ---
                if img is None:
                    print(f"Error: Could not load image {image_path}. Is PIL installed?")
                    self.current_game_image = None
                    return
                # --- END FIX ---
                size = min(Config.CANVAS_WIDTH, Config.CANVAS_HEIGHT) // 2
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                self.image_cache[image_path] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error loading game image {image_path}: {e}")
                self.current_game_image = None
                return

        self.current_game_image = self.image_cache[image_path]
        self.draw_face() # Redraw the canvas to show the image

    def clear_game_image(self):
        """Clears the currently displayed game image and shows the face again."""
        if self.current_game_image:
            self.current_game_image = None
            self.draw_face() # Redraw to restore the face

    # --- Touch Interaction Methods ---

    def enable_touch(self):
        """Enables touch interactions on the canvas."""
        # print("Touch interactions enabled.") # Silenced to reduce log spam
        self.touch_enabled = True

    def disable_touch(self):
        """Disables touch interactions on the canvas."""
        # print("Touch interactions disabled.") # Silenced to reduce log spam
        self.touch_enabled = False

    def _handle_tap(self, event):
        """Handles a single tap on the screen."""
        if self.touch_enabled:
            # Call the callback function from the main logic if it exists
            if self.tap_callback:
                self.tap_callback()

    def _handle_pat(self, event):
        """Handles a drag/slide motion on the screen, debounced to prevent spam."""
        current_time = time.time()
        # Trigger pat callback if touch is enabled, a callback is set,
        # and it's been at least 1 second since the last pat.
        if self.touch_enabled and self.pat_callback and (current_time - self.last_pat_time > 1.0):
            self.last_pat_time = current_time
            self.pat_callback()