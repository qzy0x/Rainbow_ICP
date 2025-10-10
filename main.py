from colorama import init, Fore, Style
from crack import Crack
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from urllib import parse
import random
import argparse
import base64
import hashlib
import json
import pyperclip
import requests
import time
import uuid
requests.packages.urllib3.disable_warnings()
init(autoreset=True)
colors = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN]

def auth():
    t = str(round(time.time()))
    data = {
        "authKey": hashlib.md5(("testtest" + t).encode()).hexdigest(),
        "timeStamp": t
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://beian.miit.gov.cn/",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://beian.miit.gov.cn"
    }
    try:
        resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth",verify=False, headers=headers,
                             data=parse.urlencode(data)).text
        return json.loads(resp)["params"]["bussiness"]
    except Exception:
        time.sleep(5)
        resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth",verify=False, headers=headers,
                             data=parse.urlencode(data)).text
        return json.loads(resp)["params"]["bussiness"]


def getImage(token):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://beian.miit.gov.cn/",
        "Token": token,
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://beian.miit.gov.cn"
    }
    payload = {
        "clientUid": "point-" + str(uuid.uuid4())
    }
    try:
        resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/getCheckImagePoint",
                             headers=headers,verify=False, json=payload).json()
        return resp["params"], payload["clientUid"]
    except Exception:
        time.sleep(5)
        resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/getCheckImagePoint",
                             headers=headers, verify=False,json=payload).fjson()
        return resp["params"], payload["clientUid"]


def aes_ecb_encrypt(plaintext: bytes, key: bytes, block_size=16):
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=backend)

    padding_length = block_size - (len(plaintext) % block_size)
    plaintext_padded = plaintext + bytes([padding_length]) * padding_length

    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext_padded) + encryptor.finalize()

    return base64.b64encode(ciphertext).decode('utf-8')


def generate_pointjson(big_img, small_img, secretKey,crack):
    boxes = crack.detect(big_img)
    if not boxes:
        return False
    points = crack.siamese(small_img, boxes)
    new_points = [[p[0] + 20, p[1] + 20] for p in points]
    pointJson = [{"x": p[0], "y": p[1]} for p in new_points]
    # print(json.dumps(pointJson))
    enc_pointJson = aes_ecb_encrypt(json.dumps(pointJson).replace(" ", "").encode(), secretKey.encode())
    return enc_pointJson


def checkImage(uuid_token, secretKey, clientUid, pointJson,token):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://beian.miit.gov.cn/",
        "Token": token,
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://beian.miit.gov.cn"
    }
    data = {
        "token": uuid_token,
        "secretKey": secretKey,
        "clientUid": clientUid,
        "pointJson": pointJson
    }
    resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/checkImage", headers=headers,
                         json=data,verify=False).json()
    if resp["code"] == 200 and resp["success"] == True:
            return resp["params"]["sign"]
    return False


def query(sign, uuid_token, domain,token):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://beian.miit.gov.cn/",
        "Token": token,
        "Sign": sign,
        "Uuid": uuid_token,
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://beian.miit.gov.cn",
        "Content-Type": "application/json",
        "Cookie": "__jsluid_s="+str(uuid.uuid4().hex[:32])
    }
    data = {"pageNum": "1", "pageSize": "1", "unitName": domain, "serviceType": 1}
    resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition",
                         headers=headers,verify=False, data=json.dumps(data).replace(" ","")).json()
    Size = resp["params"]["total"]
    data = {"pageNum": "1", "pageSize": f"{Size}", "unitName": domain, "serviceType": 1}
    respp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition",
                         headers=headers,verify=False, data=json.dumps(data).replace(" ","")).json()
    return respp


def main():
    fire_color = Fore.LIGHTRED_EX
    ascii_art = """\n 作者: qzy0x                           版本: 1.0
     (                                    (         (     
     )\ )                 )               )\ )  (   )\ )  
    (()/(   ) (        ( /(     (  (     (()/(  )\ (()/(  
     /(_)| /( )\  (    )\()) (  )\))(     /(_)|((_) /(_)) 
    (_)) )(_)|(_) )\ )((_)\  )\((_)()\   (_)) )\___(_))   
    | _ ((_)_ (_)_(_/(| |(_)((_)(()((_)  |_ _((/ __| _ \  
    |   / _` || | ' \)) '_ Y _ \ V  V /   | | | (__|  _/  
    |_|_\__,_||_|_||_||_.__|___/\_/\_/___|___| \___|_|    
                                    |_____|               
                    鸣谢: ravizhan"""
    print(fire_color + ascii_art)
    parser = argparse.ArgumentParser(description="ICP spider - 指定目标参数")
    parser.add_argument('-t', '--target', required=True, help='目标（例如：域名或公司名字）')
    args = parser.parse_args()
    target = args.target
    crack = Crack()
    token = auth()
    pointjson = None
    sign = None
    time.sleep(0.1)
    print(f'\n{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 获取验证码')
    while not sign:
        while not pointjson:
            params, clientUid = getImage(token)
            pointjson = generate_pointjson(params["bigImage"], params["smallImage"], params["secretKey"],crack)
            time.sleep(0.3)
        sign = checkImage(params["uuid"], params["secretKey"], clientUid, pointjson,token)
        time.sleep(0.3)
        if sign:
            print(f'{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 验证码识别成功\n')
            resp = query(sign, params["uuid"], target,token)
            return resp
        pointjson = None

if __name__ == "__main__":
    record = main()
    records = record.get("params", {}).get("list", [])
    for xx,r in enumerate(records, start=1):
        domain = r.get("domain", "")
        serviceLicence = r.get("serviceLicence", "")
        natureName = r.get("natureName", "")
        unitName = r.get("unitName", "")
        color = random.choice(colors)
        print(
            f"{color}[{xx}]{Style.RESET_ALL} "                  # 七彩数字箭头标识
            f"{Fore.WHITE}{domain:<22}"                             # 域名白色
            f"{Fore.LIGHTYELLOW_EX}{serviceLicence:<22}"           # 备案号淡黄色
            f"{Fore.LIGHTGREEN_EX}{natureName:<6}"                # 企业类型淡绿
            f"{Fore.LIGHTCYAN_EX}{unitName}"                      # 公司名称淡青
        )
    print(f'\n{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 域名已经全部复制到粘贴板\n')
    domains = [r.get("domain", "") for r in records]
    domains_text = "\n".join(domains)
    pyperclip.copy(domains_text)