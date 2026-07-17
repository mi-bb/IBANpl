# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

IBANpl — a small GTK+ 3 desktop app (Python 3) that validates Polish IBAN account numbers and looks up
the corresponding bank/branch details (name, address, BIC, etc.) from a local SQLite database sourced from
the National Bank of Poland (NBP). UI text and error messages are in Polish.

## Running

```sh
./iban        # wrapper script: cd's to repo dir, runs `python3 -O iban.py`
# or directly:
python3 iban.py
```

Requires Python 3, GTK+ 3 with PyGObject (`gi` module, `Gtk 3.0`), and SQLite 3 (stdlib `sqlite3`). There
is no requirements.txt, setup.py, build step, test suite, or linter configured in this repo.

## Architecture

Two files, cleanly separated:

- **`ibanpl.py`** — all logic, no GTK dependency. Three responsibilities:
  - `chk_iban(num)` — IBAN checksum validation (mod-97) for Polish account numbers. Strips spaces/dashes,
    prepends `PL`, validates length (28 chars incl. country code), reformats into grouped display form.
  - SQLite access layer: `b_dbop()` opens/creates `bn_base.db` and its schema (`bank`, `jorg`,
    `date_mod` tables) if missing. All queries flow through `sql_command_exec` (single row/write) or
    `sql_upd_many` (bulk insert), which wrap connect/execute/commit/rollback/close and return a
    `(success: bool, result_or_error)` tuple — every DB-facing function in the file follows this
    `(ok, data)` return convention instead of raising.
  - Bank list import: `bank_list_update()` reads `plewibnra.txt` (NBP's fixed-format export, `cp852`
    encoding) and rebuilds the `bank`/`jorg`/`date_mod` tables via `bank_base_update()`.
- **`iban.py`** — GTK UI (`AppWindow`) that wires the above into two dropdowns (bank number / branch
  number) or a free-text IBAN entry field, displaying bank/branch info in a details grid. Entry text
  changes trigger live IBAN validation and colored feedback (green/red Pango markup).

### Data model

- `bank` table: id (4-digit bank number) → name, trade name.
- `jorg` table: id (4-digit bank number) + oid (4-digit branch number) → full branch details (address,
  phone, BIC, BIC SEPA, web, affiliation/`union_n`, `parent_no`).
- `date_mod` table: single row tracking the date the local bank list was last refreshed, used by
  `chk_avail_update()` to decide whether an update prompt should be shown.
- An IBAN's first 4 digits after `PL` + 2 check digits identify the bank; the next 4 identify the branch —
  `sql_get_bank_info_frmt(num)` splits on this to join both tables.

### Updating the bank database

The NBP publishes `plewibnra.txt` at https://ewib.nbp.pl/ (under *Dane do pobrania*). Per the README, this
file must be manually downloaded and copied into the repo root, then imported via the "Uaktualnij Bazę"
button in the UI (calls `bank_list_update()`). There is no automated download — `plewibnra.txt` is read
from the local filesystem only, opened with `cp852` encoding (matches the source export's charset).

## License

GPLv3 (see `COPYING`). Copyright headers in source files should be preserved.
