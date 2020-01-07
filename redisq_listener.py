import os
import data.definitions as data_def


data_def.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

import click
import requests
import time
import json
import zmq
from tools import lookup_esi_names
from tools.redisq_cache import RedisqCache, RedisqCacheException

from esipy import EsiApp
from esipy.cache import FileCache
from esipy import EsiClient


from data.eve_type_ids import REGION_VENAL



# ###################################################################################################
# Main class
class ZKBRedisQError(Exception):
    '''Raise whenever ZKillRedisQ encounters invalid data in kms'''

class ZKBRedisQ(object):
    def __init__(self, session_id='KM52APP84'):
        self.session_id = session_id
        self.short_fail_count = 0
        self.long_fail_count = 0
        self.very_long_fail_count = 0
        self.cache_killmails = RedisqCache()
        self.create_zmq_server()

    '''
        Setup a ZMQ server using the Publisher / Subscriber model
    '''
    def create_zmq_server(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind('tcp://*:7272')
        self.zmq_topic = 'zkb'

    '''
        Fetch the next killmail from zkillboard's RedisQ server.
        The request will block up to 10 seconds and either return a killmail or 'None' if no killmail occurred in the
        last 10 seconds.
        Return is the killmail JSON, which is removed from the RedisQ 'package' container.
        The ESI hash of the killmail will be added to each killmail using the key 'hash'. This is the only modification
        that is made to JSON received from zkillboard RedisQ
    '''
    def get_next_redisq(self, session_id='KM52APP84'):
        target_url = f'https://redisq.zkillboard.com/listen.php?queueID={session_id}'
        try:
            resp = requests.get(target_url, timeout=30.0)
            if resp.status_code != 200:
                raise ZKBRedisQError(f'Status code not 200 for {target_url}')
        except requests.exceptions.Timeout:
            raise ZKBRedisQError(f'Request timed out for {target_url}')
        except requests.exceptions.RequestException as e:
            raise ZKBRedisQError(f'Error fetching from redisq: [{e}]')
        data = resp.json()
        try:
            # Put the ESI hash into the actual killmail, and return only the killmail
            # No killmail will return None
            try:
                data['package']['killmail']['hash'] = data['package']['zkb']['hash']
            except (KeyError, TypeError):
                return None
            return data['package']['killmail']
        except KeyError:
            raise ZKBRedisQError(f'Killmail for {target_url} does not contain package! {data}')


    '''
        Main loop: 
            Fetch killmails
            Use ESI to lookup all character, corporation, and alliance IDs
            Save the killmail to sqlite
            Broadcast to ZMQ subscribers a dictionary containing the killmail and a dictionary of names
    '''
    def main_loop(self):
        print('--- Redisq Listener running ---')
        # Main loop
        while True:
            try:
                killmail = self.get_next_redisq()
            except ZKBRedisQError as e:
                self.short_fail_count += 1  # A short term failure has occured
                if self.short_fail_count < 3:
                    # If we haven't had too many short terms, wait a few seconds and try again
                    print(f'   xxx Short term failure {self.short_fail_count}, sleeping 5 seconds... [{e}]')
                    time.sleep(1.0 * 5.0)  # 5 seconds
                    print(f'   xxx ...done sleeping.')
                    continue
                elif self.long_fail_count < 3:
                    # If we have had too many short terms but not a lot of long terms, wait a longer amount of time
                    self.short_fail_count = 0  # Reset short term fail count
                    self.long_fail_count += 1  # We are having one more long term wait
                    print(f'   xxx Long term failure {self.long_fail_count}, sleeping 60 seconds... [{e}]')
                    time.sleep(1.0 * 60.0)  # 1 minute
                    print(f'   xxx ...done sleeping.')
                    continue
                else:
                    # We have had too many short and long term errors, wait avery long time.
                    short_fail_count = 0  # Reset the short
                    long_fail_count = 0  # Reset the long
                    self.very_long_fail_count += 1  # Increment our very long fail counter
                    print(f'   xxx Very long term failure {self.very_long_fail_count}, sleeping 5 minutes... [{e}]')
                    time.sleep(1.0 * 60.0 * 5.0)  # 5 minutes
                    print(f'   xxx ...done sleeping.')
                    continue

            # No message received in 10 seconds, fetch again.
            if killmail == None:
                continue

            # json_response is successful, test for needed variables
            try:
                kill_id = killmail['killmail_id']
            except KeyError:
                print(f'Key error in json: [{killmail}]')
                continue
            except TypeError:
                print('Empty message...')
                continue

            # Convert the killmail to a string
            killmail_string = json.dumps(killmail)

            # Cache the json in sqlite
            try:
                self.cache_killmails.insert_killmail(kill_id, killmail_string)
            except RedisqCacheException as e:
                print(f'   xxx sqlite error inserting killmail [{e}] - [{killmail_string}]')

            # Generate the ZMQ message containing the killmail and a names dictionary
            data = {
                'killmail': killmail,
                'names': lookup_esi_names.get_names_for_killmail(killmail)
            }

            # Broadcast the kill
            try:
                self.socket.send_string(f'{self.zmq_topic} {json.dumps(data)}')
            except zmq.ZMQError as e:
                print(f'   xxx When broadcasting {kill_id} got exception [{e}]')

            # Message to console
            print(f'Broadcasting {kill_id}')


    """"
        Simulate a stream of incoming killmails to test ZMQ subscribers
    """
    def test_data_replay(self, killmails, delay=1.0):
        for killmail in killmails:
            killmail_id = killmail['killmail_id']
            print(f'Broadcasting {killmail_id}')
            data = {
                'killmail': killmail,
                'names': lookup_esi_names.get_names_for_killmail(killmail)
            }
            try:
                # print(f'{self.zmq_topic} {json.dumps(data)}')
                self.socket.send_string(f'{self.zmq_topic} {json.dumps(data)}')
            except zmq.ZMQError as e:
                print(f'   xxx When broadcasting {killmail_id} got exception [{e}]')
            except json.JSONDecodeError as e:
                print(f'   xxx Error decoding JSON [{e}] [{killmail}')
            time.sleep(delay)


# ######################################################################################################
# Utility functions

def cache_save_zkb_region(region_id, killmails):
    with open(f'cache/zkb_regions/{region_id}.json', 'w') as fp:
        fp.write(json.dumps(killmails))

def cache_load_zkb_region(region_id):
    with open(f'cache/zkb_regions/{region_id}.json', 'r') as fp:
        return json.loads(fp.read())

def cache_save_esi_region(region_id, killmails):
    with open(f'cache/esi_regions/{region_id}.json', 'w') as fp:
        fp.write(json.dumps(killmails))

def cache_load_esi_region(region_id):
    with open(f'cache/esi_regions/{region_id}.json', 'r') as fp:
        return json.loads(fp.read())

def download_from_zkillboard(region_id, num_pages):
    killmails = []

    for page in range(1, num_pages + 1):
        url = f'https://zkillboard.com/api/kills/regionID/{region_id}/page/{page}/'
        print(f'Downloading {url}')
        r = requests.get(url)
        killmails += json.loads(r.content)
        time.sleep(1)
    return killmails

def download_from_esi(killmails):
    cache = FileCache(path=os.path.join(ROOT_DIR, 'cache/esipy_swagger'))
    esi_app = EsiApp(cache=cache, cache_time=60 * 60 * 24)
    app = esi_app.get_latest_swagger

    client = EsiClient(
        retry_requests=True,  # set to retry on http 5xx error (default False)
        headers={'User-Agent': 'Something CCP can use to contact you and that define your app'},
        raw_body_only=True,
        # default False, set to True to never parse response and only return raw JSON string content.
    )

    operations = []
    for killmail in killmails:
        operations.append(
            app.op['get_killmails_killmail_id_killmail_hash'](
                killmail_hash=killmail['zkb']['hash'],
                killmail_id=killmail['killmail_id']
            )
        )
    results = client.multi_request(operations)

    full_killmails = []
    for result in results:
        full_killmails.append(json.loads(result[1].raw))

    return full_killmails



# ######################################################################################################
# Entry point

@click.command()
@click.option('--loaddata', 'mode', flag_value='loaddata', help='Load replay test data from zkillboard')
@click.option('--replay', 'mode', flag_value='replay', help='Replay test data from zkillboard')
def startup(mode):
    if mode == 'loaddata':
        print('Downloading test data from zkillboard...')
        zkillboard_killmails = download_from_zkillboard(REGION_VENAL, 25)
        print('...finished downloading.')
        cache_save_zkb_region(REGION_VENAL, zkillboard_killmails)
        print('Downloading ESI killmails...')
        esi_killmails = download_from_esi(zkillboard_killmails)
        print('...finished downloading.')
        cache_save_esi_region(REGION_VENAL, esi_killmails)
        print('\n\nDone, data ready for replay.')
    elif mode == 'replay':
        print('Starting in replay mode...\n\n')
        test_killmails = cache_load_esi_region(REGION_VENAL)
        test_killmails.reverse()
        redisq_listener = ZKBRedisQ()
        redisq_listener.test_data_replay(test_killmails)
    else:
        print('Starting in normal mode...\n\n')
        redisq_listener = ZKBRedisQ()
        redisq_listener.create_zmq_server()
        redisq_listener.main_loop()

    print('...exiting.')

if __name__ == "__main__":
    startup()


