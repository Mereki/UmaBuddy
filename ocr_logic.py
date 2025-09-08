import cv2
from PIL import ImageGrab
import numpy as np
import easyocr  # The new OCR library
import json
import time
import re
import threading
from pynput import keyboard
from database import get_event_outcomes

# --- Visual Debugger ---
SAVE_DEBUG_IMAGES = True


class OcrEngine:
    """Manages the OCR process using the EasyOCR library."""

    def __init__(self, overlay_widget):
        self.overlay = overlay_widget
        self.settings = self.load_settings()
        if not self.settings:
            self.engine_ok = False
            return

            # --- NEW: Initialize EasyOCR ---
        print("Initializing EasyOCR... (This may take a moment)")
        # This is the line that will trigger the one-time model download.
        self.reader = easyocr.Reader(['en'])
        print("EasyOCR initialized successfully.")
        self.engine_ok = True

        # --- NEW: Clear the status message from the overlay ---
        self.overlay.clear_outcomes()

        # State Management
        self.STATE_SEARCH_CHAR = "SEARCHING_FOR_CHARACTER"
        self.STATE_SEARCH_EVENT = "SEARCHING_FOR_EVENT"
        self.current_state = self.STATE_SEARCH_CHAR

        self.current_character_candidate = ""
        self.last_seen_event = ""

        # Start the hotkey listener in a background thread
        self.listener_thread = threading.Thread(target=self.start_hotkey_listener)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        print("Hotkey listener started. Press F10 at any time to reset character search.")

    def load_settings(self):
        """Loads configuration from settings.json."""
        try:
            with open("settings.json", "r") as f:
                print("Core logic loaded settings from settings.json")
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("\n--- CRITICAL ERROR ---")
            print("Could not load settings.json in core_logic.")
            return None

    def reset_search(self):
        """Resets the state to search for a new character."""
        self.current_state = self.STATE_SEARCH_CHAR
        self.current_character_candidate = ""
        self.last_seen_event = ""
        self.overlay.clear_outcomes()
        print("\n--- HOTKEY PRESSED: RESETTING ---")
        print("Now searching for a character name on the selection screen...")

    def start_hotkey_listener(self):
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()

    def on_press(self, key):
        if key == keyboard.Key.f10:
            self.reset_search()

    def clean_text(self, text):
        """Strips all non-alphanumeric characters from text for reliable matching."""
        return re.sub(r'[^a-zA-Z0-9\s]', '', text).strip()

    def main_loop(self):
        """The main OCR processing loop that runs continuously."""
        if not self.engine_ok:
            print("OCR engine did not start due to an initialization error.")
            return

        print(f"Starting OCR engine. Initial state: {self.current_state}")

        try:
            while True:
                if self.current_state == self.STATE_SEARCH_CHAR:
                    region = self.settings.get('character_region')
                    if not region:
                        time.sleep(5)
                        continue

                    bbox = (region['left'], region['top'], region['left'] + region['width'],
                            region['top'] + region['height'])
                    img_pil = ImageGrab.grab(bbox=bbox)
                    img_np = np.array(img_pil)

                    # --- OCR with EasyOCR ---
                    results = self.reader.readtext(img_np)
                    # Combine results into a single string
                    text = ' '.join([res[1] for res in results])
                    cleaned_text = self.clean_text(text)

                    if SAVE_DEBUG_IMAGES:
                        # Draw boxes for debugging
                        for (bbox, text, prob) in results:
                            (top_left, top_right, bottom_right, bottom_left) = bbox
                            top_left = tuple(map(int, top_left))
                            bottom_right = tuple(map(int, bottom_right))
                            cv2.rectangle(img_np, top_left, bottom_right, (0, 255, 0), 2)
                        # Convert back to BGR for saving with cv2
                        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                        cv2.imwrite("debug_char_region.png", img_bgr)

                    if cleaned_text and cleaned_text != self.current_character_candidate:
                        self.current_character_candidate = cleaned_text
                        print(f"Candidate character found: {self.current_character_candidate}")
                    elif not cleaned_text and self.current_character_candidate:
                        print(f"\n--- CHARACTER CONFIRMED: {self.current_character_candidate} ---")
                        self.current_state = self.STATE_SEARCH_EVENT
                        print("Switching state: Now searching for in-game events...")

                elif self.current_state == self.STATE_SEARCH_EVENT:
                    region = self.settings.get('event_region')
                    if not region:
                        time.sleep(5)
                        continue

                    bbox = (region['left'], region['top'], region['left'] + region['width'],
                            region['top'] + region['height'])
                    img_pil = ImageGrab.grab(bbox=bbox)
                    img_np = np.array(img_pil)

                    results = self.reader.readtext(img_np)
                    text = ' '.join([res[1] for res in results])
                    cleaned_text = self.clean_text(text)

                    if cleaned_text and cleaned_text != self.last_seen_event:
                        print(f"\nDetected event: '{cleaned_text}'")
                        outcomes = get_event_outcomes(cleaned_text, self.current_character_candidate)

                        if outcomes:
                            outcome_descriptions = [desc for _, desc in outcomes]
                            self.overlay.update_outcomes(outcome_descriptions)
                            print(f"-> Displaying {len(outcomes)} outcomes on overlay.")
                        else:
                            self.overlay.clear_outcomes()
                            print(f"-> Event not found for '{self.current_character_candidate}' or in 'Common' events.")

                        self.last_seen_event = cleaned_text
                    elif not cleaned_text:
                        self.last_seen_event = ""
                        self.overlay.clear_outcomes()

                # Main loop delay
                time.sleep(1)
        except Exception as e:
            print(f"\n--- An unexpected error occurred in the main OCR loop ---")
            print(e)
            print("----------------------------------------------------------\n")


def run_ocr_engine(overlay_widget):
    """Entry point function to be called from the GUI in a separate thread."""
    engine = OcrEngine(overlay_widget)
    engine.main_loop()

