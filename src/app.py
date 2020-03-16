
import os
import re
import json
import time
import atexit

import requests as rq

from flask import Flask, request, redirect, render_template, send_from_directory
from flask_table import Table, Col
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .conf.general_conf import REDIRECT_DATA, REFRESH_SECONDS


container = {
    'data': [],
}


def update_redirect_data(container):
    """
    """
    t = time.strftime("%Y-%m-%d %I:%M:%S %p")
    print('{}: Updating redirect data'.format(t))
    li_data = load_redirect_data()
    container['data'] = li_data


scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=update_redirect_data,
    args=[container],
    trigger=IntervalTrigger(seconds=REFRESH_SECONDS),
    id='update-redirect-data',
    name='Reload redirect data every {} seconds'.format(REFRESH_SECONDS),
    replace_existing=True)

atexit.register(lambda: scheduler.shutdown())


app = Flask(__name__, template_folder='templates')
app.config['DEBUG'] = True


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def get_dir(path):
    """
    """
    print('path = {}'.format(path))

    if path == 'favicon.ico':
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico',
                                   mimetype='image/vnd.microsoft.icon')

    li_data = container['data']

    if path == 'info':
        data = {}
        # data['data'] = json.dumps(li_data, indent=4)
        data['table'] = build_table(li_data)
        data['sources'] = REDIRECT_DATA
        data['refresh_seconds'] = REFRESH_SECONDS
        return render_template('main.tpl.html', data=data)

    url = get_url(path, li_data)
    print('redirect url = {}'.format(url))

    return redirect(url, code=301)


def build_table(li_data):
    """
    """

    def link(source):
        short_name = '/'.join(source.split('/')[-3:])
        return '<a href="{}">{}</a>'.format(source, short_name)

    class Item:
        def __init__(self, idx, path, redirect, source):
            self.idx = idx
            self.path = path
            self.redirect = redirect
            self.source = link(source)

    class RawCol(Col):
        def td_format(self, content):
            return content.replace("u'", "").replace("'", "")

    class ItemTable(Table):
        classes = ['table',
                   'table-striped',
                   #    'table-sm'
                   ]
        idx = Col('#')
        path = Col('Regex Pattern')
        redirect = Col('Replacement')
        source = RawCol('Source')

    items = [Item(k+1, e['pattern'], e['repl'], e['source'])
             for k, e in enumerate(li_data)]

    table = ItemTable(items)
    return table


def get_url(path, li_data):
    """
    find first pattern in li_data matching path and determine corresponding url
    if none match, returns /info
    """
    for e in li_data:
        pattern = e['pattern']
        repl = e['repl']
        if re.compile(pattern).match(path):
            s = re.sub(pattern, repl, path)
            return s

    return '/info'


def load_redirect_data():
    """
    load redirect data from files online
    """
    li_data = []

    for url in REDIRECT_DATA:
        r = rq.get(url)
        data = r.content.decode('utf-8')
        li = json.loads(data)
        for e in li:
            e['source'] = url
        li_data += li

    # print(json.dumps(li_data, indent=4))
    return li_data


update_redirect_data(container)
print(json.dumps(container['data'], indent=4))
