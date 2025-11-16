# rock_paper_scissors.py
#
# Contains the logic for the Rock, Paper, Scissors game mode.

import threading
import time
import random
# import cv2 # REMOVED: No longer needed, CameraMaster handles CV
# import numpy as np # REMOVED: No longer needed

# Assuming necessary imports from sibling modules
from robot_hardware import (
    stop as motor_stop, turn_off_led, dance_routine,
    angry_movement, win_led_sequence, lose_led_sequence
)
from chatbot_logic import speak_and_animate
from face_gui import MarichFaceApp, Config
from CameraLib.camera_master_lib import CameraMaster

# Game Constants
ROCK = 0
PAPER = 1
SCISSORS = 2
GAME_OPTIONS = {
    ROCK: {"name": "Rock", "image": Config.RPS_ROCK_PATH},
    PAPER: {"name": "Paper", "image": Config.RPS_PAPER_PATH},
    SCISSORS: {"name": "Scissors", "image": Config.RPS_SCISSORS_PATH}
}

# --- TTS Lines ---
START_LINES = [
    "Challenge accepted! Let's play rock paper scissors!",
    "Ready to lose to a machine? Let the battle begin!",
    "I hope you brought your best strategy. First match starts now."
]

SHOOT_PHRASES = [
    "Rock, Paper, Scissors, shoot!",
    "On the count of three... Rock, Paper, Scissors, go!",
    "Ready? Rock, Paper, Scissors, now!"
]

WIN_LINES = [
    "Yes! I win again! Victory is mine!",
    "Beep boop, my programming prevails! Better luck next time, human.",
    "Another flawless victory for the Marich operating system!"
]

LOSE_LINES = [
    "What?! I mean, you won! Ah, frustration!",
    "A temporary setback. I let you win that one, I promise.",
    "Curse this fleshy adversary! You got lucky, I'll admit it."
]

DRAW_LINES = [
    "A draw! Great minds think alike, but next time I'll crush you!",
    "Stalemate! Let's try to break the deadlock.",
    "We tied! Time for a rematch."
]

NEXT_MATCH_LINES = [
    "Again! I'll win next time!",
    "One more round, I need to redeem myself.",
    "Your luck won't last. Let's go again."
]

END_LINES = [
    "Thanks for the game! I enjoyed our battle of wits... and hands.",
    "Game over. Come back when you're ready for a rematch!",
    "Exiting game mode. See you next time!"
]


# --- Camera / Finger Counting Logic ---
# REMOVED: The _count_fingers and fingers_to_move functions are deleted.
# We will now rely on the CameraMaster object to provide the gesture.

# --- Game Logic ---

def determine_winner(player_move: int, marich_move: int) -> str:
    """Determines the winner ('win', 'lose', 'draw')."""
    if player_move == marich_move:
        return 'draw'
    # Player Wins: (P vs R) or (R vs S) or (S vs P)
    if (player_move == PAPER and marich_move == ROCK) or \
            (player_move == ROCK and marich_move == SCISSORS) or \
            (player_move == SCISSORS and marich_move == PAPER):
        return 'win'  # Marich loses
    # Marich Wins: (R vs P) or (S vs R) or (P vs S)
    return 'lose'  # Marich wins


# --- Main Game Thread Function ---

def run_rps_game(app: MarichFaceApp, camera: CameraMaster, stop_event: threading.Event):
    """
    Main loop for the Rock, Paper, Scissors game.
    Runs in its own thread.
    """

    # 1. Initialization
    motor_stop()
    turn_off_led()

    # --- FIX: Thread-Safety ---
    # All UI operations MUST be scheduled on the main thread using app.root.after
    app.root.after(0, lambda: app.set_emotion('happy'))
    # --- END FIX ---

    # Start the game
    # We assume speak_and_animate is thread-safe (handles its own root.after calls)
    # since the chatbot thread also uses it.
    speak_and_animate(app, random.choice(START_LINES), 'neutral')

    time.sleep(1.0)  # Pause after intro

    while not stop_event.is_set():
        # A. Marich makes a choice
        marich_choice = random.choice(list(GAME_OPTIONS.keys()))
        marich_move_name = GAME_OPTIONS[marich_choice]["name"]
        marich_image_path = GAME_OPTIONS[marich_choice]["image"]

        print(f"[RPS] Marich chose: {marich_move_name}")

        # B. Start the countdown and capture phase
        speak_and_animate(app, random.choice(SHOOT_PHRASES), 'neutral')

        # Give a small window for the user to make their move
        time.sleep(0.3)

        # --- MODIFIED BLOCK ---
        # C. Capture the player's move
        player_move_result = None

        print("[RPS] Listening for player's gesture...")
        start_capture_time = time.time()
        capture_duration = 2.0  # Listen for 2 seconds

        gesture_name = "none"
        while time.time() - start_capture_time < capture_duration:
            if stop_event.is_set(): break

            try:
                # --- FIX: Call the correct method get_gesture_detection()
                # ---      and access the .gesture attribute from the result.
                detection_result = camera.get_gesture_detection()
                
                if detection_result:
                    gesture_name = detection_result.gesture
                else:
                    gesture_name = "none" # No hand detected
                
            except AttributeError:
                print("[RPS] FATAL ERROR: 'CameraMaster' object has no attribute 'get_gesture_detection'.")
                print("[RPS] This indicates a mismatch between rock_paper_scissors.py and camera_master_lib.py.")
                # As a fallback, just pick a random move for the player to avoid a crash
                player_move_result = random.choice([ROCK, PAPER, SCISSORS])
                break  # Exit loop
            except Exception as e:
                print(f"[RPS] Error calling get_gesture_detection: {e}")
                time.sleep(0.1)
                continue

            # --- FIX: Translate gesture names from the library ("Zero", "Two", "Five")
            # ---      to the game logic ("rock", "paper", "scissors")

            if gesture_name == "Zero" or gesture_name == "One":      # "Zero" is a fist (Rock)
                player_move_result = ROCK
                break
            elif gesture_name == "Five" or gesture_name == "Four":    # "Five" is an open hand (Paper)
                player_move_result = PAPER
                break
            elif gesture_name == "Two" or gesture_name == "Three":     # "Two" is two fingers (Scissors)
                player_move_result = SCISSORS
                break   
            # --- END OF FIX ---

            # If gesture is "none" or unrecognized, keep looping
            time.sleep(0.05)  # Poll quickly

        if player_move_result is not None:
            player_move_name = GAME_OPTIONS[player_move_result]["name"]
            print(f"[RPS] Player detected move: {player_move_name}")
        else:
            print("[RPS] No clear move detected.")
            # This call is already correctly wrapped in your original file
            app.root.after(0, lambda: app.set_emotion('confused'))

        # --- END OF MODIFIED BLOCK ---

        # D. Display Marich's move and determine the winner
        # This call is already correctly wrapped
        app.root.after(0, lambda p=marich_image_path: app.display_game_image(p))

        # Short pause to let the user see the move and image appear
        time.sleep(1.0)

        if player_move_result is None:
            # If no clear move was detected after all attempts
            result = 'draw'
            result_line = "I couldn't quite see your hand! Let's call that a draw."

        else:
            result = determine_winner(player_move_result, marich_choice)
            print(f"[RPS] Result: Marich {result}s.")

            # E. Marich's Reaction (TTS, Face, Hardware)
            if result == 'lose':
                # Marich WINS
                result_line = random.choice(WIN_LINES)
                app.root.after(0, lambda: app.set_emotion('happy'))
                threading.Thread(target=dance_routine, daemon=True).start()
                threading.Thread(target=win_led_sequence, daemon=True).start()

            elif result == 'win':
                # Marich LOSES
                result_line = random.choice(LOSE_LINES)
                app.root.after(0, lambda: app.set_emotion('angry'))
                threading.Thread(target=angry_movement, daemon=True).start()
                threading.Thread(target=lose_led_sequence, daemon=True).start()

            else:  # Draw
                result_line = random.choice(DRAW_LINES)
                app.root.after(0, lambda: app.set_emotion('neutral'))
                # No movement for draw

        # Say the reaction line
        speak_and_animate(app, result_line, app.current_emotion)

        # F. Pause and cleanup before next match
        time.sleep(2.0)

        app.root.after(0, app.clear_game_image)
        motor_stop()  # Stop any lingering movement
        turn_off_led()
        app.root.after(0, lambda: app.set_emotion('neutral'))

        if not stop_event.is_set():
            # Say next match line and wait before the next loop iteration
            speak_and_animate(app, random.choice(NEXT_MATCH_LINES), 'neutral')
            time.sleep(1.0)

    # 2. Cleanup / Exit
    end_line = random.choice(END_LINES)
    speak_and_animate(app, end_line, 'neutral')
    app.root.after(0, app.clear_game_image)
    turn_off_led()
    motor_stop()
    print("[RPS] Rock Paper Scissors game thread exiting.")


def request_stop(stop_event: threading.Event | None):
    """Signal a running game loop to stop."""
    if stop_event is not None:
        stop_event.set()

