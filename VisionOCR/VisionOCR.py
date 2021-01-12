import requests
import json
import base64
from .lsgapp import mergeNearByWords
from info import vision_ocr_api_key


class VisionOCR:
    @staticmethod
    def get_ocr(picuri, merge_nearby_words=True):
        if picuri.startswith('https'):
            image_data = {"source": {"image_uri": picuri}}
        else:
            with open(picuri, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            image_data = {"content": encoded_string}

        params = {"key": vision_ocr_api_key, "fields": "responses.textAnnotations"}
        data = json.dumps({"requests": [{"image": image_data, "features": [{"type": "TEXT_DETECTION"}]}]})
        for _ in range(2):
            response_ = requests.post("https://vision.googleapis.com/v1/images:annotate", data=data, params=params)
            response = response_.json()
            try:
                response['responses'][0]
            except:
                raise Exception(response)
            if bool(response['responses'][0]):
                if merge_nearby_words:
                    return mergeNearByWords(response['responses'][0])
                else:
                    return response['responses'][0]['textAnnotations'][0]['description']
            else:
                continue
        return None
