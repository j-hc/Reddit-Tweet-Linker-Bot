import requests
import json
import base64
from info import vision_ocr_api_key


class VisionOCR:
    @staticmethod
    def _get_img_b64_from_url(url):
        img_content = requests.get(url).content
        return base64.b64encode(img_content).decode()

    @staticmethod
    def get_ocr(picuri, raw_response=True, force_try=False):
        image_uri_used = False
        if picuri.startswith('https'):
            image_data = {"source": {"image_uri": picuri}}
            image_uri_used = True
        else:
            with open(picuri, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            image_data = {"content": encoded_string}

        params = {"key": vision_ocr_api_key, "fields": "responses.textAnnotations"}
        data = json.dumps({"requests": [{"image": image_data, "features": [{"type": "TEXT_DETECTION"}]}]})
        try_amount = 6 if force_try else 3
        for tried in range(try_amount):
            if force_try and tried == 4 and image_uri_used:
                img_b64 = VisionOCR._get_img_b64_from_url(picuri)
                data = json.dumps({"requests": [{"image": {"content": img_b64}, "features": [{"type": "TEXT_DETECTION"}]}]})
            response = requests.post("https://vision.googleapis.com/v1/images:annotate", data=data, params=params)
            responses_zero = response.json()['responses'][0]
            if responses_zero.get('textAnnotations') is None:
                continue
            if raw_response:
                return responses_zero
            else:
                return responses_zero['textAnnotations'][0]['description']
        return None
