# AGENTS.md

GTK+ 3 desktop app (Python 3) that validates Polish IBAN account numbers and shows bank/branch details from a local SQLite DB. User-facing strings are gettext-based: **Polish is the source text (msgid)** — write new user-facing strings in Polish wrapped in `_()`. Other languages live in `locale/` (currently English); untranslated locales fall back to the Polish msgid. The language follows the system locale (`LANGUAGE`/`LC_*`/`LANG`). Bank/branch data from NBP stays Polish regardless of locale.

## Running

- `./iban` (wrapper: cd's to repo dir, runs `python3 -O iban.py`) or `python3 iban.py` from the repo root.
- Must run from the repo root: the DB path `bn_base.db` and the `locale/` translation dir are relative.
- Tests: `python3 -m unittest discover tests` (all) or `python3 -m unittest tests.test_ibanpl` (single module). Tests are headless — no GTK/`gi` needed.
- The UI requires a running X/Wayland session; verify UI changes by running the app.
- Dependencies: Python 3, GTK+ 3 with PyGObject (`gi`), SQLite 3 (stdlib). No linter/formatter/build config.

## Architecture (2 files)

- `ibanpl.py` — all logic, no GTK: `chk_iban()` (mod-97 checksum, prepends `PL`), the SQLite access layer, and the bank-list import from NBP. It mirrors pyfaktury's `fk/banknum.py` — keep the two in sync when either changes. **Exception:** the gettext setup and `_()`-wrapping of messages exist only here so far — pyfaktury is expected to get its own i18n later (this version is the reference); until then the files are not literally identical. `run_sql_command()` and `get_url_response()` are inlined copies of pyfaktury's `fk/sql_common.py` / `fk/sfun.py` (this repo has no package layout).
- `iban.py` — GTK UI (`AppWindow`), imports only from `ibanpl`. Keep the logic/UI split.
- `sql_get_all_bank_no()` / `sql_get_all_jorg(bid)` exist only here (the UI's comboboxes need them); pyfaktury's banknum has no equivalents.
- Bank/branch data is serialized through the `BankInfo` and `JorgInfo` dataclasses (mirrored in pyfaktury's `fk/banknum.py` — keep in sync): `from_row()`/`to_row()` convert between objects and DB rows, `JorgInfo.from_line()` parses a plewibnra.txt line, `JorgInfo.frmt_row()` renders the display values the UI shows. `bank_j_iterator`/`bank_b_iterator` yield the objects and `bank_base_update` writes them via `to_row()`; `sql_get_bank_info_frmt(num)` returns `(BankInfo | None, JorgInfo | None, error)`.

## Conventions that will bite you

- DB-facing functions never raise: reads return `tuple[list, str | None]` — (rows, error message or `None`); writes return `str | None` — (error message or `None`). Callers unpack `rows, error_info = ...` / `error_info = ...` and check for `None`.
- `b_dbop()` creates the schema (`bank`, `jorg`, `date_mod`) if missing; every DB operation opens and closes its own connection. `sql_command_exec` resolves `b_dbop` by name at call time, so `unittest.mock.patch("ibanpl.b_dbop", ...)` works — the tests rely on this.
- In the `jorg` table the columns are named opposite to intuition: `id` = 4-digit **branch** number, `oid` = 4-digit **bank** number (see `bank_j_iterator`). In `bank`, `id` = bank number.
- `sql_get_all_jorg(bid)` returns branch ids for a given bank (`where oid=?`).
- An IBAN's first 4 digits after `PL` + check digits identify the bank; the next 4 identify the branch — `sql_get_bank_info_frmt(num)` splits on this.

## Translations (i18n)

- Both files bind `_ = gettext.translation("ibanpl", localedir="locale", fallback=True).gettext` at import time — `fallback=True` means no matching catalog → Polish msgid.
- Catalog files: `locale/ibanpl.pot` (template), `locale/en/LC_MESSAGES/ibanpl.po` (English source) and the compiled `ibanpl.mo`. **Both `.po` and `.mo` are committed** (no build system, so `./iban` stays zero-step).
- After changing any `_()` string: regenerate the template and merge it into the `.po`, translate, recompile:
  ```
  xgettext --language=Python --keyword=_ --from-code=UTF-8 --package-name=IBANpl --package-version=2.0.0 -o locale/ibanpl.pot iban.py ibanpl.py
  msgmerge -U locale/en/LC_MESSAGES/ibanpl.po locale/ibanpl.pot
  msgfmt --check -o locale/en/LC_MESSAGES/ibanpl.mo locale/en/LC_MESSAGES/ibanpl.po
  ```
  `TranslationTests` in `tests/test_ibanpl.py` fails if the `.po` has untranslated entries or the `.mo` is stale relative to the `.po`.
- Keep URLs (e.g. `UPD_URL`) and other interpolations outside the `_()` strings (use `{0}`-style `format` placeholders inside them). Logger messages are not translated.

## Bank DB update flow

- `bank_list_update()` downloads directly from `UPD_URL` (`https://ewib.nbp.pl/plewibnra?dokNazwa=plewibnra.txt`) and decodes as `cp852`, tab-separated. No local `plewibnra.txt` file is involved — CLAUDE.md's "manual download" description is stale; trust the code.
- `bank_base_update()` validates content first (`validate_bank_data()` rejects malformed/incomplete data, min `MIN_BANK_RECORDS` = 100 records, so a bad download can't wipe the DB), then rebuilds `jorg`, `bank`, and `date_mod` in one atomic transaction — a failure mid-way rolls back and leaves existing data untouched.
- `chk_avail_update()` first probes the NBP server for reachability, then returns `(True, question message for the user)` — it always proposes an update (asks "again?" if one already ran today) or `(False, error message)` when the server is unreachable.
- `bn_base.db` is committed to git as a pre-seeded DB; running the app or an update modifies it locally.

## Testing conventions

`tests/test_ibanpl.py` mirrors pyfaktury's `tests/test_banknum.py` (patch targets are `ibanpl.*` here). DB tests use real SQLite DBs in `tempfile`s and a `_FailingCursorProxy` pattern to simulate mid-transaction errors — follow that instead of mocking the DB layer when testing atomicity/rollback. The module pins `os.environ["LANGUAGE"] = "pl"` **before** importing `ibanpl` (which loads its catalog at import time) so string assertions are locale-independent — keep that pin above the `ibanpl` import.

## Other

- GPLv3 (see `COPYING`) — preserve the copyright headers in both source files.
