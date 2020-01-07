'''
    Caches killmails retreived from zkillboard.
    TODO: Cache character, corpotation, and alliance names.
'''

import sqlite3
import os

from data.definitions import ROOT_DIR

class RedisqCacheException(Exception):
    '''Raise whenever any error or exception occurs'''

class RedisqCache(object):
    DEFAULT_PATH = os.path.join(ROOT_DIR, 'cache/zkb_redisq/zkb_cache.sqlite')
    CREATE_CHARACTERS = 'CREATE TABLE IF NOT EXISTS `characters` (`id`  INTEGER NOT NULL,`name`  TEXT NOT NULL,PRIMARY KEY(`id`));'
    CREATE_CORPORATIONS = 'CREATE TABLE IF NOT EXISTS `corporations` (`id`  INTEGER NOT NULL,`name`  TEXT NOT NULL,PRIMARY KEY(`id`));'
    CREATE_ALLIANCES = 'CREATE TABLE IF NOT EXISTS `alliances` (`id`  INTEGER NOT NULL,`name`  TEXT NOT NULL,PRIMARY KEY(`id`));'
    CREATE_KILLMAILS = 'CREATE TABLE IF NOT EXISTS `killmails` (`id` INTEGER NOT NULL, `killmail` TEXT NOT NULL, PRIMARY KEY(`id`));'

    def __init__(self):
            self.first_check_of_database()

    # Try opening the database and create needed tables if they do not exist.
    def first_check_of_database(self):
        db = self.connect_to_sql()
        cursor = db.cursor()
        try:
            cursor.execute(self.CREATE_CHARACTERS)
            cursor.execute(self.CREATE_CORPORATIONS)
            cursor.execute(self.CREATE_ALLIANCES)
            cursor.execute(self.CREATE_KILLMAILS)
            db.commit()
        except sqlite3.Error as e:
            raise RedisqCacheException(f'sqlite error opening killmail cache database - [{e}]')


    # Connect to the sqlite3 file and return a connection handle.
    def connect_to_sql(self, db_path=DEFAULT_PATH):
        try:
            con = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            raise RedisqCacheException(f'sqlite error connecting to database - [{db_path}] - [{e}]')

        return con

    # Either return a string name or None to indicate that the name is not in the database
    def _lookup_single_item(self, query_string):
        db = self.connect_to_sql()
        cursor = db.cursor()
        try:
            cursor.execute(query_string)
            result = cursor.fetchone()
            if result is None:
                return None
            return result[0]
        except sqlite3.Error as e:
            raise RedisqCacheException(f'sqlite error performing query - [{e}] - [{query_string}]')

    # Get a killmail by id
    def lookup_killmail(self, killmail_id):
        sql_query = f'SELECT name FROM killmails WHERE id = {killmail_id}'
        return self._lookup_single_item(sql_query)

    # Add a killmail to the database
    def insert_killmail(self, killmail_id, killmail):
        db = self.connect_to_sql()
        cursor = db.cursor()

        sql_query = f'INSERT INTO Killmails (id, killmail) VALUES (?, ?);'
        try:
            cursor.execute(sql_query, (killmail_id, killmail))
            db.commit()
        except sqlite3.Error as e:
            raise RedisqCacheException(f'sqlite error inserting killmail - [{e}] - [{sql_query}]')


if __name__ == '__main__':
    print('Do not run directly, start with redisq_listener.py')
