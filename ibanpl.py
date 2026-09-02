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
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import date
#-----------------------------------------------------------------------------#
DB_FILE_NAME = 'bn_base.db'
BANK_LIST_URL = 'https://ewib.nbp.pl/plewibnra?dokNazwa=plewibnra.txt'
#-----------------------------------------------------------------------------#
def iban_letter2num(letter):
    return str(ord(letter) - ord('A') + 10)
#-----------------------------------------------------------------------------#
def chk_iban(num):
    """Check IBAN account correctness"""
    ret = [False, '', num]
    num = num.replace(' ','')
    num = num.replace('-','')
    num = 'PL' + num
    if len(num) != 28:
        tx = "Powinno być 26 znaków jest {0:d}".format(len(num)-2)
        ret[1] = tx
    else:
        nkf = num[2:4] + ' ' + num[4:8] + ' ' + num[8:12] + ' ' + \
              num[12:16] + ' ' + num[16:20] + ' ' + num[20:24] + \
              ' ' + num[24:28]
        num = num[4:] + iban_letter2num(num[0]) + \
              iban_letter2num(num[1]) + num[2:4]
        n = 0
        try:
            n = int(num)
        except ValueError:
            ret[1] = 'Nieprawidłowy znak'
        else:   
            if n % 97 == 1:
                ret = [True, 'Numer prawidłowy', nkf]
            else:
                ret[1] = 'Błąd w numerze'
    return ret 
#-----------------------------------------------------------------------------#
def b_dbop(bn=None):
    """Open database file"""
    if not bn:
        bn = DB_FILE_NAME
    con = sqlite3.connect(bn)
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
def sql_command_get(cmd, args=(), bn=None):
    return sql_command_exec(cmd, args, True, bn, False)
#-----------------------------------------------------------------------------#
def sql_command_save(cmd, args=(), bn=None):
    return sql_command_exec(cmd, args, False, bn, True)
#-----------------------------------------------------------------------------#
def sql_command_exec(cmd, args=(), rett=False, bn=None, comm=True):
    """Execute sqlite command"""
    ret = [False, None]
    c = None
    con = None
    try:
        con = b_dbop(bn)
        c = con.cursor()
        if comm:
            con.commit()
        c.execute(cmd, args)
        if rett:
            ret[1] = c.fetchall()
        if comm:
            con.commit()
    except sqlite3.Error as e:
        print("An error occurred:", e)
        con.rollback()
        ret[1] = e
    else:
        ret[0] = True
    finally:
        if c:
            c.close()
        if con:
            con.close()
    return ret
#-----------------------------------------------------------------------------#
def chk_str_to_int(num):
    """Check if string converts to int"""
    n = 0
    try:
        n = int(num)
    except ValueError:
        return False, 'Nieprawidłowy znak'
    else:
        return True, n
    return False, 'Nieprawidłowy znak'
#-----------------------------------------------------------------------------#
def sql_get_bank_info_frmt(num):
    """Get bank info from db based on first 4 or 8 IBAN numbers"""
    ret1 = []
    ret2 = []
    if len(num) > 3:
        # bank
        r, d = chk_str_to_int(num[0:4])
        if not r:
            return r, ret1, ret2, d
        d1 = d
        r, d = sql_command_get(
            """select * from bank where id=? limit 1""", (d,))
        if not r:
            return r, ret1, ret2, d
        if d:
            ret1 = d[0]
            if len(num) > 7:
                # detailed unit info
                r, d = chk_str_to_int(num[4:8])
                if not r:
                    return r, ret1, ret2, d
                r, d = sql_command_get(
                  """select j_org_name, j_org_name_sh, j_org_street,
                  post_code || ' ' || j_org_city, post_city,
                  post_box_code || ' ' || post_box,
                  phone_code || ' ' || phone_no1 || ', ' || phone_no2,
                  phone_code || ' ' || phone_no3 || ', ' || phone_no4,
                  begin_work_date, bic, bic_sepa, web_address,
                  voivodeship || ' ' || county, mail_city || ' ' || mail_street,
                  mail_post_code || ' ' || mail_post_city,
                  mail_post_box || ' ' || mail_post_box_code, union_n, parent_no
                  from jorg where id=? and oid=? limit 1""", (d, d1,))
                if not r:
                    return r, ret1, ret2, d
                if d:
                    ret2 = d[0]
    return True, ret1, ret2, ''
#-----------------------------------------------------------------------------#
def get_date_today():
    today = date.today()
    return today.isoformat()
#-----------------------------------------------------------------------------#
def sql_get_all_bank_no():
    """Get all bank numbers"""
    r, d = sql_command_get("""select id from bank order by id""")
    if not r:
        return False, d
    return True, d
#-----------------------------------------------------------------------------#
def sql_get_all_jorg(bid):
    """Get all jorg numbers of a bid bank"""
    r, d = sql_command_get("""select id from jorg where oid=? order by id""",
            (bid, ))
    if not r:
        return False, d
    return True, d
#-----------------------------------------------------------------------------#
def chk_avail_update():
    """Check if bank base on web is newer than in local DB"""
    idd = 1
    dt = get_date_today() 
    if dt != '':
        r, d = sql_command_get(
            """select date_m from date_mod where id=?""", (idd,))
        if not r:
            return False
        # none
        if not d:
            return True, 'Brak', dt
        # to update
        elif d[0][0] != dt:
            return True, d[0][0], dt
    return False, dt, dt
#-----------------------------------------------------------------------------#
def bank_b_iterator(bdict):
    """Iterating through bank info"""
    for i in bdict:
        yield i, bdict[i][0], bdict[i][1]
#-----------------------------------------------------------------------------#
def bank_j_iterator(cont, bdict):
    """Iterating through unit info"""
    line_parts = cont.readline().split("\t")
    while (len(line_parts) > 1):
        i = int(line_parts[4][0:4])
        bdict[i] = line_parts[1].strip(), line_parts[2].strip()
        a = int(line_parts[4][4:8])
        dt = [a, i]
        dt.extend(line_parts[i].strip() for i in range(5,32))
        yield tuple(dt)
        line_parts = cont.readline().split("\t")
#-----------------------------------------------------------------------------#
def sql_upd_many(cmd, i_iter):
    """Update many items using iterators"""
    ret = [False, '']
    c = None
    con = None
    try:
        con = b_dbop()
        c = con.cursor()
        c.executemany(cmd, i_iter)
        con.commit()
    except sqlite3.Error as e:
        print("An error occurred:", e)
        con.rollback()
        ret[1] = e
    else:
        ret[0] = True
    finally:
        if c:
            c.close()
        if con:
            con.close()
    return ret
#-----------------------------------------------------------------------------#
def bank_base_update(f):
    r, d = sql_command_save("""delete from jorg""")
    if not r:
        return r, d
    r, d = sql_command_save("""delete from bank""")
    if not r:
        return r, d
    #r, d = sql_command_save("""vacuum""")
    #if not r: return r, d
    bd = {}
    jit = bank_j_iterator(f, bd)
    r, d = sql_upd_many(
        """insert or replace into jorg values (?,?,?,?,?,?,?,?,?,?,?,?,?,
           ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", jit)
    if not r:
        return r, d
    bit = bank_b_iterator(bd)
    r, d = sql_upd_many(
        """insert into bank values (?,?,?)""", bit)
    if not r:
        return r, d
    # updating date
    r, d = sql_command_save("""delete from date_mod""")
    if not r:
        return r, d
    dat = get_date_today()
    r, d = sql_command_save(
        """insert or replace into date_mod values (?,?)""",
        (1, dat))
    if not r:
        return r, d
    return True, ''
#-----------------------------------------------------------------------------#
def bank_list_download():
    """Download bank list file from NBP eWIB"""
    try:
        with urlopen(Request(BANK_LIST_URL), timeout=30) as response:
            data = response.read()
    except URLError as e:
        return False, 'Nie udało się pobrać danych: {0}'.format(e)
    return True, data.decode('cp852')
#-----------------------------------------------------------------------------#
def bank_list_update():
    """Updating bank list database from NBP eWIB"""
    r, d = bank_list_download()
    if not r:
        return r, d
    r, d = bank_base_update(io.StringIO(d))
    if not r:
        return r, d
    return True, ''
#-----------------------------------------------------------------------------#
def bank_update():
    ret = chk_avail_update()
    if ret:
        r, d = bank_list_update()
        if r:
            print('uaktualniona lista')
        else:
            print('blad przy aktualizacji', d)
    else:
        print('lista aktualna')

    return
#-----------------------------------------------------------------------------#


