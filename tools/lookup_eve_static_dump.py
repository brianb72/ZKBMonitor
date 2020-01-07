'''
    Provides access to the Eve Online Static Data Dump, which is an SQL database of all constant game data.
'''

import sqlite3
import os

from data.definitions import ROOT_DIR


class LookupEveStaticDumpException(Exception):
    '''Raise whenever any error or exception occurs'''

class LookupEveStaticDump(object):
    DEFAULT_PATH = os.path.join(ROOT_DIR, 'data/sqlite-latest.sqlite')
    UNKNOWN_STRING = '!Unknown!'

    def __init__(self):
        pass


    # Connect to the sqlite3 file and return a connection handle.
    def connect_to_sql(self, db_path=DEFAULT_PATH):
        try:
            con = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            raise LookupEveStaticDumpException(f'sqlite error could not connect to database [{db_path}] - [{e}]')

        return con

    # If lookup returns None, return UNKNOWN_STRING
    def _lookup_single_string_from_int(self, query_string, int_value):
        db = self.connect_to_sql()
        cursor = db.cursor()
        formatted_query = ''
        try:
            formatted_query = query_string % (int_value,)
            cursor.execute(formatted_query)
            result = cursor.fetchone()
            if result is None:
                return self.UNKNOWN_STRING
            return result[0]
        except sqlite3.Error as e:
            raise LookupEveStaticDumpException(f'sqlite lookup error [{e}] - [{formatted_query}]')


    # If lookup returns None, return type_id 0 (invalid id) instead
    def _lookup_single_id_from_int(self, query_string, int_value):
        db = self.connect_to_sql()
        cursor = db.cursor()
        formatted_query = ''
        try:
            formatted_query = query_string % (int_value,)
            cursor.execute(formatted_query)
            result = cursor.fetchone()
            if result is None:
                return 0
            if result[0] is None:
                return 0
            return result[0]
        except sqlite3.Error as e:
            raise LookupEveStaticDumpException(f'sqlite lookup error [{e}] - [{formatted_query}]')


    # If no result is found return an empty list.
    def _lookup_multirow_int(self, query_string, int_value):
        db = self.connect_to_sql()
        cursor = db.cursor()
        formatted_query = ''
        try:
            formatted_query = query_string % (int_value,)
            cursor.execute(formatted_query)
            result = cursor.fetchall()
            if result is None:
                return []
            return result
        except sqlite3.Error as e:
            raise LookupEveStaticDumpException(f'sqlite lookup error [{e}] - [{formatted_query}]')

    # If no result is found return an empty list.
    def _lookup_multirow_two_int(self, query_string, int_value_1, int_value_2):
        db = self.connect_to_sql()
        cursor = db.cursor()
        formatted_query = ''

        try:
            formatted_query = query_string % (int_value_1, int_value_2)
            cursor.execute(formatted_query)
            result = cursor.fetchall()
            if result is None:
                return []
            return [x[0] for x in result]
        except sqlite3.Error as e:
            raise LookupEveStaticDumpException(f'sqlite lookup error [{e}] - [{formatted_query}]')

    # If no result is found return an empty list.
    def _lookup_multirow_two_float(self, query_string, float_value_1, float_value_2):
        db = self.connect_to_sql()
        cursor = db.cursor()
        formatted_query = ''

        try:
            formatted_query = query_string % (float_value_1, float_value_2)
            cursor.execute(formatted_query)
            result = cursor.fetchall()
            if result is None:
                return []
            return [x[0] for x in result]
        except sqlite3.Error as e:
            raise LookupEveStaticDumpException(f'sqlite lookup error [{e}] - [{formatted_query}]')

    ########################
    # Type and Groups
    def get_type_name(self, type_id):
        sql_query = "SELECT typeName FROM invTypes WHERE typeID = %s"
        return self._lookup_single_string_from_int(sql_query, type_id)

    def get_group_for_type(self, type_id):
        sql_query = "SELECT groupID FROM invTypes WHERE typeID = %s"
        return self._lookup_single_string_from_int(sql_query, type_id)

    def get_typelist_for_group(self, group_id):
        sql_query = "SELECT typeID FROM invTypes WHERE groupID = %s"
        return self._lookup_multirow_int(sql_query, group_id)

    def get_marketgroup_for_type_id(self, type_id):
        sql_query = "SELECT marketGroupID FROM invTypes WHERE typeID = %s"
        return self._lookup_single_id_from_int(sql_query, type_id)

    def get_marketgroup_name(self, marketgroup_id):
        sql_query = "SELECT marketGroupName FROM invMarketGroups WHERE marketGroupID = %s"
        return self._lookup_single_string_from_int(sql_query, marketgroup_id)

    def get_marketgroup_parentgroup_id(self, marketgroup_id):
        sql_query = "SELECT parentGroupID FROM invMarketGroups WHERE marketGroupID = %s"
        return self._lookup_single_id_from_int(sql_query, marketgroup_id)

    def get_marketgroup_top_level_parent(self, marketgroup_id):
        sanity_check = 50
        current_id = marketgroup_id
        while sanity_check > 0:
            new_id = self.get_marketgroup_parentgroup_id(current_id)
            if new_id == 0:
                return current_id
            else:
                current_id = new_id
            sanity_check -= 1
        raise LookupEveStaticDumpException("EveStaticLookup::get_marketgroup_top_level_parent sanity check failed.")



    ########################
    # Map

    # Name lookup
    def get_solarsystem_name(self, solarsystem_id):
        sql_query = "SELECT solarSystemName FROM mapSolarSystems WHERE solarSystemID = %s"
        return self._lookup_single_string_from_int(sql_query, solarsystem_id)

    def get_constellation_name(self, constellation_id):
        sql_query = "SELECT constellationName FROM mapConstellations WHERE constellationID = %s"
        return self._lookup_single_string_from_int(sql_query, constellation_id)

    def get_region_name(self, region_id):
        sql_query = "SELECT regionName FROM mapRegions WHERE regionID = %s"
        return self._lookup_single_string_from_int(sql_query, region_id)


    # Misc lookup
    def get_solarsystem_security(self, solarsystem_id):
        sql_query = "SELECT security FROM mapSolarSystems WHERE solarSystemID = %s"
        return self._lookup_single_string_from_int(sql_query, solarsystem_id)


    # Cross reference
    def get_solarsystem_constellation(self, solarsystem_id):
        sql_query = "SELECT constellationID FROM mapSolarSystems WHERE solarSystemID = %s"
        return self._lookup_single_string_from_int(sql_query, solarsystem_id)

    def get_solarsystem_region(self, solarsystem_id):
        sql_query = "SELECT regionID FROM mapSolarSystems WHERE solarSystemID = %s"
        return self._lookup_single_string_from_int(sql_query, solarsystem_id)

    def get_all_solarsystem_id_by_security(self, min_security, max_security):
        sql_query = "SELECT solarSystemID FROM mapSolarSystems WHERE security BETWEEN %s AND %s"
        return self._lookup_multirow_two_float(sql_query, min_security, max_security)


    def get_jumps_in_solarsystem(self, solarsystem_id):
        sql_query = "SELECT toSolarSystemID FROM mapSolarSystemJumps WHERE fromSolarSystemID = %s"
        result =  self._lookup_multirow_int(sql_query, solarsystem_id)
        if not isinstance(result, list):    # TODO improve error checking
            raise LookupEveStaticDumpException('Invalid Result')
        return [x[0] for x in result]



    # ################################3
    # Routes

    # Find a route between two systems in the universe
    def find_route(self, start_solarsystem_id, target_solarsystem_id):
        def make_route_dict(from_system_id, distance):
            return {'from_system_id': from_system_id, 'distance': distance}

        sanity = 250    # Maximum route size before abort
        list_route_dict = {}
        list_to_walk = {}
        is_route_found = False

        # Start the list_to_walk off with the target_solarsystem_id, and a from_system_id/distance to nowhere.
        list_to_walk[target_solarsystem_id] = make_route_dict(0, 0)

        # As long as list_to_walk has systems to jump into, jump into those systems, get a list of their exits,
        # jump through those exits, and repeat until we find the start_solarsystem_id or run out of exits
        # Stop as soon as start_solarsystem_id is found
        while not is_route_found and len(list_to_walk) > 0 and sanity > 0:
            sanity -= 1
            new_to_walk = {}
            for item_system_id, item_value in list_to_walk.items():
                exit_list = self.get_jumps_in_solarsystem(item_system_id)
                new_distance = item_value['distance'] + 1

                for exit in exit_list:
                    if exit not in list_route_dict.keys():
                        new_to_walk[exit] = make_route_dict(item_system_id, new_distance)
                        list_route_dict[exit] = make_route_dict(item_system_id, new_distance)
                        if exit == start_solarsystem_id:
                            is_route_found = True
                            break

            list_to_walk = new_to_walk

        # Should never happen
        if sanity <= 0:
            raise LookupEveStaticDumpException(f'{__file__} : find_route() sanity exceeded!')

        # If we did not find a route, return an empty list
        if not is_route_found:
            return []

        # Using the list_route_dict that we created, walk from start to target to produce the shortest_route list
        current_system = start_solarsystem_id
        shortest_route = []

        while current_system != target_solarsystem_id:
            shortest_route.append(current_system)
            current_system = list_route_dict[current_system]['from_system_id']

        # shortest_route is a list of solarsystem_id that form a route from start to target
        return shortest_route


