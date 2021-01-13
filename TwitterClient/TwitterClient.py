import requests
import re
from collections import OrderedDict
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
        req_sesh.cookies.set_policy(TwitterClient.BlockAll())
        req_sesh.headers = {
            'authorization': f'Bearer {TwitterClient.TWITTER_PUBLIC_TOKEN}',
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
        response = requests.get('https://twitter.com/', headers={'User-Agent': 'Mozilla/5.0 Gecko/20100101 Firefox/80.0'}, proxies={'https': twitter_client_proxy})
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
            ('count', '1'),  # i only want the first result for now
            ('include_cards', 'false'), ('include_my_retweet', '0'), ('include_blocked_by', 'true'),
            ('include_reply_count', 'false'), ('include_descendent_reply_count', 'false'), ('include_blocking', 'true'),
            ('include_profile_interstitial_type', '1'), ('include_blocking', '1'), ('include_followed_by', '1'),
            ('include_want_retweets', '1'), ('include_mute_edge', '1'), ('skip_status', '1'), ('model_version', '7'),
            ('include_ext_alt_text', 'true'), ('include_quote_count', 'false'), ('include_reply_count', '0'),
            ('tweet_mode', 'compat'), ('include_entities', 'false'), ('include_user_entities', 'false'),
            ('send_error_codes', 'true'), ('simple_quoted_tweet', 'false'), ('query_source', ''), ('pc', '1'),
        )
        response_r = self.handled_get(f'{TwitterClient.HOST}/2/search/adaptive.json', params=params)
        response = response_r.json(object_pairs_hook=OrderedDict)
        try:
            tweets = response['globalObjects']['tweets']
            users = response['globalObjects']['users']
        except:
            return {}

        tweets_vals = list(tweets.values())
        len_tweets = len(tweets)

        if not bool(tweets):
            return {}

        b_could_be_quote = False
        the_tweet = None
        user_id_str = None
        if from_whom:
            for user in users:
                if users[user]['screen_name'] == from_whom:
                    user_id_str = user
                    break
            for tweet in tweets:
                if tweets[tweet]['user_id_str'] == user_id_str:
                    the_tweet = tweets[tweet]
                    if the_tweet['is_quote_status'] and len_tweets == 2:
                        b_could_be_quote = True
                    break
        else:
            if (tweets_vals[0].get("is_quote_status") and len_tweets < 3) or (len_tweets == 2 and (tweets_vals[1].get("self_thread") or tweets_vals[1].get("conversation_id"))):
                tweet_index_i = 0
            else:
                tweet_index_i = -1
            # if len_tweets == 2 and tweets_vals[1].get("is_quote_status"):
            if tweets_vals[0].get("is_quote_status") and len_tweets < 3:
                b_could_be_quote = True
            the_tweet = tweets_vals[tweet_index_i]

        if not the_tweet:
            return {}

        tweet_id = the_tweet['id_str']
        user_id_str = the_tweet['user_id_str']
        the_user_id = users[user_id_str]
        the_user_name = the_user_id['screen_name']
        return {"link": f"https://twitter.com/{the_user_name}/status/{tweet_id}", "user_id": user_id_str, "b_could_be_quote": b_could_be_quote}

    def get_twitter_account_status(self, username):
        params = ('variables', f'{{"screen_name":"{username}","withHighlightedLabel":true}}'),
        response = self.handled_get(f'{TwitterClient.HOST}/graphql/-xfUfZsnR_zqjFd-IfrN5A/UserByScreenName',
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
