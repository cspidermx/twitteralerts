import psycopg2
from TwitterAPI import TwitterAPI
from TwitterAPI import TwitterError
import time
from discord import discpost
import os
import datetime

consumer_key = os.environ['consumer_key']
consumer_secret = os.environ['consumer_secret']
access_token = os.environ['access_token']
access_token_secret = os.environ['access_token_secret']
DATABASE_URL = os.environ['DATABASE_URL']


def stop_daemon():
    conn = connectdb()
    cur = conn.cursor()
    cur.execute('SELECT stopped, in_use FROM service')
    sts = cur.fetchall()
    if len(sts) > 0:
        estado = sts[0][0]
    else:
        cur.execute("INSERT INTO service VALUES({},{})".format(False, False))
        conn.commit()
        estado = False
    cur.close()
    conn.close()

    return estado


def lock(cnctn, set_as):
    conn = cnctn
    while True:
        try:
            in_use = True
            sts = None
            cur = conn.cursor()
            while in_use:
                in_use = False
                cur.execute('SELECT * FROM service')
                sts = cur.fetchall()
                if len(sts) > 0:
                    if set_as:
                        in_use = sts[0][1]
            if len(sts) > 0:
                cur.execute("UPDATE service SET in_use={}".format(set_as))
                conn.commit()
            else:
                cur.execute("INSERT INTO service VALUES({},{})".format(False, set_as))
                conn.commit()
            cur.close()
            break
        except psycopg2.OperationalError:
            print('Se perdió la conexión con la base')
            conn = connectdb()


def connectdb():
    return psycopg2.connect(DATABASE_URL)


def dostuff():
    conn = connectdb()
    lock(conn, True)
    while True:
        try:
            cur = conn.cursor()
            cur.execute('SELECT id_user, handle, lookfor, discrobot, id FROM rules')
            rules = cur.fetchall()
            if len(rules) > 0:
                api = TwitterAPI(consumer_key,
                                 consumer_secret,
                                 auth_type='oAuth2')
            else:
                return

            i = 0
            for r in rules:
                rlid = r[4]
                cur.execute('SELECT * FROM since WHERE rule_id={}'.format(rlid))
                snce = cur.fetchall()
                if len(snce) == 0:
                    rules[i] += ('0',)
                else:
                    rules[i] += (snce[0][1],)
                i += 1
            break
        except psycopg2.OperationalError:
            print('Se perdió la conexión con la base')
            conn = connectdb()
    lock(conn, False)

    for r in rules:
        idusr = r[0]
        scnm = r[1]
        term = r[2]
        since = r[5]
        if since == '0':
            snc = '0'
            orgsnc = ''
            try:
                tl = api.request('statuses/user_timeline', {'screen_name': scnm,
                                                            'include_rts': False,
                                                            'trim_user': False,
                                                            'exclude_replies': True,
                                                            'tweet_mode': 'extended'})
            except TwitterError:
                print("Error en API Twitter: {}".format(TwitterError))
                print("ScreenName = {}, Since = {}".format(scnm, snc))
                return
        else:
            snc = since
            orgsnc = snc
            try:
                tl = api.request('statuses/user_timeline', {'screen_name': scnm,
                                                            'include_rts': False,
                                                            'trim_user': False,
                                                            'exclude_replies': True,
                                                            'since_id': snc,
                                                            'tweet_mode': 'extended'})
            except TwitterError:
                print("Error en API Twitter: {}".format(TwitterError))
                print("ScreenName = {}, Since = {}".format(scnm, snc))
                return
        # tl.status_code  # 200 OK ... # 429 '{"errors":[{"message":"Rate limit exceeded","code":88}]}'

        if tl.status_code != 200 and tl.status_code != 204:
            print("Error en API Twitter: {}  --  Razón: {}".format(tl.response, tl.response.reason))
            print("ScreenName = {}, Since = {}".format(scnm, snc))
            print(tl.response.status_code)
            return

        # Requests / 15-min window (app auth)  --  1500
        for post in tl:
            if int(post['id']) > int(snc):
                snc = post['id']
            do_post = False
            for t in str(term).split(','):
                t = t.strip()
                if t != '':
                    if not str(post['full_text']).find(t) == -1:
                        do_post = True
            if do_post:
                print('ID: ', post['id'])
                print('Created: ', post['created_at'])
                print('Text: ', post['full_text'])
                print('--------------------------------------------')
                if orgsnc != '':
                    discpost(post, r[3])  # r[3] contains the discord webhook URL
        if snc != '0':
            while True:
                try:
                    if r[5] == '0':
                        cur.execute("INSERT INTO since VALUES({},'{}')".format(r[4], snc))
                        conn.commit()
                    else:
                        if snc != orgsnc:
                            cur.execute("UPDATE since set idsince='{}' WHERE rule_id={}".format(snc, r[4]))
                            conn.commit()
                    break
                except psycopg2.OperationalError:
                    print('Se perdió la conexión con la base')
                    conn = connectdb()

    if conn is not None:
        cur.close()
        conn.close()
        # print('Database connection closed.')


vueltas = 1
while True:
    if not stop_daemon():
        start = datetime.datetime.now()
        dostuff()
        finish = datetime.datetime.now()
        print('{}.'.format(vueltas), start.strftime('%d\\%B\\%Y'),
              '\tSTART: {} -- END: {}'.format(start.strftime('%H:%M:%S'), finish.strftime('%H:%M:%S')))
        vueltas += 1
        if vueltas > 1440:
            vueltas = 1
        time.sleep(60)
    else:
        stop = datetime.datetime.now()
        print('Stopped: {}'.format(stop.strftime('%d\\%B\\%Y %H:%M:%S')))
        break
