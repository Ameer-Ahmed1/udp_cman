import socket
import json
import cman_game as gm  # Assuming this module contains relevant game constants
import os
import time

# Configuration
HOST = '127.0.0.1'  # Localhost
PORT = 1337         # Default port
BUFFER_SIZE = 1024

class CmanServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((HOST, PORT))
        self.clients = []
        print(f"Server is running on {HOST}:{PORT}")

        # Track connections
        self.cman = None          # Stores (address, port) for Cman
        self.spirit = None        # Stores (address, port) for Spirit
        self.watchers = []        # List of (address, port) for watchers
        self.game = gm.Game("map.txt")
        self.game_started = False

        # Use constants from cman_game for the initial game state
        self.game_state = {
            "c_coords": self.game.start_coords[0],  # Use the constant or value for Cman’s starting position
            "s_coords": self.game.start_coords[1],  # Use the constant or value for Spirit’s starting position
            "collected": [],  # Start with no points collected
            "attempts": gm.MAX_ATTEMPTS  # Use max attempts from cman_game
        }

    def start_server(self):
        print("Waiting for connections...")
        while True:
            data, address = self.server_socket.recvfrom(BUFFER_SIZE)
            message = json.loads(data.decode('utf-8'))
            self.handle_message(message, address)

    def handle_message(self, message, address):
        """Handle incoming messages based on their OPCODE."""
        opcode = message.get("opcode")
        
        if opcode == 0x00:  # Join request
            self.handle_join(message, address)
        elif opcode == 0x01:  # Player movement
            self.handle_movement(message, address)
        elif opcode == 0x0F:  # Quit
            self.handle_quit(address)
            print("Im here")
        else:
            self.send_error(address, "Invalid OPCODE")

    def handle_join(self, message, address):
        """Handle join requests."""
        role = message.get("role")
        game_state_message = {
            "opcode": 0x80,
            "freez": 1,  # Assuming a placeholder value for the freeze state
            "c_coords": self.game_state["c_coords"],
            "s_coords": self.game_state["s_coords"],
            "collected": self.game_state["collected"],
            "attempts": self.game_state["attempts"]
        }
        self.clients.append(address)
        if role == 0 and self.cman is None:  # Cman
            self.cman = address
        elif role == 1 and self.spirit is None:  # Spirit
            self.spirit = address
        elif role == 2:  # Watcher
            if address not in self.watchers:
                self.watchers.append(address)
        else:
            self.clients.remove(address)
            self.send_error(address, "Role already taken or invalid.")
        self.broadcast(game_state_message)
        self.check_start_game()

    def check_start_game(self):
        """Start the game if both players are connected."""
        if self.cman and self.spirit and not self.game_started:
            self.game_started = True
            self.update_game_state(0)
    
    def restart_game(self):
        self.cman = None          # Stores (address, port) for Cman
        self.spirit = None        # Stores (address, port) for Spirit
        self.watchers = []        # List of (address, port) for watchers

        self.game_started = False

        # Use constants from cman_game for the initial game state
        self.game_state = {
            "c_coords": self.game.start_coords[0],  # Use the constant or value for Cman’s starting position
            "s_coords": self.game.start_coords[1],  # Use the constant or value for Spirit’s starting position
            "collected": [],  # Start with no points collected
            "attempts": gm.MAX_ATTEMPTS  # Use max attempts from cman_game
        }
        self.game.restart_game()

    def announce_winner(self):
        winner = self.game.get_winner() + 1
        S_SCORE = 3-self.game.get_game_progress()[0]
        C_SCORE = self.game.get_game_progress()[1]
        game_over_message = {
            "opcode": 0x8F,  # WINNER opcode
            "winner": winner,
            "S_SCORE": S_SCORE,
            "C_SCORE": C_SCORE
        }
        self.restart_game()

        # Broadcast the winner message for 10 seconds, every second
        start_time = time.time()
        while time.time() - start_time < 10:
            self.broadcast(game_over_message)
            time.sleep(1)

    def handle_movement(self, message, address):
        """Handle player movements."""
        if address == self.cman:
            player = gm.Player.CMAN
        elif address == self.spirit:
            player = gm.Player.SPIRIT
        else:
            self.send_error(address, "You are not a player.")
            return

        direction = message.get("direction")
        direction_enum = gm.Direction(direction)

        # Try to apply the move using the game instance
        if self.game.apply_move(player, direction_enum):
            # Successfully applied the move, update game state
            self.update_game_state(1)
        else:
            self.send_error(address, "Invalid move.")
    def move_player(self, coords, direction):
        """Dummy movement logic for updating coordinates."""
        x, y = coords
        if direction == 0:  # UP
            y += 1
        elif direction == 1:  # Left
            x -= 1
        elif direction == 2:  # Down
            y -= 1
        elif direction == 3:  # Right
            x += 1
        return (x, y)

    def handle_quit(self, address):
        """Handle player or watcher quitting."""
        if address == self.cman:
            self.cman = None
        elif address == self.spirit:
            self.spirit = None
        elif address in self.watchers:
            self.watchers.remove(address)
        else:
            self.send_error(address, "Unknown client.")
        quit_confirmation = {"opcode": 0x80, "message": "Quit confirmed"}
        self.send_message(address, quit_confirmation)
        if(self.game_started == True):
            if(address == self.cman):
                self.game.declare_winner(1)
            else:
                self.game.declare_winner(0)
            self.announce_winner()        
            self.restart_game()    
        else:
            quit_notification = {
            "opcode": 0x80,
            "message": f"Player or Watcher at {address} has left the game."
        }
            self.broadcast(quit_notification)
        
    def update_game_state(self, flag):
        """Send the current game state to all clients."""
        if flag == 0:
            game_state_message = {
                "opcode": 0x80,
                "freez": 0,  
                "c_coords": list(self.game.get_current_players_coords()[gm.Player.CMAN]),
                "s_coords": list(self.game.get_current_players_coords()[gm.Player.SPIRIT]),
                "collected": self.game.get_collected_points_count(),
                "attempts": self.game.get_game_progress()[0]  # Lives left for Cman
            }
        else:
            # Update state based on the move applied
            game_state_message = {
                "opcode": 0x80,
                "freez": 1,
                "c_coords": list(self.game.get_current_players_coords()[gm.Player.CMAN]),
                "s_coords": list(self.game.get_current_players_coords()[gm.Player.SPIRIT]),
                "collected": self.game.get_collected_points_count(),
                "attempts": self.game.get_game_progress()[0]  # Lives left for Cman
            }
        curr_winner = self.game.get_winner() 
        if(curr_winner == gm.Player.NONE):
            self.broadcast(game_state_message)
        else:
            self.announce_winner()
            self.restart_game()



    def broadcast(self, message):
        """Send a message to all clients."""
        for client in [self.cman, self.spirit] + self.watchers:
            if client:
                self.send_message(client, message)

    def send_message(self, address, message):
        """Send a JSON message to a specific address."""
        self.server_socket.sendto(json.dumps(message).encode('utf-8'), address)

    def send_error(self, address, error_message):
        """Send an error message to a specific address."""
        self.send_message(address, {"opcode": 0xFF, "error": error_message})


if __name__ == "__main__":
    server = CmanServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("Server shutting down.")
