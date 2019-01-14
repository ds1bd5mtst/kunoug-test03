import json
import urllib.request, urllib.parse

def isbnsearch(isbn):
  # OpenBD API URL
  url = 'https://api.openbd.jp/v1/get'
  
  # ISBN設定
  params = {
      'isbn': isbn,
  }
  
  # ISBNをOpenBDに問い合わせし、結果をbodyに格納
  req = urllib.request.Request('{}?{}'.format(url, urllib.parse.urlencode(params)))
  with urllib.request.urlopen(req) as res:
    body = json.load(res)

  # 書名検索ができなかったら"見つかりません"と返し、できたらリターンコードと共に書名を関数の戻り値として返す
  if body[0] is None:
    mes = "ISBN" + str(isbn) + "の本は見つかりませんでした"
    return [1, mes]
  else:
    title = body[0]["summary"]["title"]
    return [0, title]
