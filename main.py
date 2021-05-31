import asyncio
import json
import os
import random
import sys
from datetime import datetime, timedelta
from time import sleep

import geocoder
import regex
import requests
from decouple import config

from tinder import TinderAPI, User


THIS_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(THIS_DIR, "data")


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
    (r"bisex(ual)?|bisessuale", +1)
]


async def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        print(timeformat, end='\r')
        await asyncio.sleep(1)
        t -= 1
    await asyncio.sleep(random.random())


async def look_human(user):
    sleep_time = random.random()
    if random.randint(0, 1):
        sleep_time += random.randint(0, len(user.photos)) * random.random()  # extra time to look at pictures
    if random.randint(0, 1):
        sleep_time += len(user.bio) * (random.randint(2, 5) / 100)  # extra time to read bio
    if sleep_time < 0.2:
        sleep_time = 0.2
    await asyncio.sleep(sleep_time)


def rate_user(user):
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


class HornyFucker:
    def __init__(self, token, save_activity=True):
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
        self.city = loc.current_result.city

    def get_own_data(self):
        profile = self.api.profile().get("data")
        meta = self.api.meta().get("data")
        user_dir = os.path.join(DATA_DIR, "user")
        os.makedirs(user_dir, exist_ok=True)
        self.write_json(os.path.join(user_dir, "meta.json"), meta)
        self.write_json(os.path.join(user_dir, "profile.json"), profile)
        return profile, meta

    async def swipe_loop(self, surge=False):
        for user in self.nearby_users:
            if not surge:
                await look_human(user)
            else:
                await asyncio.sleep(0.3)
                await self.download_user_photos(user, surge=surge)
            
            rate_user(user)
            if user.score > 0:
                if self.super_likes_remaining > 0 or datetime.now() > self.super_likes_remaining_resets:
                    self.superlike(user)
                elif self.likes_remaining > 0:
                    self.swipe_right(user)
                else:
                    print("You ran out of likes!")
                    return
            elif user.score < 0:
                self.swipe_left(user)
            elif self.likes_remaining > 0:
                self.swipe_right(user)
            else:
                print("You ran out of likes!")
                return
        print(f"Getting nearby users in {self.city}", end="...", flush=True)
        self.nearby_users = self.api.get_nearby_users()
        print("Ok.")
        if len(self.nearby_users) == 0:
            minutes_to_wait = random.randint(0, 15)
            print(f"No more potential matches. Waiting for {minutes_to_wait} minutes...")
            seconds_to_wait = minutes_to_wait * 60
            await countdown(seconds_to_wait)
        await self.swipe_loop()

    def swipe_right(self, user):
        print(f"Swiping right on {user.name}", end="...", flush=True)
        try:
            match, self.likes_remaining = self.api.like(user.user_id)
            print("It's a match!") if match else print()
        except KeyError:
            pass
        self.save_swipe("right", user)

    def swipe_left(self, user):
        print(f"Swiping left on {user.name}")
        self.api.dislike(user.user_id)
        self.save_swipe("left", user)

    def superlike(self, user):
        print(f"Super-liking {user.name}", end="...", flush=True)
        match, self.super_likes_remaining, self.super_likes_remaining_resets = self.api.superlike(user.user_id)
        print("It's a match!") if match else print()
        self.save_swipe("superlike", user)

    async def first_message_loop(self):
        print("Getting matches", end="...")
        matches = self.api.matches()
        self.matches = matches.get("data", {}).get("matches", [])
        print("Ok.")
        for match in self.matches:
            if len(match.get("messages", [])) == 0:
                self.send_standard_opener(match["_id"])
            await asyncio.sleep(2 + random.random())
        await asyncio.sleep(random.randint(15, 60) + random.random())
        await self.first_message_loop()

    def send_standard_opener(self, match_id):
        print(f"Sending standard opener to {match_id}", end="...")
        hello_there = dict(
            message="https://media.tenor.com/images/e884f717b42f78f0792d914117cd010d/tenor.gif?width=240&height=120",
            # type="gif"
        )
        r = self.api.send_message(match_id, **hello_there)
        print(r)
        sleep(1 + random.random())
        self.api.send_message(match_id, message="Quick question:")
        sleep(1 + random.random())
        self.api.send_message(match_id, message="Are you into falafel? 🥸")
        print("ok.")

    def save_swipe(self, where, user):
        if not self.save_activity:
            return
        swipe_dir = os.path.join(DATA_DIR, "swipes", self.city, where)
        os.makedirs(swipe_dir, exist_ok=True)
        filepath = os.path.join(swipe_dir, user.user_id + ".json")
        self.write_json(filepath, user.__dict__)

    @staticmethod
    def write_json(filepath, data):
        with open(filepath, "w") as f:
            f.write(json.dumps(data, indent=4))

    @staticmethod
    async def download_user_photos(user, surge=False):
        photo_dir = os.path.join(DATA_DIR, "photos", user.user_id)
        os.makedirs(photo_dir, exist_ok=True)
        existing = set(f for f in os.listdir(photo_dir) if f.endswith((".jpeg", ".jpg", ".png", ".gif")))
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
            except AssertionError:
                pass
            if not surge:
                await asyncio.sleep(random.random() * random.randint(0, 2))

    def share_user(self, user):
        return self.api.share(user.user_id)


async def main(hf, surge=False):
    swipe_loop = asyncio.create_task(hf.swipe_loop(surge=surge))
    # first_message_loop = asyncio.create_task(hf.first_message_loop())
    await swipe_loop
    # await first_message_loop


def loop_users(city, *swipes):
    for swipe in swipes:
        for user_file in os.listdir(os.path.join(DATA_DIR, "swipes", city, swipe)):
            if not user_file.endswith(".json"):
                continue
            filepath = os.path.join(DATA_DIR, "swipes", city, swipe, user_file)
            try:
                user = _load_user(filepath)
                yield user
            except json.decoder.JSONDecodeError:
                continue


def download_existing_users_photos():
    for user in loop_users("right", "left", "superlike"):
        print(f"Downloading photos for {user.user_id}", end="...", flush=True)
        horny_fucker.download_user_photos(user)
        print("Ok.")


def cleanup_photos():
    for user in loop_users(*["left"]):
        if user.gender == 0:
            photo_dir = os.path.join(DATA_DIR, "photos", user.user_id)
            print(f"removing {photo_dir}")
            os.system(f"rm -rf {photo_dir}")


def load_user(user_id):
    for swipe in ["left", "right", "superlike"]:
        user_filepath = os.path.join(DATA_DIR, "swipes", swipe, f"{user_id}.json")
        try:
            return _load_user(user_filepath)
        except FileNotFoundError:
            pass
    raise Exception(f"User does not exists {user_id}")


def _load_user(filepath):
    with open(filepath, "rb") as f:
        _data = json.load(f)
        data = _data.get("_data", _data.get("full_data"))
    return User(data, score=_data.get("score"), points=_data.get("points"))


def get_the_bis():
    for user in loop_users(*["right"]):
        if user.gender <= 0 and (user.is_bisexual or user.is_pansexual):
            try:
                print(horny_fucker.share_user(user))
                sleep(random.random() * 2)
            except Exception:
                pass


def foo():
    for user in loop_users(*["left"]):
        if user.is_bisexual or user.is_pansexual or regex.search(r"bisex(ual)?|bisessuale", user.bio):
            horny_fucker.swipe_right(user)


if __name__ == '__main__':
    token_ = config("TINDER_TOKEN")
    horny_fucker = HornyFucker(token_)
    if not sys.flags.interactive:
        asyncio.run(main(horny_fucker))
