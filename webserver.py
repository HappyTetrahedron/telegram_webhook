from flask import Flask, Response
from flask import request, abort
from telegram.constants import ParseMode

app = Flask(__name__)

params = {}


def init(sendmessage, config):
    params['send'] = sendmessage
    params['config'] = config


def run():
    app.run(params['config']['host'], params['config']['port'])


@app.route("/send", methods=['POST'])
def forward_message():
    data = request.get_json(force=True)
    token = request.headers.get('Authorization', "").lower()
    parts = token.split()

    if len(parts) != 2 or parts[0] != "token" or parts[1] != params['config']['webhook_token']:
        return abort(403)

    message = {
        "message": data['message'],
        "parse_mode": ParseMode.HTML,
    }
    params['send'](message)
    resp = Response("")
    resp.headers['Connection'] = 'close'
    return resp
