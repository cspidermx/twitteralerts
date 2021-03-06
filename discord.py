import requests
import urllib3
import re
from bitly import expand  # shorten
from cc import to_gif
import os
import ntpath
import time


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
retry_429 = 0


def getlinks(texto):
    return re.findall("(?P<url>https?://[^\s]+)", texto)


def gethashtags(texto):
    return {tag for tag in texto.split() if tag.startswith("#")}


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def cleanfiles(filedict):
    for f in filedict:
        fname = filedict[f].name
        filedict[f].close()
        retry = True
        while retry:
            try:
                os.remove(fname)
            except PermissionError:
                retry = True
            else:
                retry = False


def dopost(hook, txt, file):
    global retry_429
    if bool(file):
        resp = requests.post(hook, files=file, data=txt)
    else:
        resp = requests.post(hook, data=txt)

    if resp.status_code != 200 and resp.status_code != 204:
        if resp.status_code == 429 and retry_429 <= 2:
            print("429 Header: {}", resp.headers)
            print("429 Text: {}", resp.text)
            print("429 JSON: {}", resp.json())
            retry_429 += 1
            time.sleep(30)
            dopost(hook, txt, file)
        else:
            print("Error en post del texto: {} <{}>".format(resp.status_code, resp.reason))
    retry_429 = 0
    return resp


def discpost(st, webhookurl, media, everyone):
    # media = {'2': 'Images and GIFs', '1i': 'Images (but NOT Videos/GIFs)', '1g': 'Videos/GIFs (but NOT Images)',
    # '0': 'No Media'}
    msg = st['full_text']
    links = getlinks(msg)
    hashes = gethashtags(msg)
    for h in hashes:
        msg = msg.replace(h, "`" + h.strip("#") + "`")
    if 'entities' in st:
        ents = st['entities']
        if 'user_mentions' in ents:
            for entry in ents['user_mentions']:
                usrmention = "@" + entry['screen_name']
                usrlink = "https://twitter.com/" + entry['screen_name']
                msg = msg.replace(usrmention, "[{}](<{}>)".format(entry['name'], usrlink))
    links2 = []
    first = True
    for lnk in links:
        if 'entities' in st:
            if 'urls' in st['entities']:
                for ent in st['entities']['urls']:
                    if lnk == ent['url']:
                        links2.append({'org': ent['url'], 'ext': ent['expanded_url']})
                        # no_urls += 1
        if 'extended_entities' in st:
            if 'media' in st['extended_entities']:
                for ent in st['extended_entities']['media']:
                    if lnk == ent['url']:
                        if ent['type'] == 'video':
                            u = ent['video_info']['variants'][0]
                            links2.append({'org': ent['url'], 'ext': u['url'] + ".video"})
                        elif ent['type'] == 'animated_gif':
                            u = ent['video_info']['variants'][0]
                            links2.append({'org': ent['url'], 'ext': u['url']})
                        else:
                            links2.append({'org': ent['url'], 'ext': ent['media_url']})
                        first = False

    for lnk in links2:
        if str(lnk['ext']).find('mp4') != -1 or str(lnk['ext']).find('jpg') != -1 or str(lnk['ext']).find(
                'png') != -1 or str(lnk['ext']).find('.video') != -1:
            msg = msg.replace(lnk['org'], '')
            # msg = msg.replace(lnk['org'], shorten(lnk['ext']))
        else:
            newlnk = lnk['ext']
            if str(lnk['ext']).find('.ly') != -1:
                newlnk = expand(lnk['ext'])
            if str(newlnk).find('twitch') != 0 and not first and media != '0':
                msg = msg.replace(lnk['org'], '<' + newlnk + '>')
            else:
                msg = msg.replace(lnk['org'], newlnk)
                first = False

    if everyone:
        ev = '@everyone\n\n'
    else:
        ev = ''
    values = {"content": ev + msg}

    file = {}

    if media != '0':
        for lnk in links2:
            if str(lnk['ext']).find('mp4') != -1 or str(lnk['ext']).find('jpg') != -1 or str(lnk['ext']).find('png') != -1:
                if str(lnk['ext']).find('jpg') != -1 or str(lnk['ext']).find('png') != -1 or str(lnk['ext']).find(
                        '.video') != -1:
                    if (media == '2') or (media == '1i' and str(lnk['ext']).find('.video') == -1) or (
                            str(lnk['ext']).find('.video') != -1 and media == '1g'):
                        if str(lnk['ext']).find('.video') != -1:
                            url = lnk['ext'][:-6].split("?", 1)[0]
                        else:
                            url = lnk['ext']
                        http = urllib3.PoolManager()
                        r = http.request('GET', url, preload_content=False)
                        file_name = url.split('/')[-1]
                        f = open(file_name, "wb")
                        f.write(r.data)
                        f.close()
                        f = open(file_name, "rb")
                        file[path_leaf(f.name)] = f
                else:
                    if media == '2' or media == '1g':
                        fname = to_gif(lnk['ext'])
                        gif = open(fname, 'rb')
                        file[path_leaf(gif.name)] = gif

    response = dopost(webhookurl, values, file)
    cleanfiles(file)

    return response
