import subprocess
import sys

from czu_platform import Platform

def read_n1_p(prompt: str, platform: Platform) -> str:
	"""
	Cross-platform `read -N1 -p`
	"""

	key = None
	print(prompt, end="", flush=True)
	match platform:
		case "win32":
			# _Technically_ conio.h/getch is deprecated, but it's there and the
			# alternative is to do the equivalent of the Unix termios dance but
			# with the Console API.

			import msvcrt

			print(key := msvcrt.getch().decode("utf-8", "ignore"))
		case "cygwin" | "linux":
			# No CRT / OS API, implement manually using termios

			import termios
			import tty

			attr = termios.tcgetattr(sys.stdin)
			try:
				tty.setraw(sys.stdin)
				key = sys.stdin.read(1)
			finally:
				termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attr)
				print(key)

	return key

def psef_code(platform: Platform):
	"""
	Cross-platform `ps -ef | grep -Eq '[Cc]ode(.exe)?'`
	"""

	# These checks catch themselves if run with `python -c`...
	# Which makes sense but was An Adventure to figure out
	# Also comes with non UTF-8 stuff apparently so do memcmp instead of strcmp

	match platform:
		case "win32" | "cygwin":
			return b"Code.exe" in subprocess.run(
				["tasklist"],
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			).stdout
		case "linux":
			return b"code" in subprocess.run(
				["ps", "-ef"],
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			).stdout
