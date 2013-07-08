#!/usr/bin/python
# coding=utf8
import argparse, json, curses, sys, time, urwid
from station import Station
from player import VlcPlayer
from mixzatape_ui import StationSearchBox

# the songza terminal player
# test station ID: 1393494

# TODO:
# * add up/downvote functionality
# * add volume display
# * add replay last song feature

# MixZaTape
# =========
# A Songza player for your terminal, with a nifty (?) urwid interface.
class MixZaTape:
	def __init__(self):
		# key handlers are set here
		# TODO: add alternate key mappings, VIM-style, possibly even user configurable?
		self.key_handlers = {
			# ESC key
			"esc": ("Exit", self.exit),
			"f9": ("Skip", self.skip),
			"+": ("Volume Up", self.volume_up),
			"-": ("Volume Down", self.volume_down),
			# space bar
			"f8": ("Pause", self.pause),
			"f10": ("Seek", self.seek),
			"f1": ("Help", self.show_help),
			"f2": ("Station Search", self.show_search),
			">": ("Upvote", self.upvote),
			"<": ("Downvote", self.downvote),
		}

		# UI text
		self.ui_text = {
			"current_track":	"Playing:  ",
			"last_track":		"Previous: ",
			"select_station":	"Select a Station",
			"help_controls":	"Controls",
			"current_station":	"Station: "
		}

	# setup_screen()
	# ==============
	# Builds and sets up the major screen components
	def setup_screen(self):
		# init main screen
		self.ui = {
			"track_info": urwid.Text(""),
			"station_info": urwid.Text("{0}{1}".format(self.ui_text["current_station"], "None")),
			"time_left": urwid.Text(""),
			"progress_bar": urwid.Text(""),
			"help_screen": self.build_help_screen(),
			"search_screen": self.build_search_screen(),
			"logo": self.build_logo()
		}

		# add widgets to main container
		window = urwid.Pile([
			self.ui["logo"],
			urwid.Divider(),
			self.ui["track_info"],
			urwid.Divider(),
			self.ui["time_left"],
			self.ui["progress_bar"],
			urwid.Divider(u"\u2501", 1, 1),
			self.ui["station_info"],
			urwid.Divider(u"\u2501", 1, 1),
			self.ui["help_screen"]
		])
		self.ui["window"] = window
		self.ui["container"] = urwid.Filler(window, "top")
		
	# exit()
	# ======
	# Exits the app, cleaning up GUI elements and stopping the player.
	def exit(self):
		# stop the music
		self.player.stop()
		urwid.ExitMainLoop();

		sys.exit()

	# start()
	# =======
	# Bootstraps by parsing arguments and such.
	# Starts the main run loop and binds event handlers.
	def start(self):
		# parse arguments
		parser = argparse.ArgumentParser(description="Plays music from Songza in your terminal")
		# parser.add_argument("--query", metavar="Query Text", help="Query text used to search for stations; the app will start with query results pre-populated")
		parser.add_argument("--station_id", metavar="1234567", help="This is the station ID used internally by Songza")
		parser.add_argument("--debug", action="store_true", help="Add this flag to dump debug info to a file.")

		args = parser.parse_args()

		# instatiate a player and station
		self.player = VlcPlayer()
		self.station = Station(self.player, 0, args.debug)

		# start streaming music, if station id was provided
		if args.station_id:
			self.station.station_id = args.station_id
			self.play_next()
			self.station.update_track_info()

		# build out the screen
		self.setup_screen()

		palette = [
			("bold", "default,bold", "default"),
			("reversed", "standout", ""),
			("logo", "standout", "black")
		]

		# start the run loop
		loop = urwid.MainLoop(self.ui["container"], palette, unhandled_input=self.handle_input)
		loop.set_alarm_in(1, self.stream)
		loop.set_alarm_in(.5, self.update_player_ui)
		loop.run()

	# handle_input(key)
	# =================
	def handle_input(self, key):
		# fire handler for the input key
		handler = self.key_handlers.get(key)
		if (handler is not None):
			handler[1]()

	# update_player_ui(loop, user_data)
	# =================================
	# Updates the player UI (current track, progress, etc).
	def update_player_ui(self, loop, user_data):
		# set a new timer
		loop.set_alarm_in(.5, self.update_player_ui)

		# don't redraw if currently paused	
		if self.is_paused():
			return

		# show the current track if not null or empty
		# remember that the cursor positon moves with the text by default
		if (bool(self.station.current_track)):
			track_text = [
				self.ui_text["current_track"],
				("bold", unicode(self.station.current_track["title"] + " ")),
				unicode(self.station.current_track["artist"]["name"])
			]

			self.ui["track_info"].set_text(track_text)

			# show time remaining
			seconds = int(self.time_remaining())

			# Occasionally, seconds remaining can be negative, especially immediately
			# after un-pausing. Skip this update if that is the case.
			if (seconds < 0):
				return
			duration = int(self.station.current_track["duration"])
			self.ui["time_left"].set_text("{0}:{1:02d} / {2}:{3:02d}".format(
				seconds / 60,
				seconds % 60,
				duration / 60,
				duration % 60
			))

			self.ui["progress_bar"].set_text(self.draw_progress_bar(3, 0, duration - seconds, duration, 50, u"\u2588"))
		else:
			self.ui["track_info"].set_text("")

	# draw_progress_bar(current, startY, startX, total, size, chr)
	# ============================================================
	# Draws a progress bar of the specified size.
	# - current: current value
	# - total: total value
	# - size: size of the bar (in characters)
	# - chr: character to use in drawing
	def draw_progress_bar(self, startY, startX, current, total, size, chr):
		progress = int((current * 1.0 / total) * size)
		bar = "".join([chr] * progress)

		# add caps
		gap = "".join(["-"] * (size - progress))
		bar += gap
		return u"{0}{1}{0}".format(u"|", bar)

	# stream(loop, user_data)
	# =======================
	# The stream() callback is fired in the main run loop to continuously stream music
	def stream(self, loop, user_data):
		if not self.is_paused():
			# check if current song is almost done
			time_left = self.time_remaining()
			
			# unable to accurately read time remaining, usually due to seeking (time == -1)
			if time_left > 0:
				if (time_left <= 5 and self.station.next_track == None):
					self.play_next()

				if (time_left <= 1 and self.station.next_track is not None):
					self.update_track_info()

		loop.set_alarm_in(1, self.stream)

	# build_logo()
	# ============
	def build_logo(self):
		text = urwid.Text(("reversed", "\n|[●▪▪●]| MixZaTape\n"))
		text.set_align_mode("center")
		return urwid.AttrMap(text, "logo")
		# return urwid.Filler(text, "bottom")

	# build_station_list(query)
	# ========================
	# Fires off a query for stations with the specified query test
	# and builds a select list of stations.
	def build_station_list(self, query):
		# build menu options
		# flatten down to just name => id dictionary
		menu_opts = {}
		stations = self.station.query_station(query)
		for station in stations:
			menu_opts[station["name"]] = station["id"]

		body = [urwid.Text(self.ui_text["select_station"]), urwid.Divider()]
		for k in menu_opts.keys():
			button = urwid.Button(k)
			urwid.connect_signal(button, "click", self.on_station_selected, (k, menu_opts[k]))
			body.append(urwid.AttrMap(button, None, focus_map="reversed"))

		return urwid.BoxAdapter(urwid.ListBox(urwid.SimpleFocusListWalker(body)), 20)

	# build_help_screen()
	# ===================
	# Build the help screen.
	def build_help_screen(self):
		body = [urwid.Text(("bold", self.ui_text["help_controls"])), urwid.Divider()]
	
		# display control keys in alphabetical order
		keys = self.key_handlers.keys()
		keys.sort()
		for k in keys:
			handler = self.key_handlers[k]
			body.append(urwid.Text("[{0}]: {1}".format(k, handler[0])))

		return urwid.Pile(body)

	# build_search_screen()
	# =====================
	# Build the station search screen.
	def build_search_screen(self):
		input = StationSearchBox("Station Search: ", "")
		urwid.connect_signal(input, "keypress", self.on_search_keypress)

		body = [
			input
		]

		return urwid.Pile(body)
		

	# handler for selected station
	def on_station_selected(self, button, key_value):
		self.change_station(key_value[0], key_value[1])

	# custom keypress handler for the station list
	def on_search_keypress(self, widget, size, key):
		# submit query on enter
		if (key == "enter"):
			station_list = self.build_station_list(widget.get_edit_text())
			self.show_screen(station_list)
		# allow controls keys to execute
		elif (key in self.key_handlers):
			self.key_handlers[key][1]()

	# show_screen(screen)
	# ===================
	# Inserts the specified screen into the main window.
	def show_screen(self, screen):
		i = len(self.ui["window"].contents) - 1
		self.ui["window"].contents[i] = (screen, ("weight", 1))
		self.ui["window"].focus_position = i

	# show_help()
	# ===========
	# Display the help screen.
	def show_help(self):
		self.show_screen(self.ui["help_screen"])

	# show_search()
	# =============
	# Display the search screen.
	def show_search(self):
		self.show_screen(self.ui["search_screen"])

	# change_station(station_name, station_id)
	# ========================================
	def change_station(self, station_name, station_id):
		# set ui components with new station info
		self.ui["station_info"].set_text(
			"{0}{1} ({2})".format(
				self.ui_text["current_station"],
				station_name,
				station_id
			)
		)
		self.station.change_station(station_name, station_id)
		self.skip()
		
	# the below functions are wrappers for the station and player classes

	def play_next(self):
		self.station.play_next()

	def skip(self):
		# TODO some sort of status indicator on skip? Or limit skips?
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

	def is_paused(self):
		return self.player.is_paused

	def time_remaining(self):
		# return self.station.time_remaining()
		return self.player.time_remaining()

	def seek(self):
		return self.player.seek(self.player.get_time() + 30)

	# upvote current track
	def upvote(self):
		if bool(self.station.current_track):
			self.station.vote(self.station.current_track["id"], True)

	# downvote current track
	# and skip it
	def downvote(self):
		if bool(self.station.current_track):
			self.station.vote(self.station.current_track["id"], False)
			self.skip()

# ---------------------------------------------------------- #

mixtape = MixZaTape()
mixtape.start()
