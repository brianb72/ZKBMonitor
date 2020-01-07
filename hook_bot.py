'''
    Create a Discord Hook Bot
    Subscribe to ZMQ server
    Parse killmails and broadcast to Discord channel
'''

from discord import Webhook, RequestsWebhookAdapter
import zmq
import json
from tools.lookup_eve_static_dump import LookupEveStaticDump, LookupEveStaticDumpException

from dateutil.parser import parse as dateutil_parser
from datetime import datetime, timedelta
import pytz

from data.eve_type_ids import WATCH_REGIONS, HOME_SYSTEM_ID


# Discord Secrets
# Generate an ID / Token here: http://discordapp.com/developers/applications/me
# Place your values in these two variables

discord_webhook_id = 123456789  # <-- change to your id
discord_webhook_token = '---> put your token here <---'


# Eve static lookup
lookup = LookupEveStaticDump()

# Start the webhook bot
webhook = Webhook.partial(discord_webhook_id, discord_webhook_token, adapter=RequestsWebhookAdapter())
webhook.send('Now Online')
print('Hookbot online')

# Start the message queue and subscribe to the 'zkb' topic
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:7272")
socket.setsockopt_string(zmq.SUBSCRIBE, 'zkb')

'''
    Extract specified id from a killmail entity
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
    Extract specified id from killmail entity and returns the string name
'''
def get_character_name(entity, names):
    try:
        return names['character_ids'][get_character(entity)]
    except KeyError:
        return ''


def get_corporation_name(entity, names):
    try:
        return names['corporation_ids'][get_corporation(entity)]
    except KeyError:
        return ''


def get_alliance_name(entity, names):
    try:
        return names['alliance_ids'][get_alliance(entity)]
    except KeyError:
        return ''

'''
    The json module loads integer dictionary keys as strings.
    { 10000: 'foo' } becomes { '10000': 'foo' }
    Convert the string keys in a dictionary to integer keys.
'''
def dict_string_keys_to_int(d):
    return {int(k):v for k,v in d.items()}


########################
# Main loop

while True:
    # Receive json_killmails from the message queue, discard the topic
    raw_message = socket.recv_string()
    topic, data = raw_message.split(' ', 1)


    # Convert the json, if invalid discard this killmail
    try:
        message_dict = json.loads(data)

    except json.decoder.JSONDecodeError as e:
        print(f'JSON error for killmail - [{e}]')
        continue

    # Extract the data we received from the server
    killmail = message_dict['killmail']

    region_id = lookup.get_solarsystem_region(killmail['solar_system_id'])
    if region_id not in WATCH_REGIONS:
        continue


    # Time
    killmail_time = dateutil_parser(killmail['killmail_time'])
    oldest_date = datetime.now() - timedelta(minutes=45)
    oldest_date = pytz.utc.localize(oldest_date)
    if killmail_time < oldest_date:
        print(f'Too old {killmail_time} < {oldest_date}')
        continue
    time_string = f'{killmail_time.year}-{killmail_time.month:02}-{killmail_time.day:02} {killmail_time.hour:02}:{killmail_time.minute:02}'

    names = message_dict['names']
    names['character_ids'] = dict_string_keys_to_int(names['character_ids'])
    names['corporation_ids'] = dict_string_keys_to_int(names['corporation_ids'])
    names['alliance_ids'] = dict_string_keys_to_int(names['alliance_ids'])

    # Eve static data dump lookups
    killmail_id = killmail['killmail_id']
    solar_system_id = killmail['solar_system_id']
    solar_system_name = lookup.get_solarsystem_name(solar_system_id)
    region_name = lookup.get_region_name(region_id)
    ship_name = lookup.get_type_name(killmail['victim']['ship_type_id'])


    # Victim
    victim_name = get_character_name(killmail['victim'], names)
    victim_alliance = get_alliance_name(killmail['victim'], names)
    victim_corporation = get_corporation_name(killmail['victim'], names)
    if get_alliance(killmail['victim']) != 0:
        victim_str = f'{victim_alliance:.30} | {victim_corporation:.30} | {victim_name}'
    elif get_corporation(killmail['victim']) != 0:
        victim_str = f'{victim_corporation:.30} | {victim_name}'
    else:
        victim_str = f'{victim_name}'

    # Attackers
    attacker_count = len(killmail['attackers'])
    alliance_ids = []
    corporation_ids = []

    # Get unique alliances and corporation ids in attackers
    for attacker in killmail['attackers']:
        alliance_id = get_alliance(attacker)
        if alliance_id != 0:
            alliance_ids.append(alliance_id)
        else:
            corporation_id = get_corporation(attacker)
            if corporation_id != 0:
                corporation_ids.append(corporation_id)

    # Lookup the names and create name strings
    alliance_names = []
    corporation_names = []
    for alliance_id in set(alliance_ids):
        if alliance_id == 0:
            continue
        try:
            alliance_names.append(names['alliance_ids'][alliance_id])
        except KeyError:
            alliance_names.append('[unknown alliance]')
    for corporation_id in set(corporation_ids):
        if corporation_id == 0:
            continue
        try:
            corporation_names.append(names['corporation_ids'][corporation_id])
        except KeyError:
            corporation_names.append('[unknown corporation]')

    alliance_str = ', '.join(alliance_names)
    corporation_str = ', '.join(corporation_names)
    faction_str = ''

    if len(alliance_names) > 0:
        alliance_str = f'Alliances: {alliance_str}'
        faction_str += alliance_str
    if len(corporation_str) > 0:
        corporation_str = f'Corporations: {corporation_str}'
        if len(faction_str) > 0:
            faction_str += ' | '
        faction_str += corporation_str

    try:
        route = lookup.find_route(HOME_SYSTEM_ID, solar_system_id)
        jumps_from_home = len(route)
    except LookupEveStaticDumpException as e:
        print(f'error finding route between {HOME_SYSTEM_ID} and {solar_system_id} - [{e}]')
        jumps_from_home = -1

    msg = (f'{killmail_id} [{time_string} / {region_name} / {solar_system_name} / {jumps_from_home} jumps]   '
            f'[{victim_str} - {ship_name:.20}]  -  '
            f'[Attackers: {attacker_count}    '
            f'{faction_str}]')


    webhook.send(msg)
    print(msg)