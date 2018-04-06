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
        CREATE TABLE IF NOT EXISTS market (
            tid INTEGER,
            datestamp STRING,
            resource STRING,
            quantity INTEGER,
            price INTEGER,
            seller STRING,
            PRIMARY KEY (tid, datestamp)
        );
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS market_datestamp_idx on market (datestamp);')
    c.execute('CREATE INDEX IF NOT EXISTS market_resource_idx on market (resource);')
    c.execute('CREATE INDEX IF NOT EXISTS market_quantity_idx on market (quantity);')
    c.execute('CREATE INDEX IF NOT EXISTS market_price_idx on market (price);')
    c.execute('DELETE FROM market WHERE datestamp=date("now");')
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
msgs['crystals'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"premium"})
msgs['platinum'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"platinum"})
msgs['food'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"food"})
msgs['wood'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"wood"})
msgs['iron'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"iron"})
msgs['stone'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"stone"})
msgs['crafting materials'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"weapon_scraps"})
msgs['gem fragments'] = json.dumps({"type":"page","page":"market","market_type":"currency","page_num":"%%","q":None,"ll":None,"hl":None,"st":"gem_fragments"})
msgs['ingredients'] = json.dumps({"type":"page","page":"market","market_type":"ingredient","page_num":"%%","q":0,"ll":0,"hl":0,"st":"all"})

resources = dict()

battles = 0
for event in ws:
    #print(event)
    try:
        if isinstance(event, events.Ready):
            print("Requesting crystals (page 0)")
            ws.send_text(msgs['crystals'].replace('"%%"', '0'))

        if isinstance(event, events.Text):
            j = json.loads(event.text)[0]
            if 'type' in j:
                if (j['type'] == 'page') and (j['page'] == 'market'):
                    rec = j['result']
                    pageno = rec['page']
                    resource = rec['cn'].lower()
                    print("Processing {} (page {})".format(resource, pageno))
                    if resource not in resources:
                        resources[resource] = dict()
                    assert len(rec['l']) > 0
                    for l in rec['l']:
                        resources[resource][l['tid']] = l
                    sleep(1)
                    if len(resources[resource]) == rec['t']:
                        #trigger next resource
                        pageno = 0
                        if resource == 'crystals':
                            print("Requesting platinum (page {})".format(pageno))
                            ws.send_text(msgs['platinum'].replace('"%%"', str(pageno)))
                        elif resource == 'platinum':
                            print("Requesting food (page {})".format(pageno))
                            ws.send_text(msgs['food'].replace('"%%"', str(pageno)))
                        elif resource == 'food':
                            print("Requesting wood (page {})".format(pageno))
                            ws.send_text(msgs['wood'].replace('"%%"', str(pageno)))
                        elif resource == 'wood':
                            print("Requesting iron (page {})".format(pageno))
                            ws.send_text(msgs['iron'].replace('"%%"', str(pageno)))
                        elif resource == 'iron':
                            print("Requesting stone (page {})".format(pageno))
                            ws.send_text(msgs['stone'].replace('"%%"', str(pageno)))
                        elif resource == 'stone':
                            print("Requesting crafting materials (page {})".format(pageno))
                            ws.send_text(msgs['crafting materials'].replace('"%%"', str(pageno)))
                        elif resource == 'crafting materials':
                            print("Requesting gem fragments (page {})".format(pageno))
                            ws.send_text(msgs['gem fragments'].replace('"%%"', str(pageno)))
                        elif resource == 'gem fragments':
                            print("Requesting ingredients (page {})".format(pageno))
                            ws.send_text(msgs['ingredients'].replace('"%%"', str(pageno)))
                        elif resource == 'ingredients':
                            print("DONE")
                            ws.close()
                    else:
                        #fetch next page
                        pageno += 1
                        print("Requesting {} (page {})".format(resource, pageno))
                        ws.send_text(msgs[resource].replace('"%%"', str(pageno)))

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        ws.close()

print("Data fetched")

# Store it
c = conn.cursor()
try:
    for resource in resources.keys():
        for rec in resources[resource].values():
            c.execute("INSERT INTO market (tid, datestamp, resource, quantity, price, seller) VALUES (?, date('now'), ?, ?, ?, ?)", (rec['tid'], rec['n'], rec['v'], rec['price'], rec['seller']))

    #convert singular to plural
    pairs = [
        ('aberration mind source', 'aberration mind sources'),
        ('animal eye', 'animal eyes'),
        ('animal tooth', 'animal teeth'),
        ('animal tongue', 'animal tongues'),
        ('animal wing', 'animal wings'),
        ('beast fur', 'beast furs'),
        ('beast limb', 'beast limbs'),
        ('beast tooth', 'beast teeth'),
        ('beast wing', 'beast wings'),
        ('bird nest', 'bird nests'),
        ('bone shard', 'bone shards'),
        ('chunk of coal', 'chunks of coal'),
        ('chunk of graphite', 'chunks of graphite'),
        ('construct power', 'construct powers'),
        ('copper ore', 'copper ores'),
        ('crystal', 'crystals'),
        ('dragon eye', 'dragon eyes'),
        ('dragon scale', 'dragon scales'),
        ('dragon tail', 'dragon tails'),
        ('fish fin', 'fish fins'),
        ('golden apple', 'golden apples'),
        ('honeycomb', 'honeycombs'),
        ('humanoid bone', 'humanoid bones'),
        ('humanoid flesh', 'humanoid fleshes'),
        ('humanoid limb', 'humanoid limbs'),
        ('lucky coin', 'lucky coins'),
        ('magical stone', 'magical stones'),
        ('octopus ink', 'octopus inks'),
        ('ooze gel', 'ooze gels'),
        ('plant branch', 'plant branches'),
        ('plant root', 'plant roots'),
        ('plant vine', 'plant vines'),
        ('protection stone', 'protection stones'),
        ('rainbow shard', 'rainbow shards'),
        ('rune stone', 'rune stones'),
        ('serpent eye', 'serpent eyes'),
        ('serpent tail', 'serpent tails'),
        ('serpent tongue', 'serpent tongues'),
        ('squid tentacle', 'squid tentacles'),
        ('turtle shell', 'turtle shells'),
        ('vermin eye', 'vermin eyes'),
        ('vermin tooth', 'vermin teeth'),
        ('yellow pollen', 'yellow pollens')
    ]
    for pair in pairs:
        c.execute("UPDATE market SET resource=? WHERE resource=?", (pair[1], pair[0]))

except Exception as e:
    conn.rollback()
    c.close()
    conn.close()
    raise RuntimeError("An error occured while storing fetched data: {}".format(repr(e)))
conn.commit()
c.close()
print("Data stored")
conn.close()

