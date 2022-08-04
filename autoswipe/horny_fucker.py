import json
import logging
import os
import random
import regex
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Tuple

import geocoder
import requests

from .tinder import TinderAPI, User
from .utils import setup_logger


logger = setup_logger("horny_fucker", to_terminal_level=logging.INFO)


BIO_SCORES = [
    # NEGATIVE STUFF
    (r"(?<!(no(t looking for( a)?)? ))(long[- ]?term relationships?)", -1),
    (r"(?<!(no(t looking for( a)?)? ))(husbands?)", -5),
    (r"(?<!(no(t looking for( a)?)? )|non[- ]?)(monogamous)", -3),
    (r"vegan", -1),  # and I'm vegan myself...
    (r"(^|\W)(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)(\W|$)", -1),
    (r"(♈|♉|♊|♋|♌|♍|♎|♏|♐|♑|♒|♓)", -1),
    (r"(add|follow) me (on )?(ig|(insta(gram)?))", -1),

    # POSITIVE STUFF
    (r"(no(t looking for( a)?)? )(long[- ]?term relationships?)", +1),
    (r"non[- ]monogamous", +2),
    (r"polyamorous", +2),
    (r"(^|\W)(poly)(\W|$)", +2),
    (r"(?<!(no(t looking for( a)?)? ))(hookups?)", +1),
    (r"open relationships?|offene Beziehung", +1),
    (r"falafels?", +10),
    (r"sex[- ]?positive", +2),
    (r"kinky", +2),
    (r"bisex(ual)?|bisessuale", +1),
    (r"\bbi\b", +1)
]


class HornyFucker:
    def __init__(
        self,
        token: str,
        save_activity: bool = True,
        data_dir: Path = None,
    ):
        if data_dir is None:
            parent_dir = Path(__file__).parent.parent.resolve()
            self.data_dir = parent_dir / "data"
        else:
            self.data_dir = Path(data_dir)
        self.api = TinderAPI(token)
        self.nearby_users = []
        self.matches = []
        self.likes_remaining = 100
        self.super_likes_remaining = 5
        self.super_likes_remaining_resets = datetime.now() + timedelta(days=1)
        self.save_activity = save_activity
        self.profile, self.meta = self.get_own_data()
        pos = (self.profile["user"]["pos"]["lat"], self.profile["user"]["pos"]["lon"])
        loc = geocoder.reverse(pos, provider="osm")
        self.city = str(loc.current_result.city)

    def get_own_data(self) -> Tuple[dict, dict]:
        profile = self.api.profile().get("data")
        meta = self.api.meta().get("data")
        user_dir = self.data_dir / "user"
        user_dir.mkdir(exist_ok=True, parents=True)
        self.write_json(user_dir / "meta.json", meta)
        self.write_json(user_dir / "profile.json", profile)
        return profile, meta

    def swipe_loop(self, surge: bool = False):
        for user in self.nearby_users:
            if not surge:
                self.look_human(user)
            else:
                sleep(0.3)
            if self.save_activity:
                self.download_user_photos(user, surge=surge)
            self.rate_user(user)
            if user.score > 0:
                if self.super_likes_remaining > 0 or datetime.now() > self.super_likes_remaining_resets:
                    self.superlike(user)
                elif self.likes_remaining > 0:
                    self.swipe_right(user)
                else:
                    logger.info("You ran out of likes!")
                    return
            elif user.score < 0:
                self.swipe_left(user)
            elif self.likes_remaining > 0:
                self.swipe_right(user)
            else:
                logger.info("You ran out of likes!")
                return
        logger.info(f"Getting nearby users in {self.city}")
        self.nearby_users = self.api.get_nearby_users()
        if len(self.nearby_users) == 0:
            minutes_to_wait = random.randint(0, 15)
            logger.info(f"No more potential matches. Waiting for {minutes_to_wait} minutes...")
            seconds_to_wait = minutes_to_wait * 60
            self.countdown(seconds_to_wait)
        self.swipe_loop()

    def swipe_right(self, user: User):
        logger.info(f"Swiping right on {user.name}")
        try:
            match, self.likes_remaining = self.api.like(user.user_id)
            if match:
                logger.info("It's a match!")
        except KeyError:
            pass
        self.save_swipe("right", user)

    def swipe_left(self, user: User):
        logger.info(f"Swiping left on {user.name}")
        self.api.dislike(user.user_id)
        self.save_swipe("left", user)

    def superlike(self, user: User):
        logger.info(f"Super-liking {user.name}")
        match, self.super_likes_remaining, self.super_likes_remaining_resets = self.api.superlike(user.user_id)
        if match:
            logger.info("It's a match!")
        self.save_swipe("superlike", user)

    def save_swipe(self, where: str, user: User):
        if not self.save_activity:
            return
        swipe_dir = self.data_dir / "swipes" / self.city / where
        swipe_dir.mkdir(exist_ok=True, parents=True)
        filepath = swipe_dir / (user.user_id + ".json")
        self.write_json(filepath, user.__dict__)

    def share_user(self, user: User):
        return self.api.share(user.user_id)
    
    @staticmethod
    def write_json(filepath: Path, data: json):
        with filepath.open("w") as f:
            f.write(json.dumps(data, indent=4, ensure_ascii=False))

    def download_user_photos(self, user: User, surge: bool = False):
        photo_dir = self.data_dir / "photos" / user.user_id
        photo_dir.mkdir(exist_ok=True, parents=True)
        existing = set([f for f_ in [photo_dir.glob(e) for e in (".jpeg", ".jpg", ".png", ".gif")] for f in f_])
        for photo in user.photos:
            url = photo["url"]
            _, filename = os.path.split(url)
            filename = filename.split("?")[0]
            if filename in existing:
                continue
            r = requests.get(url)
            try:
                assert r.status_code == 200, f"GET {url} <{r.status_code}>: {r.text}"
                filepath = os.path.join(photo_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(r.content)
            except AssertionError as e:
                logger.error(f"Could not download photo: {e}")
            if not surge:
                sleep(random.random() * random.randint(0, 2))

    @staticmethod
    def countdown(t: int):
        while t:
            mins, secs = divmod(t, 60)
            timeformat = '{:02d}:{:02d}'.format(mins, secs)
            print(timeformat, end='\r')
            sleep(1)
            t -= 1
        sleep(random.random())

    @staticmethod
    def look_human(user: User):
        sleep_time = random.random()
        if random.randint(0, 1):
            sleep_time += random.randint(0, len(user.photos)) * random.random()  # extra time to look at pictures
        if random.randint(0, 1):
            sleep_time += len(user.bio) * (random.randint(2, 5) / 100)  # extra time to read bio
        if sleep_time < 0.2:
            sleep_time = 0.2
        sleep(sleep_time)

    @staticmethod
    def rate_user(user: User):
        score = 0
        for pattern, points in BIO_SCORES:
            if match := regex.search(pattern, user.bio):
                score += points
                user.points.append((match.group().strip(), points))
        if user.is_traveling:
            score -= 1
            user.points.append(("is_traveling", -1))
        if user.distance > 50:
            score -= 1
            user.points.append(("distance > 50km", -1))
        if user.is_bisexual or user.is_pansexual:
            score += 1
            user.points.append((", ".join(user.sexual_orientations), +1))
        if user.gender == 0:
            score -= 1
            user.points.append(("male", -1))
        user.score = score
