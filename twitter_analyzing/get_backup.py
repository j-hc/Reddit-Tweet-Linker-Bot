import requests


class Backup:
    @staticmethod
    def capture_tweet_arch(url):
        data = {
            'url': url,
            'capture_all': 'on'
        }
        requests.post(f'http://web.archive.org/save/{url}', data=data)
        return f"https://web.archive.org/web/submit?url={url}"
