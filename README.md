# IBANpl

Informacja o polskich bankach na podstawie numeru konta IBAN
 Polish bank information based on the IBAN account number

Program oraz funkcje pozwalające na sprawdzenie poprawności numeru
konta oraz wyświetlenie informacji o polskich bankach
(nazwa banku, adres i inne dane) na podstawie numeru konta IBAN.

The program and accompanying functions allow you to check the
correctness of an account number and to display information about
Polish banks (bank name, address and other data) based on the IBAN
account number.

Program korzysta z bazy danych SQLite.
The program uses an SQLite database.

# Wymagania / Requirements

 * Python 3
 * GTK+ 3
 * SQLite 3

OS:
 * Linux
 * Windows

# Aktualizacja bazy danych banków / Bank database update

Po uruchomieniu programu wystarczy kliknąć przycisk _**Uaktualnij bazę**_ — aktualna
lista banków zostanie pobrana automatycznie z serwisu eWIB Narodowego Banku Polskiego
(https://ewib.nbp.pl/).

After starting the program, simply click the _**Update Database**_ button —
the current list of banks is downloaded automatically from the eWIB service
of the National Bank of Poland (https://ewib.nbp.pl/).

# Wspierane języki / Languages

Język interfejsu jest wybierany automatycznie na podstawie ustawień
systemowych (`LANGUAGE`/`LC_*`/`LANG`). Polskie teksty są językiem
źródłowym, tłumaczenie angielskie znajduje się w katalogu `locale/en`.
Dane banków i jednostek organizacyjnych pochodzące z serwisu eWIB NBP
są zawsze w języku polskim.

The interface language follows the system locale (`LANGUAGE`/`LC_*`/`LANG`).
Polish is the source language; an English translation is provided in
`locale/en/`. Bank and branch data from the NBP eWIB service is always
in Polish.

# Copyright and license

Copyright (C) 2016-2026 Michal Babik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

