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
import unicodedata
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


def query(sign, uuid_token, domain,token, service_type=1):
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
    page_size = 40
    data = {"pageNum": "1", "pageSize": str(page_size), "unitName": domain, "serviceType": service_type}
    resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition",
                         headers=headers,verify=False, data=json.dumps(data).replace(" ","")).json()
    try:
        total = resp.get("params", {}).get("total", 0) or 0
        aggregated = resp.get("params", {}).get("list", []) or []
        if isinstance(total, int) and total > len(aggregated):
            total_pages = (total + page_size - 1) // page_size
            for page in range(2, total_pages + 1):
                print(f'{Fore.LIGHTCYAN_EX}[+]{Style.RESET_ALL} 翻页获取第 {page}/{total_pages} 页 ...')
                time.sleep(0.5)
                data = {"pageNum": str(page), "pageSize": str(page_size), "unitName": domain, "serviceType": service_type}
                page_resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition",
                         headers=headers,verify=False, data=json.dumps(data).replace(" ","")).json()
                page_list = page_resp.get("params", {}).get("list", []) or []
                aggregated.extend(page_list)
            resp["params"]["list"] = aggregated
        return resp
    except Exception:
        return resp


def query_detail_by_app_mini(sign, uuid_token, token, data_id, service_type):
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
    payload = {"dataId": data_id, "serviceType": service_type}
    resp = requests.post(
        "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryDetailByAppAndMiniId",
        headers=headers, verify=False, data=json.dumps(payload).replace(" ", "")
    ).json()
    return resp

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
    parser = argparse.ArgumentParser(description="ICP spider - 查询目标备案信息")
    parser.add_argument('-t', '--target', required=True, help='目标（例如：域名或公司名或备案号）')
    parser.add_argument('-type', '--type', default=1, type=int, choices=[1,6,7,8],
                        help='类型（默认1；网站=1,APP=6,小程序=7,快应用=8）')
    args = parser.parse_args()
    target = args.target
    service_type = args.type
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
        # 在 main() 中，在返回前插入针对 APP/小程序的详情查询
        if sign:
            print(f'{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 验证码识别成功\n')
            resp = query(sign, params["uuid"], target,token, service_type)
            return resp, service_type, {"sign": sign, "uuid": params["uuid"], "token": token}
        pointjson = None

def output_website_records(records):
    for xx, r in enumerate(records, start=1):
        domain = r.get("domain", "")
        serviceLicence = r.get("serviceLicence", "")
        natureName = r.get("natureName", "")
        unitName = r.get("unitName", "")
        color = random.choice(colors)
        print(
            f"{color}[{xx}]{Style.RESET_ALL} "
            f"{Fore.WHITE}{domain:<22}"
            f"{Fore.LIGHTYELLOW_EX}{serviceLicence:<22}"
            f"{Fore.LIGHTGREEN_EX}{natureName:<6}"
            f"{Fore.LIGHTCYAN_EX}{unitName}"
        )
    print(f'\n{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 域名已经全部复制到粘贴板\n')
    domains = [r.get("domain", "") for r in records]
    domains_text = "\n".join(domains)
    pyperclip.copy(domains_text)

def _display_width(s):
    w = 0
    for ch in str(s or ""):
        e = unicodedata.east_asian_width(ch)
        w += 2 if e in ("F", "W") else 1
    return w

def pad_display(s, width):
    s = str(s or "")
    w = _display_width(s)
    if w >= width:
        return s
    return s + " " * (width - w)

def output_app_mini_records(records, sign, uuid_token, token, service_type):
    names = []
    name_w, licence_w, nature_w = 30, 30, 6
    for xx, r in enumerate(records, start=1):
        data_id = r.get("dataId")
        if data_id is None:
            continue
        time.sleep(0.15)
        detail_resp = query_detail_by_app_mini(sign, uuid_token, token, data_id, service_type)
        params = detail_resp.get("params", {})
        serviceName = params.get("serviceName", "")
        serviceLicence = params.get("serviceLicence", "")
        natureName = params.get("natureName", "")
        unitName = params.get("unitName", "")
        names.append(serviceName)
        color = random.choice(colors)
        print(
            f"{color}[{xx}]{Style.RESET_ALL} "
            f"{Fore.WHITE}{pad_display(serviceName, name_w)}"
            f"{Fore.LIGHTYELLOW_EX}{pad_display(serviceLicence, licence_w)}"
            f"{Fore.LIGHTGREEN_EX}{pad_display(natureName, nature_w)}"
            f"{Fore.LIGHTCYAN_EX}{unitName}"
        )
    print(f'\n{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 内容已经全部复制到粘贴板\n')
    pyperclip.copy("\n".join([n for n in names if n]))

if __name__ == "__main__":
    record, service_type, ctx = main()
    records = record.get("params", {}).get("list", [])
    if service_type == 1:
        output_website_records(records)
    elif service_type in (6, 7):
        output_app_mini_records(records, ctx["sign"], ctx["uuid"], ctx["token"], service_type)