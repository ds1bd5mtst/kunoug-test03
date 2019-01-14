import os, re, requests
from io import BytesIO

subscription_key = os.environ["APIKEY"]
endpoint = 'https://japaneast.api.cognitive.microsoft.com/vision/v2.0/ocr'

def get_isbn(image):
    # リクエストのヘッダー
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        "Content-Type": "application/octet-stream"
    }

    # リクエストのパラメータ
    params = {'visualFeatures': 'Categories,Description,Color'}

    # POST処理
    response = requests.post(
        endpoint,
        headers=headers,
        params=params,
        data=image,
    )

    # Jsonデータを受け取る
    data = response.json()

    # Textに代入する
    text = ''
    for region in data['regions']:
        for line in region['lines']:
            for word in line['words']:
                text += word.get('text', '')
                if data['language'] != 'ja':
                    text += ' '
        text += '\n'

    # Text検出できなかった場合
    if len(text) == 0:
        isbn_num = 'ISBNが読み取れませんでした'
    # ISBNが旧フォーマットの場合
    elif text.count('-') == 3:
        isbn_num = "ISBNが旧フォーマットです"
    # ISBNが新フォーマットの場合
    elif text.count('-') == 4:
        retext = re.search('[A-Z]*.[0-9]*-.*-.*-.*-.*', text)
        isbn_num = retext.group().replace(" ", "")
        isbn_num = isbn_num.replace("-", "")
        isbn_match = re.search(r"[0-9]{1,13}",isbn_num)
        isbn_num = int(isbn_match.group(0))
    else:
        isbn_num = 'ISBNが読み取れませんでした'

    return isbn_num
