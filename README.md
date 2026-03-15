# VSCode-Portable Updater

VSCode's [Portable][pm1] [Mode][pm2] [doesn't][nu1] [support][nu2] [auto-updates][nu3] on Windows and Linux, unlike its normal installer-based versions.

> Portable mode is supported on the ZIP download for Windows, and the TAR.GZ download for Linux, as well as the regular Application download for macOS.

> Portable mode is only supported on the Windows ZIP (`.zip`) archive. Note also that the Windows ZIP archive does not support auto update.

This tool helps update your VSCode-Portable install. Works best with VSCode's own auto-updates disabled (just the VSCode updater, extensions can still be allowed to auto-update).

[pm1]: https://github.com/microsoft/vscode-docs/blob/d18aa1b37e54c83fe12b15d1b9213ab410972b71/docs/editor/portable.md?plain=1#L8
[pm2]: https://github.com/microsoft/vscode-docs/blob/d18aa1b37e54c83fe12b15d1b9213ab410972b71/docs/editor/portable.md?plain=1#L116
[nu1]: https://github.com/microsoft/vscode-docs/blob/d18aa1b37e54c83fe12b15d1b9213ab410972b71/docs/editor/portable.md?plain=1#L12
[nu2]: https://github.com/microsoft/vscode-docs/blob/d18aa1b37e54c83fe12b15d1b9213ab410972b71/docs/editor/portable.md?plain=1#L15
[nu3]: https://github.com/microsoft/vscode-docs/blob/d18aa1b37e54c83fe12b15d1b9213ab410972b71/docs/editor/portable.md?plain=1#L73

## Installation

Simply [`cp src/codezipupdate.py /usr/local/bin/codezipupdate`][src] or wherever is customary for the system you're using. There are no dependencies other than the Python standard library. [Certified Works on My Machine][womm] on Python 3.12.10.

[src]: ./src/codezipupdate.py
[womm]: https://blog.codinghorror.com/the-works-on-my-machine-certification-program/

## Usage

Simply run `codezipupdate` and it will prompt you to update if there is one:

```
$ codezipupdate
Checking for updates...
Local version: a.bc (abcdef)
Upstream version: x.yz (fedcba)
Replace local version with upstream version? (y/N) y
Downloading new version...
Finished downloading.
Checking file integrity...
File OK.
Extracting files...
Finished extracting.
Finished updating.
```

Otherwise it will inform you of the lack of updates:

```
$ codezipupdate
Checking for updates...
No updates found.
```

It will also remind you to close VSCode before updating (though this is mostly a problem on Windows):

```
$ codezipupdate
Checking for updates...
Local version: a.bc (abcdef)
Upstream version: x.yz (fedcba)
Close VSCode before updating.
```

As well as if downloading failed:

```
Downloading new version...
Download failed, aborting.
```

Or the downloaded file doesn't look right:

```
Downloading new version...
Finished downloading.
Checking file integrity...
File may be corrupted:
  Expected: fedcba
  Received: 654321
Aborting.
```
