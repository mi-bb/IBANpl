# -*- coding: UTF-8 -*-
#                                                                  
#         _/_/_/  _/_/_/      _/_/    _/      _/  _/_/_/    _/     
#          _/    _/    _/  _/    _/  _/_/    _/  _/    _/  _/      
#         _/    _/_/_/    _/_/_/_/  _/  _/  _/  _/_/_/    _/       
#        _/    _/    _/  _/    _/  _/    _/_/  _/        _/        
#     _/_/_/  _/_/_/    _/    _/  _/      _/  _/        _/_/_/_/   
#                                                                  
#    Copyright (C) 2016-2019 Michał Bąbik
#
#    Used parts of code from Wikipedia (http://pl.wikipedia.org/wiki/IBAN)
#    This file is part of IBANpl.
#
#    IBANpl is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    IBANpl is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with IBANpl.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------------#
import sqlite3
import io
import logging
from collections.abc import Callable, Iterable, Iterator
from sqlite3 import Connection
from urllib.request import Request, urlopen
from urllib.error import URLError
from http.client import HTTPResponse
from datetime import date
logger = logging.getLogger(__name__)
#-----------------------------------------------------------------------------#
UPD_URL = "https://ewib.nbp.pl/plewibnra?dokNazwa=plewibnra.txt"
UPD_TIMEOUT = 30
MIN_BANK_RECORDS = 100
BANK_DB_FILE_NAME = "bn_base.db"
#-----------------------------------------------------------------------------#
def iban_letter2num(letter: str) -> str:
    return str(ord(letter) - ord("A") + 10)
#-----------------------------------------------------------------------------#
def chk_iban(number: str) -> tuple[bool, str, str]:
    """Check IBAN account correctness.

    Args:
        number (str): IBAN Number to check

    Returns:
        tuple[bool, str, str]: Tuple containing validation information:
        - bool info about number correctness
        - string with verification message
        - string with formatted IBAN number or processed number
    """
    number = number.replace(" ","")
    number = number.replace("-","")
    number = "PL" + number

    if len(number) != 28:
        msg = "Powinno być 26 znaków jest {0:d}".format(len(number)-2)
        return False, msg, number

    nkf = number[2:4] + " " + number[4:8] + " " + number[8:12] + " " + \
          number[12:16] + " " + number[16:20] + " " + number[20:24] + \
          " " + number[24:28]
    number = number[4:] + iban_letter2num(number[0]) + \
          iban_letter2num(number[1]) + number[2:4]

    try:
        n = int(number)
    except ValueError:
        return False, "Nieprawidłowy znak", number

    if n % 97 == 1:
        return True, "Numer prawidłowy", nkf
    else:
        return False, "Błąd w numerze", number
#-----------------------------------------------------------------------------#
def b_dbop(db_file_name: str | None = None) -> sqlite3.Connection:
    """Open database file"""
    if not db_file_name:
        db_file_name = BANK_DB_FILE_NAME
    con = sqlite3.connect(db_file_name)
    con.text_factory = str
    c = con.cursor()
    c.executescript("""
    create table if not exists
    bank (id integer primary key,
          bank_name text,
          bank_tname text);
    create table if not exists
    jorg (id integer,
          oid integer,
          j_org_name text,
          j_org_name_sh text,
          j_org_city text,
          j_org_street text,
          post_code text,
          post_city text,
          post_box text,
          post_box_code text,
          phone_code text,
          phone_no1 text,
          phone_no2 text,
          phone_no3 text,
          phone_no4 text,
          begin_work_date text,
          bic text,
          bic_sepa text,
          web_address text,
          voivodeship text,
          county text,
          mail_city text,
          mail_street text,
          mail_post_code text,
          mail_post_city text,
          mail_post_box text,
          mail_post_box_code text,
          union_n text,
          parent_no integer);
    create table if not exists
    date_mod (id integer,
              date_m text);""")
    con.commit()
    #c.close()
    return con
    #return con, cc
#-----------------------------------------------------------------------------#
def run_sql_command(
    open_conn: Callable[[str | None], Connection],
    cmd: str, args: tuple = (), return_result: bool = False,
    db_file_name: str | None = None,
    commit: bool = True) -> tuple[list, str | None]:
    """Execute cmd/args against the connection open_conn(db_file_name) returns.

    Inlined copy of pyfaktury's fk/sql_common.py -- keep in sync. open_conn
    is referenced by name (resolved at call time), so unittest.mock.patch on
    the module-level b_dbop still takes effect.
    """
    result_value: list = []
    c = None
    con = None
    error_info = None
    try:
        con = open_conn(db_file_name)
        c = con.cursor()
        c.execute(cmd, args)
        if return_result:
            result_value = c.fetchall()
        if commit:
            con.commit()
    except sqlite3.Error as e:
        error_info = str(e)
        logger.error("An error occurred: %s", error_info)
        if con:
            con.rollback()
    finally:
        if c:
            c.close()
        if con:
            con.close()
    return result_value, error_info
#-----------------------------------------------------------------------------#
def sql_command_get(cmd: str, args: tuple = (),
                    db_file_name: str | None = None) -> tuple[list, str | None]:
    return sql_command_exec(cmd, args, True, db_file_name, False)
#-----------------------------------------------------------------------------#
def sql_command_save(cmd: str, args: tuple = (),
                     db_file_name: str | None = None) -> str | None:
    _, error_info = sql_command_exec(cmd, args, False, db_file_name, True)
    return error_info
#-----------------------------------------------------------------------------#
def sql_command_exec(cmd: str, args: tuple = (), rett: bool = False,
                     db_file_name: str | None = None,
                     comm: bool = True) -> tuple[list, str | None]:
    """Execute sqlite command"""
    return run_sql_command(b_dbop, cmd, args, rett, db_file_name, comm)
#-----------------------------------------------------------------------------#
def chk_str_to_int(number: str) -> tuple[int, str | None]:
    """Check if string converts to int"""
    n = 0
    try:
        n = int(number)
    except ValueError:
        return 0, "Nieprawidłowy znak"
    return n, None
#-----------------------------------------------------------------------------#
def sql_get_all_bank_no() -> tuple[list, str | None]:
    """Get all bank numbers"""
    return sql_command_get("""select id from bank order by id""")
#-----------------------------------------------------------------------------#
def sql_get_all_jorg(bid: int) -> tuple[list, str | None]:
    """Get all jorg (branch) numbers of a bank with oid number bid"""
    return sql_command_get(
        """select id from jorg where oid=? order by id""", (bid,))
#-----------------------------------------------------------------------------#
def sql_get_bank_info_frmt(number: str) -> tuple[list, list, str | None]:
    """Get bank info from db based on first 4 or 8 IBAN numbers"""
    ret1 = []
    ret2 = []
    if len(number) > 3:
        # bank
        d, error_info = chk_str_to_int(number[0:4])
        if error_info is not None:
            return ret1, ret2, error_info
        d1 = d
        logger.debug("First number id: %d", d1)
        d, error_info = sql_command_get(
            """select * from bank where id=? limit 1""", (d1,))
        if error_info is not None:
            return ret1, ret2, error_info
        if d:
            ret1 = d[0]
            if len(number) > 7:
                # detailed unit info
                d, error_info = chk_str_to_int(number[4:8])
                if error_info is not None:
                    return ret1, ret2, error_info
                d2 = d
                logger.debug("Second number id: %d", d2)
                d, error_info = sql_command_get(
                  """select j_org_name, j_org_name_sh, j_org_street,
                  post_code || ' ' || j_org_city, post_city,
                  post_box_code || ' ' || post_box,
                  phone_code || ' ' || phone_no1 || ', ' || phone_no2,
                  phone_code || ' ' || phone_no3 || ', ' || phone_no4,
                  begin_work_date, bic, bic_sepa, web_address,
                  voivodeship || ' ' || county, mail_city || ' ' || mail_street,
                  mail_post_code || ' ' || mail_post_city,
                  mail_post_box || ' ' || mail_post_box_code, union_n, parent_no
                  from jorg where id=? and oid=? limit 1""", (d2, d1,))
                if error_info is not None:
                    return ret1, ret2, error_info
                if d:
                    ret2 = d[0]
    return ret1, ret2, None
#-----------------------------------------------------------------------------#
def get_date_today_iso() -> str:
    today = date.today()
    return today.isoformat()
#-----------------------------------------------------------------------------#
def get_url_response(url: str,
                     timeout: float | None = None) -> HTTPResponse | None:
    """Check if url responses.

    Inlined copy of pyfaktury's fk/sfun.py:ge_url_response -- keep in sync.
    """
    req = Request(url)
    try:
        response = urlopen(req, timeout=timeout)
    except URLError as e:
        logger.error("We failed to reach a server. Reason %s", str(e))
        return None
    return response
#-----------------------------------------------------------------------------#
def chk_avail_update() -> tuple[bool, str]:
    """Check if bank data update service (NBP) is reachable"""
    response = get_url_response(UPD_URL, timeout=UPD_TIMEOUT)
    if not response:
        return False, "Nie udało się połączyć z serwerem NBP w celu " + \
                "pobrania danych o bankach (" + UPD_URL + ")"
    response.close()
    date_today = get_date_today_iso()
    d, error_info = sql_command_get(
            """select date_m from date_mod where id=1""")
    if error_info is not None:
        return False, error_info
    if len(d) > 0 and len(d[0]) > 0 and (d[0][0] != date_today):
        return True, "Czy uaktualnić bazę informacji o bankach o dane " + \
                "pobrane ze strony NBP ?"
    else:
        return True, "Dzisiaj już aktualizowano dane. Czy wykonać " + \
                "aktualizację o dane pobrane ze strony NBP jeszcze raz ?"
#-----------------------------------------------------------------------------#
def bank_b_iterator(bdict: dict) -> Iterator[tuple[int, str, str]]:
    """Iterating through bank info"""
    for i in bdict:
        yield i, bdict[i][0], bdict[i][1]
#-----------------------------------------------------------------------------#
def bank_j_iterator(content: io.StringIO, bdict: dict) -> Iterator[tuple]:
    """Iterating through unit info"""
    line = content.readline().split("\t")
    while (len(line) > 1):
        i = int(line[4][0:4])
        bdict[i] = line[1].strip(), line[2].strip()
        a = int(line[4][4:8])
        dt = [a, i]
        dt.extend(line[i].strip() for i in range(5,32))
        yield tuple(dt)
        line = content.readline().split("\t")
#-----------------------------------------------------------------------------#
def sql_upd_many(cmd: str, i_iter: Iterable[tuple]) -> str | None:
    """Update many items using iterators"""
    error_info = None
    c = None
    con = None
    try:
        con = b_dbop()
        c = con.cursor()
        c.executemany(cmd, i_iter)
        con.commit()
    except sqlite3.Error as e:
        logger.error("An error occurred while updating data: %s", str(e))
        if con:
            con.rollback()
        error_info = str(e)
    finally:
        if c:
            c.close()
        if con:
            con.close()
    return error_info
#-----------------------------------------------------------------------------#
def validate_bank_data(content: io.StringIO) -> str | None:
    """Sanity-check downloaded bank registry data before it replaces the DB

    Guards against wiping the bank tables with an empty, truncated or
    otherwise malformed response (e.g. an HTML error page) instead of the
    expected plewibnra.txt-format data. Mirrors the parsing/termination
    logic of bank_j_iterator() without writing anything, then rewinds
    content back to where it started so the real import can run.
    """
    pos = content.tell()
    count = 0
    try:
        line = content.readline().split("\t")
        while len(line) > 1:
            if len(line) < 32:
                return "Nieprawidłowy format pobranych danych o " + \
                        "bankach (linia {0})".format(count + 1)
            try:
                int(line[4][0:4])
                int(line[4][4:8])
            except (ValueError, IndexError):
                return "Nieprawidłowy format pobranych danych o " + \
                        "bankach (linia {0})".format(count + 1)
            count += 1
            line = content.readline().split("\t")
    finally:
        content.seek(pos)
    if count < MIN_BANK_RECORDS:
        return "Pobrane dane o bankach wyglądają na niekompletne " + \
                "(otrzymano {0} rekordów)".format(count)
    return None
#-----------------------------------------------------------------------------#
def bank_base_update(content: io.StringIO) -> str | None:
    """Replace the bank registry tables with freshly downloaded data.

    Validates content, then wipes and repopulates the jorg and bank
    tables, followed by the date_mod timestamp, in that order, all
    within a single database transaction. If any step fails the whole
    transaction is rolled back, so the existing data stays untouched
    rather than being left partially updated.

    Args:
        content (io.StringIO): Bank registry data in plewibnra.txt
            format, as produced by bank_list_update().

    Returns:
        str | None: An error message describing the first failure
        encountered (validation or a database step), or None if the
        update completed successfully.
    """
    if (error_info := validate_bank_data(content)) is not None:
        return error_info
    bd: dict = {}
    jit = bank_j_iterator(content, bd)
    error_info = None
    c = None
    con = None
    try:
        con = b_dbop()
        c = con.cursor()
        c.execute("""delete from jorg""")
        c.execute("""delete from bank""")
        c.executemany(
            """insert or replace into jorg values (?,?,?,?,?,?,?,?,?,?,?,?,?,
               ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", jit)
        bit = bank_b_iterator(bd)
        c.executemany("""insert into bank values (?,?,?)""", bit)
        c.execute("""delete from date_mod""")
        c.execute(
            """insert or replace into date_mod values (?,?)""",
            (1, get_date_today_iso()))
        con.commit()
    except Exception as e:
        # Broader than sqlite3.Error: the executemany() calls above also
        # drive bank_j_iterator()/bank_b_iterator(), which can raise
        # plain ValueError/IndexError on unexpected input. Any failure
        # here must still roll back the transaction, not just DB errors.
        error_info = str(e)
        logger.error("An error occurred on bank data update: %s", error_info)
        if con:
            con.rollback()
    finally:
        if c:
            c.close()
        if con:
            con.close()
    return error_info
#-----------------------------------------------------------------------------#
def bank_list_update() -> str | None:
    """Updating bank list database with data downloaded from NBP"""
    response = get_url_response(UPD_URL, timeout=UPD_TIMEOUT)
    if not response:
        return "Nie udało się pobrać danych o bankach z serwera NBP"
    try:
        content = response.read().decode("cp852")
    except Exception as e:
        logger.error("Błąd podczas przetwarzania pobranych danych: %s", str(e))
        return "Błąd podczas przetwarzania pobranych danych: " + str(e)
    finally:
        response.close()
    return bank_base_update(io.StringIO(content))
#-----------------------------------------------------------------------------#
def bank_update() -> None:
    status, info = chk_avail_update()
    if status:
        error_info = bank_list_update()
        if error_info is None:
            logger.info("lista została uaktualniona")
        else:
            logger.error("blad przy aktualizacji: %s", error_info)
    else:
        logger.error("błąd podczas sprawdzania aktualizacji: %s", info)
#------------------------------------------------------------------------------#
