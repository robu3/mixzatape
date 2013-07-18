import subprocess, os, sys, logging, re

# Many thanks to PyRadio (https://github.com/coderholic/pyradio)
# for the media playing code (borrowed & remixed here; gotta love open source)
# Wraps VLC player; assumes that "vlc" is in your path
class VlcPlayer:
	def __init__(self, debug=False):
		self.process = None

		# is_paused
		# =========
		# True if playback is currently paused
		self.is_paused = False

		self.time = 0

		self.debug = debug

		# regex used to parse VLC STDOUT for time remaining
		# sometimes we get extra prompt characters that need to be trimmed
		self.time_remaining_regex = r"[> ]*(\d*)\r\n"

		# setup logger
		# clear log on startup
		logpath = "./.player.log"
		if os.path.exists(logpath):
			os.remove(logpath)

		if self.debug:
			self.logger = logging.getLogger("player")
			handler = logging.FileHandler(logpath)
			formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
			handler.setFormatter(formatter)
			self.logger.addHandler(handler)
			self.logger.setLevel(logging.DEBUG)

	#def __del__(self):
		#self.process.close()

	# send_command(command)
	# =====================
	# Sends the specified command to the player
	def send_command(self, command):
		if self.process is not None:
			self.process.stdin.write(command.encode("utf-8"))

	# send_command_readline(command)
	# ==============================
	# Sends the specified command to the player, and returns on line of response from STDOUT
	def send_command_readline(self, command):
		if self.process is not None:
			self.process.stdin.write(command.encode("utf-8"))
		
			# make sure to forward to the end	
			return self.process.stdout.readline()

		return None

	# is_open()
	# =========
	# Returns true if the player is currently open.
	def is_open(self):
		return bool(self.process)	

	# volume_up()
	# ===========
	# Raises the volume.
	def volume_up(self):
		self.send_command_readline("volup\n")

	# volume_down()
	# ============
	# Lowers the volume.
	def volume_down(self):
		self.send_command_readline("voldown\n")

	# pause()
	# =======
	# Pauses playback.
	def pause(self):
		self.is_paused = not self.is_paused
		self.send_command("pause\n")

	# stop()
	# ======
	# Stops all playback, shutting down the player.
	def stop(self):
		self.send_command("shutdown\n")
		self.process = None

	# enqueue(file)
	# =============
	# Adds a file to queue.
	def enqueue(self, file):
		self.send_command("enqueue " + file + "\n")

	# skip()
	# ======
	# Skips the current track
	def skip(self):
		self.send_command("next\n")
		self.time = 0

	# seek(seconds)
	# =============
	# Skips the current track
	def seek(self, seconds):
		self.send_command("seek {0}\n".format(seconds))
		# update time value
		# self.time += seconds

	# get_time()
	# ==========
	# Gets the running time in for the current track.
	def get_time(self):
		try:
			# buffer the current time value
			self.time = int(self.send_command_readline("get_time\n")[2:])
		finally:
			# Sometimes when seeking, VLC is slow to respond, and the STDOUT output
			# gets out of sync. In this case, return the last know time value.
			return self.time
			

	# play(file)
	# ==========
	# Plays the file with the specified name.
	def play(self, file):
		# print "filename: " + file

		# if already playing, add the next file to the queue
		if self.is_open():
			# print "is open"
			self.enqueue(file)
		else:
			self.process = subprocess.Popen(["vlc", "-Irc", "--quiet", file],
											shell=False,
											stdout=subprocess.PIPE,
											stdin=subprocess.PIPE,
											stderr=subprocess.STDOUT)

			self.process.stdout.readline()
			self.process.stdout.readline()

	# time_remaining()
	# ================
	# The amount of time remaining on the current track.
	def time_remaining(self):
		default = -1

		if (self.is_open()):	
			try:
				
				# use regex to chop off leading chars
				# attempt to read duration of track
				response_text = self.send_command_readline("get_length\n")
				match_dur = re.search(self.time_remaining_regex, response_text)

				if match_dur:
					duration = int(match_dur.group(1))
				else:
					self.logger.debug("unable to parse time remaining text: {0}", response_text)

				# attempt to read current time elasped
				response_text = self.send_command_readline("get_time\n")
				match_rem = re.search(self.time_remaining_regex, response_text)

				if match_rem:
					remaining = int(match_rem.group(1))
				else:
					self.logger.debug("unable to parse time remaining text: {0}", response_text)

				#duration = int(self.send_command_readline("get_length\n")[2:])
				#remaining = int(self.send_command_readline("get_time\n")[2:])

				if match_dur and match_rem:
					return duration - remaining
				else:
					return default

			except Exception, ex:
				self.logger.error("error: " + str(ex))
				return default

		return default
