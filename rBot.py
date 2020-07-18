import requests
import logging
from http import cookiejar
from rUtils import get_token, rNotif
from time import sleep


logging.basicConfig(level=logging.INFO, datefmt='%H:%M',
                    format='%(asctime)s, [%(filename)s:%(lineno)d] %(funcName)s(): %(message)s', filename='rbot.log')
logger = logging.getLogger("logger")


class BlockAll(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False


class rBot:
    base = "https://oauth.reddit.com"

    def __init__(self, useragent, client_id, client_code, bot_username, bot_pass):
        self.useragent = useragent
        self.client_id = client_id
        self.client_code = client_code
        self.bot_username = bot_username
        self.bot_pass = bot_pass
        self.req_sesh = self.prep_session()
        self.fetch_token()  # Fetch the token on instantioation (i cant spell for shit)

    def handled_get(self, url, **kwargs):
        response = self.req_sesh.get(url, **kwargs)
        if response.status_code == 403 or response.status_code == 401:
            self.fetch_token()
            response = self.req_sesh.get(url, **kwargs)
        elif response.status_code == 503:
            logger.info("servers busy wait for 30s")
            sleep(30)
            response = self.req_sesh.post(url, **kwargs)
        elif response.status_code == 404:  # why tf 404 tho
            logger.info("404 try again")
            sleep(5)
            response = self.req_sesh.post(url, **kwargs)
        return response

    def handled_post(self, url, **kwargs):
        response = self.req_sesh.post(url, **kwargs)
        if response.status_code == 403 or response.status_code == 401:
            self.fetch_token()
            response = self.req_sesh.post(url, **kwargs)
        elif response.status_code == 503:
            logger.info("servers busy wait for 30s")
            sleep(30)
            response = self.req_sesh.post(url, **kwargs)
        return response

    def prep_session(self):
        req_sesh = requests.Session()
        req_sesh.cookies.set_policy(BlockAll())  # we dont need cookies
        req_sesh.headers.update({"User-Agent": self.useragent})
        return req_sesh

    def fetch_token(self):
        token = get_token(self.client_id, self.client_code, self.bot_username, self.bot_pass, self.useragent)
        logger.info('got new token: ' + token)
        self.req_sesh.headers.update({"Authorization": f"bearer {token}"})

    def read_notif(self, notif):
        self.handled_post(f"{self.base}/api/read_message", data={"id": notif.id_})
        logger.info("read the notif")

    def del_comment(self, thingid):
        self.handled_post(f"{self.base}/api/del", data={"id": thingid})
        logger.info("comment removed")

    def send_reply(self, text, thing):
        data = {'api_type': 'json', 'return_rtjson': '1', 'text': text, "thing_id": thing.id_}
        reply_req = self.handled_post(f"{self.base}/api/comment", data=data)
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

    def check_last_comment_scores(self, limit=5):
        profile = self.handled_get(f"{self.base}/user/{self.bot_username}.json?limit={limit}")
        try:
            cm_bodies = profile.json()["data"]["children"]
        except:
            logger.exception(profile.content.decode() + "\n")
        for cm_body in cm_bodies:
            yield cm_body

    def check_inbox(self):
        unread_notifs_req = self.handled_get(f"{self.base}/message/unread.json")
        try:
            unread_notifs = unread_notifs_req.json()['data']['children']
        except:
            logger.exception(unread_notifs_req.content.decode() + "\n")

        for unread_notif in unread_notifs:
            notif = rNotif(unread_notif)
            self.read_notif(notif)
            yield notif
