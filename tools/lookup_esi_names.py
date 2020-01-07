'''
    Look up character, corporation, and alliance names using Eve Online's RESTFul API "ESI"
    Uses the esipy package to access ESI

    TODO: The esipy package handles failures and retries on it's own. Add some code to deal with lookups failing
        after too many internal failures. Delay and try again. How should caller deal with this modules failures and
        timeouts?
'''

import json

import os

from esipy import EsiApp
from esipy.cache import FileCache
from esipy import EsiClient

# Supress esipy warnings
import warnings
import logging
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.ERROR)


from data.definitions import ROOT_DIR




# #######################################
# ESI Client
cache = FileCache(path=os.path.join(ROOT_DIR, 'cache/esipy_swagger'))
esi_app = EsiApp(cache=cache, cache_time=60 * 60 * 24)
app = esi_app.get_latest_swagger

client = EsiClient(
    retry_requests=True,  # set to retry on http 5xx error (default False)
    headers={'User-Agent': 'Something CCP can use to contact you and that define your app'},
    raw_body_only=True,
    # default False, set to True to never parse response and only return raw JSON string content.
)


'''
    A victim or attacker is refered to as an entity. The entity dictionary contains
        killmail['victim'] = { 
            character_id: xxxxxxx,
            corporation_id: xxxxxxx,
            alliance_id: xxxxxxxx,
            ...
        }
    These get functions extract fields and return the desired value.
    If the key does not exist, return 0 (invalid type id)
'''
def get_character(entity):
    try:
        return entity['character_id']
    except KeyError:
        return 0

def get_corporation(entity):
    try:
        return entity['corporation_id']
    except KeyError:
        return 0

def get_alliance(entity):
    try:
        return entity['alliance_id']
    except KeyError:
        return 0

'''
    Each of these getters extracts all of the desired IDs from a killmail and returns a list of character, corporation,
    or alliance IDs for lookup.
'''
def get_character_ids(killmail):
    return [get_character(killmail['victim'])] + [get_character(x) for x in killmail['attackers']]

def get_corporation_ids(killmail):
    return [get_corporation(killmail['victim'])] + [get_corporation(x) for x in killmail['attackers']]

def get_alliance_ids(killmail):
    return [get_alliance(killmail['victim'])] + [get_alliance(x) for x in killmail['attackers']]



'''
    Bulk lookup of either characters, corporations, or alliances. 
    Each function accepts a list of IDs.
    Returns { id: 'name' }
'''
def bulk_character_lookup(character_list):
    characters = {}
    if len(character_list) == 0:
        return
    print(f'Bulk lookup {len(character_list)} characters...')
    operations = []
    for id in character_list:
        if id == 0:
            continue
        operations.append(
            app.op['get_characters_character_id'](
                character_id=id
            )
        )
    results = client.multi_request(operations)
    for result in results:
        character_id = int(result[0]._p['path']['character_id'])
        data = json.loads(result[1].raw)
        characters[character_id] = data['name']
    return characters

def bulk_corp_lookup(corp_list):
    corporations = {}
    if len(corp_list) == 0:
        return
    print(f'Bulk lookup {len(corp_list)} corporations...')
    operations = []
    for id in corp_list:
        if id == 0:
            continue
        operations.append(
            app.op['get_corporations_corporation_id'](
                corporation_id=id
            )
        )
    results = client.multi_request(operations)
    for result in results:
        corp_id = int(result[0]._p['path']['corporation_id'])
        data = json.loads(result[1].raw)
        corporations[corp_id] = data['name']
    return corporations

def bulk_alliance_lookup(alliance_list):
    alliances = {}
    print(f'Bulk lookup {len(alliance_list)} alliances...')

    operations = []
    for id in alliance_list:
        if id == 0:
            continue
        operations.append(
            app.op['get_alliances_alliance_id'](
                alliance_id=id
            )
        )
    results = client.multi_request(operations)
    for result in results:
        alliance_id = int(result[0]._p['path']['alliance_id'])
        data = json.loads(result[1].raw)
        alliances[alliance_id] = data['name']
    return alliances



'''
    Make all required operations for characters, corporations, and alliances    
'''
def make_character_operations(character_ids):
    if len(character_ids) == 0:
        return
    operations = []
    for id in character_ids:
        if id == 0:
            continue
        operations.append(
            app.op['get_characters_character_id'](
                character_id=id
            )
        )
    return operations

def make_corporation_operations(corporation_ids):
    if len(corporation_ids) == 0:
        return
    operations = []
    for id in corporation_ids:
        if id == 0:
            continue
        operations.append(
            app.op['get_corporations_corporation_id'](
                corporation_id=id
            )
        )
    return operations

def make_alliance_operations(alliance_ids):
    operations = []
    for id in alliance_ids:
        if id == 0:
            continue
        operations.append(
            app.op['get_alliances_alliance_id'](
                alliance_id=id
            )
        )
    return operations

'''
    Do a bulk lookup of all character, corporation, and alliance ids in the lists.
    Returns {
        'character_ids': { character_id: 'name' },
        'corporation_ids': { corporation_id: 'name' },
        'alliance_ids': { alliance_id: 'name' }
    }

'''
def bulk_lookup_names(character_ids, corporation_ids, alliance_ids):
    names = {
        'character_ids': {},
        'corporation_ids': {},
        'alliance_ids': {}
    }

    operations = make_character_operations(character_ids) \
                 + make_corporation_operations(corporation_ids) \
                 + make_alliance_operations(alliance_ids)

    results = client.multi_request(operations)

    for result in results:
        if 'character_id' in result[0]._p['path']:
            character_id = int(result[0]._p['path']['character_id'])
            data = json.loads(result[1].raw)
            names['character_ids'][character_id] = data['name']
        elif 'corporation_id' in result[0]._p['path']:
            corporation_id = int(result[0]._p['path']['corporation_id'])
            data = json.loads(result[1].raw)
            names['corporation_ids'][corporation_id] = data['name']
        elif 'alliance_id' in result[0]._p['path']:
            alliance_id = int(result[0]._p['path']['alliance_id'])
            data = json.loads(result[1].raw)
            names['alliance_ids'][alliance_id] = data['name']

    # Add empty strings for invalid id 0
    names['character_ids'][0] = ''
    names['corporation_ids'][0] = ''
    names['alliance_ids'][0] = ''
    return names


'''
    Do a bulk lookup of all character, corporation, and alliances in a killmail
    Returns {
        'character_ids': { character_id: 'name' },
        'corporation_ids': { corporation_id: 'name' },
        'alliance_ids': { alliance_id: 'name' }
    }
'''

def get_names_for_killmail(killmail):
    character_ids = get_character_ids(killmail)
    corporation_ids = get_corporation_ids(killmail)
    alliance_ids = get_alliance_ids(killmail)
    return bulk_lookup_names(character_ids, corporation_ids, alliance_ids)



if __name__ == '__main__':
    character = [95631841]
    corporation = [98366055]
    alliance = [99004357]

    print('\nCharacters: ')
    print(bulk_character_lookup(character))
    print('\nCorporations: ')
    print(bulk_corp_lookup(corporation))
    print('\nAlliance: ')
    print(bulk_alliance_lookup(alliance))

    print('\nBulk')
    d = bulk_lookup_names(character, corporation, alliance)
    print(d)

