import requests
import requests.auth
import logging
from http import cookiejar
from .rUtils import rNotif, rBase, rPost
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from ratelimit import sleep_and_retry, limits
from time import sleep, time
from .PostFetcher import PostFetcher

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

    def append_elem(self, item):
        self.list = self.list[-30:]
        self.list.append(item)


class rBot:
    base = "https://oauth.reddit.com"

    def __init__(self, useragent, client_id, client_code, bot_username, bot_pass):
        self.__pagination_before_all = None
        self.__pagination_before_specific = None
        self.already_thanked = LimitedList()

        self.next_token_t = 0

        self.useragent = useragent
        self.client_id = client_id
        self.client_code = client_code
        self.bot_username = bot_username
        self.bot_pass = bot_pass
        self.req_sesh = self.prep_session()
        self.get_new_token()  # Fetch the token on instantioation (i cant spell for shit)

    @sleep_and_retry
    @limits(calls=30, period=60)
    def handled_req(self, method, url, **kwargs):
        if self.next_token_t <= int(time()):
            self.get_new_token()

        while True:
            try:
                response = self.req_sesh.request(method, url, **kwargs)
            except requests.exceptions.RetryError:
                sleep(30)
                continue

            if response.status_code == 401:
                self.get_new_token()
                continue
            elif response.status_code == 403:
                logger.warning("Forbidden")
                return None
            else:
                return response

    def prep_session(self):
        req_sesh = requests.Session()
        retries = Retry(total=5,
                        backoff_factor=3,
                        status_forcelist=[500, 502, 503, 504, 404])
        req_sesh.mount('https://', HTTPAdapter(max_retries=retries))
        req_sesh.cookies.set_policy(BlockAll())
        req_sesh.headers.update({"User-Agent": self.useragent})
        return req_sesh

    def get_new_token(self):
        client_auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_code)
        post_data = {"grant_type": "password", "username": self.bot_username, "password": self.bot_pass}
        response_token_ = requests.post(f"{rBase}/api/v1/access_token", auth=client_auth, data=post_data,
                                        headers={"User-Agent": self.useragent})
        try:
            response_token = response_token_.json()
        except:
            raise Exception(response_token_.text)
        self.next_token_t = int(time()) + response_token['expires_in'] - 15
        access_token = response_token['access_token']
        logger.info('got new token: ' + access_token)
        self.req_sesh.headers.update({"Authorization": f"bearer {access_token}"})

    def read_notifs(self, notifs):
        ids = [notif.id_ for notif in notifs]
        ids = ','.join(ids)
        self.handled_req('POST', f"{self.base}/api/read_message", data={"id": ids})
        logger.info(f"read the notifs: {str([x for x in notifs])}")

    def del_comment(self, thingid):
        self.handled_req('POST', f"{self.base}/api/del", data={"id": thingid})
        logger.info(f"comment removed: {thingid}")

    def send_reply(self, text, thing):
        if isinstance(thing, str):
            thing_id = thing
        else:
            thing_id = thing.id_
        data = {'api_type': 'json', 'return_rtjson': '1', 'text': text, "thing_id": thing_id}
        reply_req = self.handled_req('POST', f"{self.base}/api/comment", data=data)
        if reply_req is None:
            return 0
        try:
            reply_s = reply_req.json()
        except:
            raise Exception(reply_req)
        try:
            to_log = reply_s["json"]["errors"]
            logger.warning(to_log)
            if to_log[0][0] != "DELETED_COMMENT":
                to_log = str(to_log)
                sec_or_min = "min" if "minute" in to_log else "sec"
                num_in_err = int(''.join(list(filter(str.isdigit, to_log))))
                sleep_for = num_in_err + 5 if sec_or_min == "sec" else (num_in_err * 60) + 5
                logger.info(f"sleeping for {sleep_for}")
                return sleep_for
            else:
                return 0
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

    def check_inbox(self, rkind, read_if_not_rkind=True):
        unread_notifs_req = self.handled_req('GET', f"{self.base}/message/unread")
        unread_notifs = unread_notifs_req.json()['data']['children']

        for unread_notif in unread_notifs:
            the_notif = rNotif(unread_notif)
            if unread_notif['kind'] == rkind:
                yield the_notif
            elif read_if_not_rkind:
                self.read_notifs([the_notif])

    def get_info_by_id(self, thing_id):
        thing_info = self.handled_req('GET', f'{self.base}/api/info', params={"id": thing_id}).json()
        if not bool(thing_info["data"]["children"]):
            return None
        elif thing_info["data"]["children"][0]["kind"] == "t3":
            return rPost(thing_info["data"]["children"][0])
        else:
            return thing_info

    def init_new_fetcher(self, subs=None, limit=50, sort_by='new', pagination=True, stop_if_saved=True, skip_if_nsfw=False,
                         before_or_after='before', pagination_param=None, multiname=None):
        return PostFetcher(self, subs, multiname, limit, sort_by, pagination, stop_if_saved, skip_if_nsfw,
                           before_or_after, pagination_param)

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
        logger.info(f'created or updated a multi named {multiname}')
