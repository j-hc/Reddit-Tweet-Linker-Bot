import requests
import json
import base64
from info import vision_ocr_api_key


class VisionOCR:
    @staticmethod
    def get_ocr(picuri, raw_response=True):
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
                raise Exception(response_.text)
            if bool(response['responses'][0]) and bool(response['responses'][0]['textAnnotations']):
                if raw_response:
                    # print(response['responses'][0])
                    # print(response['responses'][0]['textAnnotations'][0]['description'])
                    return response['responses'][0]
                else:
                    return response['responses'][0]['textAnnotations'][0]['description']
            else:
                print("try")
                continue
        return None
