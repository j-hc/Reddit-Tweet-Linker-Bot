import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from info import vision_api_key
import enum
import json
import base64
from collections import namedtuple

# Some stuff.. ------------------
replying_to = ["antwort an", "replying to", "yanıt olarak", "yanit olarak", "svar till"]
# -------------------------------


class Reasons(enum.Enum):
    NO_TEXT = -1
    DEFAULT = -2
    NO_AT = -3
    NO_IMG = -4
    ACCOUNT_SUSPENDED = -5


class TWStatus(enum.Enum):
    OK = 1
    SUSPENDED = 2
    DNE = 3


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
        return TWStatus.OK
    elif pagec.status_code == 307:
        return TWStatus.SUSPENDED
    elif pagec.status_code == 404:
        return TWStatus.DNE


def vision_ocr(picurl):
    params = {"key": vision_api_key, "fields": "responses.fullTextAnnotation.text"}
    #params = {"key": vision_api_key}
    img_bytes = requests.get(picurl).content
    bss = base64.b64encode(img_bytes)
    data = json.dumps({"requests": [{"image": {"content": bss.decode()}, "features": [{"type": "TEXT_DETECTION"}]}]})
    # data = json.dumps({"requests": [{"image": {"source": {"image_uri": picurl}}, "features": [{"type": "TEXT_DETECTION"}]}]})
    response = requests.post("https://vision.googleapis.com/v1/images:annotate", data=data, params=params).json()
    if bool(response['responses'][0]):
        txt = response['responses'][0]["fullTextAnnotation"]["text"]
    else:
        txt = None
    return txt


def prep_text(text, need_at):
    split_loaded = text.strip().split('\n')
    at = None
    below_this = None
    lenght = len(split_loaded)
    for at_dnm in range(lenght - 1, -1, -1):
        at_dnm_txt = str(split_loaded[at_dnm])
        at_dnm_txt_low = at_dnm_txt.lower()
        if "@" in at_dnm_txt and any(yasak in at_dnm_txt_low for yasak in replying_to):
            below_this = at_dnm + 1
        elif at_dnm < lenght - 2 and '@' in at_dnm_txt:
            try_at = at_dnm_txt.split('@')[1].split()[0]
            if bool(re.fullmatch(r'([A-Za-z0-9_]+)', try_at)):
                at = try_at
                break

    y = ['Twitter for', 'Translate Tweet', 'Twitter Web App', 'PM - ', '20 - ', '19 - ', 'for iOS', 'for Android',
         ' · ', ' Translate from ', 'Tweet your reply']
    search_list = []
    if below_this:  # IF REPLY FOUND
        ah = below_this
    elif not at:  # IF AT NOT FOUND
        ah = 0
    else:  # IF AT FOUND
        ah = at_dnm + 1
    for s in split_loaded[ah:len(split_loaded)]:
        if not any(yasak in s for yasak in y) and len(s) > 13 or '@' in s:
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
        find_at = at
        possible_at = [""]
        if '.' in find_at or len(find_at) < 5:
            possible_at = [""]
        else:
            account_status = is_exist_twitter(find_at)
            if account_status == TWStatus.OK:
                possible_at = [find_at]
            elif account_status == TWStatus.SUSPENDED:
                ret = {"result": "error", "reason": Reasons.ACCOUNT_SUSPENDED}
                return ret
            elif account_status == TWStatus.DNE:
                if 'l' in find_at:
                    find_at2 = find_at.replace('l', 'I')
                    if is_exist_twitter(find_at2):
                        possible_at.append(find_at2)
                if 'I' in find_at:
                    find_at3 = find_at.replace('I', 'l')
                    if is_exist_twitter(find_at3):
                        possible_at.append(find_at3)
    if not search_text:
        print("no text")
        ret = {"result": "error", "reason": Reasons.NO_TEXT}
        return ret

    possibe_search_text = [search_text]
    # print(search_text)
    search_text_splitted = search_text.split()
    search_text_splitted_2 = search_text.split()
    search_text_splitted_3 = search_text.split()

    for _ in range(0, round(len(search_text_splitted_2) * 0.7)):
        search_text_splitted_2.pop(-1)
        if len(search_text_splitted_2) < 50:
            possibe_search_text.append(" ".join(search_text_splitted_2))
    for _ in range(0, round(len(search_text_splitted_3) * 0.7)):
        search_text_splitted_3.pop(0)
        if len(search_text_splitted_3) < 50:
            possibe_search_text.append(" ".join(search_text_splitted_3))
    oss = 1
    lnn = len(search_text_splitted) * 0.5
    while len(search_text_splitted) > lnn:
        oss = oss + 1
        if oss % 2 == 0:
            search_text_splitted.pop(-1)
            to_app = " ".join(search_text_splitted)
            if to_app not in possibe_search_text and len(search_text_splitted) < 50:
                possibe_search_text.append(to_app)
        else:
            search_text_splitted.pop(0)
            to_app = " ".join(search_text_splitted)
            if to_app not in possibe_search_text and len(search_text_splitted) < 50:
                possibe_search_text.append(to_app)

    temp = search_text.split()
    new2 = ' '.join(s for s in temp if not any(c.isdigit() for c in s))
    ekle = new2.strip()
    if ekle not in possibe_search_text and len(ekle.split()) < 50:
        possibe_search_text.append(ekle)
    # print("possible at's: ", end="")
    # print(possible_at)
    # print("possible search texts: ", end="")
    # print(possibe_search_text)
    return_dic = {"result": "success", "possible_at": possible_at, "possibe_search_text": possibe_search_text}
    return return_dic


def twitter_search(possible_at, possibe_search_text, lang):
    for at_dene in possible_at:
        for search_text_use in possibe_search_text:
            if at_dene:
                print('twitter username: ' + at_dene)
                query = urllib.parse.quote(search_text_use + ' (from:{})'.format(at_dene))
            else:
                query = urllib.parse.quote(search_text_use)
            print('tweet text: ' + search_text_use)
            twit_search = 'https://mobile.twitter.com/search?q={}'.format(query)
            print('search link: ' + twit_search)
            accept_lang_header = 'tr-TR,tr;q=0.5' if lang == 'tur' else 'en-US,en;q=0.5'
            tw = requests.get(twit_search, cookies={'m5': 'off'}, headers={'Accept-Language': accept_lang_header})
            soup = BeautifulSoup(tw.content, "lxml")
            search = soup.find('table', class_='tweet')

            try:
                status_endp = search["href"].split('?p')[0]
            except TypeError:
                continue
            found_tweetr = status_endp.split('/')[1]

            if at_dene and found_tweetr != at_dene:
                continue

            tweetlink = 'https://twitter.com' + status_endp

            print('\r\nFound yay: ' + tweetlink)
            if possible_at[0] == "":
                tweeter = found_tweetr
                atsiz = True
            else:
                tweeter = at_dene
                atsiz = False
            return_dic = {"result": "success", "username": tweeter, "twitlink": tweetlink, "atliatsiz": atsiz}
            return return_dic

    ret = {"result": "error", "reason": Reasons.DEFAULT}
    return ret
