import json
from typing import Generator

from .horny_fucker import DATA_DIR
from .tinder import User


def loop_users(city: str, *swipes: str) -> Generator[User, None, None]:
    for swipe in swipes:
        for user_file in DATA_DIR / "swipes" / city / swipe:
            if not user_file.suffix == ".json":
                continue
            filepath = DATA_DIR / "swipes" / city / swipe / user_file
            try:
                user = _load_user(filepath)
                yield user
            except json.decoder.JSONDecodeError:
                continue


def cleanup_photos():
    for user in loop_users(*["left"]):
        if user.gender == 0:
            photo_dir = DATA_DIR / "photos" / user.user_id
            print(f"removing {photo_dir}")
            photo_dir.rmdir()


def load_user(user_id):
    for swipe in ["left", "right", "superlike"]:
        user_filepath = DATA_DIR / "swipes" / swipe / f"{user_id}.json"
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
