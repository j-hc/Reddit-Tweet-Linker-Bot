import requests
from requests.adapters import HTTPAdapter
from ratelimit import sleep_and_retry, limits
from time import sleep
from urllib3.util.retry import Retry


class PyYandexOCR:
    # yandex wont get mad at me since im not using this commercially :s

    def __init__(self, timeout=16):
        self.timeout = timeout
        self.s = requests.Session()
        self.s.mount('https://', HTTPAdapter(max_retries=Retry(total=4, backoff_factor=3)))
        self.s.params = {'srv': 'android'}

    @sleep_and_retry
    @limits(calls=12, period=55)
    def _handled_post(self, uri, **kwargs):
        for _ in range(5):
            try:
                response = self.s.post(uri, **kwargs)
            except Exception as e:
                print("EXCEPTION: ", end='')
                print(e)
                sleep(5)
                continue

            if response.status_code == 429 or response.status_code == 403:
                print("STATUS CODE: ", end='')
                print(response.text)
                sleep(5)
                continue

            return response
        return None

    def get_ocr(self, image, lang='*', raw_response=False):
        img_raw = self._get_img_content(image)
        if img_raw is None:
            return None
        params_ = {'lang': lang}
        files = {'file': ("file", img_raw, 'image/jpeg')}
        response = self._handled_post('https://translate.yandex.net/ocr/v1.1/recognize', params=params_, files=files, timeout=self.timeout)
        # print(response.text)
        if response is None:
            return None
        resp_j = response.json()

        if resp_j.get('error') is not None:
            # err = resp_j['description']
            return None

        if raw_response:
            return response.json()
        else:
            text = ""
            for block in resp_j['data']['blocks']:
                for box in block['boxes']:
                    text += box['text'] + '\n'
            return text.strip()

    def _get_img_content(self, pic_uri):
        if pic_uri.startswith('http'):
            for _ in range(2):
                try:
                    return requests.get(pic_uri).content
                except:
                    pass
            return None
        else:
            return open(pic_uri, 'rb')
