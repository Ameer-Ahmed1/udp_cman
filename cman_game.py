import cman_game_map as gm
import os
from enum import IntEnum

MAX_ATTEMPTS = 3
WIN_SCORE = 32

class Player(IntEnum):
	NONE = -1	# Error value for functions returning a Player value.
	CMAN = 0
	SPIRIT = 1

class Direction(IntEnum):
	UP = 0
	LEFT = 1
	DOWN = 2
	RIGHT = 3

class State(IntEnum):
	WAIT = 0	# Game may not start yet
	START = 1	# Round may start
	PLAY = 2	# Round has started
	WIN = 3		# Game ended

class Game():
	def __init__(self, map_path):
		"""

		Creates a new game instance.

		Parameters:

		map_path (str): a path to the textual map file

		"""
		assert os.path.isfile(map_path), "map file does not exist."
		self.board = gm.read_map(map_path).split('\n')
		self.board_dims = (len(self.board), len(self.board[0]))

		self.start_coords = []
		for p_char in gm.PLAYER_CHARS:
			start_row = [p_char in row for row in self.board].index(True)
			self.start_coords.append((start_row, self.board[start_row].index(p_char)))

		self.points = {(i,j):1 for i in range(self.board_dims[0])
							   for j in range(self.board_dims[1])
							   if self.board[i][j] == gm.POINT_CHAR}
		self.restart_game()

	def restart_game(self):
		"""
		
		Restarts all the variables of this game instance to their initial values.

		"""
		self.cur_coords = self.start_coords[::]
		print(self.cur_coords)
		self.score = 0
		for p in self.points.keys():
			self.points[p] = 1
		self.lives = MAX_ATTEMPTS
		self.state = State.WAIT
		self.winner = None

	def next_round(self):
		"""
		
		Moves all player coordinates to their starting coordinates and enable legal moves to be processed.

		"""
		self.cur_coords = self.start_coords[::]
		self.state = State.START

	def get_current_players_coords(self):
		"""
		
		Returns:

		list(tuple(int, int)): A list with the current coordinates of each player in this game instance

		"""
		return self.cur_coords

	def get_game_progress(self):
		"""
		
		Returns:

		tuple(int, int): A tuple with the ammount of lives left for Cman and Cman's current score in this game instance

		"""
		return self.lives, self.score

	def get_points(self):
		"""
		
		Returns:

		dict(tuple(int,int) : int): A dictionary with the coordinates of all collectible points as keys in this game instance

		Collected points will have a value of 0, uncollected will have a value of 1

		"""
		return self.points

	def get_winner(self):
		"""
		
		Returns:

		Player: The winner in this game instance, if declared, as a Player enum, or Player.NONE if no winner was declared yet

		"""
		if self.state == State.WIN:
			return self.winner
		else:
			return Player.NONE

	def declare_winner(self, player):
		"""
		
		Declares the game as finished and player as the winner, unless a winner was already declared.

		Parameters:

		player (Player): The winner

		Returns:

		Player: The declared

		"""
		if self.state != State.WIN:
			self.state = State.WIN
			self.winner = player
		return get_winner()

	def can_move(self, player):
		"""
		
		Checks whether a player may move in the current game state or not.

		Parameters:

		player (Player): The player to check

		Returns:

		bool: whether the player may move or not

		"""
		return (self.state == State.PLAY or (self.state == State.START and player == Player.CMAN))

	def apply_move(self, player, direction):
		"""
		
		Tries to apply a single movement in the game and update the game state accordingly.

		Parameters:

		player (Player): The player to move

		direction (Direction): The direction of movement

		Returns:

		bool: Whether the game state was changed or not

		"""
		if not self.can_move(player):
			return False

		p_coords = self.cur_coords[player]
		dr = -1 if direction == Direction.UP else 1 if direction == Direction.DOWN else 0
		dc = -1 if direction == Direction.LEFT else 1 if direction == Direction.RIGHT else 0
		next_coords = (p_coords[0] + dr, p_coords[1] + dc)

		if any(x < 0 for x in next_coords) or next_coords[0] >= self.board_dims[0] or next_coords[1] >= self.board_dims[1]:
			return False
		if self.board[next_coords[0]][next_coords[1]] not in gm.PASS_CHARS:
			return False
		else:
			self.state = State.PLAY
			self.cur_coords[player] = next_coords
			if player == Player.CMAN and next_coords in self.points.keys():
				self.score += self.points[next_coords]
				self.points[next_coords] = 0
				if self.score >= WIN_SCORE:
					self.declare_winner(Player.CMAN)
			if (player == Player.CMAN and next_coords in self.cur_coords[1:]) or (player != Player.CMAN and next_coords == self.cur_coords[0]):
				self.lives -= 1
				if self.lives <= 0:
					self.declare_winner(Player.SPIRIT)
				else:
					self.next_round()
			return True
