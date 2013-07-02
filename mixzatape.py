#!/usr/bin/python
import argparse, json, curses, sys, time
from station import Station
from player import VlcPlayer

# the songza terminal player
# test station ID: 1393494

# TODO implement curses
# * show current track
# * show controls settings
# * loop play next, based on song duration
#   - start buffering a few seconds before the song ends
# * modify play() in the player to check `status` when already open
#   - if status text contains "( state stopped )" then we need to send a play command
# * add skip functionality
# * add up/downvote functionality

# TODO long-term:
# * curses-based display of current volume

# MixZaTape
# =========
# A Songza player for your terminal, with a nifty curses interface.
class MixZaTape:
	def __init__(self):
		# key handlers are set here
		# TODO: add alternate key mappings, VIM-style, possibly even user configurable?
		self.key_handlers = {
			# ESC key
			27: self.exit,
			curses.KEY_RIGHT: self.skip,
			curses.KEY_LEFT: self.replay_last,
			curses.KEY_UP: self.volume_up,
			curses.KEY_DOWN: self.volume_down,
			# space bar
			32: self.pause,
			# 's'
			115: self.seek
		}

		# UI text
		self.ui_text = {
			"current_track":	"Playing:  ",
			"last_track":		"Previous: "
		}

		self.setup_screen()

	# setup_screen()
	# ==============
	def setup_screen(self):
		self.screen = curses.initscr();
		curses.noecho()
		curses.cbreak()
		self.screen.keypad(1)
		self.screen.nodelay(1)


	# exit()
	# ======
	# Exits the app, cleaning up curses settings.
	def exit(self):
		curses.nocbreak()
		self.screen.keypad(0)
		self.screen.nodelay(0)
		curses.echo()

		curses.endwin()

		# stop the music
		self.player.stop()

		sys.exit()

	# start()
	# =======
	# Bootstraps by parsing arguments and such.
	def start(self):
		# parse arguments
		parser = argparse.ArgumentParser(description="Plays music from Songza in your terminal")
		parser.add_argument("station_id", metavar="1234567", help="This is the station ID used internally by Songza")

		args = parser.parse_args()
		print args

		# instatiate a player and station
		self.player = VlcPlayer()
		self.station = Station(args.station_id, self.player)

		# start the run loop
		self.run()

	# render()
	# ========
	# Draw the UI.
	def render(self):
		self.screen.clear()

		# show the current track if not null or empty
		# remember that the cursor positon moves with the text by default
		if (bool(self.station.current_track)):
			self.screen.addstr(0, 0, self.ui_text["current_track"])
			self.screen.addstr(self.station.current_track["title"], curses.A_BOLD)
			self.screen.addstr(" " + self.station.current_track["artist"]["name"])

			# show time remaining
			seconds = int(self.time_remaining())
			self.screen.addstr(1, 0, "{0}:{1:02d}".format(seconds / 60, seconds % 60))

			duration = int(self.station.current_track["duration"])
			self.screen.addstr(" / {0}:{1:02d}".format(duration / 60, duration % 60))

			self.screen.addstr(2, 0, str(self.time_remaining()))
			self.draw_progress_bar(3, 0, duration - seconds, duration, 50, "=")
		else:
			self.screen.addstr(0, 0, "ERROR")


		self.screen.refresh()

	# draw_progress_bar(current, startY, startX, total, size, chr)
	# ============================================
	# Draws a progress bar of the specified size.
	# - current: current value
	# - total: total value
	# - size: size of the bar (in characters)
	# - chr: character to use in drawing
	def draw_progress_bar(self, startY, startX, current, total, size, chr):
		# FIX THIS
		progress = int((current * 1.0 / total) * size)
		bar = "".join([chr] * progress)
		# self.screen.addstr(startY, startX, str(progress))
		self.screen.addstr(startY, startX, bar)

	# run()
	# =====
	# The main run loop; calls the render() function and handles input.
	def run(self):
		# start streaming music
		self.play_next()

		tick = 0
		while True:

			# read input
			char = self.screen.getch()

			# fire handler for the input key
			handler = self.key_handlers.get(char)
			if (handler is not None):
				handler()
				tick = 0

			if tick > 20:
				tick = 0
				# check if current song is almost done
				time_left = self.time_remaining()
				if (time_left <= 5 and self.station.next_track == None):
					self.play_next()

				if (time_left <= 1):
					self.update_track_info()

			tick += 1
		
			# draw the screen
			self.render()
							
	def play_next(self):
		self.station.play_next()
		self.station.update_track_info()

		# redraw
		# self.render()

	def skip(self):
		# TODO some sort of stats indicator on skip? Or limit skips?
		self.play_next()
		self.player.skip()
		self.update_track_info()

	def update_track_info(self):
		self.station.update_track_info()

	def replay_last(self):
		# TODO: implement this
		self.station.play_next()

	def volume_up(self):
		self.player.volume_up()

	def volume_down(self):
		self.player.volume_down()

	def pause(self):
		self.player.pause()

	def time_remaining(self):
		# return self.station.time_remaining()
		return self.player.time_remaining()

	def seek(self):
		return self.player.seek(self.player.get_time() + 1)

# ---------------------------------------------------------- #

mixtape = MixZaTape()
mixtape.start()
