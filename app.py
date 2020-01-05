from flask import Flask, jsonify
import os
import requests
import re
import boto3
import json

app = Flask(__name__)

token = os.environ.get('slack_token')
channel = os.environ.get('slack_channel')

headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
           "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
           "Connection": "keep-alive",
           "DNT": "1",
           "TE": "Trailers",
           "Upgrade-Insecure-Requests": "1",
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0"}
slack_cookies = {"b": os.environ.get('b'),
                 "d": os.environ.get('d'),
                 "d-s": os.environ.get('ds'),
                 "x": os.environ.get('x')}


@app.route('/')
def hello():
    return "Hello World!"


def get_ids():
    s3 = boto3.resource('s3')
    obj = s3.Object('lbc-store-ids', 'ids.json')
    body = obj.get()['Body'].read().decode('utf-8')
    return json.loads(body)


def write_ids(ids):
    s3 = boto3.resource('s3')
    obj = s3.Object('lbc-store-ids', 'ids.json')
    obj.put(Body=json.dumps(ids))


@app.route('/read_ids')
def read_ids():
    return "stored ids: {}".format(get_ids())


@app.route('/add/<name>/<text>/<category>', methods=['GET'])
def add_search(name, text, category):
    searches = get_ids()
    searches[name] = {'text_search': text,
                      'category_search': category, 'ids': []}
    write_ids(searches)
    return 'ok'


@app.route('/remove/<name>', methods=['GET'])
def remove_search(name):
    searches = get_ids()
    del searches[name]
    write_ids(searches)
    return 'ok'


@app.route('/check_search')
def check_search():
    message = ''
    all_ids = get_ids()
    for search_name, search in all_ids.items():
        seen_ids = set(search.get('ids', []))
        text_search = search['text_search']
        category_search = search['category_search']
        resp = requests.get("https://www.leboncoin.fr/recherche/?category={}&text={}&locations=d_75&price=min-40".format(
            category_search, text_search), headers=headers)

        ids = set(re.split('(\"list_id\"\:)([0-9]+)', resp.text)[2::3])

        new_ids = ids - seen_ids
        if len(new_ids) != 0:
            message += '\n- Le bon coin new ids for {}: {}'.format(
                search_name, new_ids)
            seen_ids |= ids
        all_ids[search_name]['ids'] = list(seen_ids)
    write_ids(all_ids)
    if message:
        requests.get(
            "https://slack.com/api/chat.postMessage?token={}&channel={}&text={}&pretty=1".format(
                token, channel, message),
            headers=headers, cookies=slack_cookies
        )
    return "{}".format(message)


if __name__ == '__main__':
    app.run()
