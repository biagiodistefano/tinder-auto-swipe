import json
import logging
import os
import sys
from pathlib import Path
from typing import Generator, Optional

from .tinder import User


def setup_logger(
    name: str,
    log_filepath: Optional[os.PathLike] = None,
    level: Optional[int] = logging.INFO,
    newfile: Optional[bool] = False,
    to_terminal_level: Optional[int] = None
) -> logging.Logger:

    if log_filepath is not None:
        log_filepath = Path(log_filepath)
        log_filepath.parent.mkdir(exist_ok=True, parents=True)
    else:
        log_filepath = Path(name + ".log" if not name.endswith(".log") else "")

    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')
    if newfile:
        handler = logging.FileHandler(log_filepath, mode="w")
    else:
        handler = logging.FileHandler(log_filepath)

    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    if to_terminal_level is not None:
        terminal_handler = logging.StreamHandler(sys.stdout)
        terminal_handler.setLevel(to_terminal_level)
        terminal_handler.setFormatter(formatter)
        logger.addHandler(terminal_handler)
    return logger


def loop_users(city: str, *swipes: str, data_dir: Path) -> Generator[User, None, None]:
    for swipe in swipes:
        for user_file in data_dir / "swipes" / city / swipe:
            if not user_file.suffix == ".json":
                continue
            filepath = data_dir / "swipes" / city / swipe / user_file
            try:
                user = _load_user(filepath)
                yield user
            except json.decoder.JSONDecodeError:
                continue


def cleanup_photos(data_dir: Path):
    for user in loop_users(*["left"]):
        if user.gender == 0:
            photo_dir = data_dir / "photos" / user.user_id
            print(f"removing {photo_dir}")
            photo_dir.rmdir()


def load_user(user_id: str, data_dir: Path):
    for swipe in ["left", "right", "superlike"]:
        user_filepath = data_dir / "swipes" / swipe / f"{user_id}.json"
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
