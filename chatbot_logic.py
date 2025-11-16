# chatbot_logic.py
#
# This module contains the main logic for the chatbot, including
# voice recognition, LLM interaction, and command handling.

import os
import json
import pyaudio
import subprocess
from vosk import Model, KaldiRecognizer, SetLogLevel

# --- Ollama (LLM) Import with graceful compatibility shim ---
# TensorFlow 2.14.x may constrain typing_extensions (<4.6) which lacks TypeAliasType
# required by newer pydantic / Ollama client. Instead of upgrading the package and
# risking version conflicts, we inject a lightweight placeholder so import succeeds.
_OLLAMA_OK = False
_OLLAMA_ERR = None
try:  # Provide minimal shims if older typing_extensions lacks new symbols
    import typing_extensions as _te
    if not hasattr(_te, "TypeAliasType"):
        class TypeAliasType(str):  # minimal stand‑in; structural usage only
            pass
        setattr(_te, "TypeAliasType", TypeAliasType)
    if not hasattr(_te, "TypeIs"):
        # Pydantic >=2.7 references TypeIs for type narrowing; provide no-op generic
        def TypeIs(arg):  # type: ignore
            return bool  # placeholder; not executed in our usage path
        setattr(_te, "TypeIs", TypeIs)
except Exception:
    pass  # If typing_extensions itself missing (unlikely), proceed; import will fail below

try:
    import ollama  # Heavy dependency; may pull newer pydantic needing updated typing_extensions
    _OLLAMA_OK = True
except Exception as _e_ollama:
    ollama = None  # type: ignore
    _OLLAMA_OK = False
    _OLLAMA_ERR = _e_ollama
import threading
import time

# Import the necessary components from other modules
from face_gui import MarichFaceApp, Config
from robot_hardware import (
    move_forward, move_backward, move_diagonal_left_front,
    move_diagonal_right_front, move_diagonal_left_back,
    move_diagonal_right_back, move_right, move_left,
    rotate_left, rotate_right, stop,
    set_emotion_led, set_movement_led, dance_routine, car_patrol,
    trigger_beep, # Import the new beep function
    scared_led_sequence
)
from Raspbot_Lib import Raspbot

# --- Global State & Helper Functions ---
conversation_history = [
    {'role': 'system', 'content': (
        "You are Marich, an AI assistant. Your response MUST be valid JSON, with keys 'text' and 'emotion'. "
        "Rules for 'text': must be a single, short sentence. Plain words only. "
        "Rules for 'emotion': must be one of 'neutral', 'happy', or 'angry'. "
        "Act emotional - if insulted, respond with anger; if someone laughs, be happy."
    )}
]
motor_timer = None
_model_preloaded = False  # Track if model is already loaded

def preload_model():
    """Pre-load the AI model to speed up first response"""
    global _model_preloaded
    if _OLLAMA_OK and ollama is not None and not _model_preloaded:
        try:
            print("[AI] Pre-loading model for faster responses...")
            # Make a simple test call to load the model into memory
            test_history = [
                {'role': 'system', 'content': 'You are an AI. Respond with just {"text": "ready", "emotion": "neutral"}'},
                {'role': 'user', 'content': 'hello'}
            ]
            response = ollama.chat(model=Config.LLM_MODEL, messages=test_history, format='json')
            _model_preloaded = True
            print("[AI] Model pre-loaded successfully")
        except Exception as e:
            print(f"[AI] Model pre-load warning: {e}")
            # Continue anyway - model will load on first real use

def stop_car():
    """Stops the car, cancels pending timers, and resets LEDs to neutral."""
    global motor_timer
    stop()
    set_emotion_led('neutral') # Reset LEDs when stopping
    print("Car stopped. LEDs reset to neutral.")
    if motor_timer and motor_timer.is_alive():
        motor_timer.cancel()
        motor_timer = None

def speak_and_animate(app, text_to_speak, emotion='neutral'):
    """
    Generates speech using Piper and plays it, while animating the face and LEDs.
    
    Args:
        app (MarichFaceApp): The GUI application instance.
        text_to_speak (str): The text to be synthesized into speech.
        emotion (str): The emotion to display on the face and LEDs.
    """
    print(f"AI: '{text_to_speak}' (Emotion: {emotion})")
    app.root.after(0, lambda: app.set_emotion(emotion))
    # Don't call set_emotion_led here if it's the scared emotion,
    # because the threaded scared_led_sequence is handling it.
    if emotion != 'scared':
        set_emotion_led(emotion) # Control LEDs based on emotion
    
    try:
        subprocess.run(
            [Config.PIPER_PATH, "-m", Config.PIPER_MODEL, "-c", Config.PIPER_CONFIG, "--output_file", Config.TEMP_WAV_FILE],
            input=text_to_speak.encode("utf-8"), check=True, capture_output=True)

        app.root.after(0, app.start_talking)
        play_proc = subprocess.Popen(["aplay", "-D", Config.AUDIO_DEVICE, Config.TEMP_WAV_FILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        play_proc.wait()

    except Exception as e:
        print(f"Error during speech generation/playback: {e}")
    finally:
        app.root.after(0, app.stop_talking)
        if os.path.exists(Config.TEMP_WAV_FILE):
            os.remove(Config.TEMP_WAV_FILE)

# --- Main Chatbot Logic Thread ---
def run_chatbot(app, stop_event: threading.Event | None = None, suppress_initial_greeting: bool = False):
    """Chatbot main loop.

    Args:
        app: MarichFaceApp instance.
        stop_event: threading.Event set to request graceful stop.
        suppress_initial_greeting: skip first hello if True.
    """
    global conversation_history, motor_timer
    if stop_event is None:
        stop_event = threading.Event()
    pat_timer = None

    try:
        bot = Raspbot()
        bot.Ctrl_Ulatist_Switch(1) # Turn on the ultrasonic sensor
        print("[AI] Hardware sensors initialized.")
    except Exception as e:
        print(f"[AI] Warning: Could not initialize Raspbot hardware for sensors: {e}")
        bot = None # Set to None so we can check later

    time.sleep(1)
    if not suppress_initial_greeting:
        speak_and_animate(app, "Hello! My name is Marich.", 'happy')
    else:
        print("[AI] Greeting suppressed (reactivation).")
    
    # --- Touch Interaction Handlers ---
    def handle_pat_effect():
        """Shows a shy face and pink LEDs for a short duration."""
        nonlocal pat_timer
        print("Pat detected! Showing shy face.")
        
        # Set emotion on GUI thread and update LEDs
        app.root.after(0, lambda: app.set_emotion('shy'))
        set_emotion_led('shy')
        
        # Cancel previous timer if it exists to reset the duration
        if pat_timer and pat_timer.is_alive():
            pat_timer.cancel()
        
        # Define what happens when the timer finishes
        def revert_to_neutral():
            # Only revert if we are still in the 'shy' state
            if app.current_emotion == 'shy':
                print("Reverting to neutral state after pat.")
                app.root.after(0, lambda: app.set_emotion('neutral'))
                set_emotion_led('neutral')

        # Start a timer to revert to the neutral state after 2 seconds
        pat_timer = threading.Timer(2.0, revert_to_neutral)
        pat_timer.start()

    def handle_tap_effect():
        """Triggers the hardware buzzer."""
        trigger_beep()

    # Set the callbacks in the GUI app
    app.pat_callback = handle_pat_effect
    app.tap_callback = handle_tap_effect

    SetLogLevel(-1) # Hide Vosk log messages
    try:
        p = pyaudio.PyAudio()
        vosk_model = Model(Config.VOSK_MODEL_PATH)
        recognizer = KaldiRecognizer(vosk_model, 16000)
    except Exception as e:
        print(f"Error: Could not initialize speech recognition. Check Vosk model path and PyAudio setup. Details: {e}")
        return

    movement_commands = {
        "move forward": move_forward, "move back": move_backward, "move backward": move_backward,
        "move right": move_right, " moveleft": move_left, "turn right": rotate_right, "turn left": rotate_left,
        "move front left": move_diagonal_left_front, "move front right": move_diagonal_right_front,
        "move back left": move_diagonal_left_back, "move back right": move_diagonal_right_back
    }

    while not stop_event.is_set():
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
        except Exception as e:
            print(f"Error: Failed to open audio stream. Is the microphone connected? Details: {e}")
            time.sleep(5)
            continue
            
        print("\nListening...")
        if app.current_emotion not in ['shy', 'scared']: # Don't override special states
            app.root.after(0, lambda: app.set_emotion('neutral'))
        app.root.after(0, app.enable_touch)
        
        text = ""

        action_triggered = False      # Flag to break out after an action
        last_sensor_check_time = 0.0  # For throttling sensor reads
        high_five_state = "idle"      # State for high-five logic ("idle", "approached")
        approached_time = 0.0

        # --- THIS IS THE FIXED INNER LOOP ---
        while not stop_event.is_set():
            data = stream.read(4096, exception_on_overflow=False)
            
            # --- SENSOR CHECKS (High-Five & Scared) ---
            # All sensor logic is now INSIDE the audio loop
            now = time.time()
            # Check sensors 10 times per second (100ms interval)
            if bot and (now - last_sensor_check_time > 0.1):
                last_sensor_check_time = now

                # 1. High-Five Logic (Ultrasonic)
                try:
                    # Read 2-byte distance from registers 0x1b (High) and 0x1a (Low)
                    # --- FIX: Check if data is valid before indexing ---
                    data_H = bot.read_data_array(0x1b, 1)
                    data_L = bot.read_data_array(0x1a, 1)
                    
                    if data_H and data_L:
                        diss_H = data_H[0]
                        diss_L = data_L[0]
                        distance_mm = (diss_H << 8) | diss_L
                    else:
                        distance_mm = 999 # Set a default high distance if read fails
                    # --- END FIX ---

                    if high_five_state == "idle" and distance_mm < 120: # Hand approached
                        high_five_state = "approached"
                        approached_time = now
                    elif high_five_state == "approached":
                        if distance_mm > 170: # Hand receded
                            if (now - approached_time) < 1.0: # Check if it was fast (under 1 sec)
                                print("[AI] High Five!")
                                stream.stop_stream()
                                stream.close()
                                speak_and_animate(app, "High five!", 'happy')
                                high_five_state = "idle"
                                action_triggered = True
                                break # Exit inner loop
                            else:
                                high_five_state = "idle" # Too slow, reset
                        elif (now - approached_time) > 1.5: # Hand held too long, reset
                            high_five_state = "idle"
                except Exception:
                    pass # Ignore I2C errors

                # 2. Scared Logic (Line Tracker)
                try:
                    # Read the 4-bit sensor data from register 0x0a
                    # --- FIX: Check if data is valid before indexing ---
                    track_data = bot.read_data_array(0x0a, 1)
                    
                    if track_data:
                        track = track_data[0]
                    else:
                        track = 0 # Set a default of 0 (on ground) if read fails
                    # --- END FIX ---

                    # Check if all 4 bits are 1 (0x0F = 15)
                    # This means all sensors see "white" / no ground
                    if (track & 0x0F) == 0x00:
                        print("[AI] Ahh! Picked up!")
                        stream.stop_stream()
                        stream.close()
                        
                        # --- FIX: Launch new 'scared' reaction ---
                        # 1. Start the flashing red LED sequence in a non-blocking thread
                        threading.Thread(target=scared_led_sequence, daemon=True).start()
                        
                        # 2. Call speak_and_animate with the new 'scared' emotion and text
                        speak_and_animate(app, "Whoa! Put me down! I'm scared!", 'scared')
                        
                        action_triggered = True
                        break # Exit inner loop
                        # --- END FIX ---
                except Exception:
                    pass # Ignore I2C errors
            # --- END SENSOR CHECKS ---

            # --- SPEECH RECOGNITION (Now correctly indented) ---
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get('text', '').strip()
                if text: break
        # --- END OF THE FIXED INNER LOOP ---

        if stop_event.is_set():
            break
        
        # If a sensor action was triggered, skip the rest and restart the listening loop
        if action_triggered:
            app.root.after(0, app.disable_touch) # Make sure to disable touch
            # stream is already closed, so we just continue to the top of the outer loop
            continue

        # This code is only reached if speech was detected (action_triggered = False)
        app.root.after(0, app.disable_touch)
        stream.stop_stream()
        stream.close()
        if not text: continue

        print(f"You: {text}")
        user_command = text.lower()
        
        # --- Command Handling ---
        # Handle "dance" command first
        if any(word in user_command for word in ["dance", "party", "let's dance"]):
            speak_and_animate(app, "Okay, time to party!", 'happy')
            dance_routine()
            continue

        # Handle "square" command first
        if any(word in user_command for word in ["move square", "car patrol"]):
            speak_and_animate(app, "moving in a square", 'happy')
            car_patrol()
            continue

        car_moved = False
        speed = 50

        if "stop" in user_command:
            stop_car()
            speak_and_animate(app, "Stopping.", 'neutral')
            continue
        
        if "help" in user_command or "options" in user_command:
            help_text = "You can ask me to go forward, back, left, or right. You can also say turn left or turn right."
            speak_and_animate(app, help_text, 'neutral')
            continue

        for command, function in movement_commands.items():
            if command in user_command:
                set_movement_led() # Set LEDs to yellow for movement
                function(speed)
                speak_and_animate(app, f"Okay, {command}.", 'neutral')
                car_moved = True
                break
        
        if car_moved:
            if motor_timer and motor_timer.is_alive(): motor_timer.cancel()
            motor_timer = threading.Timer(0.5, stop_car)
            motor_timer.start()
            continue

        if user_command in ["goodbye", "bye", "by", "exit", "quit"]:
            stop_car()
            speak_and_animate(app, "Goodbye!", 'happy')
            time.sleep(2)
            if not stop_event.is_set():
                stop_event.set()
            app.root.after(0, app.root.quit)
            break
        
        # --- Chatbot LLM Logic ---
        print("Marich is thinking...")
        conversation_history.append({'role': 'user', 'content': text})
        
        if not _OLLAMA_OK or ollama is None:
            print('[AI] Ollama unavailable:', _OLLAMA_ERR)
            speech_text = "Chat model not installed."
            emotion = 'angry'
            conversation_history.append({'role': 'assistant', 'content': json.dumps({'text': speech_text, 'emotion': emotion})})
        else:
            try:
                # Use the model (it stays loaded in memory after first use)
                response = ollama.chat(model=Config.LLM_MODEL, messages=conversation_history, format='json')
                
                ai_response_json = json.loads(response['message']['content'])
                speech_text = ai_response_json.get('text', "I'm not sure how to respond.")
                emotion = ai_response_json.get('emotion', 'neutral').lower()
                if emotion not in Config.EMOTION_COLORS: emotion = 'neutral'
                conversation_history.append({'role': 'assistant', 'content': response['message']['content']})
            except Exception as e:
                print(f"LLM response parsing error: {e}")
                speech_text = "I seem to have gotten my wires crossed."
                emotion = 'angry'
                conversation_history.append({'role': 'assistant', 'content': json.dumps({'text': speech_text, 'emotion': emotion})})
        
        if len(conversation_history) > 7:
            conversation_history = [conversation_history[0]] + conversation_history[-6:]
            
        speak_and_animate(app, speech_text, emotion)

    # Cleanup before exiting thread
    try:
        if bot: # If bot was initialized
            bot.Ctrl_Ulatist_Switch(0) # Turn off ultrasonic sensor
    except Exception:
        pass
    try:
        stream.stop_stream()
        stream.close()
    except Exception:
        pass
    try:
        p.terminate()
    except Exception:
        pass
    print("[AI] Chatbot thread exiting.")

def request_stop(stop_event: threading.Event | None):
    """Signal a running chatbot loop to stop."""
    if stop_event is not None:
        stop_event.set()
