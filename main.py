from api_and_twitterparsing import *
import rbot
from info import useragent, client_id, client_code, bot_username, bot_pass
from strings import tr, en
from time import sleep
import traceback

def is_text_post(jsurl):
    if jsurl[0]['data']['children'][0]['data'].get("post_hint"):
        return True
    else:
        return False

def mainloop():
    twitterlinker = rbot.rBot(useragent, client_id, client_code, bot_username, bot_pass)
    twitterlinker.get_token()
    score_check_step = 0
    while True:
        # INBOX CHECK
        id_urlname = twitterlinker.check_inbox()
        if id_urlname == "tokenal":
            twitterlinker.get_token()
            continue
        if id_urlname:
            id_, linkid, subreddit, customurl, user = id_urlname
            if subreddit == "turkey" or subreddit == "turkeyjerky" or subreddit == "testyapiyorum":
                lang_arg = 'tur'
            else:
                lang_arg = 'eng'

            if lang_arg == "tur":
                l_res = tr
            else:
                l_res = en
            print('SUMMONLANDIM #####')
            print(lang_arg)

            response = requests.get('https://www.reddit.com/{}/.json'.format(linkid.split('_')[1]),
                                    headers={"User-Agent": useragent})
            jsurl = response.json()
            if customurl:
                pic = customurl
            else:
                pic = jsurl[0]['data']['children'][0]['data']['url']

            messagetxt = l_res["hello"].format(user) + "\r\n" + l_res["introduction"] + "\r\n"
            reason = None
            if is_text_post(jsurl):
                print('text post')
                reason = "\r\n" + l_res["no_image_err"]
                # twitterlinker.send_reply(l_res["introduction"] + "\r\n" + l_res["no_image_err"], id_)
                # continue
            else:
                textt = vision_ocr(pic)
                prepped_text = prep_text(textt)
                if prepped_text.get("result") == "success":
                    possible_at = prepped_text.get("possible_at")
                    possibe_search_text = prepped_text.get("possibe_search_text")

                    search_twitter = twitter_search(possible_at, possibe_search_text, lang_arg)
                    print('OCR DONE')
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
                    if prepped_text.get("reason") == REASON_NO_TEXT:
                        reason = l_res["reason_notext"]
                    else:
                        reason = l_res["reason_default"]

            if reason:
                messagetxt += l_res["because"].format(reason)
            messagetxt += l_res["outro"]

            twitterlinker.send_reply(messagetxt, id_)
            print('DONE')
            continue

        #SUBREDDIT FEED CHECK
        last_submissions = twitterlinker.fetch_subreddit_posts("turkey", 2)
        for last_submission in last_submissions:
            l_res = tr
            curr_post = last_submission["data"]
            pThing = curr_post["name"]
            if curr_post.get("post_hint") and pThing not in twitterlinker.checked_post:
                if not twitterlinker.check_if_already_post(pThing):
                    username, twitlink, atliatsiz, wordcount, reasons = tesseract(curr_post["url"], "tur", need_at=False)
                    if username and not atliatsiz:
                        backup_link = capture_tweet_arch(twitlink)
                        print("TWEET POSTU BULUNDU. BACKUP ALINDI")
                        messagetxt = l_res["introduction"] + "\r\n" + l_res["success"].format(username, twitlink) \
                                     + "\r\n\n" + l_res["archive_info"].format(backup_link) + l_res["outro"]
                        twitterlinker.send_reply(messagetxt, pThing)
                    else:
                        print("tweet postu degil")
                else:
                    print("feed check: cevaplanmis")
                twitterlinker.checked_post.append(pThing)
            else:
                print("pic degil ya da cevaplandi")

        # SCORE CHECK
        if score_check_step == 4:
            twitterlinker.check_last_comment_scores()
            score_check_step = 0
        else:
            score_check_step += 1

        print('\r\nbekleniyor')
        sleep(17)

while True:
    try:
        mainloop()
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)
        raise