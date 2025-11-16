# robot_hardware.py
#
# This file contains the functions for controlling the robot's motors and LEDs,
# directly importing from the existing hardware libraries.

import time
import threading
import random # NEW: Added for the win_led_sequence color selection

try:
    # Attempt to import hardware libraries
    from McLumk_Wheel_Sports import (
        move_forward, move_backward, move_diagonal_left_front,
        move_diagonal_right_front, move_diagonal_left_back,
        move_diagonal_right_back, move_right, move_left,
        rotate_left, rotate_right, stop
    )
    from Raspbot_Lib import Raspbot
except ImportError:
    # Create dummy functions if libraries are not found, allowing the code to run without a robot
    print("Warning: Hardware libraries not found. Running in simulation mode.")
    def move_forward(speed): print(f"Sim: Move Forward @ {speed}")
    def move_backward(speed): print(f"Sim: Move Backward @ {speed}")
    def move_diagonal_left_front(speed): print(f"Sim: Move Diagonal Left Front @ {speed}")
    def move_diagonal_right_front(speed): print(f"Sim: Move Diagonal Right Front @ {speed}")
    def move_diagonal_left_back(speed): print(f"Sim: Move Diagonal Left Back @ {speed}")
    def move_diagonal_right_back(speed): print(f"Sim: Move Diagonal Right Back @ {speed}")
    def move_right(speed): print(f"Sim: Move Right @ {speed}")
    def move_left(speed): print(f"Sim: Move Left @ {speed}")
    def rotate_left(speed): print(f"Sim: Rotate Left @ {speed}")
    def rotate_right(speed): print(f"Sim: Rotate Right @ {speed}")
    def stop(): print("Sim: Stop")
    Raspbot = None

# --- Hardware & LED Control Setup ---
bot = None
if Raspbot:
    bot = Raspbot()

# Define color mappings based on the Raspbot library's color index
# Red:0, Green:1, Blue:2, Yellow:3, Purple:4, Cyan:5, White:6
EMOTION_LED_MAP = {
    'happy': 1,   # Green
    'neutral': 2, # Blue
    'angry': 0,   # Red
    'shy': 4,     # Purple (used to represent Pink)
    # NEW: Add 'confused' to the map, using Yellow as a suitable color
    'confused': 3, # Yellow
    'scared': 0    # Red (as a fallback)
}
MOVEMENT_LED_COLOR = 3 # Yellow

def _do_beep():
    """Private function to handle the actual beeping sequence."""
    if bot:
        bot.Ctrl_BEEP_Switch(1)  # Buzzer on
        time.sleep(0.05)         # Beep for 50 milliseconds
        bot.Ctrl_BEEP_Switch(0)  # Buzzer off
    else:
        print("Sim: Beep!")

def trigger_beep():
    """Activates the buzzer in a non-blocking thread."""
    beep_thread = threading.Thread(target=_do_beep)
    beep_thread.start()

# --- LED Control Functions ---

def set_emotion_led(emotion: str):
    """Sets the LED bar color based on the robot's emotion."""
    if bot:
        # Use the original EMOTION_LED_MAP
        color_index = EMOTION_LED_MAP.get(emotion, EMOTION_LED_MAP['neutral'])
        bot.Ctrl_WQ2812_ALL(1, color_index)
        print(f"LEDs set to emotion: {emotion} (Color index: {color_index})")
    else:
        print(f"Sim: LEDs set to emotion: {emotion}")

def set_movement_led():
    """Sets the LED bar to the movement color."""
    if bot:
        bot.Ctrl_WQ2812_ALL(1, MOVEMENT_LED_COLOR)
        print("LEDs set to movement color.")
    else:
        print("Sim: LEDs set to movement color.")

def turn_off_led():
    """Turns off all LEDs on the bar."""
    if bot:
        bot.Ctrl_WQ2812_ALL(0, 0)
        print("LEDs turned off.")
    else:
        print("Sim: LEDs turned off.")

def car_patrol():
    duration = 1
    speed = 100
    move_forward(speed)
    time.sleep(duration)
    stop()
    time.sleep(1)
    move_right(speed)
    time.sleep(duration+0.2)
    stop()
    time.sleep(1)
    move_backward(speed)
    time.sleep(duration)
    stop()
    time.sleep(1)
    move_left(speed)
    time.sleep(duration+0.2)
    stop()
    time.sleep(1)
    pass

def dance_routine():
    """Performs a short dance routine with synchronized lights and movements."""
    print("Starting dance routine!")
    if not bot:
        print("Dance routine unavailable in simulation mode.")
        return

    speed = 80
    delay = 0.4

    # Sequence of moves with changing light colors
    bot.Ctrl_WQ2812_ALL(1, 4) # Purple
    rotate_left(speed)
    time.sleep(delay)
    
    bot.Ctrl_WQ2812_ALL(1, 5) # Cyan
    rotate_right(speed)
    time.sleep(delay)
    
    bot.Ctrl_WQ2812_ALL(1, 3) # Yellow
    move_right(speed)
    time.sleep(delay)
    
    bot.Ctrl_WQ2812_ALL(1, 1) # Green
    move_left(speed)
    time.sleep(delay)

    # Return to starting orientation
    rotate_right(speed)
    time.sleep(delay)
    rotate_left(speed)
    time.sleep(delay)

    stop()
    # Reset to neutral state
    set_emotion_led('neutral')
    print("Dance routine finished.")

# --- NEW: RPS Game Routines ---

def angry_movement():
    """Performs a short, angry, and erratic movement (Marich lost in RPS)."""
    print("Starting angry movement!")
    speed = 120
    delay = 0.2

    # Sequence of quick, jerky moves
    move_forward(speed)
    time.sleep(delay)
    rotate_right(speed)
    time.sleep(delay)
    move_backward(speed)
    time.sleep(delay)
    rotate_left(speed)
    time.sleep(delay)
    stop()
    print("Angry movement complete.")

def win_led_sequence(duration=1.5):
    """Flashes many colors quickly to simulate a win celebration (Marich won in RPS)."""
    print("Starting win LED sequence.")
    if not bot:
        print("Sim: Win LED sequence.")
        return

    start_time = time.time()
    # Color codes from your original mapping: Red:0, Green:1, Blue:2, Yellow:3, Purple:4, Cyan:5, White:6
    colors = [1, 2, 3, 4, 5, 6] # Exclude red, favoring brighter celebration colors
    while time.time() - start_time < duration:
        color_code = random.choice(colors)
        bot.Ctrl_WQ2812_ALL(1, color_code)
        time.sleep(0.1) # Fast flash
    
    turn_off_led()
    print("Win LED sequence complete.")

def lose_led_sequence(duration=1.5):
    """Solid red to simulate anger/losing (Marich lost in RPS)."""
    print("Starting lose LED sequence (Red).")
    if not bot:
        print("Sim: Lose LED sequence (Red).")
        return

    # Red is color code 0 in your original EMOTION_LED_MAP
    bot.Ctrl_WQ2812_ALL(1, 0)
    time.sleep(duration)
    turn_off_led()
    print("Lose LED sequence complete.")


def scared_led_sequence(duration=2.0):
    """Flashes red to simulate fear/warning."""
    print("Starting scared LED sequence (Flashing Red).")
    if not bot:
        print("Sim: Scared LED sequence (Flashing Red).")
        return

    start_time = time.time()
    # Red is color code 0
    while time.time() - start_time < duration:
        bot.Ctrl_WQ2812_ALL(1, 0) # Red
        time.sleep(0.15)
        bot.Ctrl_WQ2812_ALL(0, 0) # Off
        time.sleep(0.1)

    turn_off_led() # Ensure lights are off after
    print("Scared LED sequence complete.")