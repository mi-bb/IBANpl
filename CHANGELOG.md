# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* User interface internationalization (gettext): the language is selected
  automatically from the system settings (`LANGUAGE`/`LC_*`/`LANG`);
  an English translation was added in the `locale/en` directory.
  Polish texts remain the source language (msgid).
* Tests guarding the consistency of the translation catalog
  (`TranslationTests`) — they detect untranslated entries in the `.po`
  file and a stale compiled `.mo` file.

### Fixed

* Typos and punctuation errors in the interface messages (among others
  "numer kona" → "numer konta", missing commas, a space before the
  question mark, "Uaktualnij Bazę" → "Uaktualnij bazę").

## [1.1] - 2026-09-02

### Added

* Unit tests (`tests/test_ibanpl.py`, run with
  `python3 -m unittest discover tests`).
* Automatic bank list update — the _**Uaktualnij bazę**_ (Update Database)
  button now downloads the current data directly from the eWIB service of
  the National Bank of Poland (https://ewib.nbp.pl/). There is no longer
  a need to manually download the _plewibnra.txt_ file or copy it to the
  program directory.
* Update failures (e.g. no network connection) are now reported
  with a message.

### Changed

* The bank database update now runs in a single atomic transaction —
  a failed update does not destroy the existing data.
* The downloaded bank data is verified before saving (format and
  minimum record count checks) — a damaged or incomplete download
  cannot wipe the database.
* Code refresh aligned with the newer version from the pyfaktury
  project (`fk/banknum.py`).

## [1.0] - 2019-01-27

### Added

* First release.
