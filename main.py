import json
import os
import random
from datetime import datetime, timedelta
from time import sleep

import regex
from decouple import config
from tinder import TinderAPI


BIO_SCORES = [
    # NEGATIVE STUFF
    (r"(?<!(no(t looking for( a)?)? ))(long[- ]?term relationships?)", -1),
    (r"(?<!(no(t looking for( a)?)? ))(husbands?)", -5),
    (r"(?<!(no(t looking for( a)?)? )|non[- ]?)(monogamous)", -3),
    (r"vegan", -1),  # and I'm vegan myself...
    (r"(^|\W)(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)(\W|$)", -1),
    (r"(♈|♉|♊|♋|♌|♍|♎|♏|♐|♑|♒|♓)", -1),
    (r"add me on (ig|(insta(gram)?))", -1),

    # POSITIVE STUFF
    (r"(no(t looking for( a)?)? )(long[- ]?term relationships?)", +1),
    (r"non[- ]monogamous", +2),
    (r"polyamorous", +2),
    (r"(^|\W)(poly)(\W|$)", +2),
    (r"(?<!(no(t looking for( a)?)? ))(hookups?)", +1),
    (r"open relationships?|offene Beziehung", +1),
    (r"falafel", +10),
]


def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        print(timeformat, end='\r')
        sleep(1)
        t -= 1
    sleep(random.random())


def look_human(user):
    sleep_time = random.random()
    if random.randint(0, 1):
        sleep_time += random.randint(0, len(user.photos)) * random.random()  # extra time to look at pictures
    if random.randint(0, 1):
        sleep_time += len(user.bio) * (random.randint(2, 5)/100)  # extra time to read bio
    if sleep_time < 0.2:
        sleep_time = 0.2
    sleep(sleep_time)


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
    user.score = score


class HornyFucker:
    def __init__(self, token, save_activity=True):
        self.api = TinderAPI(token)
        self.nearby_users = []
        self.likes_remaining = 100
        self.super_likes_remaining = 5
        self.super_likes_remaining_resets = datetime.now() + timedelta(days=1)
        self.save_activity = save_activity

    def swipe_loop(self):
        for user in self.nearby_users:
            look_human(user)
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

        print("Getting nearby users", end="...")
        self.nearby_users = self.api.get_nearby_users()
        print("Ok.")
        if len(self.nearby_users) == 0:
            minutes_to_wait = random.randint(0, 15)
            print(f"No more potential matches. Waiting for {minutes_to_wait} minutes...")
            seconds_to_wait = minutes_to_wait * 60
            countdown(seconds_to_wait)
        self.swipe_loop()

    def swipe_right(self, user):
        print(f"Swiping right on {user.name}", end="...")
        match, self.likes_remaining = self.api.like(user.user_id)
        print("It's a match!") if match else print()
        self.save_data("right", user)

    def swipe_left(self, user):
        print(f"Swiping left on {user.name}")
        self.api.dislike(user.user_id)
        self.save_data("left", user)

    def superlike(self, user):
        print(f"Super-liking {user.name}", end="...")
        match, self.super_likes_remaining, self.super_likes_remaining_resets = self.api.superlike(user.user_id)
        print("It's a match!") if match else print()
        self.save_data("superlike", user)

    def save_data(self, where, user):
        if not self.save_activity:
            return
        this_dir = os.path.dirname(os.path.realpath(__file__))
        data_dir = os.path.join(this_dir, "data", "swipes", where)
        os.makedirs(data_dir, exist_ok=True)
        filepath = os.path.join(data_dir, user.user_id + ".json")
        with open(filepath, "w") as f:
            f.write(json.dumps(user.__dict__, indent=4))


if __name__ == '__main__':
    token_ = config("TINDER_TOKEN")
    horny_fucker = HornyFucker(token_)
    horny_fucker.swipe_loop()
