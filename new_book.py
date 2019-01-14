import os
import pandas as pd
from azure.storage.blob import BlockBlobService

# 変数定義
accountname = os.environ["STORAGE_NAME"]
accountkey = os.environ["STORAGE_KEY"]
container_name ='testcontainer'
temppath = "/home/"
csvname = "test02.csv"
csvpath = temppath + csvname

account2_name='ds1bd5mtst'
account2_key='QRW6ikCh6i2TAOZsJnAuliDJX03xU8xmm3GVhsLFD8cw3Z9yjOLZVE3CYdgKpV+74D4y1dKCsK6bd5fjUup3LQ=='
container2_name='testcontainer'
file2_name='bookdata.csv'

# 書籍名と所有者情報をCSVに追記する関数
def book_add(title, owner):

    # Blobへ接続しCSVをダウンロード
    block_blob_service = BlockBlobService(account_name=accountname, account_key=accountkey)
    block_blob_service.get_blob_to_path(container_name, csvname, csvpath)

    # CSVに新規図書を追加し再アップロード
    w = pd.DataFrame([[title, "0", "0", owner, "0", "0", "1F"]])
    w.to_csv(csvpath, index=True, encoding="utf-8", mode='a', header=False)
    block_blob_service.create_blob_from_path(container_name, csvname, csvpath)

    # マツコSTRGにもアップロード
    block_blob_service2 = BlockBlobService(account_name=account2_name, account_key=account2_key)
    block_blob_service2.create_blob_from_path(container2_name, file2_name, csvpath)

    # ローカルファイルを削除
    os.remove(csvpath)

