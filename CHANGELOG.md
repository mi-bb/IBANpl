# Changelog

Wszystkie istotne zmiany w tym projekcie będą dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
a projekt przestrzega [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1] - 2026-07-17

### Dodane

* Testy jednostkowe (`tests/test_ibanpl.py`, uruchamiane przez
  `python3 -m unittest discover tests`).
* Automatyczna aktualizacja listy banków — przycisk _**Uaktualnij bazę**_
  pobiera teraz aktualne dane bezpośrednio z serwisu eWIB Narodowego Banku
  Polskiego (https://ewib.nbp.pl/). Nie trzeba już ręcznie pobierać pliku
  _plewibnra.txt_ ani kopiować go do katalogu programu.
* Błąd aktualizacji (np. brak połączenia z siecią) jest zgłaszany
  komunikatem.

### Zmienione

* Aktualizacja bazy banków odbywa się teraz w jednej atomicznej transakcji —
  nieudana aktualizacja nie niszczy istniejących danych.
* Pobrane dane o bankach są weryfikowane przed zapisem (kontrola formatu
  i minimalnej liczby rekordów) — uszkodzone lub niekompletne pobranie
  nie może wyczyścić bazy.
* Uaktualnienie kodu zgodne z nowszą wersją z projektu pyfaktury
  (`fk/banknum.py`).

## [1.0] - 2019-01-27

### Dodane

* Pierwsze wydanie.
