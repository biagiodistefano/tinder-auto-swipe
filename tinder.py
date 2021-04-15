from datetime import datetime

import requests


class User:

    def __init__(self, user_id, name, gender, bio, birth_date, is_traveling, distance_mi, full_data):
        self.user_id = user_id
        self.name = name
        self.gender = gender  # 0: man, 1: woman
        self.bio = bio
        self.birth_date = birth_date
        self.is_traveling = is_traveling
        self.full_data = full_data  # full json response
        self.distance = distance_mi * 1.609344
        self.score = 0
        self.points = []

    @property
    def age(self):
        if self.birth_date is None:
            return None
        birth_date = datetime.strptime(self.birth_date, '%Y-%m-%dT%H:%M:%S.%fZ')
        x = datetime.today() - birth_date
        return int(x.days / 365.25)


# documentation here: https://gist.github.com/rtt/10403467

class TinderAPI:
    HOST = 'https://api.gotinder.com'  # base url
    CORE = HOST + '/v2/recs/core'  # returns list of nearby users
    PROFILE = HOST + '/v2/profile?include=account%2Cuser'  # returns own profile
    MATCHES = HOST + '/v2/matches'  # returns matches
    LIKE = HOST + '/like/{user_id}'  # likes a user
    DISLIKE = HOST + '/pass/{user_id}'  # passes a user
    SUPERLIKE = HOST + LIKE + '/super'  # superlikes a user
    USER = HOST + '/user/{user_id}'  # gets user's profile
    PING = HOST + '/ping'  # update location
    TRAVEL = HOST + '/passport/user/travel'  # passport to new location
    META = HOST + '/v2/meta'  # gets own metadata
    MATCH = HOST + '/user/matches/match_id'  # unmathces
    UPDATES = HOST + '/updates'

    def __init__(self, token):
        self._token = token

    def get_nearby_users(self):
        res_temp = self._get(self.CORE).get('data', {}).get('results', [])
        return [User(
            user_id=r['user']['_id'],
            name=r['user']['name'],
            gender=r['user']['gender'],
            bio=r['user'].get('bio', ''),
            birth_date=r['user'].get('birth_date', None),
            is_traveling=r['user'].get('is_traveling', False),
            distance_mi=r.get("distance_mi", 0),
            full_data=r
        ) for r in res_temp]

    def like(self, user_id):
        r = self._get(self.LIKE.format(user_id=user_id))
        return r["match"], r["likes_remaining"]

    def dislike(self, user_id):
        return self._get(self.DISLIKE.format(user_id=user_id))

    def superlike(self, user_id):
        r = self._post(self.SUPERLIKE.format(user_id=user_id))
        return (r["match"],
                r["super_likes"]["remaining"],
                datetime.strptime(r["super_likes"]["resets_at"], '%Y-%m-%dT%H:%M:%S.%fZ'))

    def matches(self, count=50):
        return self._get(self.MATCHES, count=count)

    def send_message(self, user_id, text):
        return self._post(self.MATCHES + f"/{user_id}", text=text)

    def get_user(self, user_id):
        return self._get(self.USER.format(user_id))

    def update_location(self, lat, lon):
        return self._post(self.PING, lat=lat, lon=lon)

    def travel(self, lat, lon):
        """Tinder Plus Only"""
        return self._post(self.TRAVEL, lat=lat, lon=lon)

    def unmatch(self, match_id):
        return self._delete(self.MATCH.format(match_id))

    def updates(self, last_activity_date: datetime):
        last_activity_date = last_activity_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return self._post(self.UPDATES, last_activity_date=last_activity_date)

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
    token = input("Enter your token: ")
    api = TinderAPI(token)
