#!/usr/local/bin/python3

import requests
import json
import re
import sqlite3
from lomond.websocket import WebSocket
from lomond.persist import persist
import lomond.events as events
from time import sleep

s = requests.Session()

#Load settings
with open('/home/protected/avabur/settings.json') as j:
    settings = json.load(j)

#Load/Initialize database
try:
    conn = sqlite3.connect(settings['dbfile'])
except sqlite3.DatabaseError as e:
    raise sqlite3.DatabaseError(repr(e))
c = conn.cursor()

try:
    c.execute('''
        CREATE TABLE IF NOT EXISTS clan (
            datestamp STRING PRIMARY KEY,
            xp INTEGER,
            level INTEGER,
            crystals INTEGER,
            platinum INTEGER,
            gold INTEGER,
            food INTEGER,
            wood INTEGER,
            iron INTEGER,
            stone INTEGER
        );
    ''')
    c.execute('''DROP TABLE ranks''')
    c.execute('''
        CREATE TABLE ranks (
            userid INTEGER,
            skill STRING,
            username STRING,
            level INTEGER,
            rank INTEGER,
            PRIMARY KEY (userid, skill)
        );
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            userid INTEGER,
            datestamp STRING,
            username STRING,
            level INTEGER,
            fishing INTEGER,
            woodcutting INTEGER,
            mining INTEGER,
            stonecutting INTEGER,
            crafting INTEGER,
            carving INTEGER,
            stats INTEGER,
            kills INTEGER,
            deaths INTEGER,
            harvests INTEGER,
            resources INTEGER,
            craftingacts INTEGER,
            carvingacts INTEGER,
            quests INTEGER,
            lastactive INTEGER,
            d_crystals INTEGER,
            d_platinum INTEGER,
            d_gold INTEGER,
            d_food INTEGER,
            d_wood INTEGER,
            d_iron INTEGER,
            d_stone INTEGER,
            d_xp INTEGER,
            totalacts INTEGER,
            PRIMARY KEY (userid, datestamp)
        );
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS nearestclans (
            datestamp STRING PRIMARY KEY,
            above REAL,
            ours REAL,
            below REAL
        );
    ''')
except Exception as e:
    conn.rollback()
    c.close()
    conn.close()
    raise RuntimeError(repr(e))
conn.commit()
c.close()

#Authenticate
r = s.post('https://avabur.com/login', data={"acctname": settings['username'], "password": settings['password']});
try:
    login = r.json()
    assert "s" in login
except:
    raise RuntimeError("Could not understand server response to login attempt. Aborting.")
if login['s'] == 0:
    raise RuntimeError("Authentication failed: {}".format(login['m']))
print("Login successful")

#Extract data from websockets for later processing
cdict = requests.utils.dict_from_cookiejar(s.cookies)
cookies = list()
for k in cdict:
    cookies.append('='.join([k,cdict[k]]))
cstr = ';'.join(cookies)

ws = WebSocket('wss://avabur.com/websocket')
ws.add_header('cookie'.encode('utf-8'), cstr.encode('utf-8'))

msgs = dict()
msgs['clan_profile'] = json.dumps({'start': 0, 'vm': 1, 'type': 'page', 'page': 'clans'})
msgs['clan_members'] = json.dumps({'clan': '%%', 'type': 'page', 'page': 'clan_members'})
msgs['clan_treasury'] = json.dumps({'clan': '%%', 'type': 'page', 'page': 'clan_treasury'})
msgs['clan_donations'] = json.dumps({'type': 'page', 'page': 'clan_donations'})
msgs['profile'] = json.dumps({'type': 'page', 'page': 'profile', 'username': '%%'})
msgs['allclans'] = json.dumps({"start":0,"type":"page","page":"clans"})

clan = None
treas = None
members = None
donations = None
profiles = dict()
otherclans = [None, None, None]

battles = 0
for event in ws:
    #print(event)
    try:
        if isinstance(event, events.Ready):
            print("Requesting clan profile")
            ws.send_text(msgs['clan_profile'])

        if isinstance(event, events.Text):
            j = json.loads(event.text)[0]
            if 'type' in j:
                if (j['type'] == 'page') and (j['page'] == 'clan_view'):
                    print("Processing clan profile")
                    clan = j['result']
                    sleep(1)
                    print("Requesting clan treasury")
                    ws.send_text(msgs['clan_treasury'].replace('%%', str(clan['id'])))

        if isinstance(event, events.Text):
            j = json.loads(event.text)[0]
            if 'type' in j:
                if (j['type'] == 'page') and (j['page'] == 'clan_treasury'):
                    print("Processing clan treasury")
                    treas = j['result']
                    sleep(1)
                    print("Requesting clan donations")
                    ws.send_text(msgs['clan_donations'])

        if isinstance(event, events.Text):
            j = json.loads(event.text)[0]
            if 'type' in j:
                if (j['type'] == 'page') and (j['page'] == 'clan_donations'):
                    print("Processing clan donations")
                    donations = j['results']
                    for k in donations:
                        for resource in ('experiences', 'crystals', 'food', 'iron', 'stone', 'wood', 'gold', 'platinum'):
                            if resource not in donations[k]:
                                donations[k][resource] = 0
                    sleep(1)
                    print("Requesting clan members")
                    ws.send_text(msgs['clan_members'].replace('%%', str(clan['id'])))

        if isinstance(event, events.Text):
            j = json.loads(event.text)[0]
            if 'type' in j:
                if (j['type'] == 'page') and (j['page'] == 'clan_members'):
                    print("Processing clan membership list")
                    members = json.loads(json.dumps(j))
                    for m in j['members']:
                        if int(m['rankid']) < 0:
                            continue
                        sleep(1)
                        print("Requesting profile for {}".format(m['username'].upper()))
                        ws.send_text(msgs['profile'].replace('%%', m['username']))

        if isinstance(event, events.Text):
            j = json.loads(event.text)[0]
            if 'type' in j:
                if (j['type'] == 'page') and (j['page'] == 'profile'):
                    rec = j['result']
                    print('Receiving profile for {}'.format(rec['username'].upper()))
                    node = dict()
                    node['level'] = rec['levels']['character']['level']
                    node['rank_level'] = rec['levels']['character']['rank']
                    node['fishing'] = rec['levels']['fishing']['level']
                    node['rank_fishing'] = rec['levels']['fishing']['rank']
                    node['woodcutting'] = rec['levels']['woodcutting']['level']
                    node['rank_woodcutting'] = rec['levels']['woodcutting']['rank']
                    node['mining'] = rec['levels']['mining']['level']
                    node['rank_mining'] = rec['levels']['mining']['rank']
                    node['stonecutting'] = rec['levels']['stonecutting']['level']
                    node['rank_stonecutting'] = rec['levels']['stonecutting']['rank']
                    node['crafting'] = rec['levels']['crafting']['level']
                    node['rank_crafting'] = rec['levels']['crafting']['rank']
                    node['carving'] = rec['levels']['carving']['level']
                    node['rank_carving'] = rec['levels']['carving']['rank']
                    node['house'] = rec['levels']['house']['level']
                    node['rank_house'] = rec['levels']['house']['rank']
                    node['stats'] = rec['stats']['base']['value']
                    node['rank_stats'] = rec['stats']['base']['rank']
                    node['kills'] = rec['battle']['kills']['value']
                    node['rank_kills'] = rec['battle']['kills']['rank']
                    node['deaths'] = rec['battle']['deaths']['value']
                    node['rank_deaths'] = rec['battle']['deaths']['rank']
                    node['harvests'] = rec['harvests']['harvests']['value']
                    node['rank_harvests'] = rec['harvests']['harvests']['rank']
                    node['resources'] = rec['harvests']['resources']['value']
                    node['rank_resources'] = rec['harvests']['resources']['rank']
                    node['crafting_acts'] = rec['profession']['crafts']['value']
                    node['rank_crafting_acts'] = rec['profession']['crafts']['rank']
                    node['carving_acts'] = rec['profession']['carves']['value']
                    node['rank_carving_acts'] = rec['profession']['carves']['rank']
                    node['quests'] = rec['quest']['total']['value']
                    node['rank_quests'] = rec['quest']['total']['rank']

                    profiles[rec['username']] = node

                    #check for termination
                    if len(profiles) == clan['members']:
                        sleep(1)
                        print('Getting level information on surrounding clans')
                        ws.send_text(msgs['allclans'])

        if isinstance(event, events.Text):
            j = json.loads(event.text)[0]
            if 'type' in j:
                if (j['type'] == 'page') and (j['page'] == 'clans'):
                    print("Processing surrounding clan levels")
                    r = j['result']
                    maxidx = r['ct']-1
                    idx = None
                    for i in range(len(r['cl'])):
                        if r['cl'][i]['id'] == r['c']['id']:
                            print("Found our clan at position {} in the list".format(i+1))
                            idx = i
                            break
                    otherclans[1] = r['cl'][idx]['level'] + (r['cl'][idx]['level_percent']/100)
                    if idx > 0:
                        otherclans[0] = r['cl'][idx-1]['level'] + (r['cl'][idx-1]['level_percent']/100)
                    if idx < maxidx:
                        otherclans[2] = r['cl'][idx+1]['level'] + (r['cl'][idx+1]['level_percent']/100)

                    ws.close()

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        ws.close()

print("Data fetched")

# Store it
c = conn.cursor()
try:
    #clan
    c.execute("REPLACE INTO clan (datestamp, xp, level, crystals, platinum, gold, food, wood, iron, stone) VALUES (date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)", (clan['experience'], clan['level'], treas['crystals'], treas['platinum'], treas['gold'], treas['food'], treas['wood'], treas['iron'], treas['stone']))
    #members
    for member in members['members']:
        if int(member['rankid']) >= 0:
            k = member['username']
            totalacts = profiles[k]['kills'] + profiles[k]['deaths'] + profiles[k]['harvests'] + profiles[k]['crafting_acts'] + profiles[k]['carving_acts']
            c.execute("REPLACE INTO members (userid, datestamp, username, level, fishing, woodcutting, mining, stonecutting, crafting, carving, stats, kills, deaths, harvests, resources, craftingacts, carvingacts, quests, totalacts, lastactive, d_crystals, d_platinum, d_gold, d_food, d_wood, d_iron, d_stone, d_xp) VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (int(member['userid']), k, profiles[k]['level'], profiles[k]['fishing'], profiles[k]['woodcutting'], profiles[k]['mining'], profiles[k]['stonecutting'], profiles[k]['crafting'], profiles[k]['carving'], profiles[k]['stats'], profiles[k]['kills'], profiles[k]['deaths'], profiles[k]['harvests'], profiles[k]['resources'], profiles[k]['crafting_acts'], profiles[k]['carving_acts'], profiles[k]['quests'], totalacts, int(member['active_time']), donations[k]['crystals'], donations[k]['platinum'], donations[k]['gold'], donations[k]['food'], donations[k]['wood'], donations[k]['iron'], donations[k]['stone'], donations[k]['experiences']))

    #ranks
    skills = [
        #(SKILL, RANK KEY, VALUE KEY)
        ('Character Level', 'rank_level', 'level'),
        ('Fishing', 'rank_fishing', 'fishing'),
        ('Woodcutting', 'rank_woodcutting', 'woodcutting'),
        ('Mining', 'rank_mining', 'mining'),
        ('Stonecutting', 'rank_stonecutting', 'stonecutting'),
        ('Crafting', 'rank_crafting', 'crafting'),
        ('Carving', 'rank_carving', 'carving'),
        ('House', 'rank_house', 'house'),
        ('Base Stats', 'rank_stats', 'stats'),
        ('Kills', 'rank_kills', 'kills'),
        ('Deaths', 'rank_deaths', 'deaths'),
        ('Harvests', 'rank_harvests', 'harvests'),
        ('Resources', 'rank_resources', 'resources'),
        ('Crafting Actions', 'rank_crafting_acts', 'crafting_acts'),
        ('Carving Actions', 'rank_carving_acts', 'carving_acts'),
        ('Quests', 'rank_quests', 'quests'),
    ]
    for member in members['members']:
        if int(member['rankid']) >= 0:
            k = member['username']
            for s in skills:
                c.execute("REPLACE INTO ranks (userid, username, skill, level, rank) VALUES (?, ?, ?, ?, ?)", (int(member['userid']), k, s[0], profiles[k][s[2]], profiles[k][s[1]]))

    #nearestclans
    c.execute("REPLACE INTO nearestclans (datestamp, above, ours, below) VALUES (date('now'), ?, ?, ?)", (otherclans[0], otherclans[1], otherclans[2]))

except Exception as e:
    conn.rollback()
    c.close()
    conn.close()
    raise RuntimeError("An error occured while storing fetched data: {}".format(repr(e)))
conn.commit()
c.close()
print("Data stored")
conn.close()

