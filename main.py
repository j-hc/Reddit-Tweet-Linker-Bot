import time
from api_and_twitterparsing import *
import rbot
from info import useragent, client_id, client_code, bot_username, bot_pass, ocr_api_key


twitterlinker = rbot.rBot(useragent, client_id, client_code, bot_username, bot_pass)
twitterlinker.get_token()
checked_post = []
while True:
    #INBOX CHECK
    id_urlname = twitterlinker.check_inbox()
    if id_urlname == "tokenal":
        twitterlinker.get_token()
        continue
    if id_urlname:
        id_, linkid, subreddit, customurl, user = id_urlname
        print('SUMMONLANDIM #####')

        if not linkid.split('_')[0] == 't3':
            print('not main reply')
            twitterlinker.send_reply(
                'Im a bot and I find links to the twitter screenshots. I cant see the pic. you need to mention me from a main reply to the post.',
                id_)
            continue

        response = requests.get('https://www.reddit.com/{}/.json'.format(linkid.split('_')[1]),
                                headers={"User-Agent": useragent})
        jsurl = response.json()
        if not customurl == "":
            pic = customurl
        else:
            pic = jsurl[0]['data']['children'][0]['data']['url']

        if jsurl[0]['data']['children'][0]['data']['is_self']:
            print('text post')
            twitterlinker.send_reply(
                'Im a bot and I find links to the twitter screenshots. \r\n i dunno why you called me this post has no image',
                id_)
            continue

        if subreddit == "turkey" or subreddit == "turkeyjerky" or subreddit == "testyapiyorum":
            lang_arg = 'tur'
        else:
            lang_arg = 'eng'
        print(lang_arg)

        if is_api_up():
            username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(pic, lang_arg, ocr_api_key)
            if username == -1:
                time.sleep(20)
                username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(pic, lang_arg, ocr_api_key)
        else:
            messagetxt = "merhaba {}!\r\nben bir botum ve tweet screenshotlarının linklerini buluyorum.\r\n" \
                         "OCR API'm çökmüş :(. başka zamana artık..".format(str(user).lower())
            print('api down')
            twitterlinker.send_reply(messagetxt, id_)
            continue
        print('OCR DONE')
        reason_tur, reason_eng = reasons
        if lang_arg == 'tur':
            messagetxt = "merhaba {}!\r\nben bir botum ve tweet screenshotlarının linklerini buluyorum.\r\n".format(
                str(user).lower())
            if twitlink == "":
                messagetxt += "bu tweet için bişe bulamadım çünkü {}, sorry.".format(reason_tur)
            else:
                if atliatsiz:
                    messagetxt += "bu tweeti kimin attığı ss den belli olmuyor. ama yine de denedim ve yamulmuyorsam linki bu: {}".format(
                        twitlink)
                elif not atliatsiz:
                    messagetxt += "bu tweeti @{} atmış ve yamulmuyorsam linki de bu: {}".format(
                        username, twitlink)
                if wordcount <= 4:
                    messagetxt += "\r\ntweeti bulmak icin kısaltarak aramak zorunda kaldım. sonuç doğru olmayabilir."
            messagetxt +="\r\n\n^[[sahibim](https://www.reddit.com/user/peroksizom),[source-code](https://github.com/scrubjay55/Reddit-Tweet-Linker-Bot)]" \
                         '\r\n\n^yanlıssa ^kaldırmak ^için ^downvotelayın ^:)'
        else:
            messagetxt = "Hi {}!\r\nI'm a bot and I find links to the twitter screenshots.\r\n".format(
                str(user).lower())
            if twitlink == "":
                messagetxt += "I wasn't able to find anything for this tweet because {}, sorry.".format(
                    reason_eng)
            else:
                if atliatsiz:
                    messagetxt += "I am not able to see who tweeted this. Nevertheless i tried: {}".format(
                        twitlink)
                elif not atliatsiz:
                    messagetxt += "this was tweeted by @{} and if I'm not wrong the link is: {}".format(
                        username, twitlink)
                if wordcount <= 4:
                    messagetxt += "\r\ni shortened the tweet to find it. the result might be wrong JUST AS TWEET SS MIGHT BE FAKE."
            messagetxt += "\r\n\n^[[owner](https://www.reddit.com/user/peroksizom),[source-code](https://github.com/scrubjay55/Reddit-Tweet-Linker-Bot)]" \
                          "\r\n\n^downvote ^to ^remove"
        twitterlinker.send_reply(messagetxt, id_)
        print('DONE')
        continue

    #SUBREDDIT FEED CHECK
    last_submissions = twitterlinker.fetch_subreddit_posts("turkey", 2)
    for last_submission in last_submissions:
        curr_post = last_submission["data"]
        pThing = curr_post["name"]
        if not curr_post["is_self"] and not curr_post["is_video"] and not pThing in checked_post:
            if not twitterlinker.check_if_already_post(pThing):
                if is_api_up():
                    username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(curr_post["url"], "tur", ocr_api_key, need_at=False)
                    if username == -1:
                        time.sleep(20)
                        username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(curr_post["url"], "tur", ocr_api_key, need_at=False)
                else:
                    time.sleep(30)
                    continue
                if not username == -1 and username and not atliatsiz:
                    print("TWEET POSTU BULUNDU")
                    messagetxt = "ben bir botum ve tweet screenshotlarının linklerini buluyorum.\r\n" \
                                 "bu tweeti @{} atmış ve yamulmuyorsam linki de bu: {}" \
                                 "\r\n\n^[[sahibim](https://www.reddit.com/user/peroksizom),[source-code](https://github.com/scrubjay55/Reddit-Tweet-Linker-Bot)]" \
                                '\r\n\n^yanlıssa ^kaldırmak ^için ^downvotelayın ^:)'.format(username, twitlink)
                    twitterlinker.send_reply(messagetxt, pThing)
                else:
                    print("tweet postu degil")
            else:
                print("feed check: cevaplanmis")
            checked_post.append(pThing)
        else:
            print("pic degil ya da cevaplandi")

    # SCORE CHECK
    twitterlinker.check_last_comment_scores()

    if len(checked_post) > 35:
        checked_post = []
    print('\r\nbekleniyor')
    time.sleep(12)
