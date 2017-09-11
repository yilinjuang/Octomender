import logging

from flask import Flask

app = Flask(__name__)
app.secret_key = <SECRET-KEY>
app.config['GITHUB_CLIENT_ID'] = <GITHUB-CLIENT-ID>
app.config['GITHUB_CLIENT_SECRET'] = <GITHUB-CLIENT-SECRET>
app.config['PROJECT_ID'] = <PROJECT-ID>

# Pass flask logs to gunicorn.
gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.DEBUG)

from app import views
