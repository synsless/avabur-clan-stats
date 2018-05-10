#!/usr/local/bin/python3

import json
import sqlite3
import csv
import os
import math

def buildData(dates, deltas):
    ret = []
    for i in range(len(deltas)):
        if len(dates) > len(deltas):
            ret.append((dates[i+1], deltas[i]))
        else:
            ret.append((dates[i], deltas[i]))
    return ret

def percentileIdx(n, percent):
    if not n:
        return None
    idx = int(round(percent * n + 0.5))
    return idx-1
    # k = (n-1) * percent
    # f = math.floor(k)
    # c = math.ceil(k)
    # if f == c:
    #     return (int(k), 1.0)
    # d0 = c-k
    # d1 = k-f
    # return ((int(f), d0), (int(c), d1))

def idx2val(lst, target):
    idx = target
    for rec in lst:
        if rec[1] < idx:
            idx -= rec[1]
            continue
        else:
            return rec[0]

#Load settings
with open('/home/protected/avabur/settings.json') as j:
    settings = json.load(j)

#Load/Initialize database
try:
    conn = sqlite3.connect(settings['dbfile'])
except sqlite3.DatabaseError as e:
    raise sqlite3.DatabaseError(repr(e))
c = conn.cursor()

#Get list of resources
c.execute("SELECT DISTINCT(resource) FROM market")
resources = [x[0] for x in c.fetchall()]
data = dict()
data['_going'] = dict()
for r in resources:
    c.execute("SELECT DISTINCT(datestamp) FROM market WHERE resource=? ORDER BY datestamp", (r,))
    dates = [x[0] for x in c.fetchall()]
    node = list()
    for d in dates:
        c.execute("SELECT price, quantity FROM market WHERE resource=? AND datestamp=? ORDER BY price", (r, d))
        recs = c.fetchall()

        #total inventory
        count = sum([x[1] for x in recs])
        #total value
        value = sum([x[0] * x[1] for x in recs])
        #arithmetic mean
        mean = value / count
        #minimum price (assumes sorted list)
        minprice = recs[0][0]

        #percentiles
        p10idx = percentileIdx(count, 0.1)
        p10 = idx2val(recs, p10idx)
        p50idx = percentileIdx(count, 0.5)
        p50 = idx2val(recs, p50idx)
        p90idx = percentileIdx(count, 0.9)
        p90 = idx2val(recs, p90idx)

        entry = {'date': d, 'inventory': count, 'minprice': minprice, 'mean': mean, 'p10': p10, 'p50': p50, 'p90': p90}
        node.append(entry)
    p10data = sorted([x['p10'] for x in node])
    p50ofp10idx = percentileIdx(len(p10data), 0.5)
    p50ofp10 = p10data[p50ofp10idx]
    data['_going'][r] = p50ofp10
    data[r] = node

#Get list of distinct dates
c.execute("SELECT DISTINCT(datestamp) FROM market ORDER BY datestamp")
data['_dates'] = [x[0] for x in c.fetchall()]

c.close()
conn.close()

#produce the JSON
with open(os.path.join(settings['marketdir'], 'market.json'), 'w', newline='') as outfile:
    json.dump(data, outfile)



