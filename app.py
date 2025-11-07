from flask import Flask, render_template, request, make_response, g
from redis import Redis
import os
import socket
import random
import json
import logging

option_a = os.getenv('OPTION_A', "Cats")
option_b = os.getenv('OPTION_B', "Dogs")
hostname = socket.gethostname()

app = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

def get_redis():
    if not hasattr(g, 'redis'):
        # Allow configuring Redis host/port via environment for local dev
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        g.redis = Redis(host=redis_host, port=redis_port, db=0, socket_timeout=5)
    return g.redis

@app.route("/", methods=['POST','GET'])
def hello():
    voter_id = request.cookies.get('voter_id')
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]

    vote = None

    if request.method == 'POST':
        redis = get_redis()
        vote = request.form['vote']
        app.logger.info('Received vote for %s', vote)
        data = json.dumps({'voter_id': voter_id, 'vote': vote})
        try:
            redis.rpush('votes', data)
        except Exception:
            # Don't crash the app if Redis is not available in local dev.
            app.logger.exception('Failed to push vote to Redis; continuing without persisting vote')

    resp = make_response(render_template(
        'index.html',
        option_a=option_a,
        option_b=option_b,
        hostname=hostname,
        vote=vote,
    ))
    resp.set_cookie('voter_id', voter_id)
    return resp


if __name__ == "__main__":
    # Use PORT env var when provided (useful for local dev / containers). Default to 5000
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
