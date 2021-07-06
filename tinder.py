from datetime import datetime

import requests


class User:

    def __init__(self, data, score=None, points=None):
        self.score = score if score is not None else 0
        self.points = points if points is not None else []
        self._data = data  # full json response

    @property
    def user(self):
        return self._data["user"]

    @property
    def user_id(self):
        return self.user['_id']

    @property
    def name(self):
        return self.user['name']

    @property
    def gender(self):
        return self.user['gender']

    @property
    def bio(self):
        return self.user['bio']

    @property
    def birth_date(self):
        return self.user.get('birth_date')

    @property
    def is_traveling(self):
        return self.user.get('is_traveling', False)

    @property
    def distance(self):
        return self._data.get("distance_mi", 0) * 1.609344

    @property
    def age(self):
        if self.birth_date is None:
            return None
        birth_date = datetime.strptime(self.birth_date, '%Y-%m-%dT%H:%M:%S.%fZ')
        x = datetime.today() - birth_date
        return int(x.days / 365.25)

    @property
    def photos(self):
        return self.user["photos"]

    @property
    def sexual_orientations(self):
        return [so["id"] for so in self.user.get("sexual_orientations", [])]

    @property
    def is_bisexual(self):
        return "bi" in self.sexual_orientations

    @property
    def is_pansexual(self):
        return "pan" in self.sexual_orientations

    @property
    def is_straight(self):
        return "str" in self.sexual_orientations


# documentation here: https://github.com/fbessez/Tinder

class TinderAPI:
    HOST = 'https://api.gotinder.com'  # base url
    CORE = HOST + '/v2/recs/core'  # returns list of nearby users
    PROFILE = HOST + '/v2/profile?include=account%2Cuser'  # returns own profile
    MATCHES = HOST + '/v2/matches'  # returns matches
    LIKE = HOST + '/like/{user_id}'  # likes a user
    DISLIKE = HOST + '/pass/{user_id}'  # passes a user
    SUPERLIKE = LIKE + '/super'  # superlikes a user
    USER = HOST + '/user/{user_id}'  # gets user's profile
    PING = HOST + '/ping'  # update location
    TRAVEL = HOST + '/passport/user/travel'  # passport to new location
    META = HOST + '/v2/meta'  # gets own metadata
    MATCH = HOST + '/user/matches/{match_id}'  # unmathces
    UPDATES = HOST + '/updates'
    SHARE_PROFILE = HOST + '/user/{user_id}/share'

    def __init__(self, token):
        self._token = token

    def profile(self):
        return self._get(self.PROFILE)

    def get_nearby_users(self):
        return [User(r) for r in self._get(self.CORE).get('data', {}).get('results', [])]

    def like(self, user_id):
        r = self._get(self.LIKE.format(user_id=user_id))
        return r["match"], r["likes_remaining"]

    def dislike(self, user_id):
        return self._get(self.DISLIKE.format(user_id=user_id))

    def superlike(self, user_id):
        r = self._post(self.SUPERLIKE.format(user_id=user_id))
        resets_at = r["super_likes"].get("resets_at")
        if resets_at is not None:
        	resets_at = datetime.strptime(resets_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        else:
        	resets_at = datetime.now()
        return (r.get("match"),
                r.get("super_likes", {}).get("remaining", 0),
                resets_at)

    def matches(self, count=50):
        return self._get(self.MATCHES, count=count)

    def send_message(self, match_id, message, **kwargs):
        kwargs["message"] = message
        return self._post(self.MATCHES + f"/{match_id}", **kwargs)

    def get_user(self, user_id):
        return self._get(self.USER.format(user_id=user_id))

    def update_location(self, lat, lon):
        return self._post(self.PING, lat=lat, lon=lon)

    def travel(self, lat, lon):
        """Tinder Plus Only"""
        return self._post(self.TRAVEL, lat=lat, lon=lon)

    def unmatch(self, match_id):
        return self._delete(self.MATCH.format(match_id=match_id))

    def updates(self, last_activity_date: datetime):
        last_activity_date = last_activity_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return self._post(self.UPDATES, last_activity_date=last_activity_date)

    def share(self, user_id):
        return self._post(self.SHARE_PROFILE.format(user_id=user_id))["link"]

    def meta(self):
        return self._get(self.META)

    def _get(self, url, **params):
        r = requests.get(url, params=params, headers={"X-Auth-Token": self._token})
        assert r.status_code == 200, f"GET {url} <{r.status_code}>: {r.text}"
        return r.json()

    def _post(self, url, **payload):
        r = requests.post(url, json=payload, headers={"X-Auth-Token": self._token})
        assert r.status_code == 200, f"POST {url} <{r.status_code}>: {r.text}"
        return r.json()

    def _delete(self, url):
        r = requests.delete(url, headers={"X-Auth-Token": self._token})
        assert r.status_code == 200, f"DELETE {url} <{r.status_code}>: {r.text}"
        return r.json()


if __name__ == '__main__':
    token_ = input("Enter your token: ")
    api = TinderAPI(token_)
