# Copyright (C) 2015  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import psycopg2


def connect(db_url):
    """Open db connection.
    """
    return psycopg2.connect(db_url)


def execute(cur, query_params):
    """Execute the query_params.
    query_params is expected to be either:
    - a sql query (string)
    - a tuple (sql query, params)
    """
    if isinstance(query_params, str):
        cur.execute(query_params)
    else:
        cur.execute(*query_params)


def entry_to_bytes(entry):
    """Convert an entry coming from the database to bytes"""
    if isinstance(entry, memoryview):
        return entry.tobytes()
    return entry


def line_to_bytes(line):
    """Convert a line coming from the database to bytes"""
    return line.__class__(entry_to_bytes(entry) for entry in line)


def cursor_to_bytes(cursor):
    """Yield all the data from a cursor as bytes"""
    yield from (line_to_bytes(line) for line in cursor)


def query_fetch(db_conn, query_params):
    """Execute sql query which returns results.
    query_params is expected to be either:
    - a sql query (string)
    - a tuple (sql query, params)
    """
    with db_conn.cursor() as cur:
        execute(cur, query_params)
        yield from cursor_to_bytes(cur)
