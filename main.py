# switchbot api rapper for hms.
# JSON取り扱い
import json
#時刻取り扱い
import time
import datetime
#外部APIアクセス
import requests
import urllib.request
#認証、暗号化関連
import hashlib
import hmac
import base64
import uuid

import os


######################################################################################## Switch Bot API用認証情報(アプリから取得)


switchbot_token  = str(os.getenv('_SWITCHBOT_TOKEN'))
switchbot_secret  = str(os.getenv('_SWITCHBOT_SECRET'))


switchbot_apiHeader = {}

######################################################################################## Switch botのAPIトップ
switchbot_api_top = 'https://api.switch-bot.com/v1.1/'
######################################################################################## Switch botのアカウントに登録されているデバイスのリスト用
# APIの実行回数制限があるので、値をキャッシュさせている。
# switchbot_devicelist_lifeはキャッシュ切れになるまでの秒数。ただし本スクリプト起動後、初回は強制取得。
switchbot_devicelist = {}
switchbot_devicelist_lastupdate = 0
switchbot_devicelist_life = 300

######################################################################################## 再試行に関する設定。回数と待機秒数。
tries = 3
retry_interval = 5


######################################################################################## Switch Bot API用認証情報(署名等用意)
# 有効期間切れが発生するので、リフレッシュできるように関数にした。
def switchbot_hedergen():
    global switchbot_apiHeader
    global switchbot_token
    global switchbot_secret

    nonce = uuid.uuid4()
    t = int(round(time.time() * 1000))
    string_to_sign = '{}{}{}'.format(switchbot_token, t, nonce)
    string_to_sign = bytes(string_to_sign, 'utf-8')
    secret = bytes(switchbot_secret, 'utf-8')
    sign = base64.b64encode(hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())

    switchbot_apiHeader['Authorization']=switchbot_token
    switchbot_apiHeader['Content-Type']='application/json'
    switchbot_apiHeader['charset']='utf8'
    switchbot_apiHeader['t']=str(t)
    switchbot_apiHeader['sign']=str(sign, 'utf-8')
    switchbot_apiHeader['nonce']=str(nonce)

######################################################################################## switchbot api呼び出し関数 post/get用

# 制御系のコマンド実行用関数。　デバイスIDを含むURLとパラメータを与える。
# スイッチボットのAPIはリクエストが正当でもしばしば'Internal server error'を返してくるので、リトライを実装した。
#POST /v1.1/devices/{deviceId}/commands
def switchbot_post(apiendpointurl: str, params: str):
    switchbot_hedergen()
    global switchbot_apiHeader
    for i in range(0, tries):
        try:
            result = requests.post(url=apiendpointurl ,data=json.dumps(params), headers=switchbot_apiHeader)
            result.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if i + 1 == tries:
                raise e
            time.sleep(retry_interval)
            continue
    return result.json()

# 状態取得系のコマンド実行用関数。　デバイスIDを含むURLとパラメータを与える。
# スイッチボットのAPIはリクエストが正当でもしばしば'Internal server error'を返してくるので、リトライを実装した。
def switchbot_get(apiendpointurl: str):
    switchbot_hedergen()
    global switchbot_apiHeader
    for i in range(0, tries):
        try:
            result = requests.get(url=apiendpointurl , headers=switchbot_apiHeader)
            result.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if i + 1 == tries:
                print(i)
                raise e
            time.sleep(retry_interval)
            continue
    return result.json()



############################アカウントに登録されているデバイスを取得してリストを返す。
#リストは最後の取得からswitchbot_devicelist_life秒経過していなければ、キャッシュから応答する。
def get_switchbot_device_list():
    apitopurl = switchbot_api_top + 'devices'
    global switchbot_devicelist
    global switchbot_devicelist_lastupdate

    if switchbot_devicelist_lastupdate == "" or switchbot_devicelist_lastupdate  <= time.time() - switchbot_devicelist_life:
        #デバイスリストがまだない or 最後の取得からswitchbot_devicelist_life秒経過している。
        body = switchbot_get(apitopurl)
        switchbot_devicelist =  body['body']['deviceList']
        switchbot_devicelist_lastupdate = time.time()
    else:
        #キャッシュで応答
        pass
    return switchbot_devicelist

######################################################################################## 単一のデバイスステータスを取得する取得時間も付与。
def get_device_status(deviceId: str = ""):
    result = False

    apitopurl = switchbot_api_top + 'devices/' + str(deviceId) + '/status'

    result = switchbot_get(apitopurl)
    result['body'].update(date=str(time.time()).split('.')[0])
                          
    if result['statusCode'] == 100:
        return result
    else:
        print(result['statusCode'])
        #raise Exception
        return result


######################################################################################## スイッチボットのBOTで物理ボタンを押す。

def push_switchbot_bot(deviceId: str = ""):
    result = False
    apitopurl = switchbot_api_top + 'devices/' + deviceId + '/commands'

    request= {
    "command": "press",
    "parameter": "default",
    "commandType": "command"
    }
    result = switchbot_post(apitopurl,request)
    return result


def on_switchbot_bot(deviceId: str = ""):
    result = False
    apitopurl = switchbot_api_top + 'devices/' + deviceId + '/commands'

    request= {
    "command": "turnOn",
    "parameter": "default",
    "commandType": "command"
    }
    result = switchbot_post(apitopurl,request)
    return result


def off_switchbot_bot(deviceId: str = ""):
    result = False
    apitopurl = switchbot_api_top + 'devices/' + deviceId + '/commands'

    request= {
    "command": "turnOff",
    "parameter": "default",
    "commandType": "command"
    }
    result = switchbot_post(apitopurl,request)
    return result


######################################################################################## スイッチボットのPlugをON/OFFする。
def ctrl_switchbot_plug(deviceId: str,status: int):

    if(status == 1):
        command="turnOn"
    elif(status == 0):
        command="turnOff"
    else:
        raise Exception
    
    apitopurl = switchbot_api_top + 'devices/' + deviceId + '/commands'
    request= {
    "command": command,
    "parameter": "default",
    "commandType": "command"
    }  

    result = switchbot_post(apitopurl,request)

    return result


######################################################################################## メイン関数。
def main():

    pass

if __name__ == "__main__":
    main()

