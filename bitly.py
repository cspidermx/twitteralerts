import requests
import urllib3
import os


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
access_token_bitly = os.environ['access_token_bitly']


def shorten(uri):
    query_params = {
        'access_token': access_token_bitly,
        'longUrl': uri
    }

    endpoint = 'https://api-ssl.bitly.com/v3/shorten'
    response = requests.get(endpoint, params=query_params, verify=False)

    data = response.json()

    if not data['status_code'] == 200:
        print("Unexpected status_code: {} in bitly response. {}".format(data['status_code'], response.text))
        return uri

    return data['data']['url']


def expand(uri):
    query_params = {
        'access_token': access_token_bitly,
        'shortUrl': uri
    }

    endpoint = 'https://api-ssl.bitly.com/v3/expand'
    response = requests.get(endpoint, params=query_params, verify=False)

    data = response.json()

    if not data['status_code'] == 200:
        print("Unexpected status_code: {} in bitly response. {}".format(data['status_code'], response.text))
        return uri

    return data['data']['expand'][0]['long_url']

