import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from google.cloud import vision
import os
from info import gcloud_creds_path
import enum

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcloud_creds_path
client = vision.ImageAnnotatorClient()


class Reasons(enum.Enum):
    TOO_BIG = -2
    NO_TEXT = -4
    DEFAULT = -3
    NO_AT = -5


def capture_tweet_arch(url):
    data = {
        'url': url,
        'capture_all': 'on'
    }
    requests.post(f'http://web.archive.org/save/{url}', data=data)
    return f"https://web.archive.org/web/submit?url={url}"


def is_exist_twitter(username):
    pagec = requests.get(f"https://mobile.twitter.com/{username}", allow_redirects=False, cookies={'m5': 'off'})
    if pagec.status_code == 200:  # OK
        return True
    else:
        return False


def vision_ocr(picurl):
    response = client.annotate_image({
        'image': {'source': {'image_uri': picurl}},
        'features': [{'type': vision.enums.Feature.Type.TEXT_DETECTION}],
    })
    try:
        txt = response.text_annotations[0].description
    except:
        txt = None
    return txt


def prep_text(text, need_at):
    try:
        split_loaded = text.split('\n')
    except:  # NoneType return from ocr
        ret = {"result": "error", "reason": Reasons.DEFAULT}
        return ret
    i = 0
    at = ""
    for at_dnm in split_loaded:
        i = i + 1
        at_re = re.search(r'@([A-Za-z0-9_]+)', at_dnm)
        if at_re:
            at = at_re.group(0)
            break
    else:
        i = 0

    y = ['Twitter for', 'Translate Tweet', 'Twitter Web App', 'PM - ', '20 - ', '19 - ', 'for iOS', 'for Android', ' Retweet ', ' Beğeni ']
    search_list = []
    ah = i
    for s in split_loaded[i:len(split_loaded)]:
        if not any(yasak in s for yasak in y):
            if (len(s) > 13 or '@' in s) and ah >= i and 'Replying to @' not in s:
                search_list.append(s.strip())
        else:
            break
        ah = ah + 1

    search_list = ' '.join(search_list).split()
    search_list = [x for x in search_list if '#' not in x and x]  # clear from hashtags and NoneTypes
    search_text = ' '.join(search_list)
    if not at:
        print("@username gozukmuyor")
        possible_at = [""]
        if need_at:
            ret = {"result": "error", "reason": Reasons.NO_AT}
            return ret
    else:
        find_at = at.split('@')[1].split(' ')[0].strip()
        if is_exist_twitter(find_at):
            possible_at = [find_at]
        else:
            possible_at = []
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
                if is_exist_twitter(find_at):
                    possible_at.append(find_at)
    if not search_text:
        print("no text")
        ret = {"result": "error", "reason": Reasons.NO_TEXT}
        return ret

    possibe_search_text = [search_text]
    #print(search_text)
    search_text_splitted = search_text.split()
    search_text_splitted_2 = search_text.split()
    search_text_splitted_3 = search_text.split()

    split_by_at = search_text.split('@')
    if '@' in search_text and len(split_by_at[0].split()) > 1:
        news = split_by_at[0].strip()
        possibe_search_text.append(news)
        news = news.split(" ")
        for xs in range(0, 5):
            if len(news) >= 2:
                news.pop()
                possibe_search_text.append(" ".join(news))
            else:
                break

    for _ in range(0, round(len(search_text_splitted_2) * 3 / 5)):
        search_text_splitted_2.pop(-1)
        possibe_search_text.append(" ".join(search_text_splitted_2))
    for _ in range(0, round(len(search_text_splitted_3) * 3 / 5)):
        search_text_splitted_3.pop(0)
        possibe_search_text.append(" ".join(search_text_splitted_3))
    oss = 1
    while len(search_text_splitted) > 3:
        oss = oss + 1
        if oss % 2 == 0:
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
    #print("possible at's: ", end="")
    #print(possible_at)
    #print("possible search texts: ", end="")
    #print(possibe_search_text)
    return_dic = {"result": "success", "possible_at": possible_at, "possibe_search_text": possibe_search_text}
    return return_dic


def twitter_search(possible_at, possibe_search_text, lang):
    for at_dene in possible_at:
        for search_text_use in possibe_search_text:
            if at_dene:
                #print('twitter username: @' + at_dene)
                query = urllib.parse.quote(search_text_use + ' (from:{})'.format(at_dene))
            else:
                query = urllib.parse.quote(search_text_use)
            print('tweet text: ' + search_text_use)
            twit_search = 'https://mobile.twitter.com/search?q={}'.format(query)
            #print('search link: ' + twit_search)
            accept_lang_header = 'tr-TR,tr;q=0.5' if lang == 'tur' else 'en-US,en;q=0.5'
            tw = requests.get(twit_search, cookies={'m5': 'off'}, headers={'Accept-Language': accept_lang_header})
            soup = BeautifulSoup(tw.content, "lxml")
            search = soup.find('table', class_='tweet')

            try:
                status_endp = search["href"].split('?p')[0]
                found_tweetr = status_endp.split('/')[1]
                if at_dene and found_tweetr == at_dene:
                    tweetlink = 'https://twitter.com' + status_endp
                elif at_dene and found_tweetr != at_dene:
                    continue
                else:
                    tweetlink = 'https://twitter.com' + status_endp
                print('\r\nFound yay: ' + tweetlink)
                if possible_at[0] == "":
                    tweeter = ""
                    atsiz = True
                else:
                    tweeter = at_dene
                    atsiz = False
                return_dic = {"result": "success", "username": tweeter, "twitlink": tweetlink, "atliatsiz": atsiz}
                return return_dic
            except:
                pass
    ret = {"result": "error"}
    return ret
