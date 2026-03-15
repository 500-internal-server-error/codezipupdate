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

from czu_platform import get_platform
from czu_util import read_n1_p, psef_code

class ExitStatus(IntEnum):
	OK = 0
	UNSUPPORTED_PLATFORM = 1
	MISSING_UTIL = 2
	BAD_ARGS = 3
	BAD_UPDATE_CHECK = 4
	NO_UPDATES = 0
	BUSY_VSCODE = 5
	UPDATE_REFUSED = 6
	DOWNLOAD_FAILED = 7
	DOWNLOAD_CORRUPTED = 8
	UPDATED_FAILED = 9

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

	platform = get_platform()
	if platform is None:
		return ExitStatus.UNSUPPORTED_PLATFORM

	code_exe = None
	match platform:
		case "win32":
			code_exe = "code.cmd"
		# Technically Cygwin Python should find .cmd files since Cygwin is
		# still Windows, but it cannot
		case "cygwin" | "linux":
			code_exe = "code"

	code_exe_path = shutil.which(code_exe)
	if code_exe_path is None:
		print("Could not find VSCode! Is it in `$PATH`?", file=sys.stderr)
		return ExitStatus.MISSING_UTIL

	# Prepare temporary directory to grab and store update check result in

	update_check_base_dir = None

	# Manual ~ check to avoid throwing and also work in Cygwin + native Python

	if home := os.getenv("HOME"):
		update_check_base_dir = Path(home)
	elif userprofile := os.getenv("USERPROFILE"):
		update_check_base_dir = Path(userprofile)

	if update_check_base_dir is None:
		print("Your house is gone!", file=sys.stderr)
		return ExitStatus.UNSUPPORTED_PLATFORM

	update_check_dir = update_check_base_dir / "tmp-vsc-upd"
	update_check_result_file = update_check_dir / "tmp-vsc-upd-checkres"

	update_check_dir.mkdir(parents=True, exist_ok=True)

	install_dir = Path(code_exe_path).parent.parent
	install_dir_tmp = update_check_dir / "tmp-install"
	install_dir_tmp.mkdir(parents=True, exist_ok=True)

	local_vscode_build_info = (
		subprocess
			.run(
				[code_exe, "--version"],
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

	# Check for updates

	update_check_platform_url = None
	match platform:
		case "win32" | "cygwin":
			update_check_platform_url = "win32-x64-archive"
		case "linux":
			update_check_platform_url = "linux-x64"

	try:
		if subprocess.run(
			[
				"curl",
				"-s",
				"-o",
				update_check_result_file,
				f"https://update.code.visualstudio.com/api/update/{update_check_platform_url}/stable/{local_vscode_version_hash}"
			]
		).returncode != 0:
			print("Failed to check for updates", file=sys.stderr)

			if not args.debug:
				shutil.rmtree(update_check_dir)

			return ExitStatus.BAD_UPDATE_CHECK
	except FileNotFoundError:
		print("Required `curl` but not found", file=sys.stderr)

		if not args.debug:
			shutil.rmtree(update_check_dir)

		return ExitStatus.MISSING_UTIL

	if update_check_result_file.stat().st_size == 0:
		print("No updates found.")

		if not args.debug:
			shutil.rmtree(update_check_dir)

		return ExitStatus.NO_UPDATES

	upstream_vscode_version_name = None
	upstream_vscode_version_hash = None
	with open(update_check_result_file, "rb") as f:
		update_check_result = json.load(f)
		upstream_vscode_version_name = update_check_result["name"]
		upstream_vscode_version_hash = update_check_result["version"]

	print(f"Local version: {local_vscode_version_name} ({local_vscode_version_hash})")
	print(f"Upstream version: {upstream_vscode_version_name} ({upstream_vscode_version_hash})")

	if psef_code(platform):
		# This is only a problem on Windows but forcing everyone to deal with
		# it makes the code simpler, Unix users need to restart anyway even if
		# they can update without closing
		print("Close VSCode before updating.")

		if not args.debug:
			shutil.rmtree(update_check_dir)

		return ExitStatus.BUSY_VSCODE

	if read_n1_p(
		"Replace local version with upstream version? (y/N) ",
		platform
	).lower() != "y":
		print("Aborting.")

		if not args.debug:
			shutil.rmtree(update_check_dir)

		return ExitStatus.UPDATE_REFUSED

	update_check_result = None
	with open(update_check_result_file, "rb") as f:
		update_check_result = json.load(f)

	# Download update

	print("Downloading new version...")

	src = update_check_result["url"]
	out = update_check_dir / src.rsplit("/", 1)[-1]
	try:
		if subprocess.run(["curl", "-o", out, src]).returncode != 0:
			print("Download failed, aborting.", file=sys.stderr)

			if not args.debug:
				shutil.rmtree(update_check_dir)

			return ExitStatus.DOWNLOAD_FAILED
	except KeyboardInterrupt:
		print("Download cancelled, aborting.", file=sys.stderr)

		if not args.debug:
			shutil.rmtree(update_check_dir)

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
			shutil.rmtree(update_check_dir)

	# Replace files

	print("Extracting files...")

	extractor = None
	match platform:
		case "win32" | "cygwin":
			# %SYSTEMROOT% should always exist but fallback here for static
			# analysis
			systemroot = Path(os.getenv("SYSTEMROOT") or "C:/Windows")

			# bsdtar can extract zip files just fine and has been around since
			# Win10 17063 (2017)
			extractor = systemroot / "System32" / "tar.exe"
		case "linux":
			# any tar can extract tar files
			extractor = Path("tar")

	if subprocess.run([extractor, "-xf", out, "-C", install_dir_tmp]).returncode != 0:
		print("Failed to extract", file=sys.stderr)

		if not args.debug:
			shutil.rmtree(update_check_dir)

		return ExitStatus.DOWNLOAD_CORRUPTED

	print("Finished extracting.")

	print("Replacing files...")

	backup_dir = install_dir.with_name(install_dir.name + ".old")
	try:
		os.replace(install_dir, backup_dir)

		match platform:
			case "win32" | "cygwin":
				os.replace(install_dir_tmp, install_dir)
			case "linux":
				os.replace(install_dir_tmp / "VSCode-linux-x64", install_dir)

		# check for Portable Mode data
		# https://code.visualstudio.com/docs/editor/portable

		old_portable_data_dir = backup_dir / "data"
		new_portable_data_dir = install_dir / "data"

		if old_portable_data_dir.exists():
			os.replace(old_portable_data_dir, new_portable_data_dir)
	except OSError:
		print("Failed to replace files", file=sys.stderr)

		if not args.debug:
			shutil.rmtree(update_check_dir)

		return ExitStatus.UPDATED_FAILED

	print("Finished replacing files.")

	print("")

	if not args.debug:
		# Unfortunately there is no Path#rmtree()
		# https://github.com/python/cpython/issues/92771
		shutil.rmtree(update_check_dir)
		shutil.rmtree(backup_dir)

	print("Finished updating.")

	return ExitStatus.OK

if __name__ == "__main__":
	sys.exit(main())
