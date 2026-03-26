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

Run [`build.sh`][buildsh] and it will produce a `czu.tar.zst` tarball that can be extracted directly (e.g., `tar -xf czu.tar.zst -C /opt`) or to a standard location (e.g., `tar -xf czu.tar.zst --strip-components=1 -C /usr/local`). There are no dependencies other than the Python standard library. [Certified Works on My Machine][womm] on Python 3.14.3.

[buildsh]: ./build.sh
[womm]: https://blog.codinghorror.com/the-works-on-my-machine-certification-program/

## Usage

Simply run `czu` and it will prompt you to update if there is one:

```
$ czu
Checking for updates...
Local version: a.bc (abcdef)
Upstream version: x.yz (fedcba)
Replace local version with upstream version? (y/N) y
Downloading new version...
  % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                 Dload  Upload  Total   Spent   Left   Speed
100 100.1M 100 100.1M   0      0 10.10M      0   00:10   00:10         10.10M
Finished downloading.
Checking file integrity...
File OK.
Extracting files...
Finished extracting.
Replacing files...
Finished replacing files.

Finished updating.
```

Otherwise it will inform you of the lack of updates:

```
$ czu
Checking for updates...
No updates found.
```

It will also remind you to close VSCode before updating (though this is mostly a problem on Windows):

```
$ czu
Checking for updates...
Local version: a.bc (abcdef)
Upstream version: x.yz (fedcba)
Close VSCode before updating.
```

As well as if downloading failed:

```
Downloading new version...
  % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                 Dload  Upload  Total   Spent   Left   Speed
 10 100.1M  10  10.1M   0      0 10.10M      0   00:01   00:01         10.10M
Download failed, aborting.
```

Or the downloaded file doesn't look right:

```
Downloading new version...
  % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                 Dload  Upload  Total   Spent   Left   Speed
100 100.1M 100 100.1M   0      0 10.10M      0   00:10   00:10         10.10M
Finished downloading.
Checking file integrity...
File may be corrupted:
  Expected: fedcba
  Received: 654321
Aborting.
```
