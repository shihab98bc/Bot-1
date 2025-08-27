import os
import orjson
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio
import random
import httpx
from html import escape
from requests_toolbelt.multipart.encoder import MultipartEncoder
import re
from datetime import datetime
from urllib.parse import quote
import time
import aiohttp
from selectolax.parser import HTMLParser
from diskcache import Cache
import pyotp
import json
from bs4 import BeautifulSoup
cache = Cache('cache_dir')
IVASMS_NUMBERS_CACHE_KEY = 'ivasms_numbers_cache'


load_dotenv("config.env")
TOKEN = os.getenv("BOT_TOKEN")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IVASMS_REFRESH_INTERVAL = 12 * 60 * 60
user_last_active = {}
ivasms_numbers_cache: list[tuple[str, str]] = []
ivasms_numbers_cache_ts: float | None = None
ivasms_cache_lock = asyncio.Lock()
INACTIVITY_TIMEOUT = 30 * 60
group_id = -1002845536950

BASE_URL_NUMBERS = "https://www.ivasms.com/portal/sms/received/getsms/number"
BASE_URL_MESSAGES = "https://www.ivasms.com/portal/sms/received/getsms/number/sms"

cookies = {
    "XSRF-TOKEN": "eyJpdiI6IlZraUNSK1dBdlFGYnpwUnpuYlBFTWc9PSIsInZhbHVlIjoia1NhNFYvWktxVmduYUFyb1A3endmcHUrbVgwMlJzeXVwTUdXbEJPNi9uVzd1SVRhQ2M3YWZDcU1qNWZjNHpwK0hkQ3Q0akRKYkd4OUVTSXNxZllEWmQ3OXlvbmM5MVQyYnFVWHZzOEJib1Q4OWU0TzF2d0kwSVlFK2h5SVJXaWciLCJtYWMiOiIxZjRjZmFiMTE2ZmU3YmQ3MGE0M2FhMTk1YjZjZWJiMmI0NzZlYjkzNzJiNmU2ODNkZDg3ZjU1NDdhZWI2MDRjIiwidGFnIjoiIn0%3D; expires=Sun, 24 Aug 2025 18:43:37",
    "ivas_sms_session": "eyJpdiI6IlV5VjlxSURQNlFrV0VPWUgxZ1Y3SHc9PSIsInZhbHVlIjoicFZpU050SE9TMWoxV0Qxdi9IRDZ6eHArWklQWmg4Mjkrbm1PcGdPUjlOVERyeUhxWWtrNDBZRklxZUxNd1laRWh0empxc2tLa0ZRSWF0MytQZ05pZnNUUnVxbVViVnNYNjNFYTdMYnc0STBIQ0RCSUxNR0VrdXFpMGZWNXltck4iLCJtYWMiOiJmNmJkZDdjNjAzN2U1MzNkZWI0ODFjZGY2OWVhNGY2ZDZiM2Y0YWExM2FiNTNmNjk5ZTY3ZTllZDI5MTdjOGMzIiwidGFnIjoiIn0%3D; expires=Sun, 24 Aug 2025"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.ivasms.com/portal/sms/received",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)
SEC_CH_UA = '"Not)A;Brand";v="8", "Chromium";v="138"'

BASE_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-GB,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://tempmail.plus/en/",
    "Sec-Ch-Ua": SEC_CH_UA,
    "Sec-Ch-Ua-Mobile": "?0",
    'Sec-Ch-Ua-Platform': '"Windows"',
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Accept-Encoding": "gzip, deflate, br",
}
if not TOKEN or not EMAIL or not PASSWORD:
    raise RuntimeError("BOT_TOKEN, EMAIL, and PASSWORD must be set in config.env!")

logging.basicConfig(filename='bot_errors.log', level=logging.ERROR)

bot = Bot(token=TOKEN)
dp = Dispatcher()

headers_2fa = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://2fa-auth.com/",
    "Origin": "https://2fa-auth.com",
}


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en-GB;q=0.8,en;q=0.7",
    "Referer": "https://www.ivasms.com/login",
    "Origin": "https://www.ivasms.com",
    "Content-Type": "application/x-www-form-urlencoded",
}

AVAILABLE_DOMAINS = [
    "mailto.plus", "fexpost.com", "fexbox.org", "mailbox.in.ua", "rover.info",
    "chitthi.in", "fextemp.com", "any.pink", "merepost.com"
]

user_data = {}
user_locks = {}
user_clients = {}

COUNTRY_FLAGS = {
    "BOLIVIA": "🇧🇴",
    "ARGENTINA": "🇦🇷", 
    "BRAZIL": "🇧🇷",
    "CHILE": "🇨🇱",
    "COLOMBIA": "🇨🇴",
    "ECUADOR": "🇪🇨",
    "GUYANA": "🇬🇾",
    "PARAGUAY": "🇵🇾",
    "PERU": "🇵🇪",
    "SURINAME": "🇸🇷",
    "URUGUAY": "🇺🇾",
    "VENEZUELA": "🇻🇪",
    "MEXICO": "🇲🇽",
    "PANAMA": "🇵🇦",
    "COSTA RICA": "🇨🇷",
    "NICARAGUA": "🇳🇮",
    "HONDURAS": "🇭🇳",
    "EL SALVADOR": "🇸🇻",
    "GUATEMALA": "🇬🇹",
    "BELIZE": "🇧🇿",
    "UNITED STATES": "🇺🇸",
    "USA": "🇺🇸",
    "CANADA": "🇨🇦",
    "UNITED KINGDOM": "🇬🇧",
    "UK": "🇬🇧",
    "FRANCE": "🇫🇷",
    "GERMANY": "🇩🇪",
    "ITALY": "🇮🇹",
    "SPAIN": "🇪🇸",
    "PORTUGAL": "🇵🇹",
    "NETHERLANDS": "🇳🇱",
    "BELGIUM": "🇧🇪",
    "SWITZERLAND": "🇨🇭",
    "AUSTRIA": "🇦🇹",
    "SWEDEN": "🇸🇪",
    "NORWAY": "🇳🇴",
    "DENMARK": "🇩🇰",
    "FINLAND": "🇫🇮",
    "POLAND": "🇵🇱",
    "CZECH REPUBLIC": "🇨🇿",
    "HUNGARY": "🇭🇺",
    "ROMANIA": "🇷🇴",
    "BULGARIA": "🇧🇬",
    "GREECE": "🇬🇷",
    "TURKEY": "🇹🇷",
    "RUSSIA": "🇷🇺",
    "UKRAINE": "🇺🇦",
    "BELARUS": "🇧🇾",
    "LATVIA": "🇱🇻",
    "LITHUANIA": "🇱🇹",
    "ESTONIA": "🇪🇪",
    "SLOVAKIA": "🇸🇰",
    "SLOVENIA": "🇸🇮",
    "CROATIA": "🇭🇷",
    "SERBIA": "🇷🇸",
    "BOSNIA": "🇧🇦",
    "MONTENEGRO": "🇲🇪",
    "MACEDONIA": "🇲🇰",
    "ALBANIA": "🇦🇱",
    "KOSOVO": "🇽🇰",
    "MOLDOVA": "🇲🇩",
    "GEORGIA": "🇬🇪",
    "ARMENIA": "🇦🇲",
    "AZERBAIJAN": "🇦🇿",
    "KAZAKHSTAN": "🇰🇿",
    "UZBEKISTAN": "🇺🇿",
    "KYRGYZSTAN": "🇰🇬",
    "TAJIKISTAN": "🇹🇯",
    "TURKMENISTAN": "🇹🇲",
    "AFGHANISTAN": "🇦🇫",
    "PAKISTAN": "🇵🇰",
    "INDIA": "🇮🇳",
    "BANGLADESH": "🇧🇩",
    "SRI LANKA": "🇱🇰",
    "NEPAL": "🇳🇵",
    "BHUTAN": "🇧🇹",
    "MALDIVES": "🇲🇻",
    "MYANMAR": "🇲🇲",
    "THAILAND": "🇹🇭",
    "LAOS": "🇱🇦",
    "CAMBODIA": "🇰🇭",
    "VIETNAM": "🇻🇳",
    "MALAYSIA": "🇲🇾",
    "SINGAPORE": "🇸🇬",
    "INDONESIA": "🇮🇩",
    "PHILIPPINES": "🇵🇭",
    "BRUNEI": "🇧🇳",
    "EAST TIMOR": "🇹🇱",
    "CHINA": "🇨🇳",
    "JAPAN": "🇯🇵",
    "SOUTH KOREA": "🇰🇷",
    "NORTH KOREA": "🇰🇵",
    "MONGOLIA": "🇲🇳",
    "TAIWAN": "🇹🇼",
    "HONG KONG": "🇭🇰",
    "MACAU": "🇲🇴",
    "AUSTRALIA": "🇦🇺",
    "NEW ZEALAND": "🇳🇿",
    "FIJI": "🇫🇯",
    "PAPUA NEW GUINEA": "🇵🇬",
    "SOLOMON ISLANDS": "🇸🇧",
    "VANUATU": "🇻🇺",
    "NEW CALEDONIA": "🇳🇨",
    "FRENCH POLYNESIA": "🇵🇫",
    "SAMOA": "🇼🇸",
    "TONGA": "🇹🇴",
    "KIRIBATI": "🇰🇮",
    "TUVALU": "🇹🇻",
    "NAURU": "🇳🇷",
    "PALAU": "🇵🇼",
    "MICRONESIA": "🇫🇲",
    "MARSHALL ISLANDS": "🇲🇭",
    "SOUTH AFRICA": "🇿🇦",
    "EGYPT": "🇪🇬",
    "MOROCCO": "🇲🇦",
    "ALGERIA": "🇩🇿",
    "TUNISIA": "🇹🇳",
    "LIBYA": "🇱🇾",
    "SUDAN": "🇸🇩",
    "SOUTH SUDAN": "🇸🇸",
    "ETHIOPIA": "🇪🇹",
    "SOMALIA": "🇸🇴",
    "KENYA": "🇰🇪",
    "TANZANIA": "🇹🇿",
    "UGANDA": "🇺🇬",
    "RWANDA": "🇷🇼",
    "BURUNDI": "🇧🇮",
    "DR CONGO": "🇨🇩",
    "CONGO": "🇨🇬",
    "GABON": "🇬🇦",
    "CAMEROON": "🇨🇲",
    "NIGERIA": "🇳🇬",
    "NIGER": "🇳🇪",
    "CHAD": "🇹🇩",
    "MALI": "🇲🇱",
    "BURKINA FASO": "🇧🇫",
    "SENEGAL": "🇸🇳",
    "GAMBIA": "🇬🇲",
    "GUINEA BISSAU": "🇬🇼",
    "GUINEA": "🇬🇳",
    "SIERRA LEONE": "🇸🇱",
    "LIBERIA": "🇱🇷",
    "IVORY COAST": "🇨🇮",
    "GHANA": "🇬🇭",
    "TOGO": "🇧🇯",
    "BENIN": "🇧🇯",
    "CENTRAL AFRICAN REPUBLIC": "🇨🇫",
    "EQUATORIAL GUINEA": "🇬🇶",
    "SAO TOME AND PRINCIPE": "🇸🇹",
    "CAPE VERDE": "🇨🇻",
    "MAURITANIA": "🇲🇷",
    "WESTERN SAHARA": "🇪🇭",
    "ANGOLA": "🇦🇴",
    "ZAMBIA": "🇿🇲",
    "ZIMBABWE": "🇿🇼",
    "BOTSWANA": "🇧🇼",
    "NAMIBIA": "🇳🇦",
    "LESOTHO": "🇱🇸",
    "ESWATINI": "🇸🇿",
    "MADAGASCAR": "🇲🇬",
    "MAURITIUS": "🇲🇺",
    "SEYCHELLES": "🇸🇨",
    "COMOROS": "🇰🇲",
    "DJIBOUTI": "🇩🇯",
    "ERITREA": "🇪🇷",
    "ISRAEL": "🇮🇱",
    "PALESTINE": "🇵🇸",
    "LEBANON": "🇱🇧",
    "SYRIA": "🇸🇾",
    "JORDAN": "🇯🇴",
    "IRAQ": "🇮🇶",
    "KUWAIT": "🇰🇼",
    "SAUDI ARABIA": "🇸🇦",
    "YEMEN": "🇾🇪",
    "OMAN": "🇴🇲",
    "UAE": "🇦🇪",
    "QATAR": "🇶🇦",
    "BAHRAIN": "🇧🇭",
    "IRAN": "🇮🇷"
}

ADMIN_ID = "5705479420"
bot_password = None
unlocked_users = set()

def get_country_flag(range_name):
    for country, flag in COUNTRY_FLAGS.items():
        if country.upper() in range_name.upper():
            return flag
    return "🇦🇫"

def get_user_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

async def get_user_client(user_id):
    client = user_clients.get(user_id)
    if client is None or getattr(client, 'is_closed', False):
        client = httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0)
        user_clients[user_id] = client
    return client

sms_tasks = {}

def save_user_data():
    try:
        data_to_save = {}
        for uid, data in user_data.items():
            data_to_save[uid] = {k: v for k, v in data.items() if k != "sms_task"}
        data_to_save['config'] = {
            'password': bot_password,
            'email': EMAIL,
            'account_password': PASSWORD
        }
        with open("user_data.json", "wb") as f:
            f.write(orjson.dumps(data_to_save))
    except Exception as e:
        logging.error(f"Error saving user data: {e}")


def load_user_data():
    global user_data, bot_password
    try:
        with open("user_data.json", "rb") as f:
            data = orjson.loads(f.read())
            config = data.get('config', {})
            bot_password = config.get('password')

            saved_email = config.get('email')
            saved_pass = config.get('account_password')

            # If account changed → reset all user_data
            if saved_email != EMAIL or saved_pass != PASSWORD:
                print("⚠️ Account credentials changed, clearing old sessions...")
                user_data = {}
                return

            user_data = {k: v for k, v in data.items() if k != 'config'}
    except FileNotFoundError:
        user_data = {}
    except Exception as e:
        logging.error(f"Error loading user data: {e}")
        user_data = {}

def load_ivasms_numbers_cache():
    global ivasms_numbers_cache, ivasms_numbers_cache_ts
    data = cache.get(IVASMS_NUMBERS_CACHE_KEY)
    if data:
        ivasms_numbers_cache = data.get("numbers", [])
        ivasms_numbers_cache_ts = data.get("timestamp")
        print(f"[ivasms_cache] Loaded {len(ivasms_numbers_cache)} numbers from diskcache.")
    else:
        print("[ivasms_cache] No cached numbers yet in diskcache.")

def save_ivasms_numbers_cache():
    try:
        cache.set(IVASMS_NUMBERS_CACHE_KEY, {
            "timestamp": ivasms_numbers_cache_ts,
            "numbers": ivasms_numbers_cache
        })
        print(f"[ivasms_cache] Saved {len(ivasms_numbers_cache)} numbers to diskcache.")
    except Exception as e:
        logging.error(f"[ivasms_cache] Error saving cache: {e}")
load_user_data()
load_ivasms_numbers_cache()


def generate_email():
    name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890', k=10))
    domain = random.choice(AVAILABLE_DOMAINS)
    return f"{name}@{domain}"

client_httpx: httpx.AsyncClient | None = None

async def fetch_mails(email):
    global client_httpx
    encoded_email = email.replace("@", "%40")
    url = f"https://tempmail.plus/api/mails?email={encoded_email}&first_id=0&epin="
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": f"email={encoded_email}",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://tempmail.plus/en/"
    }
    try:
        r = await client_httpx.get(url, headers=headers)
        print(f"[fetch_mails] Step 1: status_code = {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            return data.get("mail_list", [])
        else:
            print(f"[fetch_mails] Response text: {r.text[:500]}")
    except httpx.TimeoutException:
        logging.error("[fetch_mails] TimeoutException: The request timed out.")
    except httpx.RequestError as e:
        logging.error(f"[fetch_mails] RequestError: {e}")
    except Exception as e:
        logging.error(f"[fetch_mails] Exception: {e}")
    return []

async def fetch_mail_content(email: str, mail_id: int | str) -> str:
    global client_httpx
    enc_email = email
    url = f"https://tempmail.plus/api/mails/{mail_id}"
    params = {"email": enc_email, "epin": ""}
    cookie_email = quote(email)
    headers = {**BASE_HEADERS, "Cookie": f"email={cookie_email}"}
    try:
        r = await client_httpx.get(url, params=params, headers=headers)
        print(f"[fetch_mail_content] status = {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            mail_text = data.get("text")
            if mail_text and mail_text.strip() != "":
                return mail_text
            mail_html = data.get("html")
            if mail_html and mail_html.strip() != "":
                return mail_html
            return "(No content)"
        else:
            print(f"[fetch_mail_content] Response text: {r.text[:500]}")
    except httpx.TimeoutException:
        logging.error("[fetch_mail_content] TimeoutException: The request timed out.")
    except httpx.RequestError as e:
        logging.error(f"[fetch_mail_content] RequestError: {e}")
    except Exception as e:
        print(f"[fetch_mail_content] Exception: {e}")
    return "(Failed to fetch content)"





async def login_ivasms_and_get_csrf(client: httpx.AsyncClient) -> str | None:
    try:
        home_resp = await client.get("https://www.ivasms.com/")
        soup = HTMLParser(home_resp.text)
        login_link_node = soup.css_first("a.default-btn-one")
        if not login_link_node:
            return None
        login_url = login_link_node.attributes.get("href")
        login_resp = await client.get(login_url)
        login_soup = HTMLParser(login_resp.text)
        token_input_node = login_soup.css_first('input[name="_token"]')
        if not token_input_node:
            print("[login_ivasms_and_get_csrf] Could not find CSRF token. Page content:")
            print(login_resp.text[:1000])
            return None
        csrf_token = token_input_node.attributes.get("value")
        payload = {
            "_token": csrf_token,
            "email": EMAIL,
            "password": PASSWORD,
            "remember": "on",
            "g-recaptcha-response": "",
            "submit": "register",
        }
        login_response = await client.post(login_url, data=payload)
        if "dashboard" not in str(login_response.url) and "Logout" not in login_response.text:
            return None
        return csrf_token
    except httpx.TimeoutException:
        logging.error("[login_ivasms_and_get_csrf] TimeoutException: The request timed out.")
    except httpx.RequestError as e:
        logging.error(f"[login_ivasms_and_get_csrf] RequestError: {e}")
    except Exception as e:
        logging.error(f"[login_ivasms_and_get_csrf] Exception: {e}")
    return None


async def fetch_all_ivasms_numbers(client: httpx.AsyncClient) -> tuple[list[tuple[str, str]], str | None]:
    try:
        csrf_token = await login_ivasms_and_get_csrf(client)
        if not csrf_token:
            return [], None

        api_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": HEADERS["User-Agent"],
            "Referer": "https://www.ivasms.com/portal/numbers",
            "X-Csrf-Token": csrf_token,
        }

        results: list[tuple[str, str]] = []
        start = 0
        length = 100
        draw = 1

        while True:
            params = {
                "draw": draw,
                "columns[1][data]": "Number",
                "columns[2][data]": "range",
                "order[0][column]": "1",
                "order[0][dir]": "desc",
                "start": start,
                "length": length,
                "search[value]": "",
                "_": str(int(time.time() * 1000)),
            }
            try:
                res = await client.get("https://www.ivasms.com/portal/numbers", params=params, headers=api_headers)
            except httpx.TimeoutException:
                logging.error("[fetch_all_ivasms_numbers] TimeoutException: The request timed out.")
                break
            except httpx.RequestError as e:
                logging.error(f"[fetch_all_ivasms_numbers] RequestError: {e}")
                break
            if res.status_code != 200:
                break
            try:
                data = res.json()
            except Exception as e:
                logging.error(f"[fetch_all_ivasms_numbers] JSON error: {e}")
                break

            rows = data.get("data", [])
            if not rows:
                break

            for item in rows:
                num = item.get("Number")
                rng = item.get("range")
                if num and rng:
                    results.append((str(num), str(rng)))

            start += length
            draw += 1

        return results, csrf_token
    except httpx.TimeoutException:
        logging.error("[fetch_all_ivasms_numbers] TimeoutException: The request timed out.")
    except httpx.RequestError as e:
        logging.error(f"[fetch_all_ivasms_numbers] RequestError: {e}")
    except Exception as e:
        logging.error(f"[fetch_all_ivasms_numbers] Exception: {e}")
    return [], None




async def ivasms_numbers_refresher(admin_user_id: str | None = None):
    global ivasms_numbers_cache, ivasms_numbers_cache_ts
    while True:
        async with ivasms_cache_lock:
            client = httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0)
            try:
                numbers, _csrf = await fetch_all_ivasms_numbers(client)
            except Exception as e:
                logging.error(f"[ivasms_refresher] fetch error: {e}", exc_info=True)
                numbers = []
            finally:
                await client.aclose()

            if numbers:
                ivasms_numbers_cache = numbers
                ivasms_numbers_cache_ts = time.time()
                save_ivasms_numbers_cache()
                print(f"[ivasms_refresher] Cached {len(numbers)} numbers.")

                if admin_user_id:
                    try:
                        await bot.send_message(
                            admin_user_id,
                            f"✅ List updated ({len(numbers)} numbers) - will be updated again in 12 hours.",
                            reply_markup=main_keyboard,
                        )
                    except Exception as e:
                        logging.error(f"[ivasms_refresher] notify admin failed: {e}")
            else:
                print("[ivasms_refresher] Failed to update numbers. Will try again later.")

        await asyncio.sleep(IVASMS_REFRESH_INTERVAL)

async def fetch_sms_for_random_number(client):
    try:
        home_resp = await client.get("https://www.ivasms.com/")
        print(f"[fetch_sms_for_random_number] Step 1: home_resp.status_code = {home_resp.status_code}")
        soup = HTMLParser(home_resp.text)
        login_link_node = soup.css_first("a.default-btn-one")
        if not login_link_node:
            return None, None, None, "❌ Login link not found"
        login_url = login_link_node.attributes.get("href")
        login_resp = await client.get(login_url)
        print(f"[fetch_sms_for_random_number] Step 2: login_resp.status_code = {login_resp.status_code}")
        login_soup = HTMLParser(login_resp.text)
        token_input_node = login_soup.css_first('input[name="_token"]')
        if not token_input_node:
            return None, None, None, "❌ CSRF token not found"
        csrf_token = token_input_node.attributes.get("value")
        payload = {
            "_token": csrf_token,
            "email": EMAIL,
            "password": PASSWORD,
            "remember": "on",
            "g-recaptcha-response": "",
            "submit": "register"
        }
        login_response = await client.post(login_url, data=payload)
        print(f"[fetch_sms_for_random_number] Step 3: login_response.status_code = {login_response.status_code}")
        if "dashboard" not in str(login_response.url) and "Logout" not in login_response.text:
            return None, None, None, "❌ Login failed"
        api_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": HEADERS["User-Agent"],
            "Referer": "https://www.ivasms.com/portal/numbers",
            "X-Csrf-Token": csrf_token,
        }
        start = 0
        length = 20
        draw = 1
        all_numbers = []
        while True:
            params = {
                "draw": draw,
                "columns[1][data]": "Number",
                "columns[2][data]": "range",
                "order[0][column]": "1",
                "order[0][dir]": "desc",
                "start": start,
                "length": length,
                "search[value]": "",
                "_": "1752050736497"
            }
            try:
                res = await client.get("https://www.ivasms.com/portal/numbers", params=params, headers=api_headers)
            except httpx.TimeoutException:
                logging.error("[fetch_sms_for_random_number] TimeoutException: The request timed out.")
                break
            except httpx.RequestError as e:
                logging.error(f"[fetch_sms_for_random_number] RequestError: {e}")
                break
            print(f"[fetch_sms_for_random_number] Step 4: numbers list res.status_code = {res.status_code}")
            try:
                data = res.json()
            except Exception:
                return None, None, None, "❌ Response is not JSON:\n" + res.text[:500]
            numbers = data.get("data", [])
            if not numbers:
                break
            for item in numbers:
                num = item.get("Number")
                range_name = item.get("range")
                if num and range_name:
                    all_numbers.append((num, range_name))
            start += length
            draw += 1
        if not all_numbers:
            return None, None, None, "❌ No numbers found"
        number, range_name = random.choice(all_numbers)
        print(f"📞 Chosen number: {number} ({range_name})")
        return number, csrf_token, range_name, None
    except httpx.TimeoutException:
        logging.error("[fetch_sms_for_random_number] TimeoutException: The request timed out.")
    except httpx.RequestError as e:
        logging.error(f"[fetch_sms_for_random_number] RequestError: {e}")
    except Exception as e:
        logging.error(f"[fetch_sms_for_random_number] Exception: {e}")
    return None, None, None, "❌ An error occurred while connecting to the site."

async def fetch_sms(client, csrf_token, number, range_name, user_id=None):
    try:
        client.headers.update({
            "Referer": "https://www.ivasms.com/portal/sms/received",
            "X-Requested-With": "XMLHttpRequest",
            "X-Csrf-Token": csrf_token,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })
        try:
            init_resp = await client.post("https://www.ivasms.com/portal/sms/received/getsms", data={
                "_token": csrf_token, "from": "", "to": ""
            })
        except httpx.TimeoutException:
            logging.error("[fetch_sms] TimeoutException (init_resp): The request timed out.")
            return None
        except httpx.RequestError as e:
            logging.error(f"[fetch_sms] RequestError (init_resp): {e}")
            return None
        print(f"[fetch_sms] Step 1: init_resp.status_code = {init_resp.status_code}")
        boundary = "----WebKitFormBoundary47BYZce2WkQnyt2w"
        multipart_data = MultipartEncoder(
            fields={
                "from": "",
                "to": "",
                "_token": csrf_token
            },
            boundary=boundary
        )
        try:
            multipart_resp = await client.post(
                "https://www.ivasms.com/portal/sms/received/getsms",
                data=multipart_data.to_string(),
                headers={
                    **client.headers,
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Accept": "text/html, */*; q=0.01"
                }
            )
        except httpx.TimeoutException:
            logging.error("[fetch_sms] TimeoutException (multipart_resp): The request timed out.")
            return None
        except httpx.RequestError as e:
            logging.error(f"[fetch_sms] RequestError (multipart_resp): {e}")
            return None
        print(f"[fetch_sms] Step 2: multipart_resp.status_code = {multipart_resp.status_code}")
        try:
            number_resp = await client.post(
                "https://www.ivasms.com/portal/sms/received/getsms/number",
                data={
                    "_token": csrf_token,
                    "start": "",
                    "end": "",
                    "range": range_name                                                                                                 
                },
                headers={
                    **client.headers,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Accept": "text/html, */*; q=0.01"
                }
            )
        except httpx.TimeoutException:
            logging.error("[fetch_sms] TimeoutException (number_resp): The request timed out.")
            return None
        except httpx.RequestError as e:
            logging.error(f"[fetch_sms] RequestError (number_resp): {e}")
            return None
        print(f"[fetch_sms] Step 3: number_resp.status_code = {number_resp.status_code}")
        attempt = 1
        message_text = None
        while True:
            try:
                sms_resp = await client.post(
                    "https://www.ivasms.com/portal/sms/received/getsms/number/sms",
                    data={
                        "_token": csrf_token,
                        "start": "",
                        "end": "",
                        "Number": number,
                        "Range": range_name
                    },
                    headers={
                        **client.headers,
                        "Accept": "text/html, */*; q=0.01",
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
                    }
                )
            except httpx.TimeoutException:
                logging.error(f"[fetch_sms] TimeoutException (sms_resp, attempt {attempt}): The request timed out.")
                attempt += 1
                await asyncio.sleep(3)
                continue
            except httpx.RequestError as e:
                logging.error(f"[fetch_sms] RequestError (sms_resp, attempt {attempt}): {e}")
                attempt += 1
                await asyncio.sleep(3)
                continue
            print(f"[fetch_sms] Step 4 (attempt {attempt}): sms_resp.status_code = {sms_resp.status_code}")
            soup = HTMLParser(sms_resp.text)
            message_element = soup.css_first("p.mb-0.pb-0")
            if message_element:
                message_text = message_element.text(strip=True)
                print(f"Message: {message_text}")
                break
            else:
                print("No message found")
                attempt += 1
                await asyncio.sleep(3)
        return message_text
    except httpx.TimeoutException:
        logging.error("[fetch_sms] TimeoutException: The request timed out.")
    except httpx.RequestError as e:
        logging.error(f"[fetch_sms] RequestError: {e}")
    except Exception as e:
        logging.error(f"[fetch_sms] Exception: {e}")
    return None

async def load_saved_data():
    if os.path.exists("sms_data.json"):
        try:
            with open("sms_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading saved data: {e}")
    return {"total_sms": 0, "ranges": {}}

async def get_csrf_token_async():
    async with httpx.AsyncClient() as client:
        main_page = await client.get("https://www.ivasms.com/portal/sms/received", headers=headers, cookies=cookies)
        main_soup = BeautifulSoup(main_page.text, "html.parser")
        
        token_input = main_soup.find("input", {"name": "_token"})
        if token_input:
            return token_input.get("value")
        else:
            meta_token = main_soup.find("meta", {"name": "csrf-token"})
            if meta_token:
                return meta_token.get("content")
            else:
                return "SESSION_TOKEN_PLACEHOLDER"

async def extract_ranges_and_messages_async(token):
    url_ranges = "https://www.ivasms.com/portal/sms/received/getsms"
    data_ranges = {
    "from": "2025-08-24",
    "to": "2025-08-24",
        "_token": token
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url_ranges, headers=headers, cookies=cookies, data=data_ranges)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        all_ranges = {}
        count_elements = soup.find_all("p", class_="mb-0 pb-0")
        
        for count_elem in count_elements:
            try:
                count_text = count_elem.get_text().strip()
                if count_text.replace('.', '').isdigit() and '.' not in count_text:
                    count = int(count_text)
                    
                    parent = count_elem.parent
                    while parent and not parent.get("onclick"):
                        parent = parent.parent
                    
                    if parent and parent.get("onclick"):
                        onclick = parent.get("onclick")
                        if "getDetials" in onclick:
                            range_name = onclick.split("'")[1]
                            if range_name not in all_ranges or all_ranges[range_name]["count"] < count:
                                all_ranges[range_name] = {"count": count, "numbers": {}}
            except Exception as e:
                continue
        
        return all_ranges

async def extract_numbers_for_range_async(token, range_name):
    number_data = {
        "_token": token,
        "start": "2025-08-24",
        "end": "2025-08-24",
        "range": range_name
    }
    
    try:
        async with httpx.AsyncClient() as client:
            number_resp = await client.post(BASE_URL_NUMBERS, headers=headers, cookies=cookies, data=number_data)
            
            if number_resp.status_code == 200:
                number_soup = BeautifulSoup(number_resp.text, "html.parser")
                card_divs = number_soup.find_all("div", class_=lambda x: x and "card card-body" in x)
                numbers_found = []
                
                for card in card_divs:
                    try:
                        first_div = card.find("div", class_="col-sm-4")
                        if first_div and first_div.get("onclick"):
                            onclick = first_div.get("onclick")
                            
                            if "getDetialsNumber" in onclick:
                                onclick_parts = onclick.split("'")
                                
                                if len(onclick_parts) >= 3:
                                    number_text = onclick_parts[1]
                                    number_id = onclick_parts[3]
                                    
                                    all_p_elements = card.find_all("p", class_="mb-0 pb-0")
                                    count_value = 1
                                    
                                    if all_p_elements and len(all_p_elements) > 0:
                                        first_p_text = all_p_elements[0].get_text().strip()
                                        if first_p_text.isdigit():
                                            count_value = int(first_p_text)
                                    
                                    number_details = {
                                        "number": number_text,
                                        "id": number_id,
                                        "count": count_value
                                    }
                                    
                                    numbers_found.append(number_details)
                    except Exception as e:
                        continue
                
                return numbers_found
    except Exception as e:
        return []
    
    return []

async def get_sms_for_number_async(token, number, range_name):
    try:
        sms_data = {
            "_token": token,
            "start": "2025-08-24",
            "end": "2025-08-24",
            "Number": number,
            "Range": range_name
        }
        
        async with httpx.AsyncClient() as client:
            sms_resp = await client.post(
                BASE_URL_MESSAGES,
                headers=headers,
                cookies=cookies,
                data=sms_data
            )
            
            if sms_resp.status_code == 200:
                soup = BeautifulSoup(sms_resp.text, "html.parser")
                message_element = soup.find("p", class_="mb-0 pb-0")
                if message_element:
                    return message_element.get_text().strip()
        return None
    except Exception as e:
        logging.error(f"Error fetching messages for number {number}: {e}")
        return None

async def compare_and_find_new_data_async(token):
    saved_data = await load_saved_data()
    logging.info(f"📊 Saved data: {saved_data['total_sms']} messages in {len(saved_data['ranges'])} ranges")
    
    current_ranges = await extract_ranges_and_messages_async(token)
    current_total = sum(r['count'] for r in current_ranges.values())
    logging.info(f"📊 Current ranges: {current_total} messages in {len(current_ranges)} ranges")
    
    changed_ranges = []
    new_messages = []
    
    for range_name, current_data in current_ranges.items():
        saved_range = saved_data["ranges"].get(range_name, {"count": 0, "numbers": {}})
        current_count = current_data["count"]
        saved_count = saved_range["count"]
        
        if current_count != saved_count:
            logging.info(f"🔄 Change detected in range {range_name}: {saved_count} → {current_count}")
            changed_ranges.append(range_name)
    
    if not changed_ranges:
        logging.info("✅ No changes in ranges")
        return new_messages
    
    logging.info(f"🔍 Found {len(changed_ranges)} changed ranges")
    
    for range_name in changed_ranges:
        logging.info(f"\n--- Fetching numbers for range: {range_name} ---")
        
        numbers = await extract_numbers_for_range_async(token, range_name)
        current_numbers = {}
        
        for num_data in numbers:
            current_numbers[num_data["number"]] = {
                "count": num_data["count"],
                "id": num_data["id"]
            }
        
        saved_numbers = saved_data["ranges"].get(range_name, {}).get("numbers", {})
        
        for number, current_num_data in current_numbers.items():
            current_count = current_num_data["count"]
            
            if number not in saved_numbers:
                logging.info(f"🆕 New number: {number} (messages: {current_count})")
                
                message = await get_sms_for_number_async(token, number, range_name)
                if message:
                    new_message = {
                        "range": range_name,
                        "number": number,
                        "count": current_count,
                        "message": message,
                        "type": "new_number"
                    }
                    new_messages.append(new_message)
                    logging.info(f"📨 Message for number {number}: {message[:100]}...")
            
            elif saved_numbers[number]["count"] != current_count:
                old_count = saved_numbers[number]["count"]
                logging.info(f"📈 Message count changed for {number}: {old_count} → {current_count}")
                
                message = await get_sms_for_number_async(token, number, range_name)
                if message:
                    new_message = {
                        "range": range_name,
                        "number": number,
                        "count": current_count,
                        "message": message,
                        "type": "new_message"
                    }
                    new_messages.append(new_message)
                    logging.info(f"📨 New messages for {number}: {message[:100]}...")
        
        # تحديث البيانات الحالية
        current_ranges[range_name]["numbers"] = current_numbers
    
    return new_messages

async def format_data_for_json_async(all_ranges):
    all_data = {
        "total_sms": 0,
        "ranges": {}
    }
    
    for range_name, data in all_ranges.items():
        count = data["count"]
        all_data["total_sms"] += count
        
        range_data = {
            "count": count,
            "numbers": {}
        }
        
        numbers = data.get("numbers", [])
        if numbers and isinstance(numbers, list) and len(numbers) > 0:
            for item in numbers:
                if isinstance(item, dict):
                    number = item['number']
                    count_value = item.get("count", 1)
                    
                    range_data["numbers"][number] = {
                        "count": count_value,
                        "messages": []
                    }
        
        all_data["ranges"][range_name] = range_data
    
    return all_data

async def save_to_json_async(all_data, filename="sms_data.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        logging.info("✅ Saved data to sms_data.json")
        return True
    except Exception as e:
        logging.error(f"❌ Error saving file: {e}")
        return False

async def scrape_sms_data():
    try:
        print(f"🔑 [{datetime.now().strftime('%H:%M:%S')}] Getting CSRF token...")
        token = await get_csrf_token_async()
        
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Comparing data and finding new messages...")
        new_messages = await compare_and_find_new_data_async(token)
        
        if new_messages:
            logging.info(f"\n📊 Summary of new messages:")
            logging.info(f"   New messages: {len(new_messages)}")
            try:
                with open("new_messages.json", "w", encoding="utf-8") as f:
                    json.dump(new_messages, f, ensure_ascii=False, indent=2)
                logging.info("✅ Saved new messages to new_messages.json")
            except Exception as e:
                logging.error(f"❌ Error saving new messages: {e}")
        else:
            logging.info("✅ No new messages")
        
        current_ranges = await extract_ranges_and_messages_async(token)
        for range_name, data in current_ranges.items():
            numbers = await extract_numbers_for_range_async(token, range_name)
            current_ranges[range_name]["numbers"] = numbers
        
        all_data = await format_data_for_json_async(current_ranges)
        await save_to_json_async(all_data)
        
        return new_messages
        
    except Exception as e:
        logging.error(f"Error in scrape_sms_data: {e}")
        return []



async def start_sms_monitoring():
    print("🚀 Starting SMS monitoring every 20 seconds...")
    logging.info("🚀 Starting new messages monitoring every 20 seconds...")
    
    print("⏳ Waiting 10 seconds before starting...")
    await asyncio.sleep(10)
    
    while True:
        try:
            print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Checking for new messages...")
            new_messages = await scrape_sms_data()
            
            if new_messages:
                print(f"🎉 [{datetime.now().strftime('%H:%M:%S')}] Found {len(new_messages)} new messages!")
                logging.info(f"🎉 Found {len(new_messages)} new messages!")
                
                # إرسال كل رسالة للمجموعة بشكل منفصل
                for msg_data in new_messages:
                    try:
                        message_text = msg_data['message']
                        otp_match = re.search(r'\b\d{5,6}\b', message_text)
                        otp_code = otp_match.group() if otp_match else "Not available"

                        service_match = re.search(
                            r'FACEBOOK|GOOGLE|TWITTER|INSTAGRAM|WHATSAPP|.*?Service.*?:\s*(\w+)',
                            message_text,
                            re.IGNORECASE
                        )
                        service = service_match.group(0).upper() if service_match else "UNKNOWN"

                        country_flag = get_country_flag(msg_data['range'])
                        group_msg = (
                            f"🔔 {country_flag} <b>{msg_data['range']} {service} OTP Received...</b>\n\n"
                            f"⚙️ <b>Service:</b> <code>{service}</code>\n"
                            f"🌐 <b>Country:</b> <code>{msg_data['range']}</code> {country_flag}\n"
                            f"☎️ <b>Number:</b> <code>{msg_data['number']}</code>\n"
                            f"🔑 <b>Your OTP:</b> <code>{otp_code}</code>\n\n"
                            f"❤️ <b>Full-Message:</b>\n"
                            f"<code>{escape(message_text)}</code>"
                            f"🚀 <b>Be Active - New OTP Coming...</b> {datetime.now().strftime('%I:%M %p')}"
                        )
                        
                        await bot.send_message(group_id, group_msg, parse_mode="HTML")
                        print(f"📨 [{datetime.now().strftime('%H:%M:%S')}] Sent message to group: {msg_data['number']}")
                        logging.info(f"✅ Sent new message to group: {msg_data['number']}")
                        
                        # انتظار قليلاً بين الرسائل لتجنب التقييد
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logging.error(f"❌ Error sending message to group: {e}")
            else:
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] No new messages found")
                logging.info("✅ No new messages")
            
            print(f"⏳ [{datetime.now().strftime('%H:%M:%S')}] Waiting 5 seconds for next check...")
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Error in SMS monitoring: {e}")
            logging.error(f"Error in SMS monitoring: {e}")
            await asyncio.sleep(60)

async def fetch_2fa_code(keys: str, session: aiohttp.ClientSession) -> str | None:

    # توليد كود TOTP
        totp = pyotp.TOTP(keys.replace(" ", "").upper() )
        code = totp.now()
        return code
    



async def sms_watcher(
    bot: Bot,
    client: httpx.AsyncClient,
    user_id: str,
    number: str,
    csrf_token: str,
    range_name: str,
):
    try:
        message_text = await fetch_sms(client, csrf_token, number, range_name, user_id=user_id)
        if message_text:
            otp_match = re.search(r'\b\d{5,6}\b', message_text)
            otp_code = otp_match.group() if otp_match else "Not available"

            service_match = re.search(
                r'FACEBOOK|GOOGLE|TWITTER|INSTAGRAM|WHATSAPP|.*?Service.*?:\s*(\w+)',
                message_text,
                re.IGNORECASE
            )
            service = service_match.group(0).upper() if service_match else "UNKNOWN"

            now = datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p")

            reply_msg = (
                "🔥 <b>Wow Got a New OTP</b> 🔥\n\n"
                f"🕰️ <b>Time:</b> <code>{now}</code>\n"
                f"☎️ <b>Number:</b> <code>{number}</code>\n"
                f"⚙️ <b>Service:</b> <code>{service}</code>\n"
                f"🔥 <b>OTP Code:</b> <code>{otp_code}</code>\n"
                f"\n<code>{escape(message_text)}</code>"
            )
            await bot.send_message(user_id, reply_msg, parse_mode="HTML", reply_markup=main_keyboard)
            
            # Send to group with the same format as the image
            group_msg = (
                f"🔔 🇦🇫 <b>unknown  {service} OTP Received...</b>\n\n"
                f"⚙️ <b>Service:</b> <code>{service}</code>\n"
                f"🌐 <b>Country:</b> <code>unknown</code> 🇦🇫\n"
                f"☎️ <b>Number:</b> <code>{number}</code>\n"
                f"🔑 <b>Your OTP:</b> <code>{otp_code}</code>\n\n"
                f"❤️ <b>Full-Message:</b>\n"
                f"<code>{escape(message_text)}</code>\n\n"
                f"🚀 <b>Be Active - New OTP Coming...</b> {datetime.now().strftime('%I:%M %p')}"
            )
            
            try:
                await bot.send_message(group_id, group_msg, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Failed to send message to group: {e}")
                
        else:
            await bot.send_message(user_id, "⚠️ No messages received yet.", parse_mode="HTML", reply_markup=main_keyboard)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.error(f"SMS watcher error for user {user_id}: {e}")
        await bot.send_message(user_id, "⚠️ Error occurred in SMS watcher.")
    finally:
        await client.aclose()




   
class Form(StatesGroup):
    waiting_for_key = State()
        
        
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Get Number")],
        [KeyboardButton(text="Get Tempmail") , KeyboardButton(text="Get 2FA")],
        [KeyboardButton(text="Stop")]
    ],
    resize_keyboard=True
)

@dp.message(Command("setpassword"))
async def set_password(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id != ADMIN_ID:
        await message.answer("❌ Only admin can set the password.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /setpassword <password>")
        return
    global bot_password
    bot_password = args[1]
    save_user_data()
    await message.answer("✅ Password set. Bot is now locked.")

@dp.message(Command("removepassword"))
async def remove_password(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id != ADMIN_ID:
        await message.answer("❌ Only admin can remove the password.")
        return
    global bot_password
    bot_password = None
    unlocked_users.clear()
    save_user_data()
    await message.answer("✅ Password removed. Bot is now unlocked for everyone.")

@dp.message(Command("unlock"))
async def unlock_bot(message: types.Message):
    user_id = str(message.from_user.id)
    if bot_password is None:
        await message.answer("✅ Bot is not locked.")
        return
    if user_id == ADMIN_ID:
        await message.answer("✅ Admin doesn't need to unlock.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1] != bot_password:
        await message.answer("❌ Incorrect password.")
        return
    unlocked_users.add(user_id)
    await message.answer("✅ Bot unlocked for you.")

# حذف تكرار cmd_start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        return
    await message.answer(
        "👋 Welcome! Please choose a button below or use the commands.\n"
        "/get - Show your temp email\n"
        "/new - Create a new email\n",
        reply_markup=main_keyboard
    )

@dp.message(lambda m: m.text == "Get Tempmail")
async def cmd_get_tempmail(message: types.Message):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        return
    user_last_active[user_id] = time.time()
    lock = get_user_lock(user_id)
    async with lock:
        if user_id not in user_data or "email" not in user_data[user_id]:
            email = generate_email()
            # احفظ الإيميل مباشرة
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]["email"] = email
            try:
                mails = await fetch_mails(email)
                last_mail_id = mails[0]["mail_id"] if mails else None
            except Exception as e:
                logging.error(f"[Get Tempmail] Error in fetch_mails for user {user_id}: {e}")
                last_mail_id = None
            user_data[user_id]["last_mail_id"] = last_mail_id
            save_user_data()
            await message.answer(f"✅ A new temp email was created:\n<code>{escape(email)}</code>", parse_mode="HTML", reply_markup=main_keyboard)
        else:
            email = user_data[user_id]["email"]
            await message.answer(f"📧 Your temp email is:\n<code>{escape(email)}</code>", parse_mode="HTML", reply_markup=main_keyboard)

async def get_fresh_csrf_and_client(user_id):
    client = await get_user_client(user_id)
    now = time.time()
    user_info = user_data.get(user_id, {})
    session_cookie = user_info.get("ivas_sms_session")
    session_time = user_info.get("ivas_sms_session_time", 0)
    
    if not session_cookie or now - session_time > 3600:
        csrf_token = await login_ivasms_and_get_csrf(client)
       
        cookies = client.cookies.jar
        ivas_sms_session = None
        for cookie in cookies:
            if cookie.name == "ivas_sms_session":
                ivas_sms_session = cookie.value
                break
        if ivas_sms_session:
            user_data.setdefault(user_id, {})
            user_data[user_id]["ivas_sms_session"] = ivas_sms_session
            user_data[user_id]["ivas_sms_session_time"] = now
            save_user_data()
    else:
        
        client.cookies.set("ivas_sms_session", session_cookie, domain="www.ivasms.com")
        csrf_token = user_info.get("csrf_token")
    return client, csrf_token

@dp.message(lambda m: m.text == "Get Number")
async def cmd_get_number(message: types.Message):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        return
    user_last_active[user_id] = time.time()
    lock = get_user_lock(user_id)

    async with lock:
        user_data.setdefault(user_id, {})

        # 1) عندك رقم محفوظ؟ رجّع الرقم لكن جلب CSRF جديد دائماً
        if "number" in user_data[user_id]:
            number = user_data[user_id]["number"]
            range_name = user_data[user_id].get("range_name")
            client, csrf_token = await get_fresh_csrf_and_client(user_id)
            user_data[user_id]["csrf_token"] = csrf_token
            save_user_data()
            await message.answer(
                f"📞 <b>Your Number:</b> <code>{number}</code>",
                parse_mode="HTML",
                reply_markup=main_keyboard,
            )
            # شغّل مراقبة SMS حتى عند الرقم المحفوظ
            task = asyncio.create_task(
                sms_watcher(bot, client, user_id, number, csrf_token, range_name)
            )
            sms_tasks[user_id] = task
            return

        # 2) مهمة SMS شغالة؟
        existing_task = sms_tasks.get(user_id)
        if existing_task and not existing_task.done():
            await message.answer(
                "⏳ Monitoring this number is in progress. Please wait or press Stop to stop monitoring.",
                reply_markup=main_keyboard,
            )
            return

        # --- 3) Try to use the cached numbers ---
        async with ivasms_cache_lock:
            cached_numbers = list(ivasms_numbers_cache)

        if cached_numbers:
           
            used_numbers = set(
                data.get("number")
                for uid, data in user_data.items()
                if uid != user_id and data.get("number")
            )
            available_numbers = [item for item in cached_numbers if item[0] not in used_numbers]
            prev_number = user_data[user_id].get("number")
           
            if prev_number and len(available_numbers) > 1:
                available_numbers = [item for item in available_numbers if item[0] != prev_number]
          
            if available_numbers:
                number, range_name = random.choice(available_numbers)
            else:
                number, range_name = random.choice(cached_numbers)
            client, csrf_token = await get_fresh_csrf_and_client(user_id)
            if not csrf_token:
                # fallback if login failed
                await client.aclose()
                user_clients.pop(user_id, None)
                await message.answer(
                    "⚠️ Failed to log in to ivasms (cache). Will try to fetch directly...",
                    reply_markup=main_keyboard,
                )
             
                client = await get_user_client(user_id)
                number, csrf_token, range_name, error = await fetch_sms_for_random_number(client)
                if error:
                    await client.aclose()
                    user_clients.pop(user_id, None)
                    await message.answer(error, reply_markup=main_keyboard)
                    return

        # --- 4) Save user data ---
        user_data[user_id]["number"] = number
        user_data[user_id]["csrf_token"] = csrf_token
        user_data[user_id]["range_name"] = range_name
        save_user_data()

        # --- 5) Send the number ---
        await message.answer(
            f"📞 <b>Your Number:</b> <code>{number}</code>",
            parse_mode="HTML",
            reply_markup=main_keyboard,
        )

        # --- 6) Start SMS monitoring (do not close client; sms_watcher will close it) ---
        task = asyncio.create_task(
            sms_watcher(bot, client, user_id, number, csrf_token, range_name)
        )
        sms_tasks[user_id] = task



        

@dp.message(lambda m: m.text and m.text.isdigit())
async def handle_copy_number(message: types.Message):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        return
    await message.answer(f"Number copied: <code>{escape(message.text)}</code>", parse_mode="HTML")


@dp.message(lambda m: m.text == "Get 2FA")
async def handle_get_2fa(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        return
    await state.set_state(Form.waiting_for_key)
    
    await message.answer("🔑 Please send the 2FA key now:")


@dp.message(Form.waiting_for_key)
async def handle_key_input(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        await state.clear()
        return
    key = message.text.strip()
    global session_aiohttp
    if key.lower() == "stop":
        await state.clear()
        await cmd_stop(message)  
        return
    if session_aiohttp is None:
        import aiohttp
        session_aiohttp = aiohttp.ClientSession()
    code = await fetch_2fa_code(key, session_aiohttp)
    if code:
        await message.answer(f"✅ 2FA Code: <code>{escape(code)}</code>", parse_mode="HTML")
        await message.answer("This code is valid for 30 seconds only. If it does not work, please try again.")
    else:
        await message.answer("❌ Failed to fetch 2FA code. Please make sure the key is valid.")

    await state.clear()

@dp.message(lambda m: m.text == "Stop")
async def cmd_stop(message: types.Message):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        return
    if user_id in user_data:
        user_data[user_id]["stop_mail"] = True
        user_data[user_id]["stop_sms"] = True
        # إلغاء مهمة SMS إذا كانت موجودة
        sms_task = sms_tasks.get(user_id)
        if sms_task and not sms_task.done():
            sms_task.cancel()
            try:
                await sms_task
            except asyncio.CancelledError:
                pass
            del sms_tasks[user_id]
        
        for key in ["email", "last_mail_id", "number", "range_name"]:
            if key in user_data[user_id]:
                del user_data[user_id][key]
        # حذف القفل الخاص بالمستخدم
        user_locks.pop(user_id, None)
        # إغلاق جلسة httpx الخاصة بالمستخدم
        client = user_clients.pop(user_id, None)
        if client:
            await client.aclose()
        await message.answer("🛑 Monitoring stopped and data deleted.", reply_markup=main_keyboard)
        save_user_data()
    else:
        await message.answer("⚠️ No active session.")

@dp.message(lambda m: m.text == "Monitor SMS")
async def cmd_monitor_sms(message: types.Message):
    user_id = str(message.from_user.id)
    if bot_password is not None and user_id != ADMIN_ID and user_id not in unlocked_users:
        await message.answer("❌ Bot is locked. Use /unlock <password> to access.")
        return
    try:
        await message.answer("🔍 Starting new messages monitoring...")
        new_messages = await scrape_sms_data()
        if new_messages:
            await message.answer(f"🔔 Found {len(new_messages)} new messages!")
            for msg_data in new_messages:
                try:
                    message_text = msg_data['message']
                    otp_match = re.search(r'\b\d{5,6}\b', message_text)
                    otp_code = otp_match.group() if otp_match else "Not available"
                    service_match = re.search(
                        r'FACEBOOK|GOOGLE|TWITTER|INSTAGRAM|WHATSAPP|.*?Service.*?:\s*(\w+)',
                        message_text,
                        re.IGNORECASE
                    )
                    service = service_match.group(0).upper() if service_match else "UNKNOWN"
                    country_flag = get_country_flag(msg_data['range'])
                    group_msg = (
                        f"🔔 {country_flag} <b>{msg_data['range']} {service} OTP Received...</b>\n\n"
                        f"⚙️ <b>Service:</b> <code>{service}</code>\n"
                        f"🌐 <b>Country:</b> <code>{msg_data['range']}</code> {country_flag}\n"
                        f"☎️ <b>Number:</b> <code>{msg_data['number']}</code>\n"
                        f"🔑 <b>Your OTP:</b> <code>{otp_code}</code>\n\n"
                        f"❤️ <b>Full-Message:</b>\n"
                        f"<code>{escape(message_text)}</code>\n\n"
                        f"🚀 <b>Be Active - New OTP Coming...</b> {datetime.now().strftime('%I:%M %p')}"
                    )
                    await bot.send_message(group_id, group_msg, parse_mode="HTML")
                    logging.info(f"✅ Sent new message to group: {msg_data['number']}")
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.error(f"❌ Error sending message to group: {e}")
            await message.answer("✅ Sent all new messages to the group")
        else:
            await message.answer("✅ No new messages now")
    except Exception as e:
        logging.error(f"Error in monitor SMS: {e}")
        await message.answer("❌ Error occurred while monitoring messages")

async def mail_checker():
    while True:
        for user_id, data in user_data.items():
            if "email" not in data:
                continue
            email = data["email"]
            last_mail_id = data.get("last_mail_id")
            try:
                mails = await fetch_mails(email)
            except Exception as e:
                logging.error(f"[mail_checker] Error in fetch_mails for user {user_id}: {e}")
                continue

            if mails:
                newest_mail = mails[0]
                if newest_mail["mail_id"] != last_mail_id:
                    user_data[user_id]["last_mail_id"] = newest_mail["mail_id"]
                    save_user_data()
                    subject = newest_mail.get("subject", "(No Subject)") or "(No Subject)"
                    sender_name = newest_mail.get("from_name", "")
                    sender_mail = newest_mail.get("from_mail", "")
                    time = newest_mail.get("time", "")

                    try:
                        mail_text = await fetch_mail_content(email, newest_mail["mail_id"])
                    except Exception as e:
                        logging.error(f"[mail_checker] Error in fetch_mail_content for user {user_id}: {e}")
                        mail_text = "(Failed to fetch content)"

                    otp_match = re.search(r'\d+', subject)
                    if not otp_match:
                        otp_match = re.search(r'\d+', mail_text)
                    otp_code = otp_match.group() if otp_match else "Not available"

                    mail_text_clean = mail_text.replace("<style", "<!--<style").replace("</style>", "</style>-->")

                    text = (
                        f"📩 <b>New email received!</b>\n\n"
                        f"<b>📧 Your email:</b> <code>{escape(email)}</code>\n"
                        f"<b>👤 From:</b> {escape(sender_name)} &lt;{escape(sender_mail)}&gt;\n"
                        f"<b>📝 Subject:</b> {escape(subject)}\n"
                        f"<b>🕒 Time:</b> {escape(time)}\n\n"
                        f"🔥 <b>OTP Code:</b> <code>{otp_code}</code>\n"
                        f"<b>📨 Content:</b>\n"
                        f"<pre>{escape(mail_text_clean)}</pre>"
                    )
                    await bot.send_message(user_id, text, parse_mode="HTML")
        await asyncio.sleep(3)

async def cleanup_inactive_users():
    while True:
        now = time.time()
        inactive_users = [
            user_id for user_id, last_active in user_last_active.items()
            if now - last_active > INACTIVITY_TIMEOUT
        ]
        for user_id in inactive_users:
           
            sms_task = sms_tasks.get(user_id)
            if sms_task and not sms_task.done():
                sms_task.cancel()
                try:
                    await sms_task
                except asyncio.CancelledError:
                    pass
                del sms_tasks[user_id]
            
            user_locks.pop(user_id, None)
            
            user_last_active.pop(user_id, None)
           
        await asyncio.sleep(300)  

async def main():
    global session_aiohttp, client_httpx
    import aiohttp
    session_aiohttp = aiohttp.ClientSession()
    import httpx
    client_httpx = httpx.AsyncClient()
    try:
        asyncio.create_task(mail_checker())
        asyncio.create_task(ivasms_numbers_refresher())
        asyncio.create_task(cleanup_inactive_users()) 
        asyncio.create_task(start_sms_monitoring())  
        print("🚀 Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        await session_aiohttp.close()
        await client_httpx.aclose()

if __name__ == "__main__":
    asyncio.run(main())