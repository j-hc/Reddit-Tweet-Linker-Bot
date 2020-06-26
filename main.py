from api_and_twitterparsing import *
import rbot
from info import useragent, client_id, client_code, bot_username, bot_pass, ocr_api_key
from strings import tr, en
from time import sleep
import traceback

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

            if not linkid.split('_')[0] == 't3':
                print('not main reply')
                twitterlinker.send_reply(l_res["introduction"] + " " + l_res["not_main_reply_err"], id_)
                continue

            response = requests.get('https://www.reddit.com/{}/.json'.format(linkid.split('_')[1]),
                                    headers={"User-Agent": useragent})
            jsurl = response.json()
            if not customurl == "":
                pic = customurl
            else:
                pic = jsurl[0]['data']['children'][0]['data']['url']

            if not jsurl[0]['data']['children'][0]['data'].get("post_hint"):
                print('text post')
                twitterlinker.send_reply(l_res["introduction"] + "\r\n" + l_res["no_image_err"], id_)
                continue

            if is_api_up(wait=False):
                username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(pic, lang_arg, ocr_api_key)
                if username == -1:
                    time.sleep(20)
                    username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(pic, lang_arg, ocr_api_key)
            else:
                messagetxt = l_res["hello"].format(user) + "\r\n" + l_res["introduction"] + "\r\n" + l_res["api_down_err"]
                print('api down')
                twitterlinker.send_reply(messagetxt, id_)
                continue
            print('OCR DONE')
            if twitlink:
                print("getting backup archive")
                backup_link = capture_tweet_arch(twitlink)
            if reasons == REASON_DEFAULT:
                reason = l_res["reason_default"]
            elif reasons == REASON_TOO_BIG:
                reason = l_res["reason_toobig"]
            else:
                reason = l_res["reason_default"]

            messagetxt = l_res["hello"].format(user) + "\r\n" + l_res["introduction"] + "\r\n"
            if not twitlink:
                messagetxt += l_res["because"].format(reason)
            else:
                if atliatsiz:
                    messagetxt += l_res["couldnt_find_at"].format(twitlink)
                elif not atliatsiz:
                    messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + l_res["archive_info"].format(backup_link)
                if wordcount <= 4:
                    messagetxt += "\r\n" + l_res["shortened_warn"]
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
                    if is_api_up(wait=True):
                        username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(curr_post["url"], "tur", ocr_api_key, need_at=False)
                        if username == -1:
                            time.sleep(20)
                            username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(curr_post["url"], "tur", ocr_api_key, need_at=False)
                    if not username == -1 and username and not atliatsiz:
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
        time.sleep(17)

while True:
    try:
        mainloop()
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)
        raise