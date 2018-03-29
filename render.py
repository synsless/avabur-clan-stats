#!/usr/local/bin/python3

import json
import sqlite3
import csv
import os
import math

def calcDeltas(lst):
    if lst == None:
        return None
    elif len(lst) == 1:
        return [0]
    else:
        ret = []
        for i in range(1, len(lst)):
            ret.append(lst[i] - lst[i-1])
        assert len(ret) == len(lst)-1
        return ret

def buildData(dates, deltas):
    ret = []
    for i in range(len(deltas)):
        if len(dates) > len(deltas):
            ret.append((dates[i+1], deltas[i]))
        else:
            ret.append((dates[i], deltas[i]))
    return ret

def trimOutliers(lst, percent, ceil=True):
    lst = sorted(lst)
    count = len(lst) * percent
    if ceil:
        count = math.ceil(count)
    else:
        count = math.floor(count)
    if (count*2 >= len(lst)):
        return(lst)
    else:
        return lst[count:len(lst)-count]

def calcMedian(lst):
    lst = sorted(lst)
    if (len(lst) % 2 == 1):
        return lst[(len(lst)-1)//2]
    else:
        val1 = lst[int(math.floor((len(lst)-1)/2))]
        val2 = lst[int(math.ceil((len(lst)-1)/2))]
        return (val1 + val2) / 2

#Load settings
with open('/home/protected/avabur/settings.json') as j:
    settings = json.load(j)

#Load/Initialize database
try:
    conn = sqlite3.connect(settings['dbfile'])
except sqlite3.DatabaseError as e:
    raise sqlite3.DatabaseError(repr(e))
c = conn.cursor()

#xp gained
c.execute("SELECT datestamp, xp FROM clan ORDER BY datestamp")
recs = c.fetchall()
dates = [x[0] for x in recs]
xps = [x[1] for x in recs]
xpdeltas = calcDeltas(xps)

## Try to trim really wide swings
for i in range(len(xpdeltas)):
    if xpdeltas[i] < 0:
        xpdeltas[i] = None

xpdata = buildData(dates, xpdeltas)
with open(os.path.join(settings['csvdir'], 'clan_xp.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Date", "Experience Gain"])
    for row in xpdata:
        csvw.writerow(row)

#total actions
c.execute("SELECT datestamp, sum(totalacts), count() FROM members GROUP BY datestamp ORDER BY datestamp")
recs = c.fetchall()
dates = [x[0] for x in recs]
totals = [x[1] for x in recs]
counts = [x[2] for x in recs]
deltas = calcDeltas(totals)
avgs = [round(deltas[i] / counts[i]) for i in range(len(deltas))]

## Try to trim really wide swings
actions_total_whatiswide = 500000
actions_average_whatiswide = 50000
if 'actions_total_whatiswide' in settings:
    actions_total_whatiswide = settings['actions_total_whatiswide']
if 'actions_average_whatiswide' in settings:
    actions_average_whatiswide = settings['actions_average_whatiswide']
dd = calcDeltas(deltas)
for i in range(len(dd)):
    if abs(dd[i]) > actions_total_whatiswide:
        deltas[i+1] = None
dd = calcDeltas(avgs)
for i in range(len(dd)):
    if abs(dd[i]) > actions_average_whatiswide:
        avgs[i+1] = None

totaldata = buildData(dates, deltas)
avgdata = buildData(dates, avgs)
with open(os.path.join(settings['csvdir'], 'clan_actions_total.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Date", "Total Actions"])
    for row in totaldata:
        csvw.writerow(row)
with open(os.path.join(settings['csvdir'], 'clan_actions_avg.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Date", "Average Actions"])
    for row in avgdata:
        csvw.writerow(row)

#aggregate donations (other than xp)
c.execute("SELECT datestamp, d_crystals, d_platinum, d_gold, d_food, d_wood, d_iron, d_stone FROM members GROUP BY datestamp ORDER BY datestamp")
recs = c.fetchall()
dates = [x[0] for x in recs]
plat = [x[2] for x in recs]
gold = [x[3] for x in recs]
plat = calcDeltas(plat)
gold = calcDeltas(gold)
platdata = buildData(dates, plat)
golddata = buildData(dates, gold)
with open(os.path.join(settings['csvdir'], 'clan_donations_plat.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Date", "Platinum"])
    for row in platdata:
        csvw.writerow(row)
with open(os.path.join(settings['csvdir'], 'clan_donations_gold.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Date", "Gold"])
    for row in golddata:
        csvw.writerow(row)

#per-user total actions
## First get maxdate
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]

## Get list of current members
c.execute("SELECT DISTINCT(username) FROM members WHERE datestamp=? ORDER BY username COLLATE NOCASE", [maxdate])
usernames = [x[0] for x in c.fetchall()]

## Get list of distinct dates
c.execute("SELECT DISTINCT(datestamp) FROM members ORDER BY datestamp")
alldates = [x[0] for x in c.fetchall()]
alldates.pop(0)

## Now get their total action data
rawdata = dict()
for u in usernames:
    rawdata[u] = list()
    for row in c.execute("SELECT datestamp, totalacts FROM members WHERE username=?", [u]):
        rawdata[u].append((row[0], row[1]))

## Now turn that into deltas for each user
deltadata = dict()
for u in usernames:
    dates = [x[0] for x in rawdata[u]]
    counts = [x[1] for x in rawdata[u]]
    deltas = calcDeltas(counts)
    deltadata[u] = buildData(dates, deltas)

## Now convert that into a format suitable for CSV output (rows are dates, users are columns)
## This uses a number nested loops. It's not the most efficient, but it's good enough.
csvout = []
csvout.append(['Date'] + usernames)
### This gives us the row structure
for d in alldates:
    row = [d]
    ### This loop ensures the correct order
    for u in usernames:
        ### Look at each delta entry for the given user and see if it matches the date.
        found = False
        for delta in deltadata[u]:
            if (delta[0] == d):
                found = True
                row.append(delta[1])
                break
        if not found:
            row.append(None)
    csvout.append(row)

## Print it!
with open(os.path.join(settings['csvdir'], 'individual_actions.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    for row in csvout:
        csvw.writerow(row)

#per-user base stats
## First get list of all users
c.execute("SELECT DISTINCT(username) FROM members ORDER BY username COLLATE NOCASE")
usernames = [x[0] for x in c.fetchall()]

## Get list of distinct dates
c.execute("SELECT DISTINCT(datestamp) FROM members ORDER BY datestamp")
alldates = [x[0] for x in c.fetchall()]

## Now get their total action data
rawdata = dict()
for u in usernames:
    rawdata[u] = list()
    for row in c.execute("SELECT datestamp, stats FROM members WHERE username=?", [u]):
        rawdata[u].append((row[0], row[1]))

## Now convert that into a format suitable for CSV output (rows are dates, users are columns)
## This uses a number nested loops. It's not the most efficient, but it's good enough.
csvout = []
csvout.append(['Date'] + usernames)
### This gives us the row structure
for d in alldates:
    row = [d]
    ### This loop ensures the correct order
    for u in usernames:
        ### Look at each delta entry for the given user and see if it matches the date.
        found = False
        for stat in rawdata[u]:
            if (stat[0] == d):
                found = True
                row.append(stat[1])
                break
        if not found:
            row.append(None)
    csvout.append(row)

## Print it!
with open(os.path.join(settings['csvdir'], 'individual_stats.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    for row in csvout:
        csvw.writerow(row)

#per-user xp donations
## Get latest date
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]

## Get list of all current members
c.execute("SELECT DISTINCT(username) FROM members WHERE datestamp=? ORDER BY username COLLATE NOCASE", [maxdate])
usernames = [x[0] for x in c.fetchall()]

## Get list of distinct dates
c.execute("SELECT DISTINCT(datestamp) FROM members ORDER BY datestamp")
alldates = [x[0] for x in c.fetchall()]
alldates.pop(0)

## Now get their xp donation data
rawdata = dict()
for u in usernames:
    rawdata[u] = list()
    for row in c.execute("SELECT datestamp, d_xp FROM members WHERE username=?", [u]):
        rawdata[u].append((row[0], row[1]))

## Now turn that into deltas for each user
deltadata = dict()
for u in usernames:
    dates = [x[0] for x in rawdata[u]]
    counts = [x[1] for x in rawdata[u]]
    deltas = calcDeltas(counts)
    deltadata[u] = buildData(dates, deltas)

## Now convert that into a format suitable for CSV output (rows are dates, users are columns)
## This uses a number nested loops. It's not the most efficient, but it's good enough.
csvout = []
csvout.append(['Date'] + usernames)
### This gives us the row structure
for d in alldates:
    row = [d]
    ### This loop ensures the correct order
    for u in usernames:
        ### Look at each delta entry for the given user and see if it matches the date.
        found = False
        for delta in deltadata[u]:
            if (delta[0] == d):
                found = True
                row.append(delta[1])
                break
        if not found:
            row.append(None)
    csvout.append(row)

## Print it!
with open(os.path.join(settings['csvdir'], 'individual_xpdonated.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    for row in csvout:
        csvw.writerow(row)

#per-user gold donations
## Get latest date
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]

## Get list of all current members
c.execute("SELECT DISTINCT(username) FROM members WHERE datestamp=? ORDER BY username COLLATE NOCASE", [maxdate])
usernames = [x[0] for x in c.fetchall()]

## Get list of distinct dates
c.execute("SELECT DISTINCT(datestamp) FROM members ORDER BY datestamp")
alldates = [x[0] for x in c.fetchall()]
alldates.pop(0)

## Now get their xp donation data
rawdata = dict()
for u in usernames:
    rawdata[u] = list()
    for row in c.execute("SELECT datestamp, d_gold FROM members WHERE username=?", [u]):
        rawdata[u].append((row[0], row[1]))

## Now turn that into deltas for each user
deltadata = dict()
for u in usernames:
    dates = [x[0] for x in rawdata[u]]
    counts = [x[1] for x in rawdata[u]]
    deltas = calcDeltas(counts)
    deltadata[u] = buildData(dates, deltas)

## Now convert that into a format suitable for CSV output (rows are dates, users are columns)
## This uses a number nested loops. It's not the most efficient, but it's good enough.
csvout = []
csvout.append(['Date'] + usernames)
### This gives us the row structure
for d in alldates:
    row = [d]
    ### This loop ensures the correct order
    for u in usernames:
        ### Look at each delta entry for the given user and see if it matches the date.
        found = False
        for delta in deltadata[u]:
            if (delta[0] == d):
                found = True
                row.append(delta[1])
                break
        if not found:
            row.append(None)
    csvout.append(row)

## Print it!
with open(os.path.join(settings['csvdir'], 'individual_golddonated.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    for row in csvout:
        csvw.writerow(row)

#per-user plat donations
## Get latest date
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]

## Get list of all current members
c.execute("SELECT DISTINCT(username) FROM members WHERE datestamp=? ORDER BY username COLLATE NOCASE", [maxdate])
usernames = [x[0] for x in c.fetchall()]

## Get list of distinct dates
c.execute("SELECT DISTINCT(datestamp) FROM members ORDER BY datestamp")
alldates = [x[0] for x in c.fetchall()]
alldates.pop(0)

## Now get their xp donation data
rawdata = dict()
for u in usernames:
    rawdata[u] = list()
    for row in c.execute("SELECT datestamp, d_platinum FROM members WHERE username=?", [u]):
        rawdata[u].append((row[0], row[1]))

## Now turn that into deltas for each user
deltadata = dict()
for u in usernames:
    dates = [x[0] for x in rawdata[u]]
    counts = [x[1] for x in rawdata[u]]
    deltas = calcDeltas(counts)
    deltadata[u] = buildData(dates, deltas)

## Now convert that into a format suitable for CSV output (rows are dates, users are columns)
## This uses a number nested loops. It's not the most efficient, but it's good enough.
csvout = []
csvout.append(['Date'] + usernames)
### This gives us the row structure
for d in alldates:
    row = [d]
    ### This loop ensures the correct order
    for u in usernames:
        ### Look at each delta entry for the given user and see if it matches the date.
        found = False
        for delta in deltadata[u]:
            if (delta[0] == d):
                found = True
                row.append(delta[1])
                break
        if not found:
            row.append(None)
    csvout.append(row)

## Print it!
with open(os.path.join(settings['csvdir'], 'individual_platdonated.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    for row in csvout:
        csvw.writerow(row)


#activity status
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]
c.execute("SELECT username, (STRFTIME('%s', 'now') - lastactive) AS inactive FROM members WHERE datestamp=? AND inactive>= 86400 ORDER BY inactive", [maxdate])
recs = c.fetchall()
recs = [(x[0], math.floor(x[1]/86400)) for x in recs]
with open(os.path.join(settings['csvdir'], 'individual_lastactive.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Member", "Time Inactive"])
    for row in recs:
        csvw.writerow(row)

#per-user average actions
## Get max date
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]

## Get list of current users
c.execute("SELECT DISTINCT(username) FROM members where datestamp=? ORDER BY username COLLATE NOCASE", [maxdate])
usernames = [x[0] for x in c.fetchall()]

## Now get their total action data
actions_outliers_percent = 0.1
if 'actions_outliers_percent' in settings:
    actions_outliers_percent = settings['actions_outliers_percent']
avgacts = list()
for u in usernames:
    totals = []
    for row in c.execute("SELECT totalacts FROM members WHERE username=? ORDER BY datestamp", [u]):
        totals.append(row[0])
    deltas = calcDeltas(totals)
    deltas = trimOutliers(deltas, actions_outliers_percent)
    avg = round(sum(deltas) / len(deltas))
    avgacts.append((u, avg))

## sort by average
avgacts = sorted(avgacts, key=lambda x: x[1])

## Print it!
with open(os.path.join(settings['csvdir'], 'individual_avgacts.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Member","Average Actions"])
    for row in avgacts:
        csvw.writerow(row)

#per-user median actions
## Get max date
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]

## Get list of current users
c.execute("SELECT DISTINCT(username) FROM members where datestamp=? ORDER BY username COLLATE NOCASE", [maxdate])
usernames = [x[0] for x in c.fetchall()]

## Now get their total action data
medacts = list()
for u in usernames:
    totals = []
    for row in c.execute("SELECT totalacts FROM members WHERE username=? ORDER BY datestamp", [u]):
        totals.append(row[0])
    deltas = calcDeltas(totals)
    deltas = trimOutliers(deltas, actions_outliers_percent)
    median = round(calcMedian(deltas))
    medacts.append((u, median))

## sort by average
medacts = sorted(medacts, key=lambda x: x[1])

## Print it!
with open(os.path.join(settings['csvdir'], 'individual_medacts.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Member","Median Actions"])
    for row in medacts:
        csvw.writerow(row)

# Treasury status (single graph)
with open(os.path.join(settings['csvdir'], 'clan_treasury.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Date","Crystals", "Platinum", "Gold", "Food", "Wood", "Iron", "Stone"])
    for row in c.execute("SELECT datestamp, crystals, platinum, gold, food, wood, iron, stone FROM clan ORDER BY datestamp"):
        csvw.writerow(row)

# Battler/harvest ratio
## Get max date
c.execute("SELECT MAX(datestamp) FROM members")
maxdate = c.fetchone()[0]

## Get list of current users
c.execute("SELECT DISTINCT(username) FROM members where datestamp=? ORDER BY username COLLATE NOCASE", [maxdate])
usernames = [x[0] for x in c.fetchall()]

## Get battle/harvest data
treedata = list()
for row in c.execute("SELECT username, ((max(kills)-min(kills))+(max(deaths)-min(deaths))) AS battles, ( (max(harvests)-min(harvests))+(max(craftingacts)-min(craftingacts))+(max(carvingacts)-min(carvingacts))) FROM members GROUP BY username"):
    if row[0] in usernames:
        total = row[1] + row[2]
        ratio = 0
        if (total > 0):
            ratio = round(row[1] / total, 2)
        treedata.append((row[0], ratio))
treedata = sorted(treedata, key=lambda x: (x[1], x[0].lower()))

with open(os.path.join(settings['csvdir'], 'individual_ratios.csv'), 'w', newline='') as csvfile:
    csvw = csv.writer(csvfile, dialect=csv.excel)
    csvw.writerow(["Member", "Ratio"])
    for row in treedata:
        csvw.writerow(row)

#Rankings table
ranks = {'data': []}
for row in c.execute("SELECT username, skill, rank, level FROM ranks WHERE rank<=100"):
    ranks['data'].append(row)
with open(os.path.join(settings['csvdir'], 'ranks.json'), 'w', newline='') as csvfile:
    json.dump(ranks, csvfile)

c.close()
conn.close()

