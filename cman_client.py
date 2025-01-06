import socket
import argparse
import struct
import json
import time
from threading import Thread
import threading
from pynput import keyboard
from cman_utils import clear_print  # Assuming this utility is available

PORT = 1337
BUFFER_SIZE = 1024

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=["cman", "spirit", "watcher"], help="Role in the game")
    parser.add_argument("addr", help="Server address (IP or hostname)")
    parser.add_argument("-p", "--port", type=int, default=PORT, help="Server port")
    args = parser.parse_args()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (args.addr, args.port)

    # Map role to corresponding number for the game
    role = {"cman": 0, "spirit": 1, "watcher": 2}[args.role]
    
    # Join game request
    join_message = {"opcode": 0x00, "role": role}
    client_socket.sendto(json.dumps(join_message).encode('utf-8'), server_address)

    # Use an event to signal quit
    quit_event = threading.Event()

    # Start a thread to listen for server updates
    listener_thread = Thread(target=listen_for_updates, args=(client_socket, quit_event))
    listener_thread.start()

    # Monitor keyboard inputs for player actions
    if args.role in ["cman", "spirit"]:
        monitor_keyboard(client_socket, server_address, quit_event)

    # Wait for the listener thread to finish
    listener_thread.join()
    print("Client session ended.")

def listen_for_updates(client_socket, quit_event):
    """Listen for updates from the server."""
    while not quit_event.is_set():
        try:
            data, _ = client_socket.recvfrom(BUFFER_SIZE)
            message = json.loads(data.decode('utf-8'))
            opcode = message.get("opcode")

            if opcode == 0x80:  # Game state update
                if message.get("message") == "Quit confirmed":
                    print("Server confirmed quit. Exiting.")
                    quit_event.set()  # Signal to exit
                    break
                handle_game_state(message)
            elif opcode == 0x8F:  # Game over announcement
                handle_game_over(message)
                break
            elif opcode == 0xFF:  # Error
                handle_error(message)
                break
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

def handle_game_state(message):
    """Display current game state."""
    clear_print("Game state:")
    print(f"Cman coordinates: {message.get('c_coords')}")
    print(f"Spirit coordinates: {message.get('s_coords')}")
    print(f"Collected items: {message.get('collected')}")
    print(f"Attempts left for Cman: {message.get('attempts')}")
    print("Freezing state:", message.get('freez'))

def handle_game_over(message):
    """Handle the game-over scenario."""
    winner = message.get("winner")
    s_score = message.get("S_SCORE")
    c_score = message.get("C_SCORE")
    clear_print(f"Game Over! Winner: {winner}")
    print(f"Spirit's score: {s_score}, Cman's score: {c_score}")
    
    # Wait for a few seconds before exiting (simulate the 10-second broadcast)
    time.sleep(10)

def handle_error(message):
    """Handle error messages."""
    clear_print(f"Error: {message.get('error')}")

def monitor_keyboard(client_socket, server_address, quit_event):
    """Monitor keyboard inputs and send commands to the server."""
    def on_press(key):
        try:
            if key.char == 'q':  # Quit command
                quit_message = {"opcode": 0x0F}
                client_socket.sendto(json.dumps(quit_message).encode('utf-8'), server_address)
                quit_event.set()  # Signal the main loop to exit
                return False  # Stop the keyboard listener
            elif key.char in ['w', 'a', 's', 'd']:  # Movement command
                direction = {"w": 0, "a": 1, "s": 2, "d": 3}[key.char]
                move_message = {"opcode": 0x01, "direction": direction}
                client_socket.sendto(json.dumps(move_message).encode('utf-8'), server_address)
        except AttributeError:
            pass  # Handle special keys if needed

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    main()
