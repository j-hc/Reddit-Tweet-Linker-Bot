import requests
import re
from collections import OrderedDict
from .TW_user_status import TWStatus
from http import cookiejar
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError
from time import sleep


class TwitterClient:
    class BlockAll(cookiejar.CookiePolicy):
        return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
        netscape = True
        rfc2965 = hide_cookie2 = False

    TWITTER_PUBLIC_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs" \
                           "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

    def __init__(self):
        self.req_sesh = TwitterClient.prep_session()
        self.get_gt_token()

    @staticmethod
    def prep_session():
        req_sesh = requests.Session()
        req_sesh.cookies.set_policy(TwitterClient.BlockAll())
        req_sesh.headers = {
            'authorization': f'Bearer {TwitterClient.TWITTER_PUBLIC_TOKEN}',
            'User-Agent': "Firefox",
            'Accept-Encoding': None,
            'Accept': None
        }
        return req_sesh

    def handled_get(self, url, **kwargs):
        while True:
            try:
                response = self.req_sesh.get(url, **kwargs)
            except (ConnectionError, ProtocolError):
                sleep(2)
                self.get_gt_token()
                continue
            if response.status_code == 403 or response.status_code == 429:
                sleep(2)
                self.get_gt_token()
                continue
            else:
                return response

    def get_gt_token(self):
        response = requests.get('https://twitter.com/', headers={'User-Agent': 'Firefox'})
        gt_token = re.search(b'gt=([0-9]*)', response.content).group(1)
        self.req_sesh.headers.update({"x-guest-token": gt_token.decode()})

    def search_tweet(self, tweet_text, from_whom, lang):
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
            ('count', '1'),  # i only want the first result for now
            ('include_cards', 'false'), ('include_my_retweet', '0'), ('include_blocked_by', 'true'),
            ('include_reply_count', 'false'), ('include_descendent_reply_count', 'false'), ('include_blocking', 'true'),
            ('include_profile_interstitial_type', '1'), ('include_blocking', '1'), ('include_followed_by', '1'),
            ('include_want_retweets', '1'), ('include_mute_edge', '1'), ('skip_status', '1'), ('model_version', '7'),
            ('include_ext_alt_text', 'true'), ('include_quote_count', 'false'), ('include_reply_count', '0'),
            ('tweet_mode', 'compat'), ('include_entities', 'false'), ('include_user_entities', 'false'),
            ('send_error_codes', 'true'), ('simple_quoted_tweet', 'false'), ('query_source', ''), ('pc', '1'),
        )
        response_r = self.handled_get('https://api.twitter.com/2/search/adaptive.json', params=params)
        response = response_r.json(object_pairs_hook=OrderedDict)

        tweets = response['globalObjects']['tweets']
        users = response['globalObjects']['users']
        tweets_vals = list(tweets.values())

        if not bool(tweets):
            return {}

        the_tweet = None
        if from_whom:
            for tweet in tweets:
                for user in users:
                    if users[user]['screen_name'] == from_whom and tweets[tweet]['user_id_str'] == user:
                        the_tweet = tweets[tweet]
                        break
        else:
            if (tweets_vals[0].get("is_quote_status") and len(tweets) < 3) or (
                    len(tweets) == 2 and tweets_vals[1].get("self_thread")):
                the_tweet = tweets_vals[0]
            else:
                the_tweet = tweets_vals[-1]
        if not the_tweet:
            return {}
        tweet_id = the_tweet['id_str']
        user_id_str = the_tweet['user_id_str']
        the_user_id = users[user_id_str]
        the_user_name = the_user_id['screen_name']
        return {"link": f"https://twitter.com/{the_user_name}/status/{tweet_id}", "user_id": user_id_str}

    def get_twitter_account_status(self, username):
        params = ('variables', f'{{"screen_name":"{username}","withHighlightedLabel":true}}'),
        response = self.handled_get('https://api.twitter.com/graphql/-xfUfZsnR_zqjFd-IfrN5A/UserByScreenName',
                                    params=params).json()
        if response.get('errors'):
            if response['errors'][0]['code'] == 63:
                return TWStatus.SUSPENDED
            elif response['errors'][0]['code'] == 50:
                return TWStatus.DNE
        elif response['data']['user']['legacy']['protected']:
            return TWStatus.PROTECTED
        else:
            return TWStatus.OK


tw_client = TwitterClient()
