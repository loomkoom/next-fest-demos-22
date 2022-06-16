import json
import time

import requests
from steam.client import SteamClient
from steam.enums.common import EResult
from steam.enums.emsg import EMsg

client = SteamClient()
client.set_credential_location(".")


def save_config():
    with open('config.json', 'w') as file:
        json.dump(config, file)


def dump_event_dict():
    with open('event.json', 'w') as file:
        json.dump(event_dict, file)


@client.on('logged_on')
def logon():
    time.sleep(1)
    client.get_changes_since(change_number)
    print("Logged on as: ", client.user.name)
    print('--------------------------------------')


@client.on("connected")
def handle_connected():
    print("Connected to: ", client.current_server_addr)


@client.on("disconnected")
def handle_disconnect():
    print("Disconnected.")
    if client.relogin_available:
        print("Trying to reconnect...")
        client.reconnect(maxdelay=30, retry=3)


@client.on("reconnect")
def handle_reconnect(delay):
    print(f"Reconnect in {delay} ...")


@client.on("channel_secured")
def send_login():
    if client.relogin_available:
        client.relogin()


@client.on("error")
def handle_error(result):
    if result == EResult.InvalidPassword:
        config['login_key'] = ''
        save_config()
        client.login(username=username, password=password)
    print("error occurred: ", repr(result))


@client.on('auth_code_required')
def auth_code_prompt(is_2fa, mismatch):
    if is_2fa:
        code = input("Enter 2FA Code: ")
        client.login(two_factor_code=code, username=username, password=password)
    else:
        code = input("Enter Email Code: ")
        client.login(auth_code=code, username=username, password=password)


@client.on(EMsg.ClientNewLoginKey)
def loginkey(key):
    if key.body.login_key != config['login_key']:
        print(key.body.login_key)
        config['login_key'] = key.body.login_key
        save_config()


@client.on(EMsg.ClientPICSChangesSinceResponse)
def changes(resp):
    global change_number
    current_change = resp.body.current_change_number
    if current_change == change_number:
        time.sleep(5)
        client.get_changes_since(current_change)
    else:
        change_number = current_change
        app_changes = resp.body.app_changes
        if len(app_changes) > 0:
            print('--------------------------------------')
            print('since: ', resp.body.since_change_number)
            print('current: ', change_number)
            # print(app_changes)
            appids = [app.appid for app in app_changes]
            ret = client.get_product_info(apps=appids, auto_access_tokens=True)
            # print('\n',ret)
            for appid in appids:
                app = ret['apps'][appid]
                try:
                    parent = int(app['extended']['demoofappid'])
                    print(appid, app['common']['name'], parent)
                except KeyError:
                    continue

                if (parent in event_dict) and (appid not in event_demos):
                    add_demo(appid)
                    event_dict[parent] = appid
                    event_demos.add(appid)
                    dump_event_dict()
        config['change_number'] = change_number
        save_config()
        client.get_changes_since(current_change)


def add_game(appid):
    if not isinstance(appid, int):
        appids = list(map(int, appid))
    else:
        appids = [appid]
    client.request_free_license(appids)
    client.games_played(appids)
    print(client.current_games_played)
    time.sleep(2)
    print(client.current_games_played)


def add_demo(appid):
    with open('event_demos.txt', 'a', encoding='utf8') as file:
        file.write(f"{appid}\n")
    add_game(appid)
    print(f"New demo: {appid}, total is now: {len(event_demos)}")


def try_all(in_file):
    with open(in_file, "r") as file:
        lines = file.readlines()
        demos = [set(map(lambda y: y.strip(), lines[x:x + 30])) for x in range(0, len(lines), 30)]

    time.sleep(1)
    for i, batch in enumerate(demos[::-1]):
        print(f"{i}/{len(demos) - 1}")
        add_game(batch)


def check_event(parent_app):
    with requests.session() as session:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Dnt': '1',
            'Sec-Gpc': '1',
            'Upgrade-Insecure-Requests': '1',
            'referer': 'https://store.steampowered.com/sale/nextfest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.136 Safari/537.36'
        }
        req = session.get(f'https://store.steampowered.com/saleaction/ajaxgetdemoevents?appids[]={parent_app}',
                          headers=headers).json()
        time.sleep(.25)
        if not req['success']:
            print('error on ', parent_app)
        elif len(req.keys()) > 1 and req['info'][0]['demo_appid'] != 0:
            demo_appid = req['info'][0]['demo_appid']
            event_dict[parent_app] = demo_appid
            if demo_appid not in event_demos:
                event_demos.add(demo_appid)
                print(req)
                return demo_appid
        return False


def populate_dict():
    total = len(event_apps)
    missing = len(tuple(filter(lambda app: app not in event_dict or event_dict[app] == 0, event_apps)))
    known = len(tuple(filter(lambda x: x != 0, event_dict.values())))
    print(f'total apps: {total}\n'
          f'missing demos: {missing}\n'
          f'known demos: {known}')
    unknown = filter(lambda app: app not in event_dict or event_dict[app] == 0, event_apps)
    for i, app in enumerate(unknown):
        print(f" {i}/{missing - 1}", end='\r')
        if app not in event_dict or event_dict[app] == 0:
            event_dict[app] = 0
            demo = check_event(app)
            if demo:
                add_demo(demo)

    dump_event_dict()


if __name__ == '__main__':
    try:
        with open("event_apps.txt", "r") as file:
            event_apps = set(map(lambda x: int(x.strip()), file.readlines()))
        with open('event.json', 'r') as file:
            event_dict = json.load(file, object_hook=(lambda x: {int(k): v for k, v in x.items()}))
        if len(event_apps) != event_dict.keys():
            event_dict.update({app: 0 for app in set(event_dict.keys()).symmetric_difference(event_apps)})
            event_demos = set(filter(lambda y: y != 0, event_dict.values()))
            populate_dict()
            dump_event_dict()
        event_demos = set(filter(lambda y: y != 0, event_dict.values()))

        print(f"total apps: {len(event_dict)}\n"
              f"total demos: {len(event_demos)}")

        with open('config.json', 'r') as file:
            config = json.load(file)
        change_number = config['change_number']
        login_key = config['login_key']
        username = config['username']
        password = config['password']
        if client.relogin_available:
            client.relogin()
        else:
            client.login(username=username, password=password, login_key=login_key)
        client.run_forever()

        # try_all('event_demos.txt')
    except KeyboardInterrupt:
        if client.connected:
            client.logout()
        exit(0)
