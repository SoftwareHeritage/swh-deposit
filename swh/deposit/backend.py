# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from functools import wraps

import psycopg2
import psycopg2.extras


psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)


def autocommit(fn):
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        autocommit = False
        if 'cursor' not in kwargs or not kwargs['cursor']:
            autocommit = True
            kwargs['cursor'] = self.cursor()

        try:
            ret = fn(self, *args, **kwargs)
        except:
            if autocommit:
                self.rollback()
            raise

        if autocommit:
            self.commit()

        return ret

    return wrapped


class DepositBackend():
    """Backend for the Software Heritage deposit database.

    """

    def __init__(self, dbconn):
        self.db = None
        self.dbconn = dbconn
        self.reconnect()

    def reconnect(self):
        if not self.db or self.db.closed:
            self.db = psycopg2.connect(
                dsn=self.dbconn,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )

    def cursor(self):
        """Return a fresh cursor on the database, with auto-reconnection in
        case of failure

        """
        cur = None

        # Get a fresh cursor and reconnect at most three times
        tries = 0
        while True:
            tries += 1
            try:
                cur = self.db.cursor()
                cur.execute('select 1')
                break
            except psycopg2.OperationalError:
                if tries < 3:
                    self.reconnect()
                else:
                    raise

        return cur

    def commit(self):
        """Commit a transaction"""
        self.db.commit()

    def rollback(self):
        """Rollback a transaction"""
        self.db.rollback()

    deposit_keys = [
        'reception_date', 'complete_date', 'type', 'external_id',
        'status', 'client_id',
    ]

    def _format_query(self, query, keys):
        """Format a query with the given keys"""

        query_keys = ', '.join(keys)
        placeholders = ', '.join(['%s'] * len(keys))

        return query.format(keys=query_keys, placeholders=placeholders)

    @autocommit
    def deposit_add(self, deposit, cursor=None):
        """Create a new deposit.

        A deposit is a dictionary with the following keys:
            type (str): an identifier for the deposit type
            reception_date (date): deposit's reception date
            complete_date (date): deposit's date when the deposit is
            deemed complete
            external_id (str): the external identifier in the client's
            information system
            status (str): deposit status
            client_id (integer): client's identifier

        """
        query = self._format_query(
            """insert into deposit ({keys}) values ({placeholders})""",
            self.deposit_keys,
        )
        cursor.execute(query, [deposit[key] for key in self.deposi_keys])

    @autocommit
    def deposit_get(self, id, cursor=None):
        """Retrieve the task type with id

        """
        query = self._format_query(
            "select {keys} from deposit where type=%s",
            self.deposit_keys,
        )
        cursor.execute(query, (id,))
        ret = cursor.fetchone()
        return ret

    @autocommit
    def request_add(self, request, cursor=None):
        pass

    @autocommit
    def request_get(self, deposit_id, cursor=None):
        pass

    @autocommit
    def client_list(self, cursor=None):
        cursor.execute('select id, name from client')

        return {row['name']: row['id'] for row in cursor.fetchall()}

    @autocommit
    def client_get(self, id, cursor=None):
        cursor.execute('select id, name, credential from client where id=%s',
                       (id, ))

        return cursor.fetchone()
