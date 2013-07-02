from player import VlcPlayer

player = VlcPlayer()
player.play("a-side.mp4")

i = 0

while True:
	print str(i) + ":\n"
	print player.send_command_readline("get_time\n")
	i += 1
