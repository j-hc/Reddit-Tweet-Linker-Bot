import requests
import requests.auth
import logging
from http import cookiejar
from .rUtils import rNotif, rBase, rPost
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from ratelimit import sleep_and_retry, limits
from time import sleep

logging.basicConfig(level=logging.INFO, datefmt='%H:%M',
                    format='%(asctime)s, [%(filename)s:%(lineno)d] %(funcName)s(): %(message)s')
logger = logging.getLogger("logger")


class BlockAll(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False


class LimitedList:
    def __init__(self):
        self.list = []

    def append(self, item):
        self.list = self.list[:30]
        self.list.append(item)


class rBot:
    base = "https://oauth.reddit.com"

    def __init__(self, useragent, client_id, client_code, bot_username, bot_pass, exclude_from_all=None):
        self.__pagination_before_all = None
        self.__pagination_before_specific = None
        self.already_thanked = LimitedList()
        self.useragent = useragent
        self.client_id = client_id
        self.client_code = client_code
        self.bot_username = bot_username
        self.bot_pass = bot_pass
        self.req_sesh = self.prep_session()
        self.fetch_token()  # Fetch the token on instantioation (i cant spell for shit)

        if exclude_from_all is None:
            exclude_from_all = []
        for sub in exclude_from_all:
            self.exclude_from_all(sub)

    @sleep_and_retry
    @limits(calls=30, period=60)
    def handled_req(self, method, url, **kwargs):
        while True:
            if method == 'POST':
                response = self.req_sesh.post(url, **kwargs)
            elif method == 'GET':
                response = self.req_sesh.get(url, **kwargs)
            elif method == 'PUT':
                response = self.req_sesh.put(url, **kwargs)
            else:
                response = NotImplemented
            if response.status_code == 403 or response.status_code == 401:
                self.fetch_token()
                sleep(0.7)
                continue
            else:
                return response

    def prep_session(self):
        req_sesh = requests.Session()
        retries = Retry(total=5,
                        backoff_factor=1,
                        status_forcelist=[500, 502, 503, 504, 404])
        req_sesh.mount('https://', HTTPAdapter(max_retries=retries))
        req_sesh.cookies.set_policy(BlockAll())  # we dont need cookies
        req_sesh.headers.update({"User-Agent": self.useragent})
        return req_sesh

    @staticmethod
    def get_new_token(client_id_, client_code_, bot_username_, bot_pass_, useragent_):
        client_auth = requests.auth.HTTPBasicAuth(client_id_, client_code_)
        post_data = {"grant_type": "password", "username": bot_username_, "password": bot_pass_}
        response_token = requests.post(f"{rBase}/api/v1/access_token", auth=client_auth, data=post_data,
                                       headers={"User-Agent": useragent_})
        access_token = response_token.json()['access_token']
        return access_token

    def fetch_token(self):
        token = rBot.get_new_token(self.client_id, self.client_code, self.bot_username, self.bot_pass, self.useragent)
        logger.info('got new token: ' + token)
        self.req_sesh.headers.update({"Authorization": f"bearer {token}"})

    def read_notifs(self, notifs):
        ids = [notif.id_ for notif in notifs]
        ids = ','.join(ids)
        self.handled_req('POST', f"{self.base}/api/read_message", data={"id": ids})
        logger.info("read the notif")

    def del_comment(self, thingid):
        self.handled_req('POST', f"{self.base}/api/del", data={"id": thingid})
        logger.info("comment removed")

    def send_reply(self, text, thing):
        data = {'api_type': 'json', 'return_rtjson': '1', 'text': text, "thing_id": thing.id_}
        reply_req = self.handled_req('POST', f"{self.base}/api/comment", data=data)
        reply_s = reply_req.json()
        try:
            to_log = str(reply_s["json"]["errors"])
            logger.warning(to_log)
            sec_or_min = "min" if "minute" in to_log else "sec"
            num_in_err = int(''.join(list(filter(str.isdigit, to_log))))
            sleep_for = num_in_err + 5 if sec_or_min == "sec" else (num_in_err * 60) + 5
            logger.info(f"sleeping for {sleep_for}")
            return sleep_for
        except KeyError:
            logger.info("message sent")
            return 0

    def check_last_comment_scores(self, limit=20):
        profile = self.handled_req('GET', f"{self.base}/user/{self.bot_username}/comments", params={"limit": limit})
        cm_bodies = profile.json()["data"]["children"]
        score_nd_id = {}
        for cm_body in cm_bodies:
            score_nd_id.update({cm_body["data"]["name"]: cm_body["data"]["score"]})
        return score_nd_id

    def check_inbox(self, rkind):
        unread_notifs_req = self.handled_req('GET', f"{self.base}/message/unread")
        unread_notifs = unread_notifs_req.json()['data']['children']

        for unread_notif in unread_notifs:
            if unread_notif['kind'] == rkind:
                yield rNotif(unread_notif)

    def get_info_by_id(self, thing_id):
        thing_info = self.handled_req('GET', f'{self.base}/api/info', params={"id": thing_id})
        return thing_info.json()['data']['children'][0]

    def fetch_posts_from_subreddits(self, subs, limit, pagination=True, stop_if_saved=True, skip_if_nsfw=True, custom_uri=None):
        params = {"limit": limit}
        if pagination and self.__pagination_before_specific:
            params.update({"before": self.__pagination_before_specific})

        if custom_uri:
            uri = custom_uri
        else:
            subs = '+'.join(subs)
            uri = f'{self.base}/r/{subs}/new'

        posts_req = self.handled_req('GET', uri, params=params)
        posts = posts_req.json()["data"]["children"]
        if not bool(posts):
            self.__pagination_before_specific = None
            params.update({"before": None})
            return
        for post_index in range(0, len(posts)):
            the_post = rPost(posts[post_index])
            if skip_if_nsfw and the_post.over_18:
                continue
            if stop_if_saved and the_post.is_saved:
                break
            if post_index == 0:
                self.save_thing_by_id(the_post.id_)
                if pagination:
                    self.__pagination_before_specific = the_post.id_
            yield the_post

    def fetch_posts_from_own_multi(self, multiname, limit, **kwargs):
        uri = f"{self.base}/user/{self.bot_username}/m/{multiname}/new/"
        return self.fetch_posts_from_subreddits(subs=None, limit=limit, custom_uri=uri, **kwargs)

    def fetch_posts_from_all(self, limit=100, pagination=True, stop_if_saved=True, skip_if_nsfw=True):
        params = {"limit": limit}
        if pagination and self.__pagination_before_all:
            params.update({"before": self.__pagination_before_all})
        posts_req = self.handled_req('GET', f'{self.base}/r/all/new', params=params)
        posts = posts_req.json()["data"]["children"]
        if not bool(posts):
            self.__pagination_before_all = None
            return
        for post_index in range(0, len(posts)):
            the_post = rPost(posts[post_index])
            if skip_if_nsfw and the_post.over_18:
                continue
            if stop_if_saved and the_post.is_saved:
                break
            if post_index == 0:
                self.save_thing_by_id(the_post.id_)
                if pagination:
                    self.__pagination_before_all = the_post.id_
            yield the_post

    def exclude_from_all(self, sub):
        data = {'model': f'{{"name":"{sub}"}}'}
        self.handled_req('PUT', f'{self.base}/api/filter/user/{self.bot_username}/f/all/r/{sub}', data=data)

    def save_thing_by_id(self, thing_id):  # this for checking if the thing was seen before
        self.handled_req('POST', f'{self.base}/api/save', params={"id": thing_id})
        logger.info(f'{thing_id} saved')

    def create_or_update_multi(self, multiname, subs, visibility="private"):
        subreddits_d = []
        for sub in subs:
            subreddits_d.append(f'{{"name":"{sub}"}}')
        subs_quoted = ', '.join(subreddits_d)
        data = {
            'multipath': f'user/{self.bot_username}/m/{multiname}',
            'model': f'{{"subreddits":[{subs_quoted}], "visibility":"{visibility}"}}'
        }
        self.handled_req('PUT', f"{self.base}/api/multi/user/{self.bot_username}/m/{multiname}", data=data)
        logger.info('created or updated a multi')
