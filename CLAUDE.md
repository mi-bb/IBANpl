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

Must be run from the repo root — the DB path `bn_base.db` is relative. Requires Python 3, GTK+ 3 with
PyGObject (`gi` module, `Gtk 3.0`), and SQLite 3 (stdlib `sqlite3`). There is no requirements.txt,
setup.py, build step, or linter configured in this repo.

## Testing

```sh
python3 -m unittest discover tests     # all tests
python3 -m unittest tests.test_ibanpl  # single module
```

Tests are headless — no GTK/`gi` needed. DB tests use real SQLite DBs in `tempfile`s and a
`_FailingCursorProxy` pattern to simulate mid-transaction errors; prefer that over mocking the DB
layer when testing atomicity/rollback. Patch targets are `ibanpl.*`.

## Architecture

Two files, cleanly separated:

- **`ibanpl.py`** — all logic, no GTK dependency. It mirrors pyfaktury's `fk/banknum.py` — keep the
  two in sync when either changes. `run_sql_command()` and `get_url_response()` are inlined copies of
  pyfaktury's `fk/sql_common.py` / `fk/sfun.py` (this repo has no package layout). Three responsibilities:
  - `chk_iban(num)` — IBAN checksum validation (mod-97) for Polish account numbers. Strips spaces/dashes,
    prepends `PL`, validates length (28 chars incl. country code), reformats into grouped display form.
    Returns `(ok, message, formatted_number)`.
  - SQLite access layer: `b_dbop()` opens/creates `bn_base.db` and its schema (`bank`, `jorg`,
    `date_mod` tables) if missing. All queries flow through `sql_command_exec`, which delegates to
    `run_sql_command` (connect/execute/commit/rollback/close). DB-facing functions never raise: reads
    return `tuple[list, str | None]` — (rows, error message or `None`); writes return `str | None` —
    (error message or `None`).
  - Bank list import from NBP (see below).
- **`iban.py`** — GTK UI (`AppWindow`) that wires the above into two dropdowns (bank number / branch
  number) or a free-text IBAN entry field, displaying bank/branch info in a details grid. Entry text
  changes trigger live IBAN validation and colored feedback (green/red Pango markup).
- `sql_get_all_bank_no()` / `sql_get_all_jorg(bid)` exist only here (the UI's comboboxes need them);
  pyfaktury's banknum has no equivalents.

### Data model

- `bank` table: id (4-digit bank number) → name, trade name.
- `jorg` table — column names are **inverted from intuition**: `id` = 4-digit **branch** number,
  `oid` = 4-digit **bank** number (see `bank_j_iterator`). Full branch details (address, phone, BIC,
  BIC SEPA, web, affiliation/`union_n`, `parent_no`).
- `date_mod` table: single row tracking the date the local bank list was last refreshed, used by
  `chk_avail_update()`.
- An IBAN's first 4 digits after `PL` + 2 check digits identify the bank; the next 4 identify the branch —
  `sql_get_bank_info_frmt(num)` splits on this to join both tables.
- `bn_base.db` is committed to git as a pre-seeded DB; running the app or an update modifies it locally.

### Updating the bank database

`bank_list_update()` downloads directly from `UPD_URL`
(`https://ewib.nbp.pl/plewibnra?dokNazwa=plewibnra.txt`), decodes as `cp852`, tab-separated — no local
`plewibnra.txt` file is involved. `bank_base_update()` validates content first (`validate_bank_data()`
rejects malformed/incomplete data, min `MIN_BANK_RECORDS` = 100 records, so a bad download can't wipe the
DB), then rebuilds `jorg`, `bank`, and `date_mod` in one atomic transaction — a failure mid-way rolls
back and leaves existing data untouched. `chk_avail_update()` first probes the NBP server for
reachability, then returns `(True, question message for the user)` — it always proposes an update (asks
"again?" if one already ran today) or `(False, error message)` when the server is unreachable. The
"Uaktualnij Bazę" button in the UI drives this flow.

## License

GPLv3 (see `COPYING`). Copyright headers in source files should be preserved.
