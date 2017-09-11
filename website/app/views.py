import datetime
import random

from flask import abort, g, jsonify, redirect, render_template, request, session, url_for
from flask_github import GitHub, GitHubError

from app import app
from .octomender import Octomender
from .model import Repo, User, UserModel

github = GitHub(app)
users = UserModel(app.config['PROJECT_ID'])

@github.access_token_getter
def token_getter():
    if g.uid:
        return users.get_token(g.uid)
    elif g.token:
        return g.token
    app.logger.warning('token_getter: failed')

@app.before_request
def before_request():
    g.uid = None
    g.token = None
    if 'uid' in session:
        g.uid = session['uid']

@app.route('/')
def index():
    id_card = {}
    action_card = {}
    suggest_card = {}
    star_card = {}
    if g.uid:
        raw_user = github_get('user')
        if raw_user is None:
            abort(500)
        user = User(raw_user)
        app.logger.debug(user.summarize())
        id_card['name'] = user.name
        id_card['avatar'] = user.avatar
        id_card['action_url'] = url_for('logout')
        id_card['action_name'] = 'Logout'

        if users.has_suggestion(g.uid):
            action_card['enabled'] = False
            suggest_card['display'] = True
        else:
            action_card['enabled'] = True
            suggest_card['display'] = False
        star_card['enabled'] = True
    else:
        id_card['name'] = 'Octomender'
        id_card['avatar'] = url_for('static', filename='img/octonaut.jpg')
        id_card['action_url'] = url_for('login')
        id_card['action_name'] = 'Login and Try Now'

    return render_template('index.html',
                            id_card=id_card,
                            action_card=action_card,
                            suggest_card=suggest_card,
                            star_card=star_card)

@app.route('/login')
def login():
    if g.uid:
        return redirect(url_for('index'))
    else:
        if 'X-Appengine-Country' in request.headers:
            session['country'] = request.headers['X-Appengine-Country']
        return github.authorize()

@app.route('/logout')
def logout():
    session.pop('uid', None)
    return redirect(url_for('index'))

@app.route('/callback')
@github.authorized_handler
def authorized(token):
    next_url = request.args.get('next') or url_for('index')
    if token is None:
        return redirect(next_url)

    g.token = token
    user = github_get('user')
    if user is None:
        abort(500)
    uid = user['id']
    users.add(uid, token)
    if 'country' in session:
        users.set_country(uid, session['country'])
    session['uid'] = uid

    return redirect(next_url)

@app.route('/star')
def star():
    if g.uid is None:
        return redirect(url_for('login'))

    raw_stars_with_time = github_get(
            'user/{}/starred?per_page=100'.format(g.uid),
            headers={'Accept': 'application/vnd.github.v3.star+json'})
    if not raw_stars_with_time:
        return jsonify()
    stars = [Repo(s_t['repo']) for s_t in raw_stars_with_time[:10]]
    since_time = datetime.datetime.strptime(
            raw_stars_with_time[-1]['starred_at'], "%Y-%m-%dT%H:%M:%SZ")
    newest_stars = [{'name': s.name,
                     'desc': s.desc,
                     'num_stars': s.num_stars,
                     'url': s.url} for s in stars]
    return jsonify(num_repos=len(raw_stars_with_time),
                   since_year=since_time.year,
                   repos=newest_stars)

@app.route('/suggest')
def suggest():
    if g.uid is None:
        return redirect(url_for('login'))
    if users.has_suggestion(g.uid):
        suggestion = users.get_suggestion(g.uid)
        vote = users.get_vote(g.uid)
        _, detailed_repos = fetch_repos(suggestion)
        random.shuffle(detailed_repos)
        return jsonify(suggest_repos=detailed_repos,
                       vote=vote)

    suggestion = None
    vote = None
    error_msg = None
    users.set_progress(g.uid, 0.0)
    with Octomender(g.uid, users.get_token(g.uid)) as octomender:
        octomender.exec_remote()
        for respond in octomender.sync_remote():
            app.logger.debug('suggest respond: {}'.format(respond))
            if isinstance(respond, float):  # progress.
                users.set_progress(g.uid, respond)
            elif isinstance(respond, list):  # octomend results.
                suggestion = respond
            else:  # error message (str).
                error_msg = 'Sorry, {}...well...will do better in the future!'.format(respond)

    good_repos = suggestion[:10]
    bad_repos = suggestion[10:]
    available_good_repos, detailed_good_repos = fetch_repos(good_repos, 5)
    available_bad_repos, detailed_bad_repos = fetch_repos(bad_repos, 5)
    available_repos = available_good_repos + available_bad_repos
    detailed_repos = detailed_good_repos + detailed_bad_repos

    vote = dict.fromkeys(map(str, available_repos), 0)
    users.set_suggestion(g.uid, available_repos)
    users.set_vote(g.uid, vote)

    random.shuffle(detailed_repos)
    return jsonify(suggest_repos=detailed_repos,
                   vote=vote,
                   error_msg=error_msg)

@app.route('/progress')
def progress():
    if g.uid is None:
        return redirect(url_for('login'))
    progress = users.get_progress(g.uid)
    return jsonify(progress=progress)

@app.route('/vote/<updown>/<rid>')
def vote(updown, rid):
    if g.uid is None:
        return redirect(url_for('login'))
    if not users.has_suggestion(g.uid):
        app.logger.warning('vote: no suggestion to vote')
        return jsonify(success=False)
    if updown not in ['1', '-1']:
        app.logger.warning('vote: illegal updown {}'.format(updown))
        return jsonify(success=False)

    vote = users.get_vote(g.uid)
    if rid not in vote:
        app.logger.warning('vote: rid {} not in vote'.format(rid))
        return jsonify(success=False)

    vote[rid] = int(updown)
    users.set_vote(g.uid, vote)
    return jsonify(success=True)

@app.errorhandler(400)
def bad_request(e):
    return 'Bad Request', 400

@app.errorhandler(500)
def internal_server_error(e):
    return 'Internal Server Error', 500

def github_get(url, **kwargs):
    try:
        res = github.request('GET', url, all_pages=True, **kwargs)
    except GitHubError as e:
        app.logger.error('github_get: {} {}'.format(url, e))
        return None
    return res

def fetch_repos(repo_ids, num_required=None):
    available_repos = []
    detailed_repos = []
    for rid in repo_ids:
        raw_repo = github_get('repositories/{}'.format(rid))
        if raw_repo is None:
            continue
        available_repos.append(rid)
        repo = Repo(raw_repo)
        detailed_repos.append({'id': repo.id,
                               'name': repo.name,
                               'desc': repo.desc,
                               'num_stars': repo.num_stars,
                               'url': repo.url})
        if len(available_repos) == num_required:
            break
    return available_repos, detailed_repos
