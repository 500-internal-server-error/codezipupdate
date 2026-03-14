import sys
from typing import Literal

Platform = Literal["win32", "cygwin", "linux"]
MaybeNonePlatform = Platform | None

def get_platform() -> MaybeNonePlatform:
	"""
	Custom platform narrowing to allow exhaustive matching on `sys.platform`
	"""

	match sys.platform:
		case "win32" | "cygwin" | "linux":
			return sys.platform
		case _:
			# Portable distributions only available for Windows and Linux
			return None
