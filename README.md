# Tinder Auto Swipe

**Disclaimer**: using this will get you banned, probably.

**Requires Python 3.8 or above.**

**This is a quick & dirty code. Use it at your own risk.**

## Basic setup

```shell
git clone git@github.com:biagiodistefano/tinder-auto-swipe.git
cd tinder-auto-swipe
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

* Log in to [Tinder.com](https://www.tinder.com/) via the web app.
* Open the browser console
* open the `XHR` tab
* Perform any action on the website (e.g., like or dislike someone)
* Check out the request on the XHR tab, go to headers
* Copy the value of `X-Auth-Token`

Now run

```shell
python main.py --token <X-Auth-Token> [--surge] [--save] [--data-dir <path/to/data/dir>]
```

### Params
* `token`: the Auth token for Tinder (perform login separately as explained above, I'm too lazy to program the login myself, but PRs are welcome)
* `surge`: will only wait for `0.3` seconds between swipes
* `save`: will save activity locally (users' data and photos)
* `data-dir`: specify where tos ave users' data. Defaults to `./data`

## CUSTOMISE YOUR PREFERENCES

* Add regexes to `BIO_SCORES` in `main.py`
* Add logic to `rate_user(user)`