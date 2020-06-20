import requests
from bs4 import BeautifulSoup
import json
import urllib.parse

def is_api_up():
    stat_page = requests.get('https://status.ocr.space/')
    soup = BeautifulSoup(stat_page.content, "lxml")
    status = soup.find('span', class_='status')
    status = str(status).split('>')[1].split('<')[0].strip()
    if status == 'DOWN':
        print("api down")
        return False
    else:
        return True

def is_exist_twitter(username):
    pagec = requests.get("https://mobile.twitter.com/{}".format(username), allow_redirects=False, cookies={'m5': 'off'})
    if pagec.status_code == 200:  # OK
        return True
    elif pagec.status_code == 307:  # account suspended
        return False
    elif pagec.status_code == 404:  # DNE
        return False
    else:
        return False

def ocr_and_twit(picurl, lang, ocr_api_key, need_at=True):
    payload = {'apikey': ocr_api_key, 'url': picurl, 'language': lang}
    postre = requests.post("https://api.ocr.space/parse/image", data=payload)
    print('ocr request\n')
    try:
        loaded = str(json.loads(postre.content.decode())["ParsedResults"][0]['ParsedText'])
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
                if is_exist_twitter(find_at):
                    possible_at.append(find_at)
    if not search_text:
        reasons = ('*shrugs*', '*shrugs*')
        ret = ("", "", "", "", reasons)
        return ret

    print("search_text: " + search_text)
    possibe_search_text = [search_text]
    search_text_splitted = search_text.split(' ')
    search_text_splitted_2 = search_text.split(' ')
    search_text_splitted_3 = search_text.split(' ')

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
    """
    if '@' in search_text:
        new = search_text.split('@')[0].strip()
        if new not in possibe_search_text:
            possibe_search_text.append(new)
        temp = search_text.split(' ')
        new2 = ' '.join(s for s in temp if not any(c.isdigit() for c in s))
        ekle = new2.strip()
        if ekle not in possibe_search_text:
            possibe_search_text.append(ekle)
    """
    print("possible at's: ", end="")
    print(possible_at)
    print("possible search texts: ", end="")
    print(possibe_search_text)
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