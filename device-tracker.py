#!/usr/bin/python3

import sys, http.client, json, re;

guidPats = {
    'and':
    re.compile(r'^android-[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$'), 
    'win': re.compile(r'^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$'),
    'iOS': re.compile(r'^[A-F0-9]{8}(-[A-F0-9]{4}){3}-[A-F0-9]{12}$'),
    'web': re.compile(r'^[a-f0-9]{32}$'),
    'text': re.compile(r'^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}-0$')
}

devNames = {'and': 'Android', 'win': 'Windows App', 'iOS': 'iOS',
        'web': 'Website', 'text': 'Texting', 'un': 'Unknown'}

def getDevice(sourceGUID):
    for (name, pat) in guidPats.items():
        if pat.match(sourceGUID):
            return name
    sys.stderr.write('Unknown GUID: "' + sourceGUID + '"\n')
    return 'un'

def createUser(userid, name):
    user = {'name': name, 'userid': userid, 'total': 0, 'devs': {}}
    for d in devNames.keys():
        user['devs'][d] = 0
    return user


sys.stdout.write('Input access token: ')
token = input()

headers = {'X-Access-Token': token, 'User-Agent': 'gm-device-tracker', 
        'Accept': '*/*'}
conn = http.client.HTTPSConnection('api.groupme.com')

page = 1
more = True
groups = []
while more:
    conn.request('GET', '/v3/groups?page=%d' % page, None, headers)
    data = json.loads(conn.getresponse().read().decode('utf-8'))
    if data['meta']['code'] != 200:
        sys.stderr.write('Error with reading request: \n')
        for s in data['meta']['errors']:
            sys.stderr.write('  ' + s + '\n')
        sys.exit(1)
    resp = data['response']
    if len(resp) == 0:
        more = False
    else:
        for gr in resp:
            groups += [{'id': gr['id'], 'name': gr['name']}]
        page += 1
    conn.close()


print('Choose the groups to analyze: (Separate indexes by a comma).')
for i in range(len(groups)):
    gr = groups[i]
    print('%3d - %s (%s)' % (i, gr['name'], gr['id']))
selected = [groups[int(n)] for n in re.split(r'\s*,\s*',input())]

users = {}
for gr in selected:
    more = True
    before = ''
    count = 1
    read = 0
    while read < count:
        conn.request('GET', '/v3/groups/%s/messages?limit=100&before_id=%s' %
                (gr['id'], before), None, headers)
        data = json.loads(conn.getresponse().read().decode('utf-8'))
        code = data['meta']['code']
        if code == 200: # Okay status
            msgs = data['response']['messages']
            count = int(data['response']['count'])
            for m in msgs:
                sender = m['sender_id']
                if not sender in users:
                    users[sender] = createUser(sender, m['name'])
                dev = getDevice(m['source_guid'])
                users[sender]['devs'][dev] += 1
                users[sender]['total'] += 1
                before = m['id']
                read += 1
                sys.stdout.write('\rRead %d of %d messages from group %s' % 
                        (read, count, gr['name']))
                sys.stdout.flush()
        else:
            sys.stderr.write('Error with reading request: \n')
            for s in data.meta.code.errors:
                sys.stderr.write('  ' + s + '\n')
            sys.exit(1)
    print('')

devs = list(devNames.keys())
devs.sort();

print('Device user statistics:')

rows = [['Name', 'User ID'] + [devNames[d] for d in devs] + ['Total']]
for user in sorted(users.values(), key=lambda x: x['name']):
    rows += [[user['name'], user['userid']] + [str(user['devs'][d]) for d in devs] + \
        [str(user['total'])]]

maxWidths = [0 for h in rows[0]]
for row in rows:
    for i in range(len(maxWidths)):
        maxWidths[i] = max(maxWidths[i], len(row[i]))

sys.stdout.write('\n')
first = True
for row in rows:
    for i in range(len(maxWidths)):
         sys.stdout.write(row[i].ljust(maxWidths[i]) + ' | ')
    sys.stdout.write('\n')
    if first:
        first = False
        print('*' * (sum(maxWidths) + len(maxWidths) * 3  ))

