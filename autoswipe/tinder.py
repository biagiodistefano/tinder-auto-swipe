from datetime import date, datetime
from functools import cached_property
from typing import Any, Dict, List, Tuple, Union

import requests


class User:

    def __init__(
        self,
        data: dict,
        score: int = None,
        points: List[Tuple[str, int]] = None
    ):
        self.score = score if score is not None else 0
        self.points = points if points is not None else []
        self._data = data

    @property
    def user(self) -> dict:
        return self._data["user"]

    @property
    def user_id(self) -> str:
        return self.user['_id']

    @property
    def name(self) -> str:
        return self.user['name']

    @property
    def gender(self) -> int:
        return self.user['gender']

    @property
    def bio(self) -> str:
        return self.user['bio']

    @cached_property
    def birth_date(self) -> Union[date, None]:
        if bd := self.user.get('birth_date'):
            return datetime.strptime(bd, '%Y-%m-%dT%H:%M:%S.%fZ').date()
        return None

    @property
    def is_traveling(self) -> bool:
        return self.user.get('is_traveling', False)

    @cached_property
    def distance(self) -> float:
        return self._data.get("distance_mi", 0) * 1.609344

    @cached_property
    def age(self) -> Union[int, None]:
        if bd := self.birth_date:
            x = datetime.today().date() - bd
            return int(x.days / 365.25)
        return None

    @property
    def photos(self) -> List[dict]:
        return self.user["photos"]

    @cached_property
    def sexual_orientations(self) -> List[str]:
        return [so["id"] for so in self.user.get("sexual_orientations", [])]

    @cached_property
    def is_bisexual(self) -> bool:
        return "bi" in self.sexual_orientations

    @cached_property
    def is_pansexual(self) -> bool:
        return "pan" in self.sexual_orientations

    @cached_property
    def is_straight(self) -> bool:
        return "str" in self.sexual_orientations

    @cached_property
    def interests(self) -> List[str]:
        return [i["name"].lower() for i in self.user.get("user_interests", {}).get("selected_interests", [])]

    def is_interested_in(self, interest: str) -> bool:
        return interest.lower() in self.interests

    @property
    def selected_descriptors(self) -> List[Dict[str, Any]]:
        return self.user.get("selected_descriptors", [])

    @cached_property
    def relationship_type(self) -> List[str]:
        # choices: ["Monogamy", "Ethical non-monogamy", "Polyamory",
        # "Open relationship", "Polyamory", "Open to exploring"]
        for descriptor in self.selected_descriptors:
            if descriptor.get("section_name") == "Relationship Type":
                return [cs["name"] for cs in descriptor.get("choice_selections", [])]
        return []

    def is_monogamous(self) -> bool:
        return "Monogamy" in self.relationship_type

    def is_enm(self) -> bool:
        return "Ethical non-monogamy" in self.relationship_type

    def is_polyamorous(self) -> bool:
        return "Polyamory" in self.relationship_type

    def is_open_relationship(self) -> bool:
        return "Open relationship" in self.relationship_type

    def is_open_to_exploring(self) -> bool:
        return "Open to exploring" in self.relationship_type


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

    def __init__(self, token: str):
        self._token = token

    def profile(self):
        return self._get(self.PROFILE)

    def get_nearby_users(self):
        return [User(r) for r in self._get(self.CORE).get('data', {}).get('results', [])]

    def like(self, user_id: str) -> Tuple[bool, int]:
        r = self._get(self.LIKE.format(user_id=user_id))
        return r["match"], r["likes_remaining"]

    def dislike(self, user_id: str) -> dict:
        return self._get(self.DISLIKE.format(user_id=user_id))

    def superlike(self, user_id: str) -> Tuple[bool, int, datetime]:
        r = self._post(self.SUPERLIKE.format(user_id=user_id))
        resets_at = r["super_likes"].get("resets_at")
        if resets_at is not None:
            resets_at = datetime.strptime(resets_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        else:
            resets_at = datetime.now()
        return (r.get("match"),
                r.get("super_likes", {}).get("remaining", 0),
                resets_at)

    def matches(self, count: int = 50) -> dict:
        return self._get(self.MATCHES, count=count)

    def send_message(self, match_id: str, message: str, **kwargs) -> dict:
        kwargs["message"] = message
        return self._post(self.MATCHES + f"/{match_id}", **kwargs)

    def get_user(self, user_id: str) -> dict:
        return self._get(self.USER.format(user_id=user_id))

    def update_location(self, lat: str, lon: str) -> dict:
        return self._post(self.PING, lat=lat, lon=lon)

    def travel(self, lat: str, lon: str) -> dict:
        """Tinder Plus Only"""
        return self._post(self.TRAVEL, lat=lat, lon=lon)

    def unmatch(self, match_id: str) -> dict:
        return self._delete(self.MATCH.format(match_id=match_id))

    def updates(self, last_activity_date: datetime) -> dict:
        last_activity_date = last_activity_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return self._post(self.UPDATES, last_activity_date=last_activity_date)

    def share(self, user_id: str) -> dict:
        return self._post(self.SHARE_PROFILE.format(user_id=user_id))["link"]

    def meta(self) -> dict:
        return self._get(self.META)

    def _get(self, url: str, **params) -> dict:
        r = requests.get(url, params=params, headers={"X-Auth-Token": self._token})
        assert r.status_code == 200, f"GET {url} <{r.status_code}>: {r.text}"
        return r.json()

    def _post(self, url: str, **payload):
        r = requests.post(url, json=payload, headers={"X-Auth-Token": self._token})
        assert r.status_code == 200, f"POST {url} <{r.status_code}>: {r.text}"
        return r.json()

    def _delete(self, url: str) -> dict:
        r = requests.delete(url, headers={"X-Auth-Token": self._token})
        assert r.status_code == 200, f"DELETE {url} <{r.status_code}>: {r.text}"
        return r.json()


if __name__ == '__main__':
    token_ = input("Enter your X-Auth-Token: ")
    api = TinderAPI(token_)
