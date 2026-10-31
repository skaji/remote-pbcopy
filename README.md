# remote-pbcopy

`pbcopy` is a well-known macOS tool that copies data to the clipboard.
It's very useful, but it only works with the clipboard on your local machine.

Fortunately, with the OSC 52 escape sequence,
we can access the local machine's clipboard from a remote machine.

I prepared a simple tool that works like `pbcopy` for remote machines.
It works with [iTerm2](https://iterm2.com/), [Ghostty](https://ghostty.org/), and
[Rex](https://www.superlogical.com/rex/docs/installation), including sessions inside
[tmux](https://github.com/tmux/tmux/wiki), [GNU screen](https://www.gnu.org/software/screen/),
and [herdr](https://herdr.dev/).

## Install

1. Use iTerm2, Ghostty, or Rex.
2. Copy a preferred `pbcopy` to a directory where `$PATH` is set.

    ```
    [local]  $ ssh remote

    # If you prefer a self-contained binary, then
    [remote] $ curl -fsSLo pbcopy-linux-amd64.tar.gz https://github.com/skaji/remote-pbcopy/releases/latest/download/pbcopy-linux-amd64.tar.gz
    [remote] $ tar xf pbcopy-linux-amd64.tar.gz
    [remote] $ mv pbcopy /path/to/bin/

    # If you prefer a perl script, then
    [remote] $ curl -fsSLo pbcopy https://raw.githubusercontent.com/skaji/remote-pbcopy/main/pbcopy
    [remote] $ chmod +x pbcopy
    [remote] $ mv pbcopy /path/to/bin/

    # If you prefer a python script, then
    [remote] $ curl -fsSLo pbcopy https://raw.githubusercontent.com/skaji/remote-pbcopy/main/pbcopy.py
    [remote] $ chmod +x pbcopy
    [remote] $ mv pbcopy /path/to/bin/
    ```

### Notes

iTerm2 and tmux require additional configuration:

* **iTerm2:** Enable **Settings → General → Selection → Applications in terminal
  may access clipboard**.

  ![iTerm2 clipboard settings](misc/preferences.png)

* **tmux:** Add the following to `~/.tmux.conf`:

  ```tmux
  set -g allow-passthrough on
  ```

## Usage

Just like the normal `pbcopy`:

```
[local]  $ ssh remote
[remote] $ date | pbcopy
[remote] $ exit
[local]  $ pbpaste
Sun Jan 18 20:28:03 JST 2015
```

Input trailing newlines are removed before copying.

## How about `pbpaste`?

This tool writes to the clipboard; it does not implement `pbpaste`.
Use Command+V to paste text from the clipboard into the remote terminal.

If you want to save the content of clipboard to a remote file, try this:

```
[remote] cat > out.txt
# press command+V to paste content of clipboard,
# and press control+D which indicates EOF
```

## See also

For OSC52

* http://doda.b.sourceforge.jp/2011/12/15/tmux-set-clipboard/
* http://qiita.com/kefir_/items/1f635fe66b778932e278
* http://qiita.com/kefir_/items/515ed5264fce40dec522
* https://chromium.googlesource.com/apps/libapps/+/HEAD/hterm/etc/osc52.vim
* https://chromium.googlesource.com/apps/libapps/+/HEAD/hterm/etc/osc52.el
* https://chromium.googlesource.com/apps/libapps/+/HEAD/hterm/etc/osc52.sh

## Author

Shoichi Kaji

## License

MIT
