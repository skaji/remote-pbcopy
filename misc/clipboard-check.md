# Clipboard check notes

These are working notes and a manual test helper, rather than a complete test
suite. Run the same checks again when changing OSC 52 handling or upgrading a
terminal/multiplexer.

## Running the checks

On a Mac with Python 3.8+, Perl, Go, tmux, and GNU screen installed, open a normal
local tab in each terminal. Start outside tmux, screen, or Herdr TUI. From the
repository directory, run one command in each app, **one app at a time**:

```sh
# In iTerm2:
python3 misc/check-clipboard.py iTerm2

# In Rex (a This Mac session):
python3 misc/check-clipboard.py Rex

# In Ghostty:
python3 misc/check-clipboard.py Ghostty

# In Herdr App (a This computer space):
python3 misc/check-clipboard.py HerdrApp
```

Keep that app and tab in front until the command prints the summary and returns
to the prompt. iTerm2 needs **Settings → General → Selection → Applications in
terminal may access clipboard** enabled.

If tmux is not on PATH, specify its executable:

```sh
TMUX_BIN=/opt/homebrew/opt/tmux/bin/tmux python3 misc/check-clipboard.py Rex
```

`SCREEN_BIN` can override `/usr/bin/screen` as well. The script builds the current
Go implementation into a temporary directory, and runs the current Perl and
Python scripts from this checkout.

The script temporarily changes the clipboard and restores its original **text**
in a `finally` block. It does not preserve images or other clipboard formats.
Avoid copying anything else during the check.

## What it checks

For each terminal, the script runs the three implementations with short and long
Japanese text in these environments:

* A plain terminal tab.
* An isolated tmux server with an empty config.
* Another isolated tmux server with `set -g allow-passthrough on`.
* An isolated GNU screen session with its startup message disabled.

It also writes raw OSC 52 sequences with an empty selection and with `c` in the
plain tab. Input has a trailing newline; the expected clipboard text accounts
for `pbcopy` removing it.

Temporary configs, the Go binary, and JSON results are kept under the printed
`/tmp/pbcopy-check-*` directory. `results.json` contains the terminal label and
each PASS/FAIL result. The script stops only its own tmux/screen sessions. It
does not edit the user's multiplexer config or attach to existing sessions.

`FAIL` is expected for tmux's initial configuration. The script prints results
without treating these expected failures as a failed test-suite exit status.
The terminal label is just a label; it does not launch or detect the named app.

## Results from 2026-10-31

On macOS, with tmux 3.8, the bundled GNU screen 4.00.03, and Herdr TUI 0.9.5,
all three implementations produced the same results. Herdr App was version
0.1.10 with Herdr Core 0.1.15. Herdr App and Herdr TUI are separate programs:
the former is an outer terminal app here, the latter an inner multiplexer.

| Environment | iTerm2 | Rex Beta | Ghostty | Herdr App |
| --- | --- | --- | --- | --- |
| Plain tab | PASS | PASS | PASS | PASS |
| tmux, empty config | FAIL | FAIL | FAIL | FAIL |
| tmux, `allow-passthrough on` | PASS | PASS | PASS | PASS |
| GNU screen | PASS | PASS | PASS | PASS |
| Herdr TUI | PASS | PASS | PASS | Not tested |

Both `OSC 52 ;; ...` and `OSC 52 ;c; ...` worked in all four outer terminals.
The code uses `c` to explicitly select the clipboard; it was not required to
make Rex or Ghostty work.

Herdr TUI needed no additional clipboard configuration in those separate manual
checks. The helper above currently automates only the plain, tmux, and screen
rows. The Herdr App → Herdr TUI combination was intentionally not tested.

## Lessons from the investigation

* Check the clipboard **outside the multiplexer**. Initial checks using
  `pbpaste` inside screen/tmux reported failures in Rex even when the clipboard
  write worked. This script keeps a small Unix-socket clipboard service in the
  outer process; workers ask it to reset/read the clipboard.
* A byte-level test that captures stdout only proves that the escape sequence
  was generated. The sequence must reach a real terminal to test clipboard
  behavior. A PTY attached only to a shell-command tool is not enough.
* In Rex, use a tab created by the app's Command+T. Initial checks in a tab
  created with `rex run` did not update the clipboard in our setup. Starting
  from a normal app-created tab avoided that difference.
* `tmux -CC` is a separate iTerm2 integration path. It is handled by `pbcopy`,
  but is not exercised by this helper.
