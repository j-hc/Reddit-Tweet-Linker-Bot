import requests
import requests.auth
import time
from datetime import datetime
import logging
from http import cookiejar

logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M',
                    format='%(asctime)s, %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')


class BlockAll(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False


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
        req_obj.headers = {"User-Agent": self.useragent}
        return req_obj

    def get_token(self):
        client_auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_code)
        post_data = {"grant_type": "password", "username": self.bot_username, "password": self.bot_pass}
        response_token = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, data=post_data,
                                       headers={"User-Agent": self.useragent})
        access_token = response_token.json()['access_token']
        logging.info('got new token: ' + access_token)
        self.req_obj.headers.update({"Authorization": "bearer {0}".format(access_token)})

    def del_comment(self, thingid):
        self.req_obj.post("https://oauth.reddit.com/api/del", data={"id": thingid})
        logging.info("comment removed")

    def send_reply(self, text, id_):
        data = {'api_type': 'json', 'return_rtjson': '1', 'text': text, "thing_id": id_}
        while True:
            rply_req = self.req_obj.post("https://oauth.reddit.com/api/comment", data=data)
            reply_s = rply_req.json()
            try:
                to_log = str(reply_s["json"]["errors"])
                logging.warning(to_log)
                sec_or_min = "min" if "minute" in to_log else "sec"
                num_in_err = int(''.join(list(filter(str.isdigit, to_log))))
                sleep_for = num_in_err + 5 if sec_or_min=="sec" else (num_in_err + 1) * 60
                logging.info("sleeping for {}".format(sleep_for))
                time.sleep(sleep_for)
                continue
            except:
                logging.info("message sent and added into answered list")
                self.already_answered.append(id_)
                break

    def check_last_comment_scores(self, limit=5):
        profile = self.req_obj.get("https://oauth.reddit.com/user/{}.json?limit={}".format(self.bot_username, limit))
        try:
            cm_bodies = profile.json()["data"]["children"]
        except:
            print(profile.content.decode())
            raise
        for cm_body in cm_bodies:
            if cm_body["data"]["score"] <= -1:
                self.del_comment(cm_body["data"]["name"])

    def check_if_already(self, context, depth=2):
        comment_info_req = self.req_obj.get("https://oauth.reddit.com{0}?depth={1}".format(context, str(depth)))
        try:
            authors = comment_info_req.json()[1]['data']['children'][0]['data']['replies']['data']['children']
        except:
            return False

        for author in authors:
            if author['data']['author'] == self.bot_username:
                self.already_answered.append("t1_" + context.split('/')[-2])
                logging.info("added into already answered")
                return True
        return False

    def check_if_already_post(self, linkid):
        if len(self.checked_post) > 35:
            self.clear_(self.checked_post)
        comment_info_req = self.req_obj.get("https://oauth.reddit.com/comments/{}/.json".format(linkid.split('_')[1]))
        for reply in comment_info_req.json()[1]["data"]["children"]:
            if reply["data"]["author"] == self.bot_username:
                self.checked_post.append(linkid)
                return True
        return False

    def clear_(self, list_):
        list = []

    def check_inbox(self):
        if len(self.already_answered) > 35:
            self.clear_(self.already_answered)  # lets not overflow :)
        childrentime = None
        while childrentime is None:
            response_inbox = self.req_obj.get("https://oauth.reddit.com/message/inbox.json")
            if response_inbox.json().setdefault("error", "tokenvar") != "tokenvar":
                return "tokenal"
            try:
                childrentime = response_inbox.json()['data']['children']
            except:
                logging.warning('server mesgul 30sn bekle')
                time.sleep(30)

        t = datetime.now()
        time_unix = time.mktime(t.timetuple())

        custom = ""
        for child in childrentime:
            js = child['data']
            body_lower = str(js['body']).lower()
            commentid_full = js['name']
            sub = str(js['subreddit']).lower()
            summoner = str(js['author']).lower()
            linkid = js['parent_id']
            type = js['type']
            context = str(js['context']).split("?")[0]
            created_utc = int(js['created_utc'])
            if created_utc < int(time_unix) - 4000:
                logging.info('nothing new')
                return False
            elif type == 'username_mention':
                logging.info("username_mention")
                if commentid_full in self.already_answered:
                    logging.info('already answered')
                    continue
                elif self.check_if_already(context):
                    logging.info('already answered to: ' + summoner)
                    continue
                if 'custom_url' in body_lower:
                    custom = body_lower[body_lower.find("(") + 1:body_lower.find(")")]
                toanswer = (commentid_full, linkid, sub, custom, summoner)
                return toanswer

            # BAD BOT
            elif type == "comment_reply" and commentid_full not in self.already_answered and (body_lower == "bad bot" or body_lower == "kotu bot" or body_lower == "kötü bot"):
                logging.info("comment_reply")
                if not self.check_if_already(context):
                    if sub == "turkey" or sub == "turkeyjerky":
                        messagetxt = "mesajımı downvotelayarak kaldırabilirsiniz :("
                    else:
                        messagetxt = "you can downvote me to remove :("

                    logging.info("bad bot comment :(")
                    self.send_reply(text=messagetxt, id_=commentid_full)
                else:
                    logging.info('already answered to: ' + summoner)

    def fetch_subreddit_posts(self, sub, count):
        posts = self.req_obj.get("https://oauth.reddit.com/r/{}/new.json?limit={}".format(sub, str(count)))
        rt = posts.json()["data"]["children"]
        return rt
