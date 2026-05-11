# -*- coding: utf-8 -*-
"""
    MicroJen Scrapers Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import

import hashlib
import re
import time
import os
from ast import literal_eval as evaluate
import six

try:
    from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError

from microjenscrapers.modules import control
from kodi_six import xbmcaddon

if six.PY2:
    str = unicode
elif six.PY3:
    str = unicode = basestring = str

cache_table = 'cache'
data_path = control.transPath(control.addon("script.module.microjenscrapers").getAddonInfo('profile'))

def get(function_, duration, *args, **table):

    try:
        response = None

        f = repr(function_)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            a.update(six.ensure_binary(i, errors='replace'))
        a = str(a.hexdigest())
    except Exception:
        pass

    try:
        table = table['table']
    except Exception:
        table = 'rel_list'

    try:
        control.makeFile(control.dataPath)
        dbcon = db.connect(control.cacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = '{f}' AND args = '{a}'".format(tn=table, f=f, a=a))
        match = dbcur.fetchone()

        try:
            response = evaluate(match[2].encode('utf-8'))
        except AttributeError:
            response = evaluate(match[2])

        t1 = int(match[3])
        t2 = int(time.time())
        update = (abs(t2 - t1) / 3600) >= int(duration)
        if not update:
            return response
    except Exception:
        pass

    try:
        r = function_(*args)
        if (r is None or r == []) and response is not None:
            return response
        elif r is None or r == []:
            return r
    except Exception:
        return

    try:
        r = repr(r)
        t = int(time.time())
        dbcur.execute("CREATE TABLE IF NOT EXISTS {} (""func TEXT, ""args TEXT, ""response TEXT, ""added TEXT, ""UNIQUE(func, args)"");".format(table))
        dbcur.execute("DELETE FROM {0} WHERE func = '{1}' AND args = '{2}'".format(table, f, a))
        dbcur.execute("INSERT INTO {} Values (?, ?, ?, ?)".format(table), (f, a, r, t))
        dbcon.commit()
    except Exception:
        pass

    try:
        return evaluate(r.encode('utf-8'))
    except Exception:
        return evaluate(r)

def timeout(function_, *args):
    try:
        key = _hash_function(function_, args)
        result = cache_get(key)
        return int(result['date'])
    except Exception:
        return None

def cache_get(key):
    # type: (str, str) -> dict or None
    try:
        cursor = _get_connection_cursor()
        cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [key])
        return cursor.fetchone()
    except OperationalError:
        return None

def cache_insert(key, value):
    # type: (str, str) -> None
    cursor = _get_connection_cursor()
    now = int(time.time())
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, date INTEGER, UNIQUE(key))"
        % cache_table
    )
    update_result = cursor.execute(
        "UPDATE %s SET value=?,date=? WHERE key=?"
        % cache_table, (value, now, key))

    if update_result.rowcount is 0:
        cursor.execute(
            "INSERT INTO %s Values (?, ?, ?)"
            % cache_table, (key, value, now)
        )

    cursor.connection.commit()

def cache_clear():
    try:
        cursor = _get_connection_cursor()

        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_meta():
    try:
        cursor = _get_connection_cursor_meta()

        for t in ['meta']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_providers():
    try:
        cursor = _get_connection_cursor_providers()

        for t in ['rel_src', 'rel_url']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_search():
    try:
        cursor = _get_connection_cursor_search()

        for t in ['tvshow', 'movies']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_all():
    cache_clear()
    cache_clear_meta()
    cache_clear_providers()

def _get_connection_cursor():
    conn = _get_connection()
    return conn.cursor()

def _get_connection():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'cache.db'))
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_meta():
    conn = _get_connection_meta()
    return conn.cursor()

def _get_connection_meta():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'meta.5.db'))
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_providers():
    conn = _get_connection_providers()
    return conn.cursor()

def _get_connection_providers():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'providers.13.db'))
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_search():
    conn = _get_connection_search()
    return conn.cursor()

def _get_connection_search():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'search.1.db'))
    conn.row_factory = _dict_factory
    return conn

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _hash_function(function_instance, *args):
    return _get_function_name(function_instance) + _generate_md5(args)


def _get_function_name(function_instance):
    return re.sub('.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))


def _generate_md5(*args):
    md5_hash = hashlib.md5()
    [md5_hash.update(six.ensure_binary(arg, errors='replace')) for arg in args]
    return str(md5_hash.hexdigest())


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff

