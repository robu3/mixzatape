import httplib, urllib, urllib2, argparse, json, os, threading, time, logging, os

# Station
# =======
# A representation of a Songza station(s); wraps the web API calls, and plays tracks using
# the specified player (VLC only at the moment)
class Station:
	# constructor
	def __init__(self, player, station_id=0, debug=False):
		# set station_id
		self.station_id = int(station_id)

		# set the player for this station
		if player is None:
			raise Error("A player must be specified when creating a new station")
		else:
			self.player = player

		# previous_track
		# =============
		# Dictionary of data for the previous track
		self.previous_track = ""

		# current_track
		# =============
		# Dictionary of data for the current track
		self.current_track = ""

		# next_track
		# =============
		# Dictionary of data for the next track
		self.next_track = None

		# track_start
		# ===========
		# Time the current track started
		self.track_start = 0

		# flip
		# Keeps track which side of the tape we're on :D
		# Seriously though, we use this to alternate files when streaming data.
		self.flip = True

		# turn debugging on
		self.debug = debug

		# setup logger
		# clear log on startup
		logpath = "./.station.log"
		if os.path.exists(logpath):
			os.remove(logpath)

		if self.debug:
			self.logger = logging.getLogger("station")
			handler = logging.FileHandler(logpath)
			formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
			handler.setFormatter(formatter)
			self.logger.addHandler(handler)
			self.logger.setLevel(logging.DEBUG)

		# HTTP headers used for requests
		# fake the user agent so we're not rejected
		self.headers = {
			"Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
			"Accept": "application/json, text/javascript, */*; q=0.01",
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36"
		}
		

	# connect()
	# =========
	# Returns a HTTP connection to the specified station.
	# This method serves as the basis for most requests.
	def connect(self):
		# create connection to songza
		domain = "songza.com"
		conn = httplib.HTTPConnection(domain)

		return conn

	# get_station_path()
	# ==================
	# Returns the path to the station
	def get_station_path(self):
		return "/api/1/station/" + str(self.station_id)

	# change_station(name, station_id)
	# ================================
	# Changes the station.
	def change_station(self, name, station_id):
		self.station_id = station_id
		
	# next()
	# ======
	# Get the next track information from the server,
	# and decode the JSON response.
	def next(self):
		# create connection
		conn = self.connect()

		# create post body
		params = urllib.urlencode({"cover_size": "m", "format": "aac", "buffer": 0 })
		conn.request("POST", self.get_station_path() + "/next", params, self.headers)

		response = conn.getresponse()
		json_data = response.read()

		if self.debug:
			self.logger.debug("next() data: " + json_data)

		# decode json data
		return json.loads(json_data)
	
	# play_next()
	# ===========
	# Get and play the next track.
	# Also sets the `current_track` property with the current track information.
	def play_next(self):
		# get the next track
		track_data = self.next()

		if self.debug:
			self.logger.debug("next track: " + track_data["listen_url"])

		# track_data -> listen_url
		# download the file specified in the response
		response = urllib2.urlopen(track_data["listen_url"])

		# remember info about the current track
		self.next_track = track_data["song"]
	
		# self.previous_track = self.current_track
		# self.current_track = track_data["song"]
	
		# overwrite the same files repeatedly
		# (we're not pirates) ;)
		filename = ( "a" if self.flip else "b") + "-side.mp4"
		track = open(filename, "w")	
		track.write(response.read())

		# flip the side
		self.flip = not self.flip

		# remember time the track was started
		self.track_start = time.time()

		# actually play the track
		# pass in the full path to the file
		# filename = os.path.dirname(os.path.abspath(__file__)) + "/" + filename
		self.player.play(filename)

	# tune_in()
	# =========
	# Tune in and stream music
	def tune_in(self):
		self.play_next()
		time.sleep(self.current_track["duration"] - 5)
		self.tune_in();


	# time_remaining()
	# ================
	def time_remaining(self):
		return self.current_track["duration"] - (time.time() - self.track_start)

	# update_track_info()
	# ===================
	# Updates the track info properties:
	# * previous_track => current_track
	# * current_track => next_track
	# * next_track => None
	def update_track_info(self):
		if (self.next_track != None):
			self.previous_track = self.current_track
			self.current_track = self.next_track
			self.next_track = None

	# query_station()
	# ===============
	# Searches Songza for new stations by name
	def query_station(self, query):
		# create connection
		conn = self.connect()

		# create request body
		conn.request("GET", "/api/1/search/station?query=" + query, None, self.headers)

		response = conn.getresponse()
		json_data = response.read()

		if self.debug:
			self.logger.debug("station query results: " + json_data)

		# decode json data
		return json.loads(json_data)
		
	# vote(song_id, up)
	# =================
	# Up or downvotes the specified song
	# * up: True for upvote, False for downvote
	def vote(self, song_id, up):
		# create connection
		conn = self.connect()

		# create request body
		direction = "up" if up else "down"
		url = "/api/1/station/{0}/song/{1}/vote/{2}".format(self.station_id, song_id, direction)

		if self.debug:
			self.logger.debug("{0}voted: {1}".format(direction, url))

		conn.request("POST", url, None, self.headers)

		response = conn.getresponse()
