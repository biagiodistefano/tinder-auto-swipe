import random
from datetime import datetime
from time import sleep

import regex
import requests
from decouple import config


BIO_DEALBREAKERS = [
    r"(?<!(no(t looking for( a)?)? ))(long[- ]?term relationships?)",
    r"(?<!(no(t looking for( a)?)? ))(husbands?)",
    r"(?<!(no(t looking for( a)?)? )|non[- ])(monogamous)",
    r"vegan",
    r"(^|\W)(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)(\W|$)",
    r"(^|\W)(♈|♉|♊|♋|♌|♍|♎|♏|♐|♑|♒|♓)(\W|$)",
]


def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        print(timeformat, end='\r')
        sleep(1)
        t -= 1
    sleep(random.random())


def look_human():
    base_sleep = 0  # random.randint(0, 2)
    if random.random() > 0.8:
        base_sleep = random.randint(3, 5)
    sleep_time = base_sleep + random.random()
    if sleep_time < 0.2:
        sleep_time = 0.2
    sleep(sleep_time)


def decide(user):
    for pattern in BIO_DEALBREAKERS:
        if match := regex.search(pattern, user.bio):
            return False, match.group()
    return True, "Horny"


class User:

    def __init__(self, user_id, name, gender, bio, birth_date=None):
        self.user_id = user_id
        self.name = name
        self.gender = gender  # 0: man, 1: woman
        self.bio = bio
        self.birth_date = datetime.strptime(birth_date, '%Y-%m-%dT%H:%M:%S.%fZ') if birth_date is not None else None

    @property
    def age(self):
        if self.birth_date is None:
            return None
        x = datetime.today() - self.birth_date
        return int(x.days / 365.25)


class TinderAPI:
    HOST = 'https://api.gotinder.com'  # base url
    CORE = HOST + '/v2/recs/core'  # returns list of nearby users
    PROFILE = HOST + '/v2/profile?include=account%2Cuser'  # returns own profile
    MATCHES = HOST + '/v2/matches'  # returns matches
    LIKE = HOST + '/like/{user_id}'  # likes a user
    DISLIKE = HOST + '/pass/{user_id}'  # passes a user

    def __init__(self, token):
        self._token = token
        self.nearby_users = []

    def get_nearby_users(self):
        res_temp = self._get(self.CORE).get('data', {}).get('results', [])
        self.nearby_users = [User(r['user']['_id'], r['user']['name'], r['user']['gender'], r['user'].get('bio', ''),
                                  r['user'].get('birth_date', None)) for r in res_temp]
        return self.nearby_users

    def like(self, user_id):
        r = self._get(self.LIKE.format(user_id=user_id))
        return r["match"], r["likes_remaining"]

    def dislike(self, user_id):
        return self._get(self.DISLIKE.format(user_id=user_id))

    def _get(self, url):
        r = requests.get(url, headers={"X-Auth-Token": self._token})
        assert r.status_code == 200, f"GET {url} <{r.status_code}>: {r.text}"
        return r.json()


def swipe_loop(api):
    for u in api.nearby_users:
        look_human()
        like, reason = decide(u)
        if like:
            print(f"Swiping right on {u.name}", end="...")
            match, likes_remaining = api.like(u.user_id)
            if match:
                print("It's a Match!")
            else:
                print()
            if likes_remaining < 1:
                print("You ran out of likes!")
                return
        else:
            print(f"Swiping left on {u.name} [{reason}]")
            api.dislike(u.user_id)
    print("Getting nearby users", end="...")
    api.get_nearby_users()
    print("Ok.")
    if len(api.nearby_users) == 0:
        minutes_to_wait = random.randint(0, 15)
        print(f"No more potential matches. Waiting for {minutes_to_wait} minutes...")
        seconds_to_wait = minutes_to_wait * 60
        countdown(seconds_to_wait)
    swipe_loop(api)


if __name__ == '__main__':
    token_ = config("TINDER_TOKEN")
    api_ = TinderAPI(token_)
    swipe_loop(api_)
