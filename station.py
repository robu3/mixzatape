import httplib, urllib, urllib2, argparse, json, os, threading, time

# Station
# =======
# A representation of a Songza station(s); wraps the web API calls, and plays tracks using
# the specified player (VLC only at the moment)
class Station:
	# constructor
	def __init__(self, station_id, player):
		# set station_id
		if station_id is not None and len(station_id) > 0:
			self.station_id = station_id
		else:
			# we need a random station id
			self.station_id = 1393494

		# set the player for this station
		if player is None:
			raise Error("A player must be specified when creating a new station")
		else:
			self.player = player

		# current_track
		# =============
		# Dictionary of data for the current track
		self.current_track = ""

		# previous_track
		# =============
		# Dictionary of data for the previous track
		self.previous_track = ""

		# track_start
		# ===========
		# Time the current track started
		self.track_start = 0

		# flip
		# Keeps track which side of the tape we're on :D
		# Seriously though, we use this to alternate files when streaming data.
		self.flip = True

		# turn debugging on
		self.debug = False
		

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
		
	# next()
	# ======
	# Get the next track information from the server,
	# and decode the JSON response.
	def next(self):
		# create connection
		conn = self.connect()

		# create post body
		# fake the user agent so we're not rejected
		headers = {
			"Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
			"Accept": "application/json, text/javascript, */*; q=0.01",
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36"
		}
		params = urllib.urlencode({"cover_size": "m", "format": "aac", "buffer": 0 })
		conn.request("POST", self.get_station_path() + "/next", params, headers)

		response = conn.getresponse()
		json_data = response.read()

		if self.debug:
			print "next track data: " + json_data

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
			print "next track: " + track_data["listen_url"]

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
	def query_station(query):
		# TODO: here
		# create connection
		conn = self.connect()

		# create post body
		# fake the user agent so we're not rejected
		headers = {
			"Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
			"Accept": "application/json, text/javascript, */*; q=0.01",
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36"
		}
		params = urllib.urlencode({"cover_size": "m", "format": "aac", "buffer": 0 })
		conn.request("GET", "/api/1/search?query=" + query, headers)

		response = conn.getresponse()
		json_data = response.read()

		if self.debug:
			print "station query results: " + json_data

		# decode json data
		return json.loads(json_data)
		
