# IBANpl

Informacja o polskich bankach na podstawie numeru konta IBAN

Program oraz funkcje pozwalające na sprawdzenie poprawności numeru
konta oraz wyświetlenie informacji o polskich bankach
(nazwa banku, adres i inne dane) na podsawie numeru konta IBAN.

Program korzysta z bazy danych SQLite.

# Wymagania

 * Python 3
 * GTK+ 3
 * SQLite 3

OS:
 * Linux
 * Windows

# Aktualizacja bazy danych banków

Należy wejść na stronę https://ewib.nbp.pl/
Przejść do zakładki _**Dane do pobrania**_ i pobrać plik _**plewibnra.txt**_.
Plik _**plewibnra.txt**_ nalezy skopiować do katalogu programu.
Po uruchomieniu programu kliknąć przycisk _**Uaktualnij bazę**_.

# Copyright and license

Copyright (C) 2016-2019 Michal Babik

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

