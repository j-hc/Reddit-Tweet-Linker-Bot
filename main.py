from api_and_twitterparsing import *
from rbot import rBot, rPostListing
from info import useragent, client_id, client_code, bot_username, bot_pass
from strings import tr, en
from time import sleep
import queue
import threading

subs_listening = ["svihs", "turkey"]


def is_img_post(jsurl):
    if not jsurl['data'].get("is_self"):
        if str(jsurl['data']['url']).split(".")[-1].lower() in ["jpg", "jpeg", "png", "tiff", "bmp"]:
            return True
        else:
            return False
    else:
        return False


def replier(to_reply_q):
    while True:
        to_reply = to_reply_q.get()
        replied = twitterlinker.send_reply(to_reply["text"], to_reply["thing"])
        if replied != 0:
            to_reply_q.put(to_reply)
            sleep(replied)


def sub_feed_checking(to_answer_q):
    # SUBREDDIT FEED CHECK
    while True:
        last_submissions = twitterlinker.fetch_subreddit_posts(subs_listening, 2)
        for last_submission in last_submissions:
            curr_post = rPostListing(last_submission)
            if not twitterlinker.check_if_already_post(curr_post.commentid_full):
                if is_img_post(last_submission):
                    to_answer_q.put({"notif": curr_post, "type": "normal"})
                    print("sub feed checker: " + curr_post.commentid_full)
                else:
                    print("thiss not pic: " + curr_post.commentid_full)
            else:
                print("already: " + curr_post.commentid_full, end=' | ')
        print()
        sleep(30)


def check_notifs(to_answer_q):
    while True:
        # INBOX CHECK
        inbox = twitterlinker.check_inbox()
        if inbox:
            if inbox == "tokenal":
                twitterlinker.get_token()
            else:
                post_obj = inbox
                print('inbox checkr: ' + post_obj["notif"].commentid_full)
                to_answer_q.put(post_obj)
        sleep(12)


def searching(to_answer_q, to_reply_q):
    while True:
        postobj = to_answer_q.get()
        if postobj["notif"].lang_arg == "tur":
            l_res = tr
        else:
            l_res = en

        if postobj["type"] == "badbot":
            print("bad bot")
            to_reply_q.put({"text": l_res["badbot"], "thing": postobj["notif"].commentid_full})
            continue
        elif postobj["type"] == "goodbot":
            print("good bot")
            to_reply_q.put({"text": l_res["goodbot"], "thing": postobj["notif"].commentid_full})
            continue
        else:
            # NOT A COMMENT_REPLY
            postobj = postobj["notif"]
        response = requests.get('https://www.reddit.com/{}/.json'.format(postobj.linkid.split('_')[1]),
                                headers={"User-Agent": useragent})
        jsurl = response.json()[0]['data']['children'][0]
        if postobj.custom:
            pic = postobj.custom
        else:
            pic = jsurl['data']['url']

        messagetxt = l_res["hello"].format(postobj.summoner) + "\r\n" + l_res["introduction"] + "\r\n"
        reason = None
        need_at = False if postobj.listing is False else True
        if not is_img_post(jsurl):
            print('text post')
            reason = "\r\n" + l_res["no_image_err"]
        else:
            textt = vision_ocr(pic)
            prepped_text = prep_text(textt, need_at=need_at)
            if prepped_text.get("result") == "success":
                possible_at = prepped_text.get("possible_at")
                possibe_search_text = prepped_text.get("possibe_search_text")

                search_twitter = twitter_search(possible_at, possibe_search_text, postobj.lang_arg)
                if search_twitter.get("result") == "success":
                    username = search_twitter.get("username")
                    twitlink = search_twitter.get("twitlink")
                    atliatsiz = search_twitter.get("atliatsiz")

                    print("getting backup archive")
                    backup_link = capture_tweet_arch(twitlink)

                    if atliatsiz:
                        messagetxt += l_res["couldnt_find_at"].format(twitlink)
                    elif not atliatsiz:
                        messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + \
                                      l_res["archive_info"].format(backup_link)
                else:
                    print("cogh garip")
                    continue
            elif postobj.listing:
                print("not a tweet: " + postobj.linkid)
                continue
            else:
                if prepped_text.get("reason") == Reasons.NO_TEXT:
                    reason = l_res["reason_notext"]
                else:
                    reason = l_res["reason_default"]

        if reason:
            messagetxt += l_res["because"].format(reason)
        messagetxt += l_res["outro"]

        to_reply_q.put({"text": messagetxt, "thing": postobj.commentid_full})
        print('search DONE: ' + postobj.commentid_full)


if __name__ == "__main__":
    twitterlinker = rBot(useragent, client_id, client_code, bot_username, bot_pass)

    to_answer_q = queue.Queue()
    to_reply_q = queue.Queue()
    checking_t = threading.Thread(target=check_notifs, args=(to_answer_q,), daemon=True)
    searching_t = threading.Thread(target=searching, args=(to_answer_q, to_reply_q), daemon=True)
    replier_t = threading.Thread(target=replier, args=(to_reply_q,), daemon=True)
    sub_listener = threading.Thread(target=sub_feed_checking, args=(to_answer_q,), daemon=True)

    checking_t.start()
    searching_t.start()
    sub_listener.start()
    replier_t.start()

    while True:
        print(f"\033[4msearching jobs: {[search['notif'] for search in list(to_answer_q.queue)]}\033[0m")
        print(f"\033[4mreplying jobs: {[replyy['thing'] for replyy in list(to_reply_q.queue)]}\033[0m")
        sleep(9)
