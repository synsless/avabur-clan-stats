#!/usr/local/bin/python3

import requests
import json
import re
import sqlite3

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
			crystals INTEGER,
			platinum INTEGER,
			gold INTEGER,
			food INTEGER,
			wood INTEGER,
			iron INTEGER,
			stone INTEGER
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
except Exception as e:
	conn.rollback()
	c.close()
	conn.close()
	raise RuntimeError(repr(e))
conn.commit()
c.close()

#Authenticate
r = s.post('https://avabur.com/login.php', data={"info": "acctname={}&password={}".format(settings['username'], settings['password'])});
try:
	login = r.json()
	assert "s" in login
	assert "m" in login
except:
	raise RuntimeError("Could not understand server response to login attempt. Aborting.")
if login['s'] == 0:
	raise RuntimeError("Authentication failed: {}".format(login['m']))
print("Login successful")

# Get clan profile
r = s.post('https://avabur.com/clan_view.php', data={"mine": "1"});
clan = r.json()

# Get treasury info
r = s.post('https://avabur.com/clan_treasury.php', data={"clan": clan['id']});
treas = r.json()

# Get membership list
r = s.post('https://avabur.com/clan_members.php', data={"clan": clan['id']});
members = r.json()

# Get donations
r = s.post('https://avabur.com/clan_donations.php', data={"clan": clan['id']});
donations = r.json()
for k in donations:
	for resource in ('experiences', 'crystals', 'food', 'iron', 'stone', 'wood', 'gold', 'platinum'):
		if resource not in donations[k]:
			donations[k][resource] = 0

# Get individual user profiles
## Raw
profiles_raw = dict()
for member in members['members']:
	r = s.post('https://avabur.com/profile.php', data={"username": member['username']});
	profiles_raw[member['username']] = r.text

## Processed
profiles = dict()
res = [
	('level', re.compile('>Level:\s+</td><td>([,\d]+)')),
	('fishing', re.compile('Fishing Level:\s+</td><td>([,\d]+)')),
	('woodcutting', re.compile('Woodcutting Level:\s+</td><td>([,\d]+)')),
	('mining', re.compile('Mining Level:\s+</td><td>([,\d]+)')),
	('stonecutting', re.compile('Stonecutting Level:\s+</td><td>([,\d]+)')),
	('crafting', re.compile('Crafting Level:\s+</td><td>([,\d]+)')),
	('carving', re.compile('Carving Level:\s+</td><td>([,\d]+)')),
	('stats', re.compile('Base Stats:\s+</td><td>([,\d]+)')),
	('kills', re.compile('Kills:\s+</td><td>([,\d]+)')),
	('deaths', re.compile('Deaths:\s+</td><td>([,\d]+)')),
	('harvests', re.compile('Total Harvests:\s+</td><td>([,\d]+)')),
	('resources', re.compile('Total Resources Gained:\s+</td><td>([,\d]+)')),
	('crafting_acts', re.compile('Crafting Actions:\s+</td><td>([,\d]+)')),
	('carving_acts', re.compile('Carving Actions:\s+</td><td>([,\d]+)')),
	('quests', re.compile('Total Quests Completed:\s+</td><td>([,\d]+)')),
]
for key in profiles_raw:
	profiles[key] = dict()
	for regex in res:
		m = regex[1].search(profiles_raw[key])
		if m == None:
			raise RuntimeError("Could not extract data from a user profile: {}, {}".format(key, regex[0]))
		profiles[key][regex[0]] = int(m.group(1).replace(',',''))
print("Data fetched")

# Store it
c = conn.cursor()
try:
	#clan
	c.execute("REPLACE INTO clan (datestamp, xp, crystals, platinum, gold, food, wood, iron, stone) VALUES (date('now'), ?, ?, ?, ?, ?, ?, ?, ?)", (clan['experience'], treas['crystals'], treas['platinum'], treas['gold'], treas['food'], treas['wood'], treas['iron'], treas['stone']))
	#members
	for member in members['members']:
		k = member['username']
		totalacts = profiles[k]['kills'] + profiles[k]['deaths'] + profiles[k]['harvests'] + profiles[k]['crafting_acts'] + profiles[k]['carving_acts']
		c.execute("REPLACE INTO members (userid, datestamp, username, level, fishing, woodcutting, mining, stonecutting, crafting, carving, stats, kills, deaths, harvests, resources, craftingacts, carvingacts, quests, totalacts, lastactive, d_crystals, d_platinum, d_gold, d_food, d_wood, d_iron, d_stone, d_xp) VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (int(member['userid']), k, profiles[k]['level'], profiles[k]['fishing'], profiles[k]['woodcutting'], profiles[k]['mining'], profiles[k]['stonecutting'], profiles[k]['crafting'], profiles[k]['carving'], profiles[k]['stats'], profiles[k]['kills'], profiles[k]['deaths'], profiles[k]['harvests'], profiles[k]['resources'], profiles[k]['crafting_acts'], profiles[k]['carving_acts'], profiles[k]['quests'], totalacts, int(member['active_time']), donations[k]['crystals'], donations[k]['platinum'], donations[k]['gold'], donations[k]['food'], donations[k]['wood'], donations[k]['iron'], donations[k]['stone'], donations[k]['experiences']))
except Exception as e:
	conn.rollback()
	c.close()
	conn.close()
	raise RuntimeError("An error occured while storing fetched data: {}".format(repr(e)))
conn.commit()
c.close()
print("Data stored")
conn.close()

