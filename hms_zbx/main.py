# zabbix api rapper for hms.
# JSON取り扱い
import json
#時刻取り扱い
import urllib.request
import ssl
import os
import re
import sys

########################################################ログ関連

print(__name__)
print("ZBX LIB LOADED")

apiversion=0

ascii_symbols = {
    "!": "_exclamation_",
    "\"": "_quotation_",
    "#": "_number_",
    "$": "_dollar_",
    "%": "_percent_",
    "&": "_ampersand_",
    "'": "_apostrophe_",
    "(": "_leftparenthesis_",
    ")": "_rightparenthesis_",
    "*": "_asterisk_",
    "+": "_plus_",
    ",": "_comma_",
    "/": "_slash_",
    ":": "_colon_",
    ";": "_semicolon_",
    "<": "_lessthan_",
    "=": "_equal_",
    ">": "_greaterthan_",
    "?": "_question_",
    "@": "_at_",
    "[": "_leftbracket_",
    "\\": "_backslash_",
    "]": "_rightbracket_",
    "^": "_caret_",
    "`": "_grave_",
    "{": "_leftbrace_",
    "|": "_verticalbar_",
    "}": "_rightbrace_",
    "~": "_tilde_"
}


######################################################################################## HTTPSの証明書検証エラー時にどう扱うかの取り扱い
# フラグ未設定時はセキュア優先
_ZBX_API_SERVER_CERT_VERIFY = int(os.getenv('_ZBX_API_SERVER_CERT_VERIFY','1'))

if _ZBX_API_SERVER_CERT_VERIFY == 1:
    print('_ZBX_API_SERVER_CERT_VERIFY is enabled.')
else:
    ssl._create_default_https_context = ssl._create_unverified_context
    print('_ZBX_API_SERVER_CERT_VERIFY is disabled.')

######################################################################################## Zabbix API認証情報
# for api
_ZBX_API_SERVER = os.getenv('_ZBX_API_SERVER')
_ZBX_APIKEY = os.getenv('_ZBX_APIKEY')
_ZBX_CALLPOINT = str(_ZBX_API_SERVER) + "/zabbix/api_jsonrpc.php"

########################################## ATENTION for zabbix server config.
# if you want to get the "last value", when the value lest 24h ago,
# ZBX_HISTORY_PERIOD in /usr/share/zabbix/include/defines.inc.php on ZBX SERVER.
# the parameter is in sec. default:86400, the period will infinity ,if you set 0.
# see also https://www.zabbix.com/documentation/3.0/en/manual/web_interface/definitions.

########################################################################################  zabbix関連関数
def callzabbix(parameter, content):
    result = False
    request = urllib.request.Request(
        url = _ZBX_CALLPOINT,
        data = json.dumps(parameter).encode()
    )
    request.add_header('Content-Type','application/json-rpc')

    # apiinfo.version を要求する場合、認証ヘッダを付けてはならない
    if parameter['method'] !='apiinfo.version':
        request.add_header('Authorization',f'Bearer {_ZBX_APIKEY}')
    
    try:
        with urllib.request.urlopen(request) as response:
            dictans = json.loads(response.read())
            if "result" in dictans:
                content["result"] = dictans["result"]
                result = True
            else:
                content["error"] = dictans["error"]
        # print("OK")
    except urllib.error.HTTPError as err:
        print("WARN",err.code)
        return False
    except urllib.error.URLError as err:
        print("ERROR",err.reason)
        return False
 
    return result


#指定されたアイテムIDのヒストリを取得する
def get_history(params):

    try:
        value_type = get_item_value_typebyid(params['itemids'])[0]['value_type']
    except:
        response = {'result': 204 }
        print('204')
        return response

    request = {
    "jsonrpc": "2.0",
    "method": "history.get",
    "params": params,
    "id": 1
    }
    request["params"]["history"] = value_type
    response = {}
    callzabbix(request, response)

    return response


# 指定されたキーを持つホストの情報を返す。　hostidが与えられた場合はそのhostidに限定する。
def get_item_bykey(key_name: str = None, host_id: int = ""):
    request = {
    "jsonrpc": "2.0",
    "method": "item.get",
    "params": {
        "output": ["itemid","hostid","name","key_","description","lastclock","lastns","lastvalue","tags"],
        #"output": "extend",
        "templated": False,
        "selectTags": ["tag", "value"],
        "filter": {
            "key_": key_name
        }
    },
    "id": 1
    }
    #print(request)

    if(host_id !=""):
        request["params"].update(hostids= host_id)

    #print(request)

    response = {}
    callzabbix(request, response)
    return response
    
# 指定されたパラメータでitemを探す
def search_item(params: dict = None):
    request = {
    "jsonrpc": "2.0",
    "method": "item.get",
    "params": params,
    "id": 1
    }

    response = {}
    callzabbix(request, response)
    return response
# 指定されたパラメータでホストを探す
def search_host(params):
    request = {
    "jsonrpc": "2.0",
    "method": "host.get",
    "params": params,
    "id": 1
    }

    response = {}
    callzabbix(request, response)
    return response


# ZabbixのAPIバージョンを返す
def get_api_version():

    request = {
        "jsonrpc": "2.0",
        "method": "apiinfo.version",
        "params": [],
        "id": 1
    }
    response = {}

    print(_ZBX_CALLPOINT)
    callzabbix(request, response)

    print(response)


    return response


# itemidを与えてアイテムの情報を検索する。


# itemidを与えて、そのitemのvalue_typeを得る。
def get_item_value_typebyid(item_id: int):
    request = {
    "jsonrpc": "2.0",
    "method": "item.get",
    "params": {
        "output": ["value_type"],
        "templated": False,
        "itemids": item_id
    },
    "id": 1
    }
    response = {}
    callzabbix(request, response)

    print(response)
    if "result" in response:
        response = response["result"]
    else:
        raise Exception
    return response

# ホストを取得する 　ホスト名を与える。戻りは配列。
def get_host(host_name: str):
    request= {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "selectTags": "extend",
            "filter": {
                "host": [
                    host_name
                ]
            }
        },
    "id": 1
    }
    response = {}
    callzabbix(request, response)
    return response

# グループを取得する。グループ名を与える。
def get_group(group_name: str ="Discovered hosts"):
    
    request = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {
            "output": "extend",
            "filter": {
                "name": [
                    group_name
                ]
            }
        },
        "id": 1
    }

    response = {}
    callzabbix(request, response)
    return response
# テンプレートを取得する。テンプレート名名を与える。
def get_template(template_name: str =""):
    
    request = {
        "jsonrpc": "2.0",
        "method": "template.get",
        "params": {
            "output": "extend",
            "filter": {
                "host": [
                    template_name
                ]
            }
        },
        "id": 1
    }

    response = {}
    callzabbix(request, response)
    return response
def create_group(group_name: str ="hms_autocreate_group"):

    response = get_group(group_name)
    if( len(response['result']) >= 1 ):
        return response
        #既にあったので終わり
    else:
        request = {
            "jsonrpc": "2.0",
            "method": "hostgroup.create",
            "params": {
                "name": group_name
            },
            "id": 1}
        response = {}
        callzabbix(request, response)
        response = get_group(group_name)
        return response
# ホストを作成する。 引数はホスト(ユニークである必要がある),グループID(事前に存在している必要がある.　そうでない場合 "Discovered hosts"グループが使用される)
def create_host(host_name: str, group_id: int = 0):

    if group_id == 0:
        group_id = get_group()['result'][0]['groupid']
    response = get_host(host_name)
    if( len(response['result']) >= 1 ):
        return response
        #既にあったので終わり
    else:
        request = {
        "jsonrpc": "2.0",
        "method": "host.create",
        "params": {
            "host": host_name,
            "groups": [
                {
                    "groupid": group_id #you have to create before run it. int.
                }
            ],
        },
        "id": 1
        }
        response = {}
        callzabbix(request, response)

        response = get_host(host_name)
        return response


# 定義済みホストの情報を更新する
# payload ={"hostid": 10633,"name":"キッチンプラグ" } の用に書く。
def update_host(payload: dict):
    request = {
        "jsonrpc": "2.0",
        "method": "host.update",
        "params": {},
        "id": 1
        }

    request['params'] = payload

    print(request)

    response = {}
    callzabbix(request, response)

    return response


# Zabbixのkey_として受け入れ可能な文字列に置換する
def conv_safe_key(keyname):

    # 正規表現パターンを定義
    # これ以外はkey_として受け入れ不可能(zabbixの仕様)
    safe_pattern = r'^[0-9a-zA-Z_.-]+$'

    keyname_safe = keyname
    # 文字列がパターンにマッチするかチェック,マッチしない->置換する.
    if not re.match(safe_pattern, keyname):
        for symbol, description in ascii_symbols.items():
            keyname_safe = keyname_safe.replace(symbol, description)
        #print(keyname + " ---> "+ keyname_safe)
    return keyname_safe


# ホストにアイテムを作成する。ホストがない場合自動で作成される。
def create_item(host_name: str ,target_key: str, value_type: int, tags: dict = [{"tag":"type","value":"undefined"}]):

    response_host = create_host(host_name)

    # key_ を使用可能文字列に置換
    target_key_safe = conv_safe_key(target_key)

    # key_からitemidを取得する
    response = get_item_bykey(target_key_safe, response_host['result'][0]['hostid'])

    if( len(response['result']) >= 1 ):
    
        #print('already exist')
        return response
        #既にあったので終わり

    else:
        print('create')

        request = {
        "jsonrpc": "2.0",
        "method": "item.create",
        "params": {
            "name": target_key, 
            "key_": target_key_safe,
            "hostid": response_host['result'][0]['hostid'],
            "type": 2, #type 2 means trapper.
            "value_type": value_type, # 0 - numeric float, 1 is character(up to 255 byte), # 4 is text(unlimited size)
            "tags": tags
        },
        "id": 1
        }

        print(request)
        response = {}
        callzabbix(request, response)
        return response
#########################################################################################################
#データ投げ込み用関数
#APIのバージョンによって挙動を変えるためのラッパー. Zabbix 7.0以降はAPI経由でのデータ挿入を使用。
def push_history(item_list):
    print('push data to zabbix')
    item_list_safe = []
    #item key_を置換する
    for item in item_list:
        item['key'] = conv_safe_key(item['key'])
        item_list_safe.append(item)


    if( int(apiversion.split('.')[0]) >= 7):
        #print('put new mode')
        return push_history7(item_list_safe)   
    else:
        return "error zabbix is too old."
######################################################################################################### Zabbix 7.0ではデータinputに対応した。
#API経由でデータを入れる場合
def push_history7(payload):
    if type(payload) is list or type(payload) is dict :
        request = {
        "jsonrpc": "2.0",
        "method": "history.push",
        "params": [{}
        ],
        "id": 1
        }

        request['params'] = payload
        #print(request)
        response = {}
        callzabbix(request, response)
        #print(response)
        return response

    else:
        print('payload is not list or dict')
        raise Exception
        
######################################################################################## メイン関数。
def main():
    pass
if __name__ == "__main__":
    main()

apiversion = get_api_version()['result']
