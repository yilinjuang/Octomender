# Doc: https://googlecloudplatform.github.io/google-cloud-python/latest/datastore/usage.html

import datetime
import json

from google.cloud import datastore

'''
UserModel
    uid (str): key
    token (str)
    country (str)
    joined_time (datetime.datetime)
    progress (float): 0.0 ~ 100.0
    suggestion (list): repo indices
    vote (json): {'rid1': vote, 'rid2': vote, ..., 'rid10': vote}
'''

class UserModel(object):
    def __init__(self, project_id):
        self.client = datastore.Client(project_id)

    def _get_key(self, uid):
        return self.client.key('User', str(uid))

    def _get_user(self, uid):
        return self.client.get(self._get_key(uid))

    def add(self, uid, token):
        user = self._get_user(uid)
        if not user:
            user = datastore.Entity(key=self._get_key(uid))
            user['joined_time'] = datetime.datetime.utcnow()
        user['token'] = token
        self.client.put(user)

    def get_token(self, uid):
        user = self._get_user(uid)
        assert user is not None
        assert 'token' in user
        return user['token']

    def set_country(self, uid, country):
        user = self._get_user(uid)
        assert user is not None
        user['country'] = country
        self.client.put(user)

    def get_progress(self, uid):
        user = self._get_user(uid)
        assert user is not None
        if 'progress' in user:
            return user['progress']
        return 0.0

    def set_progress(self, uid, progress):
        user = self._get_user(uid)
        assert user is not None
        user['progress'] = progress
        self.client.put(user)

    def has_suggestion(self, uid):
        user = self._get_user(uid)
        assert user is not None
        return 'suggestion' in user

    def get_suggestion(self, uid):
        user = self._get_user(uid)
        assert user is not None
        if 'suggestion' in user:
            return user['suggestion']
        return []

    def set_suggestion(self, uid, suggestion):
        user = self._get_user(uid)
        assert user is not None
        user['suggestion'] = suggestion
        self.client.put(user)

    def get_vote(self, uid):
        user = self._get_user(uid)
        assert user is not None
        if 'vote' in user:
            return json.loads(user['vote'])
        return {}

    def set_vote(self, uid, vote):
        user = self._get_user(uid)
        assert user is not None
        user['vote'] = json.dumps(vote)
        self.client.put(user)


class Repo(object):
    def __init__(self, repo):
        self.id = repo['id']
        self.name = repo['full_name']
        self.desc = repo['description']
        self.url = repo['html_url']
        self.num_stars = repo['stargazers_count']

    def summarize(self):
        return 'Id: {}, Name: {}, Stars: {}'.format(
                self.id, self.name, self.num_stars)


class User(object):
    def __init__(self, user):
        self.uid = user['id']
        self.name = user['login']
        self.avatar = user['avatar_url']

    def summarize(self):
        return 'Uid: {}, Name: {}, Avatar: {}'.format(
                self.uid, self.name, self.avatar)
