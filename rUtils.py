from info import useragent
import requests
from time import sleep

rBase = "https://www.reddit.com"

# Some stuff.. ------------------
turkish_subs = ["turkey", "turkeyjerky", "testyapiyorum", "kgbtr", "svihs"]
# -------------------------------


class rNotif:
    def __init__(self, notif):
        # self.kind = notif['kind']  # kind
        content = notif['data']
        self.author = content['author']  # summoner
        self.body = content['body'].lower()  # body lowered
        self.subreddit = content['subreddit'].lower()  # sub
        if self.subreddit in turkish_subs:
            self.lang = 'tur'
        else:
            self.lang = 'eng'
        # self.parentid = content['parentid']  # the post or mentioner
        self.id_ = content['name']  # answer to this. represents the comment with t1 prefix
        self.rtype = content['type']  # comment_reply or user_mention
        context = content['context']  # /r/SUB/comments/POST_ID/TITLE/COMMENT_ID/
        context_split = str(context).split('/')
        self.post_id = context_split[4]  # post id without t3 prefix
        # self.id_no_prefix = context_split[6]  # comment id without t1 prefix

    def __repr__(self):
        return f"(NotifObject: {self.id_})"


class rPost:
    def __init__(self, post):
        content = post['data']
        self.id_ = content['name']  # answer to this. represents the post with t3 prefix
        self.is_self = content['is_self']  # text or not
        self.author = content['author']  # author
        self.url = content['url']  # url
        self.subreddit = content['subreddit'].lower()
        if self.subreddit in turkish_subs:
            self.lang = 'tur'
        else:
            self.lang = 'eng'
        # self.listing = None  # true if from sub feed listener

    def __eq__(self, other):
        if self.id_ == other.id_:
            return True
        return False

    def __repr__(self):
        return f"(PostObject: {self.id_})"


class rUtils:
    @staticmethod
    def __handled_get(url, **kwargs):
        while True:
            response = requests.get(url, **kwargs)
            if response.status_code != 200:
                sleep(20)
            else:
                break
        return response

    @staticmethod
    def check_if_already_post(post, checked_posts, username):
        if post in checked_posts:
            return True
        checked_posts.append(post)
        p_name = post.id_.split('_')[1]
        comment_info_req = rUtils.__handled_get(f"{rBase}/{p_name}/.json", headers={"User-Agent": useragent})
        for reply in comment_info_req.json()[1]["data"]["children"]:
            if reply["data"]["author"] == username:
                return True
        return False

    @staticmethod
    def fetch_post_from_notif(notif):
        response = rUtils.__handled_get(f"{rBase}/{notif.post_id}/.json", headers={"User-Agent": useragent})
        post = response.json()[0]['data']['children'][0]
        return rPost(post)

    @staticmethod
    def fetch_subreddit_posts(subs, limit):
        for sub in subs:
            posts_req = rUtils.__handled_get(f"{rBase}/r/{sub}/new.json", headers={"User-Agent": useragent},
                                           params={"limit": str(limit)})
            posts = posts_req.json()["data"]["children"]
            for post in posts:
                yield rPost(post)

    @staticmethod
    def is_img_post(post):
        if not post.is_self:
            if post.url.split(".")[-1].lower() in ["jpg", "jpeg", "png", "tiff", "bmp"]:
                return True
            else:
                return False
        else:
            return False
