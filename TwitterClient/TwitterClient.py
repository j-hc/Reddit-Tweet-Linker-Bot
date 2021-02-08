import requests
import re
from .TW_user_status import TWStatus
from http import cookiejar
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError
from info import twitter_client_proxy


class TwitterClient:
    class BlockAll(cookiejar.CookiePolicy):
        return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
        netscape = True
        rfc2965 = hide_cookie2 = False

    TWITTER_PUBLIC_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs" \
                           "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

    HOST = "https://api.twitter.com"

    def __init__(self):
        self.req_sesh = self.prep_session()
        self._get_gt_token()

    def prep_session(self):
        req_sesh = requests.Session()
        req_sesh.cookies.set_policy(self.BlockAll())
        req_sesh.headers = {
            'Authorization': f'Bearer {self.TWITTER_PUBLIC_TOKEN}',
            'User-Agent': "Mozilla/5.0 Gecko/20100101 Firefox/81.0",
            'Accept-Encoding': None,
            'Accept': None
        }
        return req_sesh

    def handled_get(self, url, **kwargs):
        while True:
            try:
                response = self.req_sesh.get(url, **kwargs)
            except (ConnectionError, ProtocolError):
                self._get_gt_token()
                continue
            if response.status_code == 403 or response.status_code == 429:
                self._get_gt_token()
                continue
            else:
                return response

    def _get_gt_token(self):
        response = requests.get('https://twitter.com/', headers={'User-Agent': 'Mozilla/5.0 Gecko/20100101 Firefox/80.0'},
                                proxies={'https': twitter_client_proxy})
        gt_token = re.search(b'gt=([0-9]*)', response.content).group(1).decode()
        self.req_sesh.headers.update({"x-guest-token": gt_token})

    def search_tweet(self, tweet_text, from_whom, lang, exact_phrase=True):
        if exact_phrase:
            tweet_text = '"' + tweet_text + '"'
        if from_whom:
            query = f'{tweet_text} (from:{from_whom}) exclude:retweets'
        else:
            query = f'{tweet_text} exclude:retweets'

        if lang == "tur":
            self.req_sesh.headers.update({'Accept-Language': "tr-TR,tr;q=0.5"})
        else:
            self.req_sesh.headers.update({'Accept-Language': "en-US,en;q=0.5"})
        params = (
            ('q', query),
            ('count', '1'),  # i only want the first result
            ('include_cards', 'false'), ('include_my_retweet', '0'), ('include_blocked_by', 'true'),
            ('include_reply_count', 'false'), ('include_descendent_reply_count', 'false'), ('include_blocking', 'true'),
            ('include_profile_interstitial_type', '1'), ('include_blocking', '1'), ('include_followed_by', '1'),
            ('include_want_retweets', '1'), ('include_mute_edge', '1'), ('skip_status', '1'),
            ('include_ext_alt_text', 'true'), ('include_quote_count', 'false'), ('include_reply_count', '0'),
            ('tweet_mode', 'compat'), ('include_entities', 'false'), ('include_user_entities', 'false'),
            ('send_error_codes', 'true'), ('simple_quoted_tweet', 'false'), ('pc', '1'), ('tweet_search_mode', 'live')
        )
        response_r = self.handled_get(f'{self.HOST}/2/search/adaptive.json', params=params)
        # print(response_r.text)
        response = response_r.json()
        try:
            tweets = response['globalObjects']['tweets']
            users = response['globalObjects']['users']
        except:
            return {}
        if not bool(tweets):
            return {}

        tweets_vals = list(response['globalObjects']['tweets'].values())
        if len(tweets) != 1:
            def json_extract(obj, key):
                arr = []

                def extract(obj, arr, key):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k == key:
                                arr.append(v)
                            if isinstance(v, (dict, list)):
                                extract(v, arr, key)
                    elif isinstance(obj, list):
                        for item in obj:
                            extract(item, arr, key)
                    return arr

                values = extract(obj, arr, key)
                return values

            entries = response['timeline']['instructions'][0]['addEntries']['entries']
            for tw in reversed(json_extract(entries, 'tweet')):
                if tw.get('highlights') is not None:
                    the_tweet = tweets[tw['id']]
                    break
            else:
                the_tweet = tweets_vals[-1]
        else:
            the_tweet = tweets_vals[0]

        b_could_be_quote = the_tweet.get("is_quote_status", False)

        tweet_id = the_tweet['id_str']
        user_id_str = the_tweet['user_id_str']
        the_user_id = users[user_id_str]
        the_user_name = the_user_id['screen_name']
        return {"link": f"https://twitter.com/{the_user_name}/status/{tweet_id}", "user_id": user_id_str, "b_could_be_quote": b_could_be_quote}

    def get_twitter_account_status(self, username):
        params = {'variables': f'{{"screen_name":"{username}","withHighlightedLabel":true}}'}
        response = self.handled_get(f'{self.HOST}/graphql/-xfUfZsnR_zqjFd-IfrN5A/UserByScreenName', params=params).json()
        if response.get('errors'):
            if response['errors'][0]['code'] == 63:
                return TWStatus.SUSPENDED
            elif response['errors'][0]['code'] == 50:
                return TWStatus.DNE
        elif response['data']['user']['legacy']['protected']:
            return TWStatus.PROTECTED
        else:
            return TWStatus.OK
