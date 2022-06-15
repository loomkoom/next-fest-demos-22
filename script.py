import json
import time

import requests
from steam.client import SteamClient
from steam.enums.emsg import EMsg

client = SteamClient()


@client.on('logged_on')
def logon():
    time.sleep(1)
    client.get_changes_since(changenumber)
    print("Logged on as: ", client.user.name)


@client.on(EMsg.ClientNewLoginKey)
def loginkey(key):
    print(key.body.login_key)
    with open('key.txt', 'w') as keyfile:
        keyfile.write(key.body.login_key)


@client.on(EMsg.ClientPICSChangesSinceResponse)
def changes(x):
    global changenumber
    if x.body.current_change_number - changenumber > 0:
        changenumber = x.body.current_change_number
        if len(x.body.app_changes) > 0:
            print('--------------------------------------')
            print('since: ', x.body.since_change_number)
            print('current: ', x.body.current_change_number)
            appids = [app.appid for app in x.body.app_changes]
            ret = client.get_product_info(apps=appids, auto_access_tokens=True)
            for appid in appids:
                app = ret['apps'][appid]
                if ('extended' in app.keys()) and ('demoofappid' in app['extended'].keys()):
                    parent = int(app['extended']['demoofappid'])
                    print(appid, app['common']['name'], parent)
                    if parent in event_dict.keys():
                        add_game(appid)
                        if appid not in event_demos:
                            add_demo(appid)
                            if check_event(parent):
                                event_dict[parent] = appid
        with open('changelist.txt', 'w') as file:
            file.write(str(changenumber))
    time.sleep(5)
    client.get_changes_since(x.body.current_change_number)


def try_all(in_file):
    with open(in_file, "r") as file:
        lines = file.readlines()
        demos = [list(map(lambda y: y.strip(), lines[x:x + 30])) for x in range(0, len(lines), 30)]

    time.sleep(1)
    for i, batch in enumerate(demos[::-1]):
        print(f"{i}/{len(demos) - 1}")
        add_game(batch)


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


def check_event(parent_app):
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
    req = requests.get(f'https://store.steampowered.com/saleaction/ajaxgetdemoevents?appids[]={parent_app}',
                       headers=headers).json()
    if not req['success']:
        print('error on ', parent_app)
    elif len(req.keys()) > 1 and req['info'][0]['demo_appid'] != 0:
        demo_appid = req['info'][0]['demo_appid']
        event_dict[parent_app] = demo_appid
        if demo_appid not in event_demos:
	    event_demos.append(appid)
            print(req)
            return demo_appid
    return False


def add_demo(appid):
    with open('event_demos.txt', 'a', encoding='utf8') as file:
        file.write(f"{appid}\n")
    add_game(appid)
    print(len(event_demos))


def loop(delay):
    total = len(event_apps)
    print(f'total apps: {total}\n'
          f'missing demos: {len(list(filter(lambda x: x == 0, event_dict.values())))}\n'
          f'known demos: {len(list(filter(lambda x: x != 0, event_dict.values())))}')
    while True:
        for i, app in enumerate(event_apps):
            print(f" {i}/{len(event_apps) - 1}", end='\r')
            if app not in event_dict or event_dict[app] == 0:
                event_dict[app] = 0
                demo = check_event(app)
                if demo:
                    add_demo(demo)

        with open('event.json', 'w') as file:
            json.dump(event_dict, file)
        print(f'rechecking in {delay // 60} min')
        time.sleep(delay)


if __name__ == '__main__':
    try:
        with open("event_apps.txt", "r") as file:
            event_apps = list(map(lambda x: int(x.strip()), file.readlines()))
        with open("event_demos.txt", "r") as file:
            event_demos = list(map(lambda x: int(x.strip()), file.readlines()))
        with open('event.json', 'r') as file:
            event_dict = json.load(file, object_hook=(lambda x: {int(k): v for k, v in x.items()}))
        changenumber = int(open('changelist.txt', 'r').read().strip())

        # try_all('event_demos.txt')
        steamkey = open('key.txt').read().strip()
        if steamkey:
            client.login(username='loomkoom', password='3XmUdrxPZkY5', login_key=steamkey)
        else:
           client.cli_login(username='loomkoom', password='3XmUdrxPZkY5')

        client.run_forever()
        # loop(900)
    except KeyboardInterrupt:
        if client.connected:
            client.logout()
        exit(0)
