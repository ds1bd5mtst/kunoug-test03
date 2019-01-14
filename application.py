import os, sys, json
from io import BytesIO
import pandas as pd
import datetime
from flask import Flask, render_template, request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import FollowEvent, UnfollowEvent, MessageEvent, TextMessage, ImageMessage, TextSendMessage

from azure.storage.blob import BlockBlobService, PublicAccess

from PIL import Image

from get_title import isbnsearch
from new_book import book_add
from VisionAPI import get_isbn

app = Flask(__name__)

# DB接続設定(セキュリティの為、各値は環境変数に記載)
database_uri = 'postgresql://{dbuser}:{dbpass}@{dbhost}/{dbname}?client_encoding=utf8'.format(
    dbuser=os.environ["DB_USER"],
    dbpass=os.environ["DB_PASS"],
    dbhost=os.environ["DB_HOST"],
    dbname=os.environ["DB_NAME"]
)

# Flaskアプリケーションに、DB接続設定を付与
app.config.update(
    SQLALCHEMY_DATABASE_URI=database_uri,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

# DB接続初期化
db = SQLAlchemy(app)

# DB移行管理ツール初期化(未使用だが念の為)
migrate = Migrate(app, db)

# userlistテーブルのカラム設定
class UserList(db.Model):
    __tablename__ = "userlist"
    username = db.Column(db.VARCHAR(), primary_key=True)
    userid = db.Column(db.VARCHAR(), nullable=False)

    # UserListの引数設定をしておくと、データ追加や削除時に便利
    def __init__(self, username, userid):
        self.username = username
        self.userid = userid

#環境変数取得
# LINE Developersで設定されているアクセストークンとChannel Secretをを取得し、設定します。
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]
 
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# GETメソッド試験用
@app.route("/")
def hello():
    return "Hello World"

# DB接続試験用(SELECT文確認)
@app.route("/query")
def query():
    dbquery = db.session.query(UserList.username).all()
    ret = str(dbquery)
    return ret

# POSTメソッド試験用
@app.route('/webhook', methods=['POST'])
def webhook():
    return '', 200, {}
 
## 1 ##
#Webhookからのリクエストをチェックします。
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名検証のための値を取得します。
    signature = request.headers['X-Line-Signature']
 
    # リクエストボディを取得します。
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
 
    #handle webhook body
    # 署名を検証し、問題なければhandleに定義されている関数を呼び出す。
    try:
        handler.handle(body, signature)
    # 署名検証で失敗した場合、例外を出す。
    except InvalidSignatureError:
        abort(400)
    # handleの処理を終えればOK
    return 'OK'
 
## 2 ##
###############################################
#LINEのメッセージの取得と返信内容の設定(オウム返し)
###############################################
 
#LINEでMessageEvent（普通のメッセージを送信された場合）が起こった場合に、
#def以下の関数を実行します。
#reply_messageの第一引数のevent.reply_tokenは、イベントの応答に用いるトークンです。 
#第二引数には、linebot.modelsに定義されている返信用のTextSendMessageオブジェクトを渡しています。
 


"""
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)) #ここでオウム返しのメッセージを返します。
"""

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # マツコ用
    account_name='ds1bd5mtst'
    account_key=os.environ["STORAGE2_KEY"]
    container_name='testcontainer'
    file_name='bookdata.csv'
    file_name1='userdata.csv'

    service = BlockBlobService(account_name=account_name,account_key=account_key)
    service.get_blob_to_path(container_name,file_name,file_name)
    service.get_blob_to_path(container_name,file_name1,file_name1)

    # 山本用
    accountname2 = os.environ["STORAGE_NAME"]
    accountkey2 = os.environ["STORAGE_KEY"]
    container_name2 ='testcontainer'
    csvname2 = "test02.csv"

    service2 = BlockBlobService(account_name=accountname2, account_key=accountkey2)
    
    df1 = pd.read_csv(file_name1,encoding="utf-8", sep=",")
    
    profile = line_bot_api.get_profile(event.source.user_id)
    user_disp_name = profile.display_name
    user_id = event.source.user_id
    
    #messages = "test"
    
    
    # ユーザー登録
    messages = ""
    for index, row in df1.iterrows():
        if row["LINEID"] ==  user_id :
            messages = "登録済"
            break
        else:
            messages = "登録しました"
            
    if messages == "登録しました":
        df2 = pd.DataFrame(data=[[user_id,user_disp_name,0]],columns=['LINEID','username','userstatus'])
        df3 = df1.append(df2, ignore_index=True)
        df3 = df3.drop(["Unnamed: 0"],axis=1)
        df3.to_csv(file_name1,encoding="utf-8")
        service.create_blob_from_path(container_name,file_name1,file_name1)
    
    # ステータス確認
    status = 0
    for index, row in df1.iterrows():
        if row["LINEID"] ==  user_id :
            status = row["userstatus"]
    
    # ステータスが0の場合
    if status == 0:

        # 一覧表示
        if event.message.text == "一覧" or event.message.text == "いちらん":
            df = pd.read_csv(file_name,encoding="utf-8", sep=",")
            list = []
            for index, row in df.iterrows():
                list.append(row["title"])
            # 重複排除
            messages = ','.join(set(list))

        # 検索案内
        elif event.message.text == "検索" or event.message.text == "けんさく":
            messages = "検索したい本のタイトルを教えてね"
            for index, row in df1.iterrows():
                if row["LINEID"] ==  user_id:
                    df1.loc[index, 'userstatus'] = 1
            df1 = df1.drop(["Unnamed: 0"],axis=1)
            df1.to_csv(file_name1,encoding="utf-8")
            service.create_blob_from_path(container_name,file_name1,file_name1)

        # 借りる案内
        elif event.message.text == "借りる" or event.message.text == "かりる":
            messages = "借りたい本のタイトルを教えてね(完全一致で)"
            for index, row in df1.iterrows():
                if row["LINEID"] ==  user_id:
                    df1.loc[index, 'userstatus'] = 2
            df1 = df1.drop(["Unnamed: 0"],axis=1)
            df1.to_csv(file_name1,encoding="utf-8")
            service.create_blob_from_path(container_name,file_name1,file_name1)

        # 返す案内
        elif event.message.text == "返す" or event.message.text == "かえす":
            messages = "返したい本のタイトルを教えてね(完全一致で)"
            for index, row in df1.iterrows():
                if row["LINEID"] ==  user_id:
                    df1.loc[index, 'userstatus'] = 3
            df1 = df1.drop(["Unnamed: 0"],axis=1)
            df1.to_csv(file_name1,encoding="utf-8")
            service.create_blob_from_path(container_name,file_name1,file_name1)

        # 意味わからん文字打ってきたやつ向けに
        else:
            messages = "一覧、検索、借りる、返す、4つの中からお願いしてね"
    
    
    # 検索処理
    elif status == 1:
        df = pd.read_csv(file_name,encoding="utf-8", sep=",")
        list = []
        for index, row in df.iterrows():
            if row["title"].find(event.message.text) != -1:
                list.append(row["title"])
            # 重複排除
        messages = ','.join(set(list))
        for index, row in df1.iterrows():
            if row["LINEID"] ==  user_id:
                df1.loc[index, 'userstatus'] = 0
                df1 = df1.drop(["Unnamed: 0"],axis=1)
                df1.to_csv(file_name1,encoding="utf-8")
                service.create_blob_from_path(container_name,file_name1,file_name1)
    
    
    
    # 借りる処理
    elif status == 2:
        df = pd.read_csv(file_name,encoding="utf-8", sep=",")
        messages = ""
        for index, row in df.iterrows():
            # 指定されたタイトル名の本があった場合
            if row["title"] == event.message.text :
                # 貸出可能な場合
                if row["status"] == 0:
                    df.loc[index, 'status'] = 1
                    # rentaluserに代入する値にはLINEIDを入れる
                    profile = line_bot_api.get_profile(event.source.user_id)
                    user_disp_name = profile.display_name
                    #user_id = event.source.user_id
                    df.loc[index, 'rentaluser'] = user_disp_name
                    df.loc[index, 'rentaldate'] = datetime.date.today()
                    messages = "貸し出し完了したよ"
                    break
                else:
                    messages = "誰か借りてる"
            else:
                # 指定されたタイトル名の本がなかった場合
                if messages != "誰か借りてる":
                    messages = "そんな本ないよ"
    
        df = df.drop(["Unnamed: 0"],axis=1)
        df.to_csv(file_name,encoding="utf-8")
        
        service.create_blob_from_path(container_name,file_name,file_name)
        service2.create_blob_from_path(container_name,csvname2,file_name)
        
        for index, row in df1.iterrows():
            if row["LINEID"] ==  user_id:
                df1.loc[index, 'userstatus'] = 0
                df1 = df1.drop(["Unnamed: 0"],axis=1)
                df1.to_csv(file_name1,encoding="utf-8")
                service.create_blob_from_path(container_name,file_name1,file_name1)
    
    
    
    
    # 返す処理
    elif status == 3:
        df = pd.read_csv(file_name,encoding="utf-8", sep=",")
        messages = ""
        user_id = event.source.user_id
        for index, row in df.iterrows():
            # 指定されたタイトル名の本があった場合
            if row["title"] == event.message.text :
            # 借りてるユーザーが一致の場合（LINEIDと比較する必要あり）
                profile = line_bot_api.get_profile(event.source.user_id)
                user_disp_name = profile.display_name
                if row["rentaluser"] == user_disp_name :
                    df.loc[index, 'status'] = 0
                    df.loc[index, 'rentaluser'] = 0
                    df.loc[index, 'rentaldate'] = 0
                    messages = "返却しました"
                    break
                else:
                    messages = "借りてないよ"
            # 指定されたタイトル名の本がなかった場合
            else:
                if messages != "借りてないよ":
                    messages = "そんな本ないよ"
        df = df.drop(["Unnamed: 0"],axis=1)
        df.to_csv(file_name,encoding="utf-8")
        
        service.create_blob_from_path(container_name,file_name,file_name)
        service2.create_blob_from_path(container_name,csvname2,file_name)
        
        for index, row in df1.iterrows():
            if row["LINEID"] ==  user_id:
                df1.loc[index, 'userstatus'] = 0
                df1 = df1.drop(["Unnamed: 0"],axis=1)
                df1.to_csv(file_name1,encoding="utf-8")
                service.create_blob_from_path(container_name,file_name1,file_name1)
    
    # ユーザーの状態が意味わからんくなったとき0にもどす
    else:
        for index, row in df1.iterrows():
            if row["LINEID"] ==  user_id:
                df1.loc[index, 'userstatus'] = 0
                df1 = df1.drop(["Unnamed: 0"],axis=1)
                df1.to_csv(file_name1,encoding="utf-8")
                service.create_blob_from_path(container_name,file_name1,file_name1)
    
    
    
    """
    # CSV読み込み
    #with cd.open(file_name, "r", "Shift-JIS", "ignore") as file:
    # df = pd.read_csv(filename)
    #    df = pd.read_table(file,header=None,sep=',')
    df = pd.read_csv(file_name,encoding="utf-8", sep=",")
    """
    
    """
    # 検索
    list = []
    for index, row in df.iterrows():
        if row["title"].find(event.message.text) != -1:
            list.append(row["title"])
    
    # 重複排除
    messages = ','.join(set(list))
    """
    
    """
    #借りる
    messages = ""
    for index, row in df.iterrows():
        # 指定されたタイトル名の本があった場合
        if row["title"] == event.message.text :
            # 貸出可能な場合
            if row["status"] == 0:
                df.loc[index, 'status'] = 1
                # rentaluserに代入する値にはLINEIDを入れる
                profile = line_bot_api.get_profile(event.source.user_id)
                user_disp_name = profile.display_name
                #user_id = event.source.user_id
                df.loc[index, 'rentaluser'] = user_disp_name
                messages = "借りれるよ"
                break
            else:
                messages = "誰か借りてる"
        else:
            # 指定されたタイトル名の本がなかった場合
            if messages != "誰か借りてる":
                messages = "そんな本ないよ"
    
    df = df.drop(["Unnamed: 0"],axis=1)
    df.to_csv(file_name,encoding="utf-8")
    
    service.create_blob_from_path(container_name,file_name,file_name)
    """
    
    
    """
# 3、返す
    messages = ""
    user_id = event.source.user_id
    for index, row in df.iterrows():
        # 指定されたタイトル名の本があった場合
        if row["title"] == event.message.text :
        # 借りてるユーザーが一致の場合（LINEIDと比較する必要あり）
            if row["rentaluser"] == user_id :
                df.loc[index, 'status'] = 0
                df.loc[index, 'rentaluser'] = 0
                messages = "返却しました"
                break
            else:
                messages = "借りてないよ"
        # 指定されたタイトル名の本がなかった場合
        else:
            if messages != "借りてないいよ":
                messages = "そんな本ないよ"
    df = df.drop(["Unnamed: 0"],axis=1)
    df.to_csv(file_name)
    
    service.create_blob_from_path(container_name,file_name,file_name)
    """
    
    
    # ファイルの削除
    os.remove(file_name)
    os.remove(file_name1)
    
    """
    messages = ""
    if event.message.text == "一覧" or event.message.text == "いちらん":
        messages = "一覧は作成中です"
    else:
        messages = "よくわかりません"
    """
    
    
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=messages)) # messagesに代入されている値を返してくれる
 
 # LineBotに画像送信があった際の挙動(新規書籍登録)
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # メッセージID等を取得する、イメージをバイナリ形式で取得する
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    image = BytesIO(message_content.content)

    # イメージをVisionAPIに投げる(関数はVisionAPIファイル内で定義済)
    isbn = get_isbn(image)

    # 返ってきた結果が数値でなければ(エラーであれば)その旨を返す
    if not isinstance(isbn, int):
        mes = isbn

    # 返ってきた結果が数値なら、OpenBDに投げて書籍情報を取得する(関数はget_titleファイルで定義済)
    else:
        title = isbnsearch(isbn)

        # リターンコード1ならエラー扱い
        if title[0] == 1:
            mes = title[1]

        # リターンコード0なら書籍登録する(関数はnew_bookファイルで定義済)
        else:
            profile = line_bot_api.get_profile(event.source.user_id)
            owner = profile.display_name
            book_add(title[1], owner)
            mes = title[1] + " を登録しました"
            
    # 結果メッセージを返信する
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=mes)
    )

# LineBotを友達追加orブロック解除した際の挙動(UserListテーブルに相手のLINEの表示名、IDを追加しつつ応答を返す)
@handler.add(FollowEvent)
def handle_follow(event):
    profile = line_bot_api.get_profile(event.source.user_id)
    followname = profile.display_name
    followid = event.source.user_id

    record = UserList(followname, followid)
    db.session.add(record)
    db.session.commit()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="thanks for your following"))

# LineBotをブロックした際の挙動(UserListテーブルから相手のLINEの表示名、IDを削除する)
@handler.add(UnfollowEvent)
def handle_unfollow(event):
    unfollowid = event.source.user_id

    db.session.query(UserList).filter(UserList.userid==unfollowid).delete()
    db.session.commit()

