import requests
import requests.auth
import json
import time
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d:%H:%M',
                    format='%(asctime)s, %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',)

from http import cookiejar
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
        access_token = json.loads(response_token.content.decode())['access_token']
        logging.info('yeni token alındı: ' + access_token)
        self.req_obj.headers.update({"Authorization": "bearer {0}".format(access_token)})

    def del_comment(self, thingid):
        self.req_obj.post("https://oauth.reddit.com/api/del", data={"id": thingid})
        logging.info("message deleted")

    def send_reply(self, text, id_):
        data = {'api_type': 'json', 'return_rtjson': '1', 'text': text, "thing_id": id_}
        self.req_obj.post("https://oauth.reddit.com/api/comment", data=data)
        logging.info("message sent")

    def check_last_comment_scores(self, limit=5):
        profile = self.req_obj.get("https://oauth.reddit.com/user/{}.json?limit={}".format(self.bot_username, limit))
        cm_bodies = profile.json()["data"]["children"]
        for cm_body in cm_bodies:
            if cm_body["data"]["score"] <= -1:
                self.del_comment(cm_body["data"]["name"])
                logging.info("yorum silindi")

    def check_if_already(self, linkid, commentid):
        comment_info_req = self.req_obj.get("https://oauth.reddit.com/comments/{}/_/{}.json?depth=2".format(linkid.split('_')[1],
                                                                            commentid.split('_')[1]))
        try:
            authors = json.loads(comment_info_req.content.decode())[1]['data']['children'][0]['data']['replies']['data']['children']
        except:
            return False

        for author in authors:
            if author['data']['author'] == self.bot_username:
                return True
        return False

    def check_if_already_post(self, linkid):
        comment_info_req = self.req_obj.get("https://oauth.reddit.com/comments/{}/.json".format(linkid.split('_')[1]))
        for reply in comment_info_req.json()[1]["data"]["children"]:
            if reply["data"]["author"] == self.bot_username:
                return True
        return False

    def check_inbox(self, alreadyanswered):
        childrentime = None
        while childrentime is None:
            response_inbox = self.req_obj.get("https://oauth.reddit.com/message/inbox.json")
            try:
                error401 = response_inbox.json()['error']
                logging.error(response_inbox.json())
                return "tokenal"
            except:
                pass

            try:
                childrentime = json.loads(response_inbox.content.decode())['data']['children']
            except:
                logging.warning('server mesgul 30sn bekle')
                time.sleep(30)

        t = datetime.now()
        time_unix = time.mktime(t.timetuple())

        custom = ""
        for m in range(0, len(childrentime)):
            js = childrentime[m]['data']
            body_lower = str(js['body']).lower()
            if int(js['created_utc']) < int(time_unix) - 4000:
                logging.info('yeni bise yok')
                return False
            elif js['type'] == 'username_mention':
                commentid_full = js['name']
                sub = str(js['subreddit']).lower()
                summoner = js['author']
                linkid = js['parent_id']
                if commentid_full in alreadyanswered:
                    logging.info('zaten cevaplanmış')
                    continue
                elif self.check_if_already(linkid, commentid_full):
                    logging.info('zaten cevaplanmış ' + summoner)
                    alreadyanswered.append(commentid_full)
                    continue
                mention_content = js['body']
                if 'custom_url' in mention_content:
                    custom = mention_content[mention_content.find("(") + 1:mention_content.find(")")]
                toanswer = (commentid_full, linkid, sub, custom, summoner)
                return toanswer

            # BAD BOT
            elif js['type'] == "comment_reply" and body_lower == "bad bot" or body_lower == "kotu bot" or body_lower == "kötü bot":
                sub = str(js['subreddit']).lower()
                if sub == "turkey" or sub == "turkeyjerky":
                    messagetxt = "mesajımı downvotelayarak kaldırabilirsiniz :("
                else:
                    messagetxt = "you can downvote me to remove :("
                self.send_reply(text=messagetxt, id_=js['name'])


    def fetch_subreddit_posts(self, sub, count):
        posts = self.req_obj.get("https://oauth.reddit.com/r/{}/new.json?limit={}".format(sub, str(count)))
        return posts.json()["data"]["children"]
