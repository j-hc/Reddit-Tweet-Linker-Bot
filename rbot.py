import requests
import requests.auth
import time
from datetime import datetime
import logging
from http import cookiejar

turkish_subs = ["turkey", "turkeyjerky", "testyapiyorum", "kgbtr"]

logging.basicConfig(level=logging.INFO, datefmt='%H:%M',
                    format='%(asctime)s, [%(filename)s:%(lineno)d] %(funcName)s(): %(message)s')
logger = logging.getLogger("logger")


class BlockAll(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False


class rPostListing():
    def __init__(self, child):
        js = child['data']
        self.commentid_full = self.linkid = js['name']
        sub = str(js['subreddit']).lower()
        if sub in turkish_subs:  # #######tr subs
            self.lang_arg = 'tur'
        else:
            self.lang_arg = 'eng'
        self.summoner = str(js['author']).lower()
        self.custom = None
        self.listing = True
        self.permalink = js["permalink"]

    def __repr__(self):
        return "postobject: www.reddit.com" + self.permalink


class rPost():
    def __init__(self, child):
        js = child['data']
        self.body_lower = str(js['body']).lower()
        self.commentid_full = js['name']
        sub = str(js['subreddit']).lower()
        if sub == "turkey" or sub == "turkeyjerky" or sub == "testyapiyorum":  # #######tr subs
            self.lang_arg = 'tur'
        else:
            self.lang_arg = 'eng'
        self.summoner = str(js['author']).lower()
        self.ptype = js['type']
        self.context = str(js['context']).split("?")[0]
        self.linkid = 't3_' + self.context.split('/')[4]
        self.created_utc = int(js['created_utc'])
        self.custom = None
        self.listing = False
        self.permalink = self.context

    def __repr__(self):
        return "postobject: www.reddit.com" + self.permalink


class rBot():
    def __init__(self, useragent, client_id, client_code, bot_username, bot_pass):
        self.useragent = useragent
        self.client_id = client_id
        self.client_code = client_code
        self.bot_username = bot_username
        self.bot_pass = bot_pass
        self.already_answered = []
        self.checked_post = []
        self.req_obj = self.prep_session()

    def prep_session(self):
        req_obj = requests.Session()
        req_obj.cookies.set_policy(BlockAll())  # we dont need cookies
        req_obj.headers.update({"User-Agent": self.useragent})
        return req_obj

    def get_token(self):
        client_auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_code)
        post_data = {"grant_type": "password", "username": self.bot_username, "password": self.bot_pass}
        response_token = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, data=post_data,
                                       headers={"User-Agent": self.useragent})
        access_token = response_token.json()['access_token']
        logger.info('got new token: ' + access_token)
        self.req_obj.headers.update({"Authorization": "bearer {0}".format(access_token)})

    def del_comment(self, thingid):
        self.req_obj.post("https://oauth.reddit.com/api/del", data={"id": thingid})
        logger.info("comment removed")

    def send_reply(self, text, id_):
        data = {'api_type': 'json', 'return_rtjson': '1', 'text': text, "thing_id": id_}
        rply_req = self.req_obj.post("https://oauth.reddit.com/api/comment", data=data)
        reply_s = rply_req.json()
        try:
            to_log = str(reply_s["json"]["errors"])
            logging.warning(to_log)
            sec_or_min = "min" if "minute" in to_log else "sec"
            num_in_err = int(''.join(list(filter(str.isdigit, to_log))))
            sleep_for = num_in_err + 5 if sec_or_min == "sec" else (num_in_err * 60) + 5
            logger.info("sleeping for {}".format(sleep_for))
            return sleep_for
        except:
            logger.info("message sent")
            return 0

    def check_last_comment_scores(self, limit=5):
        profile = self.req_obj.get("https://oauth.reddit.com/user/{}.json?limit={}".format(self.bot_username, limit))
        cm_bodies = profile.json()["data"]["children"]
        for cm_body in cm_bodies:
            if cm_body["data"]["score"] <= -1:
                self.del_comment(cm_body["data"]["name"])

    def check_if_already(self, context, depth=2):
        if len(self.already_answered) > 35:
            self.already_answered = []  # lets not overflow :)
        commentidfull = "t1_" + context.split('/')[-2]
        if commentidfull in self.already_answered:
            return True
        self.already_answered.append(commentidfull)
        comment_info_req = self.req_obj.get("https://oauth.reddit.com{0}?depth={1}".format(context, str(depth)))
        try:
            authors = comment_info_req.json()[1]['data']['children'][0]['data']['replies']['data']['children']
        except:
            return False

        for author in authors:
            if author['data']['author'] == self.bot_username:
                logger.info("added into already answered")
                return True
        return False

    def check_if_already_post(self, linkid):
        if len(self.checked_post) > 35:
            self.checked_post = []
        if linkid in self.checked_post:
            return True
        self.checked_post.append(linkid)
        comment_info_req = self.req_obj.get("https://oauth.reddit.com/comments/{}/.json".format(linkid.split('_')[1]))
        for reply in comment_info_req.json()[1]["data"]["children"]:
            if reply["data"]["author"] == self.bot_username:
                return True
        return False

    def check_inbox(self):
        childrentime = None
        while childrentime is None:
            response_inbox = self.req_obj.get("https://oauth.reddit.com/message/inbox.json")
            if response_inbox.json().get("error"):
                return "tokenal"
            try:
                childrentime = response_inbox.json()['data']['children']
            except:
                logging.warning('server mesgul 30sn bekle')
                time.sleep(30)

        t = datetime.now()
        time_unix = time.mktime(t.timetuple())

        for child in childrentime:
            new_notif = rPost(child)
            if new_notif.created_utc < int(time_unix) - 4000:
                logger.info('nothing new')
                return False
            elif self.check_if_already(new_notif.context):
                logger.info('already answered to: ' + new_notif.summoner)
                continue
            elif new_notif.ptype == 'username_mention':
                if 'custom_url' in new_notif.body_lower:
                    new_notif.custom = new_notif.body_lower[
                                       new_notif.body_lower.find("(") + 1:new_notif.body_lower.find(")")]
                toanswer = {"notif": new_notif, "type": "normal"}
                return toanswer
            elif new_notif.ptype == "comment_reply":
                # BAD BOT
                if any(x in new_notif.body_lower for x in ["bad bot", "kotu bot", "kötü bot"]):
                    toanswer = {"notif": new_notif, "type": "badbot"}
                    return toanswer
                # GOOD BOT
                elif any(x in new_notif.body_lower for x in ["good bot", "iyi bot"]):
                    toanswer = {"notif": new_notif, "type": "goodbot"}
                    return toanswer

    def fetch_subreddit_posts(self, subs, count):
        for sub in subs:
            posts = self.req_obj.get(f"https://oauth.reddit.com/r/{sub}/new.json?limit={str(count)}")
            rtt = posts.json()["data"]["children"]
            for rt in rtt:
                yield rt
