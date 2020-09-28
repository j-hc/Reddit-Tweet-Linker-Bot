import requests
from requests.adapters import HTTPAdapter
from ratelimit import sleep_and_retry, limits
from time import sleep
# import re

class PyYandexOCR:
    def __init__(self, timeout=12, max_retries=4):
        self.timeout = timeout
        self.s = requests.Session()
        self.s.mount('https://', HTTPAdapter(max_retries=max_retries))
        self.s.params = {'srv': 'android'}

        # self._update_sessionid()

        # pr = requests.get('https://proxy.webshare.io/proxy/list/download/vrxqzvcdemlumzlnsuxwxbqttefbjnqyekbpdyzh/-/http/username/direct/').text.strip()
        # self.proxies = []
        # for p in pr.split('\r\n'):
        #     p_s = p.split(':')
        #     self.proxies.append(f"https://{p_s[2]}:{p_s[3]}@{p_s[0]}:{p_s[1]}")
        # self.prx_i = 0
        # self.prx_amount = len(self.proxies)

    @sleep_and_retry
    @limits(calls=12, period=55)
    def _handled_post(self, uri, **kwargs):
        while True:
            # proxies = {'https': self.proxies[self.prx_i % self.prx_amount]}
            try:
                response = self.s.post(uri, **kwargs)
            except Exception as e:
                print(e)
                # self.prx_i += 1
                sleep(5)
                continue

            if response.status_code == 429 or response.status_code == 403:
                print(response.text)
                sleep(5)
                # self._update_sessionid()
                continue

            return response

    def get_ocr(self, pic_url, lang='*', raw_response=False):
        img_raw = self._get_img_content(pic_url)
        if img_raw is None:
            return None
        params_ = {'lang': lang}
        files = {'file': ("file", img_raw, 'image/jpeg')}
        response = self._handled_post('https://translate.yandex.net/ocr/v1.1/recognize', params=params_, files=files, timeout=self.timeout)
        resp_j = response.json()

        if resp_j.get('error') is not None:
            # err = resp_j['description']
            return None
        
        if raw_response:
            return response
        else:
            text = []
            for block in resp_j['data']['blocks']:
                boxes = block['boxes']
                for box in boxes:
                    text.append(box['text'])
            return '\n'.join(text)

    def _get_img_content(self, pic_url):
        for _ in range(2):
            try:
                return requests.get(pic_url).content
            except:
                pass
        return None

    # def _update_sessionid(self):
    #     self.s.params.update({'sid': self._get_sessionid()})
    #
    # def _get_sessionid(self):
    #     response = requests.get('https://ceviri.yandex.com.tr/ocr', timeout=7)
    #     sid = re.search(b"SID: '(.*)'", response.content).group(1).decode()
    #     sid_split = sid.split('.')
    #     reversed_sid_l = []
    #     for sid_s in sid_split:
    #         reversed_sid_l.append(sid_s[::-1])
    #     reversed_sid = '.'.join(reversed_sid_l)
    #     return reversed_sid
