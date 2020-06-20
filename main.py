import requests
import json
from bs4 import BeautifulSoup
import time
import urllib.parse
import rbot
from info import useragent, client_id, client_code, bot_username, bot_pass, ocr_api_key


def is_api_up():
    stat_page = requests.get('https://status.ocr.space/')
    soup = BeautifulSoup(stat_page.content, "lxml")
    status = soup.find('span', class_='status')
    status = str(status).split('>')[1].split('<')[0].strip()
    if status == 'DOWN':
        return False
    else:
        return True

def is_exist_twitter(username):
    pagec = requests.get("https://mobile.twitter.com/{}".format(username), cookies={'m5': 'off'}, headers={"Accept-Language": "en-US,en;q=0.5"})
    soup = BeautifulSoup(pagec.content, "lxml")
    search = soup.find('div', class_='title')
    if search.text == "Sorry, that page doesn't exist" or search.text == "This account has been suspended.":
        return False
    else:
        return True

def ocr_and_twit(picurl, lang, ocr_api_key, need_at=True):
    payload = {'apikey': ocr_api_key, 'url': picurl, 'language': lang}
    postre = requests.post("https://api.ocr.space/parse/image", data=payload)
    print('ocr request\n')
    try:
        loaded = str(json.loads(postre.content.decode())["ParsedResults"][0]['ParsedText'])
        # loaded = str(json.loads(postre.content.decode()))
    except KeyError:
        reasons = ("görüntü boyutu çok büyük(>1MB)", 'image is bigger than 1MB')
        ret = ("", "", "", "", reasons)
        return ret
    except:
        ret = (-1, "", "", "", "")
        return ret

    print(loaded)
    split_loaded = loaded.split('\r\n')

    at = ""
    i = 0
    for at in split_loaded:
        i = i + 1
        if '@' in at:
            break
        else:
            at = ""
    if not at:
        i = 0

    y = ['Twitter for', 'Translate', 'Twitter Web App', '•', 'for iOS', 'for Android']
    search_list = []
    ah = i
    print(split_loaded)
    for s in split_loaded[i:len(split_loaded)]:
        if not any(yasak in s for yasak in y):
            if (len(s) > 13 or '@' in s) and ah >= i and 'Replying to @' not in s:
                search_list.append(s.strip())
        else:
            break
        ah = ah + 1
    search_list = ' '.join(search_list).split(' ')
    search_list = [x for x in search_list if '#' not in x and x]
    search_text = ' '.join(search_list)

    if not at:
        print("@username gozukmuyor")
        possible_at = [""]
        if not need_at:
            reasons = ('*shrugs*', '*shrugs*')
            ret = ("", "", "", "", reasons)
            return ret
    else:
        find_at = at.split('@')[1].split(' ')[0].strip()
        possible_at = [find_at]
        if '...' in find_at:
            print("@username tam gozukmuyor")
            possible_at = [""]
        else:
            if 'l' in find_at:
                find_at2 = find_at.replace('l', 'I')
                if is_exist_twitter(find_at2):
                    possible_at.append(find_at2)
            if 'I' in find_at:
                find_at3 = find_at.replace('I', 'l')
                if is_exist_twitter(find_at3):
                    possible_at.append(find_at3)
            if 'ı' in find_at:
                find_at4 = find_at.replace('ı', 'i')
                if is_exist_twitter(find_at4):
                    possible_at.append(find_at4)

            for _ in range(0, round(len(find_at) * 1 / 3)):
                find_at = find_at[:-1]
                if not is_exist_twitter(find_at):
                    possible_at.append(find_at)
    if not search_text:
        reasons = ('*shrugs*', '*shrugs*')
        ret = ("", "", "", "", reasons)
        return ret
    possibe_search_text = [search_text]
    search_text_splitted = search_text.split(' ')
    search_text_splitted_2 = search_text.split(' ')
    search_text_splitted_3 = search_text.split(' ')
    if '@' in search_text:
        news = search_text.split('@')[0].strip()
        possibe_search_text.append(news)
        news = news.split(" ")
        for xs in range(0, 5):
            try:
                news.pop()
                possibe_search_text.append(" ".join(news))
            except:
                break
    for _ in range(0, round(len(search_text_splitted_2) * 2 / 3)):
        search_text_splitted_2.pop(-1)
        possibe_search_text.append(" ".join(search_text_splitted_2))
    for _ in range(0, round(len(search_text_splitted_3) * 2 / 3)):
        search_text_splitted_3.pop(0)
        possibe_search_text.append(" ".join(search_text_splitted_3))
    print(possibe_search_text)
    os = 1
    while len(search_text_splitted) > 3:
        os = os + 1
        if os % 2 == 0:
            search_text_splitted.pop(-1)
            to_app = " ".join(search_text_splitted)
            if to_app not in possibe_search_text:
                possibe_search_text.append(to_app)
        else:
            search_text_splitted.pop(0)
            to_app = " ".join(search_text_splitted)
            if to_app not in possibe_search_text:
                possibe_search_text.append(to_app)

    temp = search_text.split(' ')
    new2 = ' '.join(s for s in temp if not any(c.isdigit() for c in s))
    ekle = new2.strip()
    if ekle not in possibe_search_text:
        possibe_search_text.append(ekle)

    if '@' in search_text:
        new = search_text.split('@')[0].strip()
        if new not in possibe_search_text:
            possibe_search_text.append(new)
        temp = search_text.split(' ')
        new2 = ' '.join(s for s in temp if not any(c.isdigit() for c in s))
        ekle = new2.strip()
        if ekle not in possibe_search_text:
            possibe_search_text.append(ekle)
    for _ in range(0, round(len(search_text.split(' ')) * 3 / 5)):
        search_text = search_text.split(' ')[:-1]
        search_text = ' '.join(search_text)
        if search_text not in possibe_search_text:
            possibe_search_text.append(search_text)
    print("possible at's: ", end="")
    print(possible_at)
    for at_dene in possible_at:
        for search_text_use in possibe_search_text:
            if not at_dene == "":
                print('twitter username: @' + at_dene)
                query = urllib.parse.quote(search_text_use + ' (from:{})'.format(at_dene))
            else:
                query = urllib.parse.quote(search_text_use)
            print('tweet text: ' + search_text_use)
            twit_search = 'https://mobile.twitter.com/search?q={}'.format(query)
            print('search link: ' + twit_search)
            tw = requests.get(twit_search, cookies={'m5': 'off'}, headers={"Accept-Language": "en-US,en;q=0.5"})
            soup = BeautifulSoup(tw.content, "lxml")
            search = soup.find('table', class_='tweet')

            try:
                tweetlink = 'https://twitter.com' + search['href'].split('?p')[0]
                print('\r\nFound yay')
                print(tweetlink)
                if possible_at[0] == "":
                    tweeter = ""
                    atsiz = True
                else:
                    tweeter = at_dene
                    atsiz = False
                ret = (tweeter, tweetlink, atsiz, len(search_text_use.split(' ')), ("", ""))
                return ret
            except:
                pass

    reasons = ('*shrugs*', '*shrugs*')
    ret = ("", "", "", "", reasons)
    return ret

twitterlinker = rbot.rBot(useragent, client_id, client_code, bot_username, bot_pass)
twitterlinker.get_token()
alreadyanswered = []
checked_post = []
while True:
    #INBOX CHECK
    id_urlname = twitterlinker.check_inbox(alreadyanswered)
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
            alreadyanswered.append(id_)
            continue

        response = requests.get('https://www.reddit.com/{}/.json'.format(linkid.split('_')[1]),
                                headers={"User-Agent": useragent})
        jsurl = json.loads(response.content.decode())
        if not customurl == "":
            pic = customurl
        else:
            pic = jsurl[0]['data']['children'][0]['data']['url']

        if jsurl[0]['data']['children'][0]['data']['is_self']:
            print('text post')
            twitterlinker.send_reply(
                'Im a bot and I find links to the twitter screenshots. \r\n i dunno why you called me this post has no image',
                id_)
            alreadyanswered.append(id_)
            continue

        if subreddit == "turkey" or subreddit == "turkeyjerky":
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
            alreadyanswered.append(id_)
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
            messagetxt +='\r\n\nu/peroksizom^beni ^yazan ^şahıs' \
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
            messagetxt += '\r\n\n^my owner: u/peroksizom' \
                          '\r\n\n^downvote ^to ^remove'
        twitterlinker.send_reply(messagetxt, id_)
        alreadyanswered.append(id_)
        print('DONE')
        continue

    #SUBREDDIT FEED CHECK
    last_submission = twitterlinker.fetch_subreddit_posts("testyapiyorum", 1)
    last_post = last_submission[0]["data"]
    pThing = last_post["name"]
    if not last_post["is_self"] and not last_post["is_video"] and not pThing in checked_post:
        if not twitterlinker.check_if_already_post(pThing):
            if is_api_up():
                username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(last_post["url"], "tur", ocr_api_key, need_at=False)
                if username == -1:
                    time.sleep(20)
                    username, twitlink, atliatsiz, wordcount, reasons = ocr_and_twit(last_post["url"], "tur", ocr_api_key, need_at=False)
            else:
                time.sleep(30)
                continue
            if not username == -1 and username and not atliatsiz:
                print("TWEET POSTU BULUNDU")
                messagetxt = "ben bir botum ve tweet screenshotlarının linklerini buluyorum.\r\n" \
                             "bu tweeti @{} atmış ve yamulmuyorsam linki de bu: {}" \
                             "\r\n\nu/peroksizom^beni ^yazan ^şahıs" \
                             "\r\n\n^yanlıssa ^kaldırmak ^için ^downvotelayın ^:)".format(username, twitlink)
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

    if len(alreadyanswered) > 35:
        alreadyanswered = []
    if len(checked_post) > 35:
        checked_post = []
    print('\r\nbekleniyor')
    time.sleep(12)
