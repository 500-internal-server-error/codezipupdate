#!/usr/bin/env python

import argparse
from enum import IntEnum
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

class ExitStatus(IntEnum):
	OK = 0
	MISSING_UTIL = 1
	BAD_ARGS = 2
	BAD_UPDATE_CHECK = 3
	NO_UPDATES = 0
	BUSY_VSCODE = 4
	UPDATE_REFUSED = 5
	DOWNLOAD_FAILED = 6
	DOWNLOAD_CORRUPTED = 7

INSTALL_DIR = Path(str(shutil.which("Code.exe"))).parent
UPDATE_CHECK_DIR = Path(str(os.getenv("HOME"))) / "tmp-vsc-upd"
UPDATE_CHECK_RESULT_FILE = UPDATE_CHECK_DIR / "tmp-vsc-upd-checkres"

def psef_code():
	"""
	Cross-platform `ps -ef | grep -E '[Cc]ode(.exe)?'`
	"""

	# These checks catch themselves if run with `python -c`...
	# Which makes sense but was An Adventure to figure out
	# Also comes with non UTF-8 stuff apparently so do memcmp instead of strcmp

	if sys.platform == "win32":
		try:
			# If ps exists on Windows it's probably Cygwin `ps`, probably has
			# `ps -efW`

			return b"Code.exe" in subprocess.run(
				["ps", "-efW"],
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			).stdout
		except FileNotFoundError:
			# Vanilla Windows, needs tasklist

			return b"Code.exe" in subprocess.run(
				["tasklist"],
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			).stdout
	else:
		if Path("/proc/cygdrive").exists():
			# Unless there's some weird tomfoolery going on it's very probably
			# Cygwin, very probably has `ps -efW`

			return b"Code.exe" in subprocess.run(
				["ps", "-efW"],
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			).stdout
		else:
			# Real Unix, definitely has `ps -ef`

			return b"code" in subprocess.run(
				["ps", "-ef"],
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			).stdout

def main() -> ExitStatus:
	parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)

	# Some arguments cannot have kwargs assigned it seems but they're here
	# anyway for consistency

	# --help manually declared here for explicitness
	parser.add_argument(
		"-h",
		"--help",
		# metavar=None
		# nargs=0,
		# required=False,
		# default=None,
		dest="print_help",
		action="help",
		help="Print this help"
	)
	parser.add_argument(
		"-g",
		"--debug",
		# metavar=None,
		# nargs=0,
		required=False,
		default=None,
		dest="debug",
		action="store_true",
		help="Print additional debug information and disables cleanup code"
	)

	# Handle args parsing manually for consistent exit code
	args = None
	try:
		args = parser.parse_args()
	except argparse.ArgumentError as e:
		print(e)
		parser.print_help()
		return ExitStatus.BAD_ARGS

	local_vscode_build_info = (
		subprocess
			.run(
				# We specifically want `code.cmd` the launcher, not `Code.exe`
				# the main binary. By default, `$PATHEXT` places `.EXE` before
				# `.CMD`, even with `vscode/bin/code.cmd` before
				# `vscode/Code.exe` in `$PATH`. On Unix, the launcher and the
				# main binary have the same name, so it's probably up to the
				# order of `$PATH`.
				["code.cmd" if sys.platform == "win32" else "code", "--version"],
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			.stdout
			.decode("utf-8")
			.splitlines()
	)
	local_vscode_version_name = local_vscode_build_info[0]
	local_vscode_version_hash = local_vscode_build_info[1]

	print("Checking for updates...")

	# Prepare temporary directory to grab and store update check result in

	UPDATE_CHECK_DIR.mkdir(parents=True, exist_ok=True)

	# Check for updates

	with (
		urllib.request.urlopen(f"https://update.code.visualstudio.com/api/update/win32-x64-archive/stable/{local_vscode_version_hash}") as conn,
		open(UPDATE_CHECK_RESULT_FILE, "wb") as f
	):
		f.write(conn.read())

	if UPDATE_CHECK_RESULT_FILE.stat().st_size == 0:
		print("No updates found.")

		if not args.debug:
			# Unfortunately there is no Path#rmtree()
			# https://github.com/python/cpython/issues/92771
			shutil.rmtree(UPDATE_CHECK_DIR)

		return ExitStatus.NO_UPDATES

	upstream_vscode_version_name = None
	upstream_vscode_version_hash = None
	with open(UPDATE_CHECK_RESULT_FILE, "rb") as f:
		update_check_result = json.load(f)
		upstream_vscode_version_name = update_check_result["version"]
		upstream_vscode_version_hash = update_check_result["hash"]

	print(f"Local version: {local_vscode_version_name} ({local_vscode_version_hash})")
	print(f"Upstream version: {upstream_vscode_version_name} ({upstream_vscode_version_hash})")

	if psef_code():
		# This is only a problem on Windows but forcing everyone to deal with
		# it makes the code simpler, Unix users need to restart anyway even if
		# they can update without closing
		print("Close VSCode before updating.")
		return ExitStatus.BUSY_VSCODE

	# No easy builtin way to replicate `read -rn1` from Bash other than
	# than manually using termios... Windows could cheat by calling the CRT
	# `getch()` but Unix is alone
	# Sadly use `input()` for cross-platform simplicity

	action = "n"
	try:
		action = input("Replace local version with upstream version? (y/N) ")
	except (EOFError, KeyboardInterrupt):
		print("")

	if action.lower() != "y":
		print("Aborting.")
		return ExitStatus.UPDATE_REFUSED

	update_check_result = None
	with open(UPDATE_CHECK_RESULT_FILE, "rb") as f:
		update_check_result = json.load(f)

	# Download update

	# Ye olde shellscript version used `curl` which gets us a progress thingy
	# for free, but it's not a thing here with only stdlib `urlopen()`...

	print("Downloading new version...")

	src = update_check_result["url"]
	out = UPDATE_CHECK_DIR / f"VSCode-win32-x64-{upstream_vscode_version_name}.zip"
	try:
		with urllib.request.urlopen(src) as conn, open(out, "wb") as f:
			f.write(conn.read())
	except Exception:
		print("Download failed, aborting.")
		return ExitStatus.DOWNLOAD_FAILED

	print("Finished downloading.")

	# Ensure hashes match

	print("Checking file integrity...")

	upstream_sum = update_check_result["sha256hash"]
	actual_sum = None
	with open(out, "rb") as f:
		actual_sum = hashlib.file_digest(f, "sha256").hexdigest()

	if upstream_sum == actual_sum:
		print("File OK.")
	else:
		print("File may be corrupted:")
		print(f"  Expected: {upstream_sum}")
		print(f"  Received: {actual_sum}")
		print("Aborting.")

		if not args.debug:
			# Unfortunately there is no Path#rmtree()
			# https://github.com/python/cpython/issues/92771
			shutil.rmtree(UPDATE_CHECK_DIR)

	# Replace files

	print("Extracting files...")
	with zipfile.ZipFile(out) as zip:
		zip.extractall(INSTALL_DIR)
	print("Finished extracting.")
	print("")

	if not args.debug:
		# Unfortunately there is no Path#rmtree()
		# https://github.com/python/cpython/issues/92771
		shutil.rmtree(UPDATE_CHECK_DIR)

	print("Finished updating.")

	return ExitStatus.OK

if __name__ == "__main__":
	sys.exit(main())
