import json
import time

import keyboard
import requests

with open("event_apps.txt", "r") as file:
    event_apps = list(map(lambda x: int(x.strip()), file.readlines()))
with open("event_demos.txt", "r") as file:
    event_demos = list(map(lambda x: int(x.strip()), file.readlines()))
with open('event.json', 'r') as file:
    event_dict = json.load(file, object_hook=(lambda x: {int(k): v for k, v in x.items()}))


def try_all(in_file):
    with open(in_file, "r") as file:
        lines = file.readlines()
        demos = [list(map(lambda y: y.strip(), lines[x:x + 30])) for x in range(0, len(lines), 30)]

    time.sleep(1)
    for i, batch in enumerate(demos[::-1]):
        print(f"{i}/{len(demos) - 1}")
        add_game(batch)


def type_txt(txt, delay):
    keyboard.write(txt, delay=0)
    keyboard.press('Enter')
    time.sleep(delay)
    keyboard.write('clear')
    keyboard.press('Enter')


def add_game(appid):
    if isinstance(appid, int):
        type_txt(f'addlicense ASF a/{appid}', .5)
        type_txt(f'play ASF {appid}', .5)
    else:
        type_txt(f'addlicense ASF a/{", a/".join(appid)}', 2)
        type_txt(f'play ASF {",".join(appid)}', 2)
    type_txt(f'reset ASF', 1)


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
            print(req)
            return demo_appid
    return False


def add_demo(appid):
    event_demos.append(appid)
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
        time.sleep(2)
        try_all('appids.txt')
    #    loop(900)
    except KeyboardInterrupt:
        exit(0)
