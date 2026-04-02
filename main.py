from colorama import init, Fore, Style
from slider_captcha import solve_captcha_x
from urllib import parse
import random
import argparse
import hashlib
import json
import pyperclip
import requests
import time
import uuid
import unicodedata
import re

requests.packages.urllib3.disable_warnings()

init(autoreset=True)
colors = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN]
PROXIES = None

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)


def _browser_headers(**extra):
    h = {
        "User-Agent": DEFAULT_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://beian.miit.gov.cn",
        "Referer": "https://beian.miit.gov.cn/",
        "Connection": "keep-alive",
    }
    h.update(extra)
    return h


def auth():
    t = str(int(time.time()))
    data = {
        "authKey": hashlib.md5(("testtest" + t).encode()).hexdigest(),
        "timeStamp": t,
    }
    headers = _browser_headers()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        resp = requests.post(
            "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth",
            verify=False,
            headers=headers,
            data=parse.urlencode(data),
            proxies=PROXIES,
        ).text
        return json.loads(resp)["params"]["bussiness"]
    except Exception:
        time.sleep(5)
        try:
            resp = requests.post(
                "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth",
                verify=False,
                headers=headers,
                data=parse.urlencode(data),
                proxies=PROXIES,
            ).text
            return json.loads(resp)["params"]["bussiness"]
        except Exception:
            return ""


def getImage(token):
    """拉取验证码图片；与 yzm.go 一致，返回 params 或 None。"""
    payload = {"clientUid": "point-" + str(uuid.uuid4())}
    headers = _browser_headers(Token=token, **{"Content-Type": "application/json"})
    url = "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/getCheckImagePoint"
    try:
        resp = requests.post(url, headers=headers, verify=False, json=payload, proxies=PROXIES).json()
        if resp.get("success") and resp.get("params"):
            p = resp["params"]
            if p.get("bigImage") and p.get("smallImage") and p.get("uuid"):
                return p
    except Exception:
        pass
    time.sleep(5)
    try:
        resp = requests.post(url, headers=headers, verify=False, json=payload, proxies=PROXIES).json()
        if resp.get("success") and resp.get("params"):
            p = resp["params"]
            if p.get("bigImage") and p.get("smallImage") and p.get("uuid"):
                return p
    except Exception:
        pass
    return None


def checkImage(captcha_uuid, slider_x, token):
    """提交滑块 x；请求体 key / value（与 yzm.go 一致）。"""
    headers = _browser_headers(Token=token, **{"Content-Type": "application/json"})
    data = {"key": captcha_uuid, "value": str(int(slider_x))}
    try:
        resp = requests.post(
            "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/checkImage",
            headers=headers,
            json=data,
            verify=False,
            proxies=PROXIES,
        ).json()
        if resp.get("code") == 200 and resp.get("success") is True:
            p = resp.get("params")
            if isinstance(p, str):
                return p
            if isinstance(p, dict) and p.get("sign"):
                return p["sign"]
    except Exception:
        pass
    return False


def query(sign, uuid_token, domain, token, service_type=1):
    headers = {
        "User-Agent": DEFAULT_UA,
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
        "Cookie": "__jsluid_s=" + str(uuid.uuid4().hex[:32])
    }
    
    # 封装一个内部请求函数，包含重试机制
    def retry_request(url, data_dict):
        for attempt in range(3): # 尝试 3 次 (1次正常 + 2次重试)
            try:
                r = requests.post(url, headers=headers, verify=False, 
                                  data=json.dumps(data_dict).replace(" ", ""), proxies=PROXIES)
                return r.json()
            except Exception:
                time.sleep(1) # 失败等待1秒
                continue
        # 3次都失败
        print(f'{Fore.RED}json解析失败{Style.RESET_ALL}')
        return {"code": 500, "msg": "json解析失败", "params": {"list": [], "total": 0}}

    page_size = 40
    data = {"pageNum": "1", "pageSize": str(page_size), "unitName": domain, "serviceType": service_type}
    
    # 使用重试机制请求第一页
    resp = retry_request("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition", data)

    try:
        total = resp.get("params", {}).get("total", 0) or 0
        aggregated = resp.get("params", {}).get("list", []) or []
        
        if isinstance(total, int) and total > len(aggregated):
            total_pages = (total + page_size - 1) // page_size
            for page in range(2, total_pages + 1):
                print(f'{Fore.LIGHTCYAN_EX}[+]{Style.RESET_ALL} 翻页获取第 {page}/{total_pages} 页 ...')
                time.sleep(0.5)
                data = {"pageNum": str(page), "pageSize": str(page_size), "unitName": domain, "serviceType": service_type}
                # 翻页请求也使用重试机制
                page_resp = retry_request("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition", data)
                
                page_list = page_resp.get("params", {}).get("list", []) or []
                aggregated.extend(page_list)
                
            resp["params"]["list"] = aggregated
        return resp
    except Exception:
        return resp


def query_detail_by_app_mini(sign, uuid_token, token, data_id, service_type):
    headers = {
        "User-Agent": DEFAULT_UA,
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
        "Cookie": "__jsluid_s=" + str(uuid.uuid4().hex[:32])
    }
    payload = {"dataId": data_id, "serviceType": service_type}
    
    # 详情页查询也加上简单的重试
    for _ in range(3):
        try:
            resp = requests.post(
                "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryDetailByAppAndMiniId",
                headers=headers, verify=False, data=json.dumps(payload).replace(" ", ""), proxies=PROXIES
            ).json()
            return resp
        except Exception:
            time.sleep(1)
            
    print(f'{Fore.RED}详情页json解析失败{Style.RESET_ALL}')
    return {"params": {}}

def main():
    fire_color = Fore.LIGHTRED_EX
    ascii_art = """\n 作者: qzy0x                           版本: 2.0
     (                                    (         (     
     )\ )                 )               )\ )  (   )\ )  
    (()/(   ) (        ( /(     (  (     (()/(  )\ (()/(  
     /(_)| /( )\  (    )\()) (  )\))(     /(_)|((_) /(_)) 
    (_)) )(_)|(_) )\ )((_)\  )\((_)()\   (_)) )\___(_))   
    | _ ((_)_ (_)_(_/(| |(_)((_)(()((_)  |_ _((/ __| _ \  
    |   / _` || | ' \)) '_ Y _ \ V  V /   | | | (__|  _/  
    |_|_\__,_||_|_||_||_.__|___/\_/\_/___|___| \___|_|    
                                    |_____|               
"""
    print(fire_color + ascii_art)
    parser = argparse.ArgumentParser(description="ICP spider - 查询目标备案信息")
    parser.add_argument('-t', '--target', required=False, help='目标（例如：域名或公司名或备案号）')
    parser.add_argument('-f', '--file', required=False, help='从文件读取目标，一行一个')
    parser.add_argument('-type', '--type', default=1, type=int, choices=[1, 6, 7, 8],
                        help='类型（默认1；网站=1,APP=6,小程序=7,快应用=8）')
    parser.add_argument('-p', '--proxy', required=False, help='全局代理（例如：http://127.0.0.1:8080 或 socks5://127.0.0.1:1080）')
    args = parser.parse_args()
    target = args.target
    file_path = args.file
    service_type = args.type
    if args.proxy:
        global PROXIES
        PROXIES = {"http": args.proxy, "https": args.proxy}
    if not target and not file_path:
        raise SystemExit("请提供 -t 或 -f 参数")
    token = auth()
    sign = None
    params = None
    time.sleep(0.1)
    print(f'\n{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 获取验证码')
    while not sign:
        p = getImage(token)
        if not p:
            time.sleep(0.3)
            continue
        params = p
        try:
            slider_x = solve_captcha_x(params["bigImage"], params["smallImage"])
        except Exception:
            time.sleep(0.3)
            continue
        sign = checkImage(params["uuid"], slider_x, token)
        time.sleep(0.3)
        if sign:
            print(f'{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 验证码识别成功\n')
            if file_path:
                targets = []
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            x = line.strip()
                            if x:
                                targets.append(x)
                except Exception:
                    targets = []
                out_index = 0
                for t in targets:
                    resp = query(sign, params["uuid"], t, token, service_type)
                    # 如果code不为200，说明可能验证码失效或被拦截
                    if resp.get("code") != 200 or resp.get("success") is False:
                        # 检查是否因为 json解析失败导致的空返回，如果是，这里会重试验证码
                        # 你可以根据需要决定是否打印详细错误
                        sign = None
                        while not sign:
                            p = getImage(token)
                            if not p:
                                time.sleep(0.2)
                                continue
                            params = p
                            try:
                                slider_x = solve_captcha_x(params["bigImage"], params["smallImage"])
                            except Exception:
                                time.sleep(0.2)
                                continue
                            sign = checkImage(params["uuid"], slider_x, token)
                            time.sleep(0.2)
                        resp = query(sign, params["uuid"], t, token, service_type)
                    
                    # --- 如果输入是域名，提取并按公司名重查 ---
                    if t and re.match(r'^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$', t):
                        _tmp_lst = resp.get("params", {}).get("list", []) or []
                        if _tmp_lst:
                            unitName = _tmp_lst[0].get("unitName", "")
                            if unitName and unitName != t:
                                print(f"{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 目标 {t} 识别为域名，提取到主体: {Fore.LIGHTCYAN_EX}{unitName}{Style.RESET_ALL}，正在重新查询主体下资产...")
                                time.sleep(0.5)
                                resp_new = query(sign, params["uuid"], unitName, token, service_type)
                                if resp_new.get("code") == 200 and resp_new.get("success") is True:
                                    resp = resp_new

                    lst = resp.get("params", {}).get("list", []) or []
                    if service_type == 1:
                        for r in lst:
                            out_index += 1
                            domain = r.get("domain", "")
                            serviceLicence = r.get("serviceLicence", "")
                            natureName = r.get("natureName", "")
                            unitName = r.get("unitName", "")
                            color = random.choice(colors)
                            print(
                                f"{color}[{out_index}]{Style.RESET_ALL} "
                                f"{Fore.WHITE}{domain:<22}"
                                f"{Fore.LIGHTYELLOW_EX}{serviceLicence:<22}"
                                f"{Fore.LIGHTGREEN_EX}{natureName:<6}"
                                f"{Fore.LIGHTCYAN_EX}{unitName}"
                            )
                    elif service_type in (6, 7):
                        name_w, licence_w, nature_w = 30, 30, 6
                        for r in lst:
                            data_id = r.get("dataId")
                            if data_id is None:
                                continue
                            time.sleep(0.15)
                            detail_resp = query_detail_by_app_mini(sign, params["uuid"], token, data_id, service_type)
                            prms = detail_resp.get("params", {})
                            serviceName = prms.get("serviceName", "")
                            serviceLicence = prms.get("serviceLicence", "")
                            natureName = prms.get("natureName", "")
                            unitName = prms.get("unitName", "")
                            out_index += 1
                            color = random.choice(colors)
                            print(
                                f"{color}[{out_index}]{Style.RESET_ALL} "
                                f"{Fore.WHITE}{pad_display(serviceName, name_w)}"
                                f"{Fore.LIGHTYELLOW_EX}{pad_display(serviceLicence, licence_w)}"
                                f"{Fore.LIGHTGREEN_EX}{pad_display(natureName, nature_w)}"
                                f"{Fore.LIGHTCYAN_EX}{unitName}"
                            )
                    time.sleep(0) # 1111111111111111111
                return {"params": {"list": []}}, service_type, {"sign": sign, "uuid": params["uuid"], "token": token,
                                                              "streamed": True}
            else:
                resp = query(sign, params["uuid"], target, token, service_type)
                
                # --- 如果输入是域名，提取并按公司名重查 ---
                if target and re.match(r'^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$', target):
                    _tmp_lst = resp.get("params", {}).get("list", []) or []
                    if _tmp_lst:
                        unitName = _tmp_lst[0].get("unitName", "")
                        if unitName and unitName != target:
                            print(f"{Fore.LIGHTGREEN_EX}[+]{Style.RESET_ALL} 目标 {target} 识别为域名，提取到主体: {Fore.LIGHTCYAN_EX}{unitName}{Style.RESET_ALL}，正在重新查询主体下资产...\n")
                            time.sleep(0.5)
                            resp_new = query(sign, params["uuid"], unitName, token, service_type)
                            if resp_new.get("code") == 200 and resp_new.get("success") is True:
                                resp = resp_new

                return resp, service_type, {"sign": sign, "uuid": params["uuid"], "token": token}

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
    if ctx.get("streamed"):
        pass
    else:
        records = record.get("params", {}).get("list", [])
        if service_type == 1:
            output_website_records(records)
        elif service_type in (6, 7):
            output_app_mini_records(records, ctx["sign"], ctx["uuid"], ctx["token"], service_type)
