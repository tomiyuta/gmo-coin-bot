#!/usr/bin/env python3
"""
GMO Coin Automated Trading Bot
Version: 2.0.0
License: MIT License
Copyright (c) 2024 GMO Coin Bot

A sophisticated automated trading system for GMO Coin cryptocurrency exchange.
Features include risk management, Discord integration, and GUI configuration.

For more information, see README.md
"""

import os
import csv
import requests
import json
import hmac
import hashlib
import time
import threading
import logging
import random
import sys
from threading import Lock
from datetime import datetime, timedelta
from discord import SyncWebhook
import discord
from discord.ext import commands
import traceback
import psutil
import gc

# ===============================
# 設定ファイル管理
# ===============================
CONFIG_FILE = 'config.json'

def load_config():
    """設定ファイルを読み込む"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"設定ファイル読み込みエラー: {e}")
            return {}
    return {}

def save_config(config):
    """設定ファイルを保存する"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"設定ファイル保存エラー: {e}")
        return False

def validate_config(config):
    """設定ファイルのバリデーション"""
    errors = []
    
    # 必須項目のチェック
    required_fields = ['api_key', 'api_secret', 'discord_webhook_url']
    for field in required_fields:
        if not config.get(field):
            errors.append(f"必須項目 '{field}' が設定されていません")
    
    # 数値項目の範囲チェック
    numeric_ranges = {
        'spread_threshold': (0.001, 1.0),
        'jitter_seconds': (0, 60),
        'entry_order_retry_interval': (1, 60),
        'max_entry_order_attempts': (1, 10),
        'exit_order_retry_interval': (1, 60),
        'max_exit_order_attempts': (1, 10),
        'stop_loss_pips': (0, 1000),
        'take_profit_pips': (0, 1000),
        'position_check_interval': (1, 60),
        'position_check_interval_minutes': (1, 99),
        'leverage': (1, 100),
        'risk_ratio': (0.1, 1.0)
    }
    
    for field, (min_val, max_val) in numeric_ranges.items():
        value = config.get(field)
        if value is not None:
            try:
                num_value = float(value)
                if not (min_val <= num_value <= max_val):
                    errors.append(f"'{field}' の値 ({num_value}) が範囲外です ({min_val}～{max_val})")
            except (ValueError, TypeError):
                errors.append(f"'{field}' の値が数値ではありません: {value}")
    
    # 自動再起動時間の検証
    auto_restart_hour = config.get('auto_restart_hour')
    if auto_restart_hour is not None:
        try:
            hour_value = int(auto_restart_hour)
            if not (0 <= hour_value <= 24):
                errors.append(f"'auto_restart_hour' の値 ({hour_value}) が範囲外です (0～24)")
        except (ValueError, TypeError):
            errors.append(f"'auto_restart_hour' の値が数値ではありません: {auto_restart_hour}")
    
    # 文字列項目のチェック
    autolot_value = config.get('autolot')
    if autolot_value is not None and str(autolot_value).upper() not in ['TRUE', 'FALSE']:
        errors.append("'autolot' は 'TRUE' または 'FALSE' である必要があります")
    
    return errors

def create_default_config():
    """デフォルト設定ファイルを作成"""
    default_config = {
        "api_key": "",
        "api_secret": "",
        "discord_webhook_url": "",
        "spread_threshold": 0.01,
        "jitter_seconds": 3,
        "entry_order_retry_interval": 5,
        "max_entry_order_attempts": 3,
        "exit_order_retry_interval": 10,
        "max_exit_order_attempts": 3,
        "stop_loss_pips": 0,
        "take_profit_pips": 0,
        "position_check_interval": 5,
        "position_check_interval_minutes": 10,
        "leverage": 10,
        "risk_ratio": 1.0,
        "autolot": "TRUE",
        "auto_restart_hour": None,
        "symbol_daily_volume_limit": 15000000  # 銘柄別の一日の最大取引数量（1500万ロット）
    }
    save_config(default_config)
    return default_config

# ===============================
# 設定読み込み
# ===============================
config = load_config()
if not config:
    config = create_default_config()
    print("設定ファイルを作成しました。config.jsonを編集してAPIキーを設定してください。")
    print("設定後、プログラムを再実行してください。")
    exit()

# 設定ファイルのバリデーション
validation_errors = validate_config(config)
if validation_errors:
    print("設定ファイルにエラーがあります:")
    for error in validation_errors:
        print(f"  - {error}")
    print("config.jsonを修正してから再実行してください。")
    exit()

# ===============================
# ユーザー設定可能な項目（パラメータ）
# ===============================
SPREAD_THRESHOLD = config.get('spread_threshold', 0.01)   # 許容スプレッド（例: 0.01=1pip, USD/JPY想定）
JITTER_SECONDS = config.get('jitter_seconds', 3)        # エントリー・決済時のランダム遅延（秒）
ENTRY_ORDER_RETRY_INTERVAL = config.get('entry_order_retry_interval', 5)      # エントリー注文リトライ間隔（秒）
MAX_ENTRY_ORDER_ATTEMPTS = config.get('max_entry_order_attempts', 3)        # エントリー注文最大リトライ回数
EXIT_ORDER_RETRY_INTERVAL = config.get('exit_order_retry_interval', 10)      # 決済注文リトライ間隔（秒）
MAX_EXIT_ORDER_ATTEMPTS = config.get('max_exit_order_attempts', 3)         # 決済注文最大リトライ回数
STOP_LOSS_PIPS = config.get('stop_loss_pips', 0)                  # ストップロス閾値（pips）0なら無効
TAKE_PROFIT_PIPS = config.get('take_profit_pips', 0)                # テイクプロフィット閾値（pips）0なら無効
POSITION_CHECK_INTERVAL = config.get('position_check_interval', 5)         # ポジション監視間隔（秒）
LEVERAGE = config.get('leverage', 10)  # デフォルト10倍
RISK_RATIO = config.get('risk_ratio', 1.0)  # 口座残高の何割を使うか（1.0=全額）
AUTOLOT = str(config.get('autolot', 'TRUE')).upper()  # "TRUE"で自動ロット
AUTO_RESTART_HOUR = config.get('auto_restart_hour')  # 自動再起動時間（0-24時、Noneで無効）
POSITION_CHECK_INTERVAL_MINUTES = config.get('position_check_interval_minutes', 10)
SYMBOL_DAILY_VOLUME_LIMIT = config.get('symbol_daily_volume_limit', 15000000)  # 銘柄別の一日の最大取引数量（1500万ロット）

# ===============================
# API認証情報の取得
# ===============================
# 設定ファイルからAPI認証情報を取得、なければ環境変数から取得
GMO_API_KEY = config.get('api_key') or os.environ.get('GMO_API_KEY')
GMO_API_SECRET = config.get('api_secret') or os.environ.get('GMO_API_SECRET')
DISCORD_WEBHOOK_URL = config.get('discord_webhook_url') or os.environ.get('DISCORD_WEBHOOK_GMO')
DISCORD_BOT_TOKEN = config.get('discord_bot_token', None)

if not GMO_API_KEY or not GMO_API_SECRET or not DISCORD_WEBHOOK_URL:
    print("エラー: APIキー、APIシークレット、またはDiscord Webhook URLが設定されていません")
    print("config.jsonファイルを編集して設定してください:")
    print("- api_key: GMOコインのAPIキー")
    print("- api_secret: GMOコインのAPIシークレット") 
    print("- discord_webhook_url: Discord通知用のWebhook URL")
    exit()

# ===============================
# ロギング設定
# ===============================
import logging.handlers

# ログディレクトリ作成
if not os.path.exists('logs'):
    os.makedirs('logs')

# メインログ設定（ローテーション付き）
main_log_handler = logging.handlers.RotatingFileHandler(
    'logs/main.log', 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,  # 5世代保持
    encoding='utf-8'
)
main_log_handler.setLevel(logging.INFO)
main_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# エラーログ設定（ローテーション付き）
error_log_handler = logging.handlers.RotatingFileHandler(
    'logs/error.log', 
    maxBytes=5*1024*1024,   # 5MB
    backupCount=3,  # 3世代保持
    encoding='utf-8'
)
error_log_handler.setLevel(logging.ERROR)
error_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# コンソール出力設定
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(main_log_handler)
logger.addHandler(error_log_handler)
logger.addHandler(console_handler)

# ===============================
# Discord Webhook初期化
# ===============================
try:
    webhook = SyncWebhook.from_url(DISCORD_WEBHOOK_URL)
except Exception as e:
    logging.error(f"Discord Webhook初期化エラー: {e}")
    webhook = None

# ===============================
# グローバル変数の適切な管理
# ===============================
# APIレートリミット管理用
last_post_time = 0     # 最後のPOSTリクエスト時刻
last_get_time = 0      # 最後のGETリクエスト時刻
rate_limit_errors = 0  # レートリミットエラーカウンター
current_rate_limit = 20  # 現在のレートリミット（1秒あたりのリクエスト数）

# 取引結果管理用
total_api_fee = 0      # API手数料累計
trade_results = []     # 取引結果リスト
symbol_daily_volume = {}  # 銘柄別の一日の取引数量を追跡

# 自動再起動管理用
restart_count = 0
max_restarts = 5
restart_cooldown = 300  # 5分
last_restart_time = 0

# パフォーマンスメトリクス用
performance_metrics = {
    'total_trades': 0,
    'successful_trades': 0,
    'failed_trades': 0,
    'total_profit_pips': 0,
    'total_profit_amount': 0,
    'average_profit_pips': 0,
    'win_rate': 0,
    'max_drawdown_pips': 0,
    'max_drawdown_amount': 0,
    'start_time': datetime.now(),
    'api_calls': 0,
    'api_errors': 0
}

# グローバル変数をスレッドセーフに管理
post_lock = Lock()
get_lock = Lock()

def get_memory_usage():
    """現在のメモリ使用量を取得"""
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        'rss': memory_info.rss / 1024 / 1024,  # MB
        'vms': memory_info.vms / 1024 / 1024,  # MB
        'percent': process.memory_percent()
    }

def check_memory_usage():
    """メモリ使用量をチェックし、必要に応じてGCを実行"""
    memory_usage = get_memory_usage()
    
    # メモリ使用量が100MBを超えた場合にログ出力
    if memory_usage['rss'] > 100:
        logging.warning(f"メモリ使用量が高くなっています: {memory_usage['rss']:.1f}MB")
        
        # 200MBを超えた場合は強制GC実行
        if memory_usage['rss'] > 200:
            logging.warning("メモリ使用量が200MBを超えました。ガベージコレクションを実行します。")
            gc.collect()
            
            # GC後のメモリ使用量を再チェック
            after_gc = get_memory_usage()
            logging.info(f"GC実行後のメモリ使用量: {after_gc['rss']:.1f}MB")
    
    return memory_usage

def rate_limit(method):
    global last_post_time, last_get_time, current_rate_limit
    now = time.time()
    
    with post_lock if method == 'POST' else get_lock:
        if method == 'POST':
            wait = 1.0/current_rate_limit - (now - last_post_time)
            if wait > 0:
                time.sleep(wait + random.uniform(0, 0.1))  # ジッター追加
            last_post_time = time.time()
        elif method == 'GET':
            wait = 1.0/current_rate_limit - (now - last_get_time)
            if wait > 0:
                time.sleep(wait + random.uniform(0, 0.05))  # ジッター追加
            last_get_time = time.time()

def adjust_rate_limit(error_code):
    """レートリミットエラーに応じて動的に調整"""
    global current_rate_limit, rate_limit_errors
    
    if error_code == 'ERR-5003':  # レートリミットエラー
        rate_limit_errors += 1
        if rate_limit_errors >= 3:
            current_rate_limit = max(5, current_rate_limit - 5)  # 最低5回/秒まで
            logging.warning(f"レートリミットを{current_rate_limit}回/秒に調整しました")
            rate_limit_errors = 0
    else:
        # エラーがなければ徐々に回復
        if rate_limit_errors > 0:
            rate_limit_errors = max(0, rate_limit_errors - 1)
        if current_rate_limit < 20 and rate_limit_errors == 0:
            current_rate_limit = min(20, current_rate_limit + 1)

def generate_timestamp():
    """
    GMOコインAPI用のタイムスタンプ（ミリ秒）を生成
    ※APIリクエスト直前で必ず呼び出すこと
    """
    return '{0}000'.format(int(time.time()))

def generate_signature(timestamp, method, path, body=''):
    """
    GMOコインAPI用のリクエスト署名を生成
    """
    if not GMO_API_SECRET:
        raise ValueError("APIシークレットが設定されていません")
    text = timestamp + method + path + body
    return hmac.new(GMO_API_SECRET.encode('ascii'), text.encode('ascii'), hashlib.sha256).hexdigest()

def send_discord_message(content):
    """
    Discordにメッセージを送信（ログ出力統一化）
    """
    try:
        if webhook and DISCORD_WEBHOOK_URL:
            webhook.send(content)
            logging.info(f"Discord通知送信: {content[:100]}...")  # 最初の100文字のみログ
        else:
            logging.warning("Discord Webhook URLが設定されていません")
    except Exception as e:
        logging.error(f"Discord通知エラー: {e}")
        # コンソール出力は削除（ログに統一）

def retry_request(method, url, headers, params=None, data=None):
    global performance_metrics
    
    # API呼び出しカウンター
    performance_metrics['api_calls'] += 1
    
    base_delay = 1
    max_delay = 60
    for attempt in range(3):
        try:
            rate_limit(method)
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=15)
                
            response.raise_for_status()
            res_json = response.json()
            
            if res_json.get('status') != 0:
                error_code = res_json.get('messages', [{}])[0].get('message_code')
                performance_metrics['api_errors'] += 1
                adjust_rate_limit(error_code)  # レートリミット調整
                if error_code == 'ERR-5003':  # レートリミットエラー特定
                    backoff = min((2 ** attempt) + random.random(), max_delay)
                    time.sleep(backoff)
                    continue
                    
            return res_json
            
        except requests.exceptions.RequestException as e:
            performance_metrics['api_errors'] += 1
            sleep_time = min(base_delay * (2 ** attempt) + random.random(), max_delay)
            time.sleep(sleep_time)
            
    raise Exception("Max retries exceeded")

# API呼び出し回数を削減するキャッシュ機構
ticker_cache = {}
CACHE_TTL = 5  # 5秒キャッシュ保持

def get_tickers_optimized(symbols):
    current_time = time.time()
    uncached_symbols = [s for s in symbols if ticker_cache.get(s, {}).get('expiry', 0) < current_time]
    
    if uncached_symbols:
        fresh_data = get_tickers(uncached_symbols)
        for data in fresh_data.get('data', []):
            ticker_cache[data['symbol']] = {
                'bid': data['bid'],
                'ask': data['ask'],
                'expiry': current_time + CACHE_TTL
            }
    
    return {s: ticker_cache[s] for s in symbols if s in ticker_cache}

def get_fx_balance():
    """
    現在のFX口座残高を取得
    """
    try:
        timestamp = generate_timestamp()
        method = 'GET'
        path = '/v1/account/assets'
        url = 'https://forex-api.coin.z.com/private' + path
        headers = {
            "API-KEY": GMO_API_KEY,
            "API-TIMESTAMP": timestamp,
            "API-SIGN": generate_signature(timestamp, method, path)
        }
        response = retry_request(method, url, headers)
        
        # レスポンスの詳細ログ
        logging.info(f"証拠金取得レスポンス: {response}")
        
        if not response:
            raise ValueError("証拠金取得APIからレスポンスがありません")
        
        if 'data' not in response:
            raise ValueError(f"証拠金取得APIレスポンスに'data'フィールドがありません: {response}")
        
        if not response['data']:
            raise ValueError(f"証拠金取得APIの'data'フィールドが空です: {response}")
        
        return response
    except Exception as e:
        logging.error(f"証拠金取得エラー: {e}")
        raise

def get_tickers(symbols):
    """
    指定した通貨ペアの最新レート（bid/ask）を取得
    """
    timestamp = generate_timestamp()
    method = 'GET'
    path = '/v1/ticker'
    url = 'https://forex-api.coin.z.com/public' + path
    params = {'symbol': ','.join(symbols)}
    headers = {"API-TIMESTAMP": timestamp}
    return retry_request(method, url, headers, params)

def format_price(price, symbol):
    if "JPY" in symbol:
        return f"{price:.3f}"
    else:
        return f"{price:.5f}"

def calc_auto_lot_gmobot2(balance, symbol, side, leverage):
    """
    GMOコインの仕様に基づいた正確なロット計算
    GMOコイン: 1lot = 1通貨
    証拠金必要額 = 取引額 / レバレッジ
    安全マージン0.95を適用
    """
    try:
        # 入力値の検証
        if not balance or float(balance) <= 0:
            raise ValueError(f"無効な証拠金: {balance}")
        
        if not leverage or float(leverage) <= 0:
            raise ValueError(f"無効なレバレッジ: {leverage}")
        
        if not symbol:
            raise ValueError("通貨ペアが指定されていません")
        
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"無効な売買方向: {side}")
        
        # ティッカーデータ取得
        tickers = get_tickers([symbol])
        logging.info(f"ティッカーデータ取得結果: {tickers}")
        
        if not tickers or 'data' not in tickers:
            raise ValueError("ティッカーデータの取得に失敗しました")
        
        # 通貨ペアのレート取得
        rate_data = None
        for item in tickers['data']:
            if item['symbol'] == symbol:
                rate_data = item
                break
        
        if not rate_data:
            raise ValueError(f"{symbol}のレート情報の取得に失敗しました")
        
        # 売買方向に応じたレート選択
        if side == "BUY":
            rate = float(rate_data['ask'])  # 買い注文はask
        else:
            rate = float(rate_data['bid'])  # 売り注文はbid
        
        if rate <= 0:
            raise ValueError(f"無効なレート: {rate}")
        
        # 安全マージンを適用
        safety_margin = 0.95
        balance_float = float(balance)
        leverage_float = float(leverage)
        
        # 安全な計算（ゼロ除算防止）
        if rate == 0:
            raise ValueError("レートが0のため計算できません")
        
        # GMOコインの正しいロット計算式
        # 証拠金必要額 = 取引額 ÷ レバレッジ
        # 取引額 = ロット数 × レート
        
        # リスク管理のための証拠金使用割合
        risk_percentage = RISK_RATIO  # 設定ファイルのrisk_ratioを使用
        available_balance = balance_float * risk_percentage * safety_margin
        
        # 通貨ペアに応じた計算
        if "JPY" in symbol:
            # JPYペアの場合：1lot = 1通貨（円基準）
            # 証拠金は円なので、そのまま計算可能
            volume = int((available_balance * leverage_float) / rate)
        else:
            # USDペアの場合：1lot = 1通貨（USD基準）
            # 証拠金を円からUSDに変換してから計算
            # USD/JPYレートを取得して円→USD変換
            usdjpy_tickers = get_tickers(['USD_JPY'])
            if usdjpy_tickers and 'data' in usdjpy_tickers:
                usdjpy_rate = None
                for item in usdjpy_tickers['data']:
                    if item['symbol'] == 'USD_JPY':
                        usdjpy_rate = float(item['bid'])  # 円売りレート（USDを買う）
                        break
                
                if usdjpy_rate and usdjpy_rate > 0:
                    # 円証拠金をUSDに変換
                    available_balance_usd = available_balance / usdjpy_rate
                    # USD基準でロット計算
                    volume = int((available_balance_usd * leverage_float) / rate)
                    logging.info(f"USDペア計算: 円証拠金={available_balance}, USD/JPY={usdjpy_rate}, USD証拠金={available_balance_usd}, 計算結果={volume}")
                else:
                    # USD/JPYレート取得失敗時は円基準で計算（フォールバック）
                    volume = int((available_balance * leverage_float) / rate)
                    logging.warning(f"USD/JPYレート取得失敗、円基準で計算: {volume}")
            else:
                # USD/JPYレート取得失敗時は円基準で計算（フォールバック）
                volume = int((available_balance * leverage_float) / rate)
                logging.warning(f"USD/JPYレート取得失敗、円基準で計算: {volume}")
        
        # 最小ロット数チェック
        if volume < 1:
            volume = 1
            logging.warning(f"計算されたロット数が1未満のため、最小値1に設定しました")
        
        # 最大ロット数制限（GMOコインの制限に基づく）
        max_lot = 500000  # 50万ロット制限（一回の注文上限）
        if volume > max_lot:
            volume = max_lot
            logging.warning(f"計算されたロット数が最大制限を超えたため、{max_lot}に制限しました")
        
        # デバッグ情報
        if "JPY" in symbol:
            logging.info(f"ロット計算詳細(JPYペア): 証拠金={balance_float}, リスク割合={risk_percentage}, 利用可能額={available_balance}, レバレッジ={leverage_float}, レート={rate}, 安全マージン={safety_margin}, 計算結果={volume}")
        else:
            logging.info(f"ロット計算詳細(USDペア): 証拠金={balance_float}, リスク割合={risk_percentage}, 利用可能額={available_balance}, レバレッジ={leverage_float}, レート={rate}, 安全マージン={safety_margin}, 計算結果={volume}")
        
        return volume
    except Exception as e:
        logging.error(f"自動ロット計算エラー: {e}")
        raise

def send_order(symbol, side, size=None, leverage=None):
    global total_api_fee
    timestamp = generate_timestamp()
    method = 'POST'
    path = '/v1/order'
    url = 'https://forex-api.coin.z.com/private' + path

    # 銘柄別の取引数量制限チェック
    global daily_trading_volume, symbol_daily_volume
    if size is not None:
        current_symbol_volume = symbol_daily_volume.get(symbol, 0)
        if current_symbol_volume + size > SYMBOL_DAILY_VOLUME_LIMIT:
            error_msg = f"銘柄{symbol}の一日の取引数量制限を超えます: 現在{current_symbol_volume} + 今回{size} > 制限{SYMBOL_DAILY_VOLUME_LIMIT}"
            logging.error(error_msg)
            send_discord_message(error_msg)
            raise ValueError(error_msg)
    
    # autolotがTRUEかつsize未指定なら自動計算
    if AUTOLOT == 'TRUE' and size is None:
        try:
            balance_data = get_fx_balance()
            logging.info(f"証拠金データ取得結果: {balance_data}")
            
            if not balance_data:
                error_msg = "証拠金残高の取得に失敗しました: レスポンスが空です"
                logging.error(error_msg)
                send_discord_message(error_msg)
                raise Exception(error_msg)
            
            if 'data' not in balance_data:
                error_msg = f"証拠金残高の取得に失敗しました: 'data'フィールドがありません - {balance_data}"
                logging.error(error_msg)
                send_discord_message(error_msg)
                raise Exception(error_msg)
            
            if not balance_data['data']:
                error_msg = f"証拠金残高の取得に失敗しました: 'data'フィールドが空です - {balance_data}"
                logging.error(error_msg)
                send_discord_message(error_msg)
                raise Exception(error_msg)
            
            # 証拠金データの形式を判定して取得
            balance = None
            if isinstance(balance_data['data'], list) and len(balance_data['data']) > 0:
                balance_item = balance_data['data'][0]
                if 'availableAmount' in balance_item:
                    balance = float(balance_item['availableAmount'])
                    logging.info(f"リスト形式から証拠金取得: {balance}")
                else:
                    error_msg = f"証拠金データに'availableAmount'フィールドがありません: {balance_item}"
                    logging.error(error_msg)
                    send_discord_message(error_msg)
                    raise Exception(error_msg)
            elif isinstance(balance_data['data'], dict):
                if 'availableAmount' in balance_data['data']:
                    balance = float(balance_data['data']['availableAmount'])
                    logging.info(f"辞書形式から証拠金取得: {balance}")
                else:
                    error_msg = f"証拠金データに'availableAmount'フィールドがありません: {balance_data['data']}"
                    logging.error(error_msg)
                    send_discord_message(error_msg)
                    raise Exception(error_msg)
            else:
                error_msg = f"証拠金データの形式が不正です: {type(balance_data['data'])} - {balance_data['data']}"
                logging.error(error_msg)
                send_discord_message(error_msg)
                raise Exception(error_msg)
            
            if balance is None or balance <= 0:
                error_msg = f"無効な証拠金残高: {balance}"
                logging.error(error_msg)
                send_discord_message(error_msg)
                raise Exception(error_msg)
            
            logging.info(f"自動ロット計算開始: 証拠金={balance}, 通貨ペア={symbol}, 方向={side}, レバレッジ={leverage or LEVERAGE}")
            size = calc_auto_lot_gmobot2(balance, symbol, side, leverage or LEVERAGE)
            logging.info(f"自動ロット計算完了: ロット数={size}")
            # sizeをint化
            size = int(size)
            
            # 自動ロット計算後の銘柄別取引数量制限チェック
            current_symbol_volume = symbol_daily_volume.get(symbol, 0)
            if current_symbol_volume + size > SYMBOL_DAILY_VOLUME_LIMIT:
                error_msg = f"銘柄{symbol}の一日の取引数量制限を超えます: 現在{current_symbol_volume} + 今回{size} > 制限{SYMBOL_DAILY_VOLUME_LIMIT}"
                logging.error(error_msg)
                send_discord_message(error_msg)
                raise ValueError(error_msg)
            
        except Exception as e:
            error_msg = f"自動ロット計算中にエラーが発生しました: {e}"
            logging.error(error_msg)
            send_discord_message(error_msg)
            raise

    # --- 重複建玉防止チェック ---
    # positions = check_current_positions(symbol)
    # for pos in positions:
    #     if pos['side'] == side:
    #         logging.warning(f"重複建玉検出: {symbol} {side} 既存建玉あり。再注文をスキップします。")
    #         send_discord_message(f"重複建玉検出: {symbol} {side} 既存建玉あり。再注文をスキップします。")
    #         return pos, size

    # sizeをintでAPIに送信
    if size is not None:
        body = {"symbol": symbol, "side": side, "size": str(int(size)), "executionType": "MARKET"}
    else:
        body = {"symbol": symbol, "side": side, "size": None, "executionType": "MARKET"}
    headers = {
        "API-KEY": GMO_API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": generate_signature(timestamp, method, path, json.dumps(body))
    }
    try:
        response = retry_request(method, url, headers, data=body)
    except Exception as e:
        error_msg = f"APIリクエストエラー: {e}"
        logging.error(error_msg)
        send_discord_message(error_msg)
        raise

    # APIレスポンスの検証
    if not response or not isinstance(response, dict):
        error_msg = f"無効なAPIレスポンス: {response}"
        logging.error(error_msg)
        send_discord_message(error_msg)
        raise ValueError(error_msg)
    
    if 'data' not in response or not response['data']:
        error_msg = f"APIレスポンスにデータがありません: {response}"
        logging.error(error_msg)
        send_discord_message(error_msg)
        raise ValueError(error_msg)
    
    # API手数料の取得（エラーハンドリング強化）
    try:
        if len(response['data']) > 0 and 'orderId' in response['data'][0]:
            order_id = response['data'][0]['orderId']
            fee = get_execution_fee(order_id)
            total_api_fee += fee
            logging.info(f"API手数料取得: {fee}円")
    except Exception as e:
        logging.error(f"API手数料取得エラー: {e}")
        # 手数料取得エラーは致命的ではないので続行
    
    # 取引成功時に銘柄別の取引数量を更新
    if size is not None:
        symbol_daily_volume[symbol] = symbol_daily_volume.get(symbol, 0) + size
        logging.info(f"銘柄別取引数量更新: {symbol}{symbol_daily_volume[symbol]}/{SYMBOL_DAILY_VOLUME_LIMIT}")
    
    # 実際に使用されたロット数も返す
    return response, size

def close_position(symbol, position_id, size, side):
    global total_api_fee
    timestamp = generate_timestamp()
    method = 'POST'
    path = '/v1/closeOrder'
    url = 'https://forex-api.coin.z.com/private' + path
    body = {
        "symbol": symbol,
        "side": side,
        "executionType": "MARKET",
        "settlePosition": [
            {
                "positionId": position_id,
                "size": str(size)
            }
        ]
    }
    headers = {
        "API-KEY": GMO_API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": generate_signature(timestamp, method, path, json.dumps(body))
    }
    response = retry_request(method, url, headers, data=body)
    if response and 'data' in response and len(response['data']) > 0:
        order_id = response['data'][0]['orderId']
        try:
            # --- 修正：feeをAPIから取得して加算 ---
            total_api_fee += get_execution_fee(order_id)
            executed_price = get_execution_price(order_id)
            return executed_price
        except Exception as e:
            logging.error(f"API手数料取得エラー（決済）: {e}")
            return get_execution_price(order_id)
    else:
        raise ValueError("決済注文に失敗しました")

def get_execution_fee(order_id):
    """
    注文IDから実際に発生した手数料（fee）を合計して返す
    """
    timestamp = generate_timestamp()
    method = 'GET'
    path = '/v1/executions'
    url = 'https://forex-api.coin.z.com/private' + path
    params = {"orderId": order_id}
    headers = {
        "API-KEY": GMO_API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": generate_signature(timestamp, method, path)
    }
    response = retry_request(method, url, headers, params=params)
    if 'data' in response and 'list' in response['data'] and len(response['data']['list']) > 0:
        # 複数約定がある場合はfeeを合計
        total_fee = sum(float(exe.get('fee', 0)) for exe in response['data']['list'])
        return total_fee
    else:
        raise ValueError("約定履歴から手数料情報を取得できませんでした")

def get_execution_price(order_id):
    """
    注文IDから約定価格（平均値）を取得
    """
    timestamp = generate_timestamp()
    method = 'GET'
    path = '/v1/executions'
    url = 'https://forex-api.coin.z.com/private' + path
    params = {"orderId": order_id}
    headers = {
        "API-KEY": GMO_API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": generate_signature(timestamp, method, path)
    }
    
    try:
        response = retry_request(method, url, headers, params=params)
        if 'data' in response and 'list' in response['data'] and len(response['data']['list']) > 0:
            prices = []
            for exe in response['data']['list']:
                try:
                    prices.append(float(exe['price']))
                except (KeyError, TypeError, ValueError) as e:
                    logging.error(f"約定価格変換エラー: {e}")
                    continue
            if not prices:
                raise ValueError("有効な価格データがありません")
            return sum(prices) / len(prices)
        else:
            raise ValueError("約定履歴から価格情報を取得できませんでした")
    except Exception as e:
        logging.error(f"約定価格取得エラー: {e}")
        raise

def calculate_profit_pips(entry_price, exit_price, side, symbol):
    """
    エントリー・決済価格から損益pipsを計算
    """
    pip_value = 0.01 if "JPY" in symbol else 0.0001
    if side == "BUY":
        return round((exit_price - entry_price) / pip_value, 2)
    else:
        return round((entry_price - exit_price) / pip_value, 2)

def calculate_current_profit_pips(entry_price, current_price, side, symbol):
    """
    現在の価格から含み損益pipsを計算
    """
    pip_value = 0.01 if "JPY" in symbol else 0.0001
    
    try:
        # 型変換の統一化
        if isinstance(current_price, dict) and 'bid' in current_price and 'ask' in current_price:
            bid = float(current_price['bid'])
            ask = float(current_price['ask'])
        else:
            logging.error(f"無効な価格データ形式: {current_price}")
            return 0.0
            
        entry_price = float(entry_price)
        
        if side == "BUY":
            profit_pips = (bid - entry_price) / pip_value
        else:
            profit_pips = (entry_price - ask) / pip_value
            
        return round(profit_pips, 2)
        
    except (ValueError, TypeError, KeyError) as e:
        logging.error(f"損益計算エラー: {e}, entry_price={entry_price}, current_price={current_price}")
        return 0.0

def calculate_profit_amount(entry_price, exit_price, side, symbol, size):
    """
    GMOコインの仕様に基づいた正確な損益計算
    GMOコイン: 1lot = 1通貨
    """
    pip_value = 0.01 if "JPY" in symbol else 0.0001
    
    # pips計算
    if side == "BUY":
        profit_pips = (exit_price - entry_price) / pip_value
    else:
        profit_pips = (entry_price - exit_price) / pip_value
    
    # 損益（USD建て or 円建て）
    profit = profit_pips * float(size) * pip_value
    
    # USD建て通貨ペアの場合は円換算
    if not ("JPY" in symbol):
        try:
            tickers = get_tickers(["USD_JPY"])
            usdjpy_rate = None
            if tickers and 'data' in tickers:
                for item in tickers['data']:
                    if item['symbol'] == 'USD_JPY':
                        usdjpy_rate = float(item['bid'])
                        break
            if usdjpy_rate and usdjpy_rate > 0:
                profit = profit * usdjpy_rate
        except Exception as e:
            logging.error(f"USD/JPYレート取得・円換算エラー: {e}")
            # レート取得失敗時はそのままUSD金額を返す
    
    # デバッグ情報
    logging.info(f"損益計算: エントリー={entry_price}, 決済={exit_price}, 方向={side}, ロット={size}, pips={profit_pips:.2f}, 損益={profit:.2f}")
    
    return round(profit, 2)

def get_position_by_order_id(order_data):
    """
    新規注文のorderIdから建玉情報（positionId等）を取得（完全版）
    MAX_RETRIES: 最大リトライ回数
    RETRY_DELAY: リトライ間隔（秒）
    """
    MAX_RETRIES = 5
    RETRY_DELAY = 3
    position_id = None
    execution_time = None

    try:
        # 入力データ検証（型チェック強化版）
        if not order_data or not isinstance(order_data, list) or len(order_data) == 0:
            logging.error("無効な注文データ形式")
            send_discord_message("⚠️ ポジション取得エラー: 無効な注文データ形式")
            return None
            
        order_id = order_data[0].get('orderId')
        if not order_id:
            logging.error("注文IDが存在しません")
            send_discord_message("⚠️ ポジション取得エラー: 注文IDなし")
            return None

        # 約定情報取得（リトライ機構付き）
        execution_data = None
        for _ in range(3):
            try:
                timestamp = generate_timestamp()
                method = 'GET'
                path = '/v1/executions'
                url = 'https://forex-api.coin.z.com/private' + path
                params = {"orderId": order_id}
                headers = {
                    "API-KEY": GMO_API_KEY,
                    "API-TIMESTAMP": timestamp,
                    "API-SIGN": generate_signature(timestamp, method, path)
                }
                
                response = retry_request(method, url, headers, params=params)
                if response and 'data' in response and 'list' in response['data']:
                    execution_data = response['data']['list']
                    break
            except Exception as e:
                logging.warning(f"約定情報取得リトライ中: {e}")
                time.sleep(1)

        if not execution_data:
            logging.error("約定情報取得に失敗")
            send_discord_message("⚠️ ポジション取得エラー: 約定情報なし")
            return None

        # Position IDと約定時間抽出
        for exec_data in execution_data:
            if 'positionId' in exec_data:
                position_id = exec_data['positionId']
                execution_time = datetime.fromisoformat(
                    exec_data.get('timestamp', datetime.now().isoformat()).replace('Z', '+00:00')
                )
                break
                
        if not position_id:
            logging.error("Position IDが見つかりません")
            send_discord_message("⚠️ ポジション取得エラー: Position IDなし")
            return None

        # ポジション情報取得（リトライ機構追加）
        for attempt in range(MAX_RETRIES):
            try:
                timestamp = generate_timestamp()
                method = 'GET'
                path = '/v1/openPositions'
                url = 'https://forex-api.coin.z.com/private' + path
                headers = {
                    "API-KEY": GMO_API_KEY,
                    "API-TIMESTAMP": timestamp,
                    "API-SIGN": generate_signature(timestamp, method, path)
                }
                
                pos_response = retry_request(method, url, headers)
                if not pos_response or 'data' not in pos_response or 'list' not in pos_response['data']:
                    continue

                # 該当ポジション検索
                for pos in pos_response['data']['list']:
                    if pos.get('positionId') == position_id:
                        # タイムスタンプ処理（フォーマット統一）
                        open_time = pos.get('openTime')
                        if open_time and execution_time:
                            try:
                                # タイムスタンプのフォーマット処理を改善
                                if 'T' in open_time:
                                    # ISO形式の場合
                                    open_time = datetime.fromisoformat(open_time.replace('Z', '+00:00')).isoformat(timespec='milliseconds') + 'Z'
                                else:
                                    # その他の形式の場合
                                    open_time = execution_time.isoformat(timespec='milliseconds') + 'Z'
                            except Exception as e:
                                logging.warning(f"タイムスタンプ変換エラー: {e}")
                                open_time = execution_time.isoformat(timespec='milliseconds') + 'Z'
                        else:
                            open_time = execution_time.isoformat(timespec='milliseconds') + 'Z' if execution_time else datetime.now().isoformat(timespec='milliseconds') + 'Z'

                        return {
                            'positionId': position_id,
                            'symbol': pos.get('symbol'),
                            'side': pos.get('side'),
                            'price': float(pos.get('price', 0)),
                            'size': float(pos.get('size', 0)),
                            'openTime': open_time,
                            'entry_time': execution_time.strftime('%H:%M:%S') if execution_time else datetime.now().strftime('%H:%M:%S')
                        }

                # ポジションが見つからない場合リトライ
                time.sleep(RETRY_DELAY)
                
            except KeyError as e:
                logging.warning(f"APIレスポンスキーエラー: {e}")
                time.sleep(RETRY_DELAY)
            except requests.exceptions.RequestException as e:
                logging.warning(f"リクエストエラー: {e}")
                time.sleep(RETRY_DELAY)

        logging.error(f"{MAX_RETRIES}回リトライ後もポジションを検出できず")
        send_discord_message(f"⚠️ 警告: {MAX_RETRIES}回リトライ後もポジション未検出")
        return None

    except Exception as e:
        logging.error(f"ポジション情報取得エラー: {e}")
        send_discord_message(f"⚠️ ポジション情報取得エラー: {str(e)}")
        return None

def close_position_by_info(position, exit_time, auto_closed=False, trade_index=None):
    """
    ポジション情報から決済注文を発行し、損益を記録・通知
    """
    global trade_results, total_api_fee
    exit_side = "SELL" if position['side'] == "BUY" else "BUY"
    # 決済時jitterのsleepはprocess_trades側で行うため、ここでは不要
    average_exit_price = close_position(
        position['symbol'], position['positionId'], position['size'], exit_side
    )
    profit_pips = calculate_profit_pips(
        float(position['price']), average_exit_price, position['side'], position['symbol']
    )
    profit_amount = calculate_profit_amount(
        float(position['price']), average_exit_price, position['side'], position['symbol'], position['size']
    )
    trade_results.append({
        "symbol": position['symbol'],
        "side": position['side'],
        "entry_price": float(position['price']),
        "exit_price": average_exit_price,
        "profit_pips": profit_pips,
        "profit_amount": profit_amount,
        "lot_size": position['size'],
        "entry_time": position.get('entry_time', datetime.now().strftime('%H:%M:%S')),
        "exit_time": datetime.now().strftime('%H:%M:%S'),
    })
    close_type = "自動決済" if auto_closed else "予定決済"
    # 証拠金残高取得
    balance_data = get_fx_balance()
    data = balance_data.get('data')
    if isinstance(data, list) and len(data) > 0:
        balance_amount = float(data[0].get('balance', 0))
    elif isinstance(data, dict):
        balance_amount = float(data.get('balance', 0))
    else:
        balance_amount = 0
    send_discord_message(
        f"{close_type}しました: 通貨ペア={position['symbol']}, 売買方向={position['side']}, "
        f"エントリー価格={position['price']}, 決済価格={average_exit_price}, 損益pips={profit_pips} ({profit_amount}円), ロット数={position['size']} "
        f"(決済時間: {datetime.now().strftime('%H:%M:%S')})\n"
        f"現在の証拠金残高: {balance_amount}円"
    )
    print(f"【決済完了】{close_type}: {position['symbol']} {position['side']} {position['price']}→{average_exit_price} {profit_pips}pips ({profit_amount}円) ロット数:{position['size']}")
    return profit_pips

def check_current_positions(symbol):
    """
    現在のポジションを確認する関数
    symbol: 通貨ペア（例: 'USD_JPY'）指定でそのペアのみ、Noneで全建玉
    """
    try:
        timestamp = generate_timestamp()
        method = 'GET'
        path = '/v1/openPositions'
        url = 'https://forex-api.coin.z.com/private' + path
        params = {"symbol": symbol} if symbol else {}
        headers = {
            "API-KEY": GMO_API_KEY,
            "API-TIMESTAMP": timestamp,
            "API-SIGN": generate_signature(timestamp, method, path)
        }
        response = retry_request(method, url, headers, params=params)
        if 'data' in response and 'list' in response['data']:
            return response['data']['list']
        else:
            logging.warning(f"ポジション確認中のAPIエラー: {response}")
            return []
    except Exception as e:
        logging.error(f"ポジション確認中の例外: {str(e)}")
        return []

def schedule_position_check(symbol, expected_close_time):
    """
    エントリー失敗後も定期的にポジションを確認し、あれば決済する
    """
    end_time = expected_close_time + timedelta(minutes=10)
    while datetime.now() < end_time:
        positions = check_current_positions(symbol)
        if positions:
            logging.warning(f"未認識のポジションが見つかりました。決済を実行します: {positions}")
            for position in positions:
                exit_side = "SELL" if position['side'] == "BUY" else "BUY"
                try:
                    close_position(position['symbol'], position['positionId'], position['size'], exit_side)
                    send_discord_message(f"⚠️ 未認識ポジションを検出し決済しました: {position['symbol']} {position['side']}")
                except Exception as e:
                    logging.error(f"未認識ポジション決済中のエラー: {e}")
            return True
        # 次の確認まで待機
        time.sleep(POSITION_CHECK_INTERVAL)
    return False

def monitor_and_close_positions(positions_to_monitor):
    """
    保有ポジションを監視し、ストップロス・テイクプロフィット条件で自動決済
    """
    if not positions_to_monitor:
        return
    
    try:
        # 監視対象の通貨ペアを重複排除して取得
        symbols = list(set(pos['symbol'] for pos in positions_to_monitor))
        
        # 最新のティッカー情報を一括取得
        tickers_data = get_tickers(symbols)
        
        if not tickers_data or 'data' not in tickers_data:
            logging.error("ティッカー情報の取得に失敗しました")
            return
        
        # 価格データの型変換を強化（文字列→float）
        current_prices = {}
        for t in tickers_data['data']:
            try:
                current_prices[t['symbol']] = {
                    'bid': float(t['bid']),
                    'ask': float(t['ask'])
                }
            except (ValueError, KeyError) as e:
                logging.error(f"価格データ変換エラー ({t.get('symbol', 'unknown')}): {e}")
                continue
        
        # ポジションごとに損益計算と決済判定
        positions_to_remove = []  # 削除対象を記録
        for position in positions_to_monitor:
            symbol = position['symbol']
            if symbol not in current_prices:
                continue
            
            try:
                # ポジション情報の型変換を強化
                entry_price = float(position['price'])
                side = position['side']
                current_price = current_prices[symbol]
                
                # 含み損益計算
                profit_pips = calculate_current_profit_pips(
                    entry_price, 
                    current_price, 
                    side, 
                    symbol
                )
                
                # ストップロス判定
                if STOP_LOSS_PIPS and profit_pips <= -STOP_LOSS_PIPS:
                    send_discord_message(
                        f"{symbol} {side} ポジションがストップロス条件に達しました: {profit_pips:.1f} pips"
                    )
                    close_position_by_info(position, datetime.now(), auto_closed=True)
                    positions_to_remove.append(position)
                
                # テイクプロフィット判定
                elif TAKE_PROFIT_PIPS and profit_pips >= TAKE_PROFIT_PIPS:
                    send_discord_message(
                        f"{symbol} {side} ポジションがテイクプロフィット条件に達しました: {profit_pips:.1f} pips"
                    )
                    close_position_by_info(position, datetime.now(), auto_closed=True)
                    positions_to_remove.append(position)
                    
            except KeyError as e:
                logging.error(f"ポジション情報のキー不足エラー: {e}")
                continue
            except ValueError as e:
                logging.error(f"数値変換エラー ({symbol}): {e}")
                continue
        
        # 削除対象のポジションを一括削除（スレッドセーフ）
        for position in positions_to_remove:
            try:
                positions_to_monitor.remove(position)
            except ValueError:
                # 既に削除されている場合は無視
                pass
                
    except Exception as e:
        logging.error(f"ポジション監視処理全体のエラー: {e}")
        send_discord_message(f"⚠️ ポジション監視システムエラー: {str(e)}")

def process_trades(trades):
    """
    trades.csvの取引指示に従い、エントリー・監視・決済を実行するメイン処理
    各処理の流れと目的を詳細コメントで明示
    """
    global trade_results, total_api_fee
    positions_to_monitor = []  # 監視対象の建玉リスト
    logging.info(f"取引処理開始: {len(trades)}件の取引データ")
    
    for i, trade in enumerate(trades):
        try:
            logging.info(f"取引データ {i+1} 処理開始: {trade}")
            
            # エントリー・決済予定時刻をdatetime型に変換（execute_daily_tradesで調整済み）
            now = datetime.now()
            # execute_daily_tradesで調整済みの時刻を使用
            entry_time = datetime.strptime(trade[3], '%H:%M:%S').replace(
                year=now.year, month=now.month, day=now.day)
            exit_time = datetime.strptime(trade[4], '%H:%M:%S').replace(
                year=now.year, month=now.month, day=now.day)
            
            # 日を跨ぐ取引の場合、exit_timeを適切に調整
            if exit_time <= entry_time:
                exit_time = exit_time + timedelta(days=1)
            
            logging.info(f"取引データ {i+1}: 時刻設定 - entry_time={entry_time}, exit_time={exit_time}, now={now}")
            
            # 予定時刻を過ぎていたらスキップ（execute_daily_tradesで調整済みなので通常は発生しない）
            # ただし、日を跨ぐ取引の場合は現在時刻との比較を慎重に行う
            current_time = datetime.now()
            if entry_time < current_time:
                # 日を跨ぐ取引の場合は、現在時刻が00:00-06:00の範囲で、エントリー時刻が00:00-06:00の場合は翌日として扱う
                if (current_time.hour < 6 and entry_time.hour < 6 and 
                    entry_time.date() == current_time.date()):
                    # 翌日に調整
                    entry_time = entry_time + timedelta(days=1)
                    exit_time = exit_time + timedelta(days=1)
                    logging.info(f"取引データ {i+1}: 日を跨ぐ取引として翌日に調整 - entry_time={entry_time}, exit_time={exit_time}")
                else:
                    skip_msg = f"取引データ {i+1} のエントリー時間が過ぎています。スキップします。entry_time={entry_time}, now={current_time}"
                    logging.warning(skip_msg)
                    send_discord_message(skip_msg)
                    continue

            logging.info(f"取引データ {i+1}: エントリー処理開始 - entry_time={entry_time}, exit_time={exit_time}")

            # --- JITTER（ゆらぎ）ロジック修正 ---
            now = datetime.now()
            if now < entry_time:
                jitter = random.uniform(0, JITTER_SECONDS)
                target_time = entry_time - timedelta(seconds=jitter)
                wait_time = (target_time - now).total_seconds()
                logging.info(f"取引データ {i+1}: エントリー時刻まで待機 - wait_time={wait_time}秒, target_time={target_time}")
                if wait_time > 0:
                    time.sleep(wait_time)
                # ここでエントリー実行（予定時刻-jitter～予定時刻の間で実行）

            # 売買方向・ロット数を設定
            # 漢字（買/売）と英語（long/short）の両方に対応（大文字・小文字対応）
            direction = trade[1].strip().lower()
            if direction in ["買", "long", "l"]:
                side = "BUY"
            elif direction in ["売", "short", "s"]:
                side = "SELL"
            else:
                error_msg = f"取引データ {i+1}: 無効な売買方向 '{trade[1]}' が指定されました。'買'/'売'/'long'/'short'/'l'/'s'のいずれかを指定してください。"
                logging.error(error_msg)
                send_discord_message(error_msg)
                continue
            # ロット数が空の場合はNone、そうでなければ数値に変換（*10000しない）
            if trade[5].strip() == "":
                # ロット数未指定の場合
                lot_size = None
                # autolot=OFFでロット未指定の場合のみ18倍を使用
                if AUTOLOT == 'FALSE':
                    custom_leverage = 18
                else:
                    custom_leverage = LEVERAGE
            else:
                # ロット数の処理（空文字列の場合はNone、数値の場合はfloat）
                lot_str = trade[5].strip() if len(trade) > 5 else ""
                lot_size = float(lot_str) if lot_str else None
                custom_leverage = LEVERAGE
            # 通貨ペアの正規化（USDJPY → USD_JPY、USD/JPY → USD_JPY）
            pair_raw = trade[2].strip()
            if "/" in pair_raw:
                pair = pair_raw.replace("/", "_")
            else:
                # USDJPY → USD_JPY の変換
                if len(pair_raw) == 6:  # USDJPY, EURUSD など
                    pair = f"{pair_raw[:3]}_{pair_raw[3:]}"
                else:
                    pair = pair_raw  # その他の形式はそのまま
            
            logging.info(f"取引データ {i+1}: 取引設定 - pair={pair}, side={side}, lot_size={lot_size}, leverage={custom_leverage}")

            entry_success = False
            for attempt in range(MAX_ENTRY_ORDER_ATTEMPTS):
                logging.info(f"取引データ {i+1}: エントリー試行 {attempt+1}/{MAX_ENTRY_ORDER_ATTEMPTS}")
                
                # 最新レート取得
                ticker_data = get_tickers([pair])
                # ここでbid/ask/spreadを計算
                if not ticker_data or 'data' not in ticker_data or len(ticker_data['data']) == 0:
                    # エラー処理（例: Discord通知してcontinue）
                    logging.warning(f"取引データ {i+1}: ティッカーデータ取得失敗 - ticker_data={ticker_data}")
                    time.sleep(ENTRY_ORDER_RETRY_INTERVAL)
                    continue
                
                # 修正: symbol==pairのものを必ず参照
                rate_data = None
                for item in ticker_data['data']:
                    if item['symbol'] == pair:
                        rate_data = item
                        break
                if not rate_data:
                    logging.warning(f"取引データ {i+1}: {pair}のレート情報が見つかりませんでした - ticker_data={ticker_data}")
                    time.sleep(ENTRY_ORDER_RETRY_INTERVAL)
                    continue
                bid = float(rate_data['bid'])
                ask = float(rate_data['ask'])
                spread = ask - bid
                # 通貨ペアの正しい判定
                if pair.endswith("JPY"):
                    pip_value = 0.01
                else:
                    pip_value = 0.0001
                spread_pips = spread / pip_value
                
                logging.info(f"取引データ {i+1}: レート情報 - bid={bid}, ask={ask}, spread_pips={spread_pips}")
                
                # スプレッド判定
                if spread > SPREAD_THRESHOLD:
                    spread_msg = f"取引データ {i+1} (試行 {attempt+1}/{MAX_ENTRY_ORDER_ATTEMPTS}) のスプレッドが閾値を超えています ({spread:.3f} > {SPREAD_THRESHOLD:.3f})。再試行します。"
                    logging.warning(spread_msg)
                    send_discord_message(spread_msg)
                    time.sleep(ENTRY_ORDER_RETRY_INTERVAL)
                    continue
                try:
                    # デバッグ用ログ
                    logging.info(f"取引データ {i+1}: エントリー注文発注開始 - {pair} {side} lot_size={lot_size}")
                    print(f"エントリー試行: {pair} {side} lot_size={lot_size}")
                    # 新規注文発注
                    if lot_size is None:
                        response_order, actual_size = send_order(pair, side, None, custom_leverage)
                    else:
                        response_order, actual_size = send_order(pair, side, lot_size, custom_leverage)
                    logging.info(f"取引データ {i+1}: エントリー注文レスポンス - {response_order}")
                    
                    # 建玉情報取得
                    if 'data' in response_order and response_order['data']:
                        position_info = get_position_by_order_id(response_order['data'])
                    else:
                        logging.error(f"APIレスポンスに'data'がありません: {response_order}")
                        send_discord_message(f"エントリー注文エラー: APIレスポンスに'data'がありません: {response_order}")
                        continue
                    if position_info:
                        logging.info(f"取引データ {i+1}: ポジション情報取得成功 - {position_info}")
                        # 監視用情報を付与してリストに追加
                        position_info['exit_time'] = exit_time
                        position_info['auto_closed'] = False
                        position_info['trade_index'] = i+1
                        positions_to_monitor.append(position_info)
                        entry_success = True
                        # エントリー成功通知
                        entry_price = position_info['price']
                        actual_entry_time = datetime.now()  # ←ここで実際のエントリー時刻を取得
                        # 自動ロットが使用されたかどうかを判定
                        if AUTOLOT == 'TRUE':
                            lot_info = f"自動ロット={actual_size}"
                        else:
                            lot_info = f"ロット数={trade[5]}"
                        success_msg = f"エントリーしました: 通貨ペア={pair}, 売買方向={side}, {lot_info}, エントリー価格={entry_price}, Bid={format_price(bid, pair)}, Ask={format_price(ask, pair)}, スプレッド={spread_pips:.3f}pips, エントリー時間={actual_entry_time.strftime('%H:%M:%S')}, 決済予定時間={exit_time.strftime('%H:%M:%S')}"
                        logging.info(f"取引データ {i+1}: {success_msg}")
                        send_discord_message(success_msg)
                        break  # エントリー成功でリトライループ脱出
                    else:
                        logging.error(f"取引データ {i+1}: ポジション情報取得失敗")
                except Exception as e:
                    error_msg = f"エントリー注文エラー (試行 {attempt+1}/{MAX_ENTRY_ORDER_ATTEMPTS}): {e}"
                    logging.error(f"取引データ {i+1}: {error_msg}\n{traceback.format_exc()}")
                    print(f"DEBUG: {error_msg}")  # デバッグ用コンソール出力
                    send_discord_message(error_msg)
                    time.sleep(ENTRY_ORDER_RETRY_INTERVAL)
            # すべてのエントリー試行終了後に最終ポジションチェック
            if not entry_success:
                logging.warning(f"取引データ {i+1}: すべてのエントリー試行が失敗、最終ポジションチェック実行")
                positions = check_current_positions(pair)
                if positions:
                    for position in positions:
                        logging.warning(f"すべての試行でエラーが報告されましたが、ポジションが検出されました。")
                        send_discord_message(f"⚠️ 警告: エラー報告後にポジションを検出しました: {pair} {side}")
                        position['exit_time'] = exit_time
                        position['auto_closed'] = False
                        position['trade_index'] = i+1
                        positions_to_monitor.append(position)
                        entry_success = True
                        break
            if not entry_success:
                skip_msg = f"取引データ {i+1} は最大試行回数を超えたため、エントリーをスキップします。"
                logging.error(f"取引データ {i+1}: {skip_msg}")
                send_discord_message(skip_msg)
                # 念のため定期的にポジション確認を行う
                logging.info("念のため定期的なポジション確認を開始します")
                schedule_future_check = threading.Thread(
                    target=schedule_position_check, 
                    args=(pair, exit_time)
                )
                schedule_future_check.daemon = True
                schedule_future_check.start()
                continue

            logging.info(f"取引データ {i+1}: 決済監視開始 - exit_time={exit_time}")

            # --- 決済時jitter（前倒し）ロジック修正版 ---
            # 1. 決済予定時刻-jitterの時点で監視ループを終了する
            jitter = random.uniform(0, JITTER_SECONDS)
            target_time = exit_time - timedelta(seconds=jitter)

            # 2. target_timeまでポジション監視（ストップロス・テイクプロフィット自動決済対応）
            while datetime.now() < target_time:
                try:
                    monitor_and_close_positions(positions_to_monitor)
                except Exception as e:
                    logging.error(f"ポジション監視処理中のエラー: {e}\n{traceback.format_exc()}")
                    send_discord_message(f"⚠️ ポジション監視エラー: {e}")
                time.sleep(POSITION_CHECK_INTERVAL)

            # 3. target_timeになったら即決済（リトライ機能付き）
            for position in positions_to_monitor[:]:
                if position['trade_index'] == i+1 and not position['auto_closed']:
                    logging.info(f"取引データ {i+1}: 時間指定決済開始")
                    # 決済処理にリトライ機能を追加
                    for retry_attempt in range(MAX_EXIT_ORDER_ATTEMPTS):
                        try:
                            close_position_by_info(position, exit_time, auto_closed=False, trade_index=i+1)
                            positions_to_monitor.remove(position)
                            logging.info(f"取引データ {i+1}: 決済成功")
                            break  # 成功したらリトライループを抜ける
                        except Exception as e:
                            error_msg = f"決済処理エラー (試行 {retry_attempt+1}/{MAX_EXIT_ORDER_ATTEMPTS}): {e}"
                            logging.error(f"{error_msg}\n{traceback.format_exc()}")
                            send_discord_message(error_msg)
                            if retry_attempt < MAX_EXIT_ORDER_ATTEMPTS - 1:
                                time.sleep(EXIT_ORDER_RETRY_INTERVAL)
                            else:
                                # 最大リトライ回数に達した場合
                                send_discord_message(f"⚠️ 決済処理が最大試行回数を超えました: {position['symbol']} {position['side']}")
                                # 最終的に手動決済を試行
                                try:
                                    exit_side = "SELL" if position['side'] == "BUY" else "BUY"
                                    close_position(position['symbol'], position['positionId'], position['size'], exit_side)
                                    send_discord_message(f"⚠️ 手動決済を実行しました: {position['symbol']} {position['side']}")
                                    positions_to_monitor.remove(position)
                                except Exception as final_e:
                                    logging.error(f"手動決済も失敗: {final_e}\n{traceback.format_exc()}")
                                    send_discord_message(f"⚠️ 手動決済も失敗しました: {position['symbol']} {position['side']} - {final_e}")

        except Exception as e:
            # 取引データごとの例外もDiscord通知
            error_msg = f"取引データ {i+1} の処理中にエラーが発生しました: {e}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            send_discord_message(error_msg)

    logging.info("すべての取引処理完了")
    
    # 監視中のポジションがある場合は、それらが決済されるまで待機
    if positions_to_monitor:
        logging.info(f"監視中のポジションが{len(positions_to_monitor)}件あります。決済完了まで待機します。")
        send_discord_message(f"📊 監視中のポジションが{len(positions_to_monitor)}件あります。決済完了まで待機します。")
        
        # 各ポジションの決済予定時刻を確認
        for position in positions_to_monitor:
            exit_time = position.get('exit_time')
            if exit_time:
                logging.info(f"ポジション {position['symbol']} {position['side']} の決済予定時刻: {exit_time}")
                send_discord_message(f"⏰ ポジション {position['symbol']} {position['side']} の決済予定時刻: {exit_time.strftime('%H:%M:%S')}")
        
        # 最終決済は行わず、各ポジションが予定時刻に決済されるのを待つ
        # これにより、23:36エントリー00:05決済のような日を跨ぐ取引も適切に処理される
    else:
        logging.info("監視中のポジションはありません。")

def save_daily_results():
    """
    日次取引結果をCSVファイルに保存
    """
    global trade_results
    today = datetime.now().strftime('%Y-%m-%d')
    
    # daily_resultsディレクトリを作成
    daily_results_dir = 'daily_results'
    if not os.path.exists(daily_results_dir):
        os.makedirs(daily_results_dir)
        logging.info(f"daily_resultsディレクトリを作成しました: {daily_results_dir}")
    
    filename = os.path.join(daily_results_dir, f'daily_results_{today}.csv')
    
    if not trade_results:
        return
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['日付', '通貨ペア', '売買方向', 'エントリー価格', '決済価格', 'ロット数', '損益pips', '損益金額(円)', 'エントリー時刻', '決済時刻'])
            
            for trade in trade_results:
                writer.writerow([
                    today,
                    trade['symbol'],
                    trade['side'],
                    trade['entry_price'],
                    trade['exit_price'],
                    trade.get('lot_size', 'N/A'),
                    f"{trade['profit_pips']:.1f}",
                    f"{trade.get('profit_amount', 0):.0f}",
                    trade.get('entry_time', 'N/A'),
                    trade.get('exit_time', 'N/A')
                ])
        logging.info(f"日次結果を{filename}に保存しました")
    except Exception as e:
        logging.error(f"日次結果保存エラー: {e}")

def finalize_trades_for_day(target_date):
    """
    指定日の19:00までに決済された取引のみを集計・Discord通知
    それ以降の取引はtrade_resultsに残す
    """
    global trade_results
    cutoff = datetime.combine(target_date, datetime.min.time()).replace(hour=19, minute=0, second=0)
    today_results = []
    remain_results = []
    for trade in trade_results:
        # 決済時刻をdatetime型に変換（タイムゾーン処理改善）
        exit_time_str = trade.get('exit_time')
        if exit_time_str:
            try:
                # 日付情報がなければtarget_dateを使う
                if 'T' in exit_time_str or '-' in exit_time_str:
                    # ISO形式の場合
                    exit_time_str_clean = exit_time_str.replace('Z', '+00:00')
                    exit_time = datetime.fromisoformat(exit_time_str_clean)
                else:
                    # HH:MM:SS形式の場合
                    time_obj = datetime.strptime(exit_time_str, '%H:%M:%S').time()
                    exit_time = datetime.combine(target_date, time_obj)
            except (ValueError, TypeError) as e:
                logging.error(f"決済時刻変換エラー: {e}, exit_time_str={exit_time_str}")
                exit_time = cutoff  # エラー時は当日19:00扱い
        else:
            exit_time = cutoff  # 万一なければ当日19:00扱い
        if exit_time < cutoff:
            today_results.append(trade)
        else:
            remain_results.append(trade)
    if not today_results:
        send_discord_message(f"{target_date.strftime('%Y/%m/%d')} 19:00までの取引はありませんでした。")
        trade_results = remain_results
        return
    total_profit_pips = sum(trade['profit_pips'] for trade in today_results)
    total_profit_amount = sum(trade.get('profit_amount', 0) for trade in today_results)
    
    # 口座残高取得（例外処理追加）
    try:
        balance_data = get_fx_balance()
        data = balance_data.get('data')
        if isinstance(data, list) and len(data) > 0:
            balance_amount = float(data[0].get('balance', 0))
        elif isinstance(data, dict):
            balance_amount = float(data.get('balance', 0))
        else:
            balance_amount = 0
    except Exception as e:
        logging.error(f"口座残高取得エラー: {e}")
        balance_amount = 0
    table_header = "| 通貨ペア | 売買方向 | エントリー価格 | 決済価格 | ロット数 | 損益pips | 損益金額(円) |\n|---|---|---|---|---|---|---|\n"
    table_rows = "\n".join(
        f"| {trade['symbol']} | {trade['side']} | {trade['entry_price']} | {trade['exit_price']} | {trade.get('lot_size', 'N/A')} | {trade['profit_pips']:.1f} | {trade.get('profit_amount', 0):.0f} |"
        for trade in today_results
    )
    message = (
        f"**{target_date.strftime('%Y/%m/%d')} 19:00までの取引結果**\n\n"
        f"{table_header}{table_rows}\n\n"
        f"**合計損益pips**: {total_profit_pips:.1f}\n"
        f"**本日の合計損益**: {total_profit_amount:.0f}円\n"
        f"**合計API手数料**: {round(total_api_fee)}円\n"
        f"**FX口座残高**: {balance_amount}円"
    )
    send_discord_message(message)
    # 日次結果を保存
    today = target_date.strftime('%Y-%m-%d')
    
    # daily_resultsディレクトリを作成
    daily_results_dir = 'daily_results'
    if not os.path.exists(daily_results_dir):
        os.makedirs(daily_results_dir)
        logging.info(f"daily_resultsディレクトリを作成しました: {daily_results_dir}")
    
    filename = os.path.join(daily_results_dir, f'daily_results_{today}.csv')
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['日付', '通貨ペア', '売買方向', 'エントリー価格', '決済価格', 'ロット数', '損益pips', '損益金額(円)', 'エントリー時刻', '決済時刻'])
            for trade in today_results:
                writer.writerow([
                    today,
                    trade['symbol'],
                    trade['side'],
                    trade['entry_price'],
                    trade['exit_price'],
                    trade.get('lot_size', 'N/A'),
                    f"{trade['profit_pips']:.1f}",
                    f"{trade.get('profit_amount', 0):.0f}",
                    trade.get('entry_time', 'N/A'),
                    trade.get('exit_time', 'N/A')
                ])
        logging.info(f"日次結果を{filename}に保存しました")
    except Exception as e:
        logging.error(f"日次結果保存エラー: {e}")
    # その日分をリセット
    trade_results = remain_results

def daily_finalize_scheduler():
    """
    毎日19:00に自動で集計・Discord出力するスレッド
    """
    def loop():
        while True:
            now = datetime.now()
            next_19 = now.replace(hour=19, minute=0, second=0, microsecond=0)
            if now >= next_19:
                next_19 += timedelta(days=1)
            wait_seconds = (next_19 - now).total_seconds()
            time.sleep(wait_seconds)
            finalize_trades_for_day(target_date=now.date())
    t = threading.Thread(target=loop, daemon=True)
    t.start()

def auto_restart_scheduler():
    """
    毎日指定時刻に自動再起動するスレッド
    """
    def loop():
        while True:
            try:
                # 設定を再読み込み（実行中に変更された場合のため）
                current_config = load_config()
                restart_hour = current_config.get('auto_restart_hour')
                
                if restart_hour is None:
                    # 自動再起動が無効な場合は1時間待機
                    time.sleep(3600)
                    continue
                
                now = datetime.now()
                next_restart = now.replace(hour=restart_hour, minute=0, second=0, microsecond=0)
                
                # 今日の指定時刻が既に過ぎている場合は明日に設定
                if now >= next_restart:
                    next_restart += timedelta(days=1)
                
                wait_seconds = (next_restart - now).total_seconds()
                
                logging.info(f"自動再起動スケジューラー: 次回再起動時刻 {next_restart.strftime('%Y/%m/%d %H:%M:%S')} (待機時間: {wait_seconds:.0f}秒)")
                
                # 指定時刻まで待機
                time.sleep(wait_seconds)
                
                # 再起動実行
                logging.warning(f"自動再起動時刻({restart_hour}時)に達しました。システムを再起動します。")
                send_discord_message(f"🔄 自動再起動時刻({restart_hour}時)に達しました。システムを再起動します。")
                
                # 再起動実行
                auto_restart_on_error()
                
            except Exception as e:
                logging.error(f"自動再起動スケジューラーエラー: {e}")
                time.sleep(3600)  # エラー時は1時間待機
    
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    logging.info("自動再起動スケジューラーを開始しました")

def daily_volume_reset_scheduler():
    """銘柄別取引数量を午前0時にリセットするスケジューラー"""
    def loop():
        while True:
            try:
                # 毎日午前0時に実行
                now = datetime.now()
                target_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                if now >= target_time:
                    target_time += timedelta(days=1)
                
                wait_seconds = (target_time - now).total_seconds()
                logging.info(f"取引数量リセットスケジューラー: 次回リセット時刻 {target_time.strftime('%Y/%m/%d %H:%M:%S')} (待機時間: {wait_seconds:.0f}秒)")
                time.sleep(wait_seconds)
                
                # 銘柄別取引数量をリセット
                global symbol_daily_volume
                symbol_daily_volume = {}
                logging.info("銘柄別取引数量を午前0時にリセットしました")
                send_discord_message("🔄 銘柄別取引数量を午前0時にリセットしました")
                
            except Exception as e:
                logging.error(f"取引数量リセットスケジューラーエラー: {e}")
                time.sleep(3600)  # エラー時は1時間待機
    
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    logging.info("取引数量リセットスケジューラーを開始しました")

def execute_daily_trades():
    """
    1日の取引を実行
    """
    global trade_results, total_api_fee
    
    try:
        # trades.csvから取引指示を読み込む
        with open('trades.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            trades = []
            for row_num, row in enumerate(reader, start=2):  # 行番号を追跡（ヘッダーが1行目）
                # 空行や不完全な行をスキップ
                if len(row) >= 6 and row[1].strip() and row[2].strip() and row[3].strip() and row[4].strip():
                    # 時刻形式の検証
                    try:
                        datetime.strptime(row[3].strip(), '%H:%M:%S')
                        datetime.strptime(row[4].strip(), '%H:%M:%S')
                        trades.append(row)
                    except ValueError as e:
                        logging.warning(f"行{row_num}: 時刻形式エラー - {row[3]} または {row[4]}: {e}")
                else:
                    if row and any(cell.strip() for cell in row):  # 完全に空でない行のみログ出力
                        logging.warning(f"行{row_num}: 不完全な行をスキップ: {row}")
        
        if not trades:
            send_discord_message("trades.csvに取引データがありません。本日の取引をスキップします。")
            return True
        
        now = datetime.now()
        
        # 前日の最後の取引時刻を取得（日を跨いだ取引の連続性のため）
        last_trade_time = None
        if trade_results:
            # 前日の取引結果から最後の決済時刻を取得
            last_trades = [t for t in trade_results if t.get('exit_time')]
            if last_trades:
                # 最新の決済時刻を取得
                last_exit_time_str = max(last_trades, key=lambda x: x.get('exit_time', '')).get('exit_time')
                if last_exit_time_str:
                    try:
                        if 'T' in last_exit_time_str or '-' in last_exit_time_str:
                            # ISO形式の場合
                            last_exit_time_str_clean = last_exit_time_str.replace('Z', '+00:00')
                            last_trade_time = datetime.fromisoformat(last_exit_time_str_clean)
                        else:
                            # HH:MM:SS形式の場合（前日の日付を仮定）
                            time_obj = datetime.strptime(last_exit_time_str, '%H:%M:%S').time()
                            last_trade_time = datetime.combine(now.date() - timedelta(days=1), time_obj)
                        logging.info(f"前日の最後の取引時刻: {last_trade_time.strftime('%Y/%m/%d %H:%M:%S')}")
                    except (ValueError, TypeError) as e:
                        logging.warning(f"前日の最後の取引時刻取得エラー: {e}")
        
        adjusted_trades = []
        for i, trade in enumerate(trades):
            try:
                original_entry_time = datetime.strptime(trade[3].strip(), '%H:%M:%S').replace(year=now.year, month=now.month, day=now.day)
                entry_time = original_entry_time
            except ValueError as e:
                logging.error(f"取引{i+1}: エントリー時刻の解析エラー - {trade[3]}: {e}")
                continue
            
            # 前日の最後の取引時刻がある場合、連続性を考慮
            if last_trade_time and entry_time < last_trade_time:
                # 前日の最後の取引時刻より前の場合は翌日に設定
                entry_time = entry_time + timedelta(days=1)
                logging.info(f"取引{i+1}: 前日の最後の取引時刻({last_trade_time.strftime('%H:%M:%S')})を考慮し、エントリー時刻を翌日に調整: {original_entry_time.strftime('%H:%M:%S')} → {entry_time.strftime('%Y/%m/%d %H:%M:%S')}")
            elif entry_time < now:
                # 現在時刻より前の場合は翌日に設定
                entry_time = entry_time + timedelta(days=1)
                logging.info(f"取引{i+1}: 現在時刻({now.strftime('%H:%M:%S')})を考慮し、エントリー時刻を翌日に調整: {original_entry_time.strftime('%H:%M:%S')} → {entry_time.strftime('%Y/%m/%d %H:%M:%S')}")
            else:
                logging.info(f"取引{i+1}: エントリー時刻をそのまま使用: {entry_time.strftime('%Y/%m/%d %H:%M:%S')}")
            
            # 決済時刻も同様に調整
            try:
                original_exit_time = datetime.strptime(trade[4].strip(), '%H:%M:%S').replace(year=entry_time.year, month=entry_time.month, day=entry_time.day)
                exit_time = original_exit_time
            except ValueError as e:
                logging.error(f"取引{i+1}: 決済時刻の解析エラー - {trade[4]}: {e}")
                continue
            if exit_time <= entry_time:
                exit_time = exit_time + timedelta(days=1)
                logging.info(f"取引{i+1}: 決済時刻を翌日に調整: {original_exit_time.strftime('%H:%M:%S')} → {exit_time.strftime('%Y/%m/%d %H:%M:%S')}")
            
            # trade[3]とtrade[4]を書き換えた新リストを作成
            adjusted_trade = trade.copy()
            adjusted_trade[3] = entry_time.strftime('%H:%M:%S')
            adjusted_trade[4] = exit_time.strftime('%H:%M:%S')
            # ソート用にタプルを作成（entry_time, trade）
            adjusted_trades.append((entry_time, adjusted_trade))
        
        # entry_timeでソート
        adjusted_trades.sort(key=lambda x: x[0])
        # ソート済みのtradeのみを抽出
        filtered_trades = [t[1] for t in adjusted_trades]

        # 口座残高を取得
        try:
            balance_data = get_fx_balance()
            data = balance_data.get('data')
            if isinstance(data, list) and len(data) > 0:
                balance_amount = float(data[0].get('balance', 0))
            elif isinstance(data, dict):
                balance_amount = float(data.get('balance', 0))
            else:
                balance_amount = 0
        except Exception as e:
            logging.error(f"口座残高取得エラー: {e}")
            balance_amount = 0

        # エントリー予定一覧をDiscordに通知
        today_date = datetime.now().strftime("%Y/%m/%d")
        entry_list_message = f"{today_date}のエントリー一覧:\n"
        
        # 日を跨いだ取引の情報を追加
        if last_trade_time:
            entry_list_message += f"📅 前日の最後の取引時刻: {last_trade_time.strftime('%Y/%m/%d %H:%M:%S')}\n"
            entry_list_message += f"🔄 日を跨いだ取引の連続性を考慮して時刻を調整しました\n\n"
        
        for trade in filtered_trades:
            # 通貨ペアの正規化（表示用）
            pair_display = trade[2].strip()
            if "/" in pair_display:
                pair_display = pair_display.replace("/", "_")
            elif len(pair_display) == 6:  # USDJPY, EURUSD など
                pair_display = f"{pair_display[:3]}_{pair_display[3:]}"
            
            entry_list_message += (
                f"{pair_display} {trade[1]} "
                f"ロット数: {trade[5]} エントリー時間: {trade[3]} 決済時間: {trade[4]}\n"
            )
        entry_list_message += f"\nFX口座残高: {balance_amount}円"
        entry_list_message += f"\nレバレッジ: {LEVERAGE}倍"
        entry_list_message += f"\n自動ロット設定: {AUTOLOT}"
        entry_list_message += f"\nポジション確認: {POSITION_CHECK_INTERVAL_MINUTES}分毎"
        entry_list_message += f"\nストップロス: {STOP_LOSS_PIPS} pips"
        entry_list_message += f"\nテイクプロフィット: {TAKE_PROFIT_PIPS} pips"
        send_discord_message(entry_list_message)

        # 取引実行・監視・決済
        process_trades(filtered_trades)

        # 取引集計・Discord通知
        finalize_trades_for_day(datetime.now().date())

        # 取引完了通知
        send_discord_message("本日の取引が完了しました")
        
        return True

    except FileNotFoundError:
        # trades.csvが存在しない場合のエラー通知
        error_message = "trades.csv が見つかりませんでした。プログラムを終了します。"
        send_discord_message(error_message)
        return False
    except Exception as e:
        # その他予期しないエラーの通知
        error_msg = f"プログラム実行中に予期しないエラーが発生しました: {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        send_discord_message(error_msg)
        return False

def wait_until_next_day():
    """
    翌日の最初の取引時刻まで待機
    """
    try:
        # trades.csvから最初の取引時刻を取得
        with open('trades.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            trades = []
            for row_num, row in enumerate(reader, start=2):  # 行番号を追跡（ヘッダーが1行目）
                # 空行や不完全な行をスキップ
                if len(row) >= 6 and row[1].strip() and row[2].strip() and row[3].strip() and row[4].strip():
                    # 時刻形式の検証
                    try:
                        datetime.strptime(row[3].strip(), '%H:%M:%S')
                        datetime.strptime(row[4].strip(), '%H:%M:%S')
                        trades.append(row)
                    except ValueError as e:
                        logging.warning(f"行{row_num}: 時刻形式エラー - {row[3]} または {row[4]}: {e}")
                else:
                    if row and any(cell.strip() for cell in row):  # 完全に空でない行のみログ出力
                        logging.warning(f"行{row_num}: 不完全な行をスキップ: {row}")
        
        if not trades:
            send_discord_message("trades.csvに取引データがありません。翌日の取引をスキップします。")
            return
        
        # 前日の最後の取引時刻を取得（日を跨いだ取引の連続性のため）
        last_trade_time = None
        if trade_results:
            # 前日の取引結果から最後の決済時刻を取得
            last_trades = [t for t in trade_results if t.get('exit_time')]
            if last_trades:
                # 最新の決済時刻を取得
                last_exit_time_str = max(last_trades, key=lambda x: x.get('exit_time', '')).get('exit_time')
                if last_exit_time_str:
                    try:
                        if 'T' in last_exit_time_str or '-' in last_exit_time_str:
                            # ISO形式の場合
                            last_exit_time_str_clean = last_exit_time_str.replace('Z', '+00:00')
                            last_trade_time = datetime.fromisoformat(last_exit_time_str_clean)
                        else:
                            # HH:MM:SS形式の場合（前日の日付を仮定）
                            time_obj = datetime.strptime(last_exit_time_str, '%H:%M:%S').time()
                            last_trade_time = datetime.combine(datetime.now().date() - timedelta(days=1), time_obj)
                        logging.info(f"前日の最後の取引時刻: {last_trade_time.strftime('%Y/%m/%d %H:%M:%S')}")
                    except (ValueError, TypeError) as e:
                        logging.warning(f"前日の最後の取引時刻取得エラー: {e}")
        
        # 全ての取引を時間順にソートしてから最初の取引時刻を取得
        now = datetime.now()
        sorted_trades = []
        
        for i, trade in enumerate(trades):
            try:
                # エントリー時刻を解析
                entry_time = datetime.strptime(trade[3].strip(), '%H:%M:%S').replace(year=now.year, month=now.month, day=now.day)
                
                # 前日の最後の取引時刻がある場合、連続性を考慮
                if last_trade_time and entry_time < last_trade_time:
                    entry_time = entry_time + timedelta(days=1)
                    logging.info(f"取引{i+1}: 前日の最後の取引時刻を考慮し、エントリー時刻を翌日に調整: {entry_time.strftime('%Y/%m/%d %H:%M:%S')}")
                elif entry_time < now:
                    entry_time = entry_time + timedelta(days=1)
                    logging.info(f"取引{i+1}: 現在時刻を考慮し、エントリー時刻を翌日に調整: {entry_time.strftime('%Y/%m/%d %H:%M:%S')}")
                
                sorted_trades.append((entry_time, trade))
                
            except ValueError as e:
                logging.error(f"取引{i+1}: エントリー時刻の解析エラー - {trade[3]}: {e}")
                continue
        
        if not sorted_trades:
            send_discord_message("有効な取引データがありません。翌日の取引をスキップします。")
            return
        
        # エントリー時刻でソート
        sorted_trades.sort(key=lambda x: x[0])
        
        # 最初の取引時刻を取得
        first_trade_datetime = sorted_trades[0][0]
        first_trade_time = first_trade_datetime.time()
        
        # 前日の最後の取引時刻がある場合、連続性を考慮
        if last_trade_time:
            # 前日の最後の取引時刻より前の場合は翌日に設定
            if first_trade_datetime < last_trade_time:
                first_trade_datetime = first_trade_datetime + timedelta(days=1)
                logging.info(f"前日の最後の取引時刻({last_trade_time.strftime('%Y/%m/%d %H:%M:%S')})を考慮し、翌日の取引時刻を調整: {first_trade_datetime.strftime('%Y/%m/%d %H:%M:%S')}")
        
        # 現在時刻から次の取引時刻までの待機時間を計算
        wait_seconds = (first_trade_datetime - now).total_seconds()
        
        # デバッグ用ログ
        logging.info(f"現在時刻: {now.strftime('%Y/%m/%d %H:%M:%S')}")
        logging.info(f"翌日取引時刻: {first_trade_datetime.strftime('%Y/%m/%d %H:%M:%S')}")
        logging.info(f"待機時間: {wait_seconds}秒")
        
        if wait_seconds > 0:
            send_discord_message(f"翌日の取引開始時刻（{first_trade_datetime.strftime('%Y/%m/%d %H:%M:%S')}）まで待機します（{wait_seconds:.0f}秒）")
            time.sleep(wait_seconds)
        else:
            # 待機時間が0以下の場合（既に時刻が過ぎている場合）
            send_discord_message(f"翌日の取引時刻（{first_trade_datetime.strftime('%Y/%m/%d %H:%M:%S')}）は既に過ぎています。即座に次の取引を開始します。")
            logging.warning(f"翌日の取引時刻が既に過ぎています: {first_trade_datetime.strftime('%Y/%m/%d %H:%M:%S')}")
        
    except Exception as e:
        logging.error(f"翌日待機処理エラー: {e}")
        send_discord_message(f"翌日待機処理でエラーが発生しました: {e}")
        # エラーの場合は1時間待機
        time.sleep(3600)

def main():
    global trade_results, total_api_fee
    periodic_position_check()  # 追加: 定期ポジション監視を開始
    daily_finalize_scheduler()
    
    # 自動再起動スケジューラーを起動
    auto_restart_scheduler()
    
    # 取引数量リセットスケジューラーを起動
    daily_volume_reset_scheduler()
    
    # 自動再起動設定の通知
    if AUTO_RESTART_HOUR is not None:
        send_discord_message(f"自動取引システムを開始しました。毎日継続実行します。\n🔄 自動再起動設定: 毎日{AUTO_RESTART_HOUR}時に再起動")
    else:
        send_discord_message("自動取引システムを開始しました。毎日継続実行します。\n🔄 自動再起動: 無効（連続運転）")
    
    # 初回バックアップ実行
    try:
        backup_path = backup_config_and_data()
        if backup_path:
            send_discord_message(f"初回バックアップ完了: {backup_path}")
    except Exception as e:
        logging.error(f"初回バックアップエラー: {e}")
    
    day_count = 0
    last_health_check = 0
    last_backup = time.time()
    
    while True:
        try:
            day_count += 1
            current_date = datetime.now().strftime('%Y/%m/%d')
            send_discord_message(f"=== {current_date} の取引開始 (実行回数: {day_count}回目) ===")
            
            # メモリ使用量チェック
            memory_usage = check_memory_usage()
            logging.info(f"メモリ使用量: {memory_usage['rss']:.1f}MB")
            
            # 定期的なヘルスチェック（6時間ごと）
            current_time = time.time()
            if current_time - last_health_check > 21600:  # 6時間
                health_status = health_check()
                if not health_status['overall_health']:
                    send_discord_message("⚠️ ヘルスチェックで問題が検出されました。システムを再起動します。")
                    if not auto_restart_on_error():
                        send_discord_message("⚠️ 自動再起動に失敗しました。手動介入が必要です。")
                        break
                last_health_check = current_time
            
            # 定期的なバックアップ（24時間ごと）
            if current_time - last_backup > 86400:  # 24時間
                try:
                    backup_path = backup_config_and_data()
                    if backup_path:
                        send_discord_message(f"定期バックアップ完了: {backup_path}")
                    last_backup = current_time
                except Exception as e:
                    logging.error(f"定期バックアップエラー: {e}")
            
            # 1日の取引を実行
            success = execute_daily_trades()
            
            if not success:
                send_discord_message("取引実行に失敗しました。プログラムを終了します。")
                break
            
            # 取引結果をリセット（翌日待機前に実行）
            trade_results = []
            total_api_fee = 0
            
            # 翌日の最初の取引時刻まで待機
            wait_until_next_day()
            
        except KeyboardInterrupt:
            send_discord_message("ユーザーによる停止要求を受けました。プログラムを終了します。")
            break
        except Exception as e:
            logging.error(f"予期しないエラーが発生しました: {e}\n{traceback.format_exc()}")
            send_discord_message(f"予期しないエラーが発生しました: {e}")
            
            # 重大なエラーの場合は自動再起動を試行
            if "API" in str(e) or "Connection" in str(e):
                send_discord_message("⚠️ 重大なエラーが発生しました。自動再起動を試行します。")
                if not auto_restart_on_error():
                    send_discord_message("⚠️ 自動再起動に失敗しました。手動介入が必要です。")
                    break
            else:
                # 軽微なエラーの場合は1時間待機してから再試行
                time.sleep(3600)

# --- Discord Bot機能 ---
if DISCORD_BOT_TOKEN:
    intents = discord.Intents.default()
    intents.message_content = True  # メッセージ内容Intentを有効化
    bot = commands.Bot(command_prefix='', intents=intents, case_insensitive=True)

    @bot.event
    async def on_ready():
        """Bot起動時の処理"""
        logging.info(f'Discord Bot connected as {bot.user}')
        send_discord_message(f"🤖 Botが起動しました: {bot.user}")
        
    @bot.event
    async def on_command_error(ctx, error):
        """コマンドエラー時の処理"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ 不明なコマンドです。`command`でコマンド一覧を確認してください。")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ このコマンドを実行する権限がありません。")
        else:
            logging.error(f"Discord Bot コマンドエラー: {error}")
            await ctx.send(f"❌ コマンド実行中にエラーが発生しました: {str(error)}")

    @bot.command(name='kill')
    async def kill(ctx):
        """全ポジションを即座に決済（緊急時）"""
        global trade_results
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ このコマンドは管理者のみ実行可能です。")
            return
        await ctx.send('🚨 全通貨ペアの全ポジション決済を実行します...')
        logging.warning(f"Discord Bot: 全ポジション決済コマンド実行 by {ctx.author}")
        try:
            positions = get_all_positions()
            if not positions:
                await ctx.send('✅ 現在ポジションはありません。')
                return
            closed = []
            success_count = 0
            error_count = 0
            for pos in positions:
                try:
                    if not isinstance(pos, dict) or not all(key in pos for key in ['symbol', 'positionId', 'size', 'side', 'price']):
                        closed.append(f"❌ 無効なポジション情報: {pos}")
                        error_count += 1
                        continue
                    exit_side = 'SELL' if pos['side'] == 'BUY' else 'BUY'
                    entry_price = float(pos['price'])
                    size = float(pos['size'])
                    symbol = pos['symbol']
                    executed_price = close_position(symbol, pos['positionId'], size, exit_side)
                    profit_pips = calculate_profit_pips(entry_price, executed_price, pos['side'], symbol)
                    profit_amount = calculate_profit_amount(entry_price, executed_price, pos['side'], symbol, size)
                    closed.append(
                        f"✅ {symbol} {pos['side']} {size}lot 決済\n"
                        f"エントリー価格: {entry_price}\n"
                        f"決済価格: {executed_price}\n"
                        f"損益: {profit_pips}pips ({profit_amount}円)"
                    )
                    # trade_resultsに追加
                    trade_results.append({
                        "symbol": symbol,
                        "side": pos['side'],
                        "entry_price": entry_price,
                        "exit_price": executed_price,
                        "profit_pips": profit_pips,
                        "profit_amount": profit_amount,
                        "lot_size": size,
                        "entry_time": pos.get('openTime', ''),
                        "exit_time": datetime.now().strftime('%H:%M:%S'),
                    })
                    success_count += 1
                except Exception as e:
                    error_msg = f"❌ {pos.get('symbol', 'Unknown')} 決済失敗: {e}"
                    closed.append(error_msg)
                    error_count += 1
                    logging.error(f"ポジション決済エラー: {e}")
            result_msg = f"**決済結果**\n成功: {success_count}件, 失敗: {error_count}件\n\n"
            result_msg += '\n\n'.join(closed)
            if len(result_msg) > 2000:
                chunks = [result_msg[i:i+1900] for i in range(0, len(result_msg), 1900)]
                for i, chunk in enumerate(chunks):
                    await ctx.send(f"決済結果 (Part {i+1}/{len(chunks)}):\n{chunk}")
            else:
                await ctx.send(result_msg)
            positions_after = get_all_positions()
            if not positions_after:
                await ctx.send('✅ 全てのポジションが決済されました。')
            else:
                remaining_msg = '⚠️ 残存ポジション:\n'
                for pos in positions_after:
                    remaining_msg += f"{pos['symbol']} {pos['side']} {pos['size']}\n"
                await ctx.send(remaining_msg)
        except Exception as e:
            error_msg = f'❌ 全ポジション決済中にエラーが発生しました: {e}'
            await ctx.send(error_msg)
            logging.error(f"全ポジション決済エラー: {e}")
            send_discord_message(f"⚠️ Discord Bot 全ポジション決済エラー: {e}")

    @bot.command(name='stop')
    async def stop(ctx):
        """システムを完全停止"""
        # 権限チェック
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ このコマンドは管理者のみ実行可能です。")
            return
            
        await ctx.send('🛑 自動取引システムを停止します...')
        logging.warning(f"Discord Bot: システム停止コマンド実行 by {ctx.author}")
        send_discord_message("🛑 Discordコマンドにより自動取引システムを停止します")
        
        # 安全な停止処理
        try:
            # 残存ポジションの確認
            positions = get_all_positions()
            if positions:
                warning_msg = f"⚠️ 停止前に{len(positions)}件のポジションが残存しています。"
                await ctx.send(warning_msg)
                send_discord_message(warning_msg)
            
            # ログ出力
            logging.info("Discord Bot コマンドによりシステムを停止します")
            
            # システム停止
            os._exit(0)
        except Exception as e:
            logging.error(f"システム停止エラー: {e}")
            await ctx.send(f"❌ システム停止中にエラーが発生しました: {e}")

    @bot.command(name='position')
    async def position(ctx):
        """現在のポジション一覧表示"""
        try:
            positions = get_all_positions()
            if not positions:
                await ctx.send('📊 現在ポジションはありません。')
            else:
                msg = f"📊 **現在のポジション ({len(positions)}件)**\n"
                for i, pos in enumerate(positions, 1):
                    # 型チェックを強化
                    if isinstance(pos, dict) and all(key in pos for key in ['symbol', 'side', 'size']):
                        msg += f"{i}. {pos['symbol']} {pos['side']} {pos['size']}lot\n"
                    else:
                        msg += f"{i}. ❌ 無効なポジション情報: {pos}\n"
                
                # 長いメッセージは分割
                if len(msg) > 2000:
                    chunks = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
                    for i, chunk in enumerate(chunks):
                        await ctx.send(f"ポジション一覧 (Part {i+1}/{len(chunks)}):\n{chunk}")
                else:
                    await ctx.send(msg)
        except Exception as e:
            error_msg = f'❌ ポジション取得エラー: {e}'
            await ctx.send(error_msg)
            logging.error(f"ポジション取得エラー: {e}")

    @bot.command(name='status')
    async def status(ctx):
        """システム状態の詳細表示"""
        try:
            system_status = get_system_status()
            if system_status:
                msg = f"**🖥️ システム状態**\n"
                msg += f"💾 メモリ使用量: {system_status['memory_usage_mb']:.1f}MB ({system_status['memory_percent']:.1f}%)\n"
                msg += f"📊 アクティブポジション: {system_status['active_positions']}件\n"
                msg += f"⚡ レートリミット: {system_status['rate_limit']}回/秒\n"
                msg += f"⚠️ レートリミットエラー: {system_status['rate_limit_errors']}回\n"
                msg += f"📈 取引結果数: {system_status['trade_results_count']}件\n"
                msg += f"💰 累計API手数料: {system_status['total_api_fee']:.0f}円\n"
                
                # 自動再起動設定の表示
                if AUTO_RESTART_HOUR is not None:
                    msg += f"🔄 自動再起動: 毎日{AUTO_RESTART_HOUR}時に再起動\n"
                else:
                    msg += f"🔄 自動再起動: 無効（連続運転）\n"
                
                await ctx.send(msg)
            else:
                await ctx.send('❌ システム状態の取得に失敗しました。')
        except Exception as e:
            error_msg = f'❌ システム状態取得エラー: {e}'
            await ctx.send(error_msg)
            logging.error(f"システム状態取得エラー: {e}")

    @bot.command(name='health')
    async def health(ctx):
        """システムの健全性チェック"""
        try:
            await ctx.send('🔍 ヘルスチェックを実行中...')
            health_status = health_check()
            if health_status:
                msg = f"**🏥 ヘルスチェック結果**\n"
                msg += f"🌐 API接続: {'✅' if health_status['api_connection'] else '❌'}\n"
                msg += f"💬 Discord接続: {'✅' if health_status['discord_connection'] else '❌'}\n"
                msg += f"💿 ディスク容量: {'✅' if health_status['disk_space'] else '❌'}\n"
                msg += f"💾 メモリ使用量: {'✅' if health_status['memory_usage'] else '❌'}\n"
                msg += f"📁 ファイルアクセス: {'✅' if health_status['file_access'] else '❌'}\n"
                msg += f"🎯 全体状態: {'✅' if health_status['overall_health'] else '❌'}"
                await ctx.send(msg)
            else:
                await ctx.send('❌ ヘルスチェックの実行に失敗しました。')
        except Exception as e:
            error_msg = f'❌ ヘルスチェックエラー: {e}'
            await ctx.send(error_msg)
            logging.error(f"ヘルスチェックエラー: {e}")

    @bot.command(name='performance')
    async def performance(ctx):
        """取引パフォーマンスレポート"""
        try:
            await ctx.send('📊 パフォーマンスレポートを生成中...')
            report = get_performance_report()
            
            # 長いレポートは分割
            if len(report) > 2000:
                chunks = [report[i:i+1900] for i in range(0, len(report), 1900)]
                for i, chunk in enumerate(chunks):
                    await ctx.send(f"パフォーマンスレポート (Part {i+1}/{len(chunks)}):\n{chunk}")
            else:
                await ctx.send(report)
        except Exception as e:
            error_msg = f'❌ パフォーマンスレポート取得エラー: {e}'
            await ctx.send(error_msg)
            logging.error(f"パフォーマンスレポート取得エラー: {e}")

    @bot.command(name='backup')
    async def backup(ctx):
        """手動バックアップ実行"""
        try:
            await ctx.send('💾 バックアップを開始します...')
            backup_path = backup_config_and_data()
            if backup_path:
                await ctx.send(f'✅ バックアップが完了しました: {backup_path}')
                logging.info(f"Discord Bot: 手動バックアップ完了 by {ctx.author}")
            else:
                await ctx.send('❌ バックアップに失敗しました。')
                logging.error(f"Discord Bot: 手動バックアップ失敗 by {ctx.author}")
        except Exception as e:
            error_msg = f'❌ バックアップエラー: {e}'
            await ctx.send(error_msg)
            logging.error(f"バックアップエラー: {e}")

    @bot.command(name='restart')
    async def restart(ctx):
        """システムを再起動"""
        # 権限チェック
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ このコマンドは管理者のみ実行可能です。")
            return
            
        try:
            await ctx.send('🔄 システムを再起動します...')
            logging.warning(f"Discord Bot: システム再起動コマンド実行 by {ctx.author}")
            send_discord_message("🔄 Discordコマンドによりシステムを再起動します")
            
            # 再起動実行
            success = auto_restart_on_error()
            if success:
                await ctx.send('✅ 再起動処理を開始しました。')
            else:
                await ctx.send('❌ 再起動に失敗しました。手動介入が必要です。')
        except Exception as e:
            error_msg = f'❌ 再起動エラー: {e}'
            await ctx.send(error_msg)
            logging.error(f"再起動エラー: {e}")

    @bot.command(name='testlot')
    async def testlot(ctx):
        """ロット計算のテスト実行"""
        try:
            await ctx.send("🧮 ロット計算テストを実行中...")
            
            # 現在の証拠金残高を取得
            balance_data = get_fx_balance()
            if not balance_data or 'data' not in balance_data:
                await ctx.send("❌ 証拠金残高の取得に失敗しました")
                return
                
            if isinstance(balance_data['data'], list) and len(balance_data['data']) > 0:
                balance = float(balance_data['data'][0]['availableAmount'])
            elif isinstance(balance_data['data'], dict):
                balance = float(balance_data['data']['availableAmount'])
            else:
                await ctx.send("❌ 証拠金残高の形式が不正です")
                return
            
            # 主要通貨ペアでロット計算テスト
            symbols = ['USD_JPY', 'EUR_JPY', 'CHF_JPY', 'GBP_JPY', 'EUR_USD', 'GBP_USD', 'AUD_JPY', 'NZD_JPY', 'CAD_JPY']
            result_msg = f"💰 証拠金残高: {balance:,.0f}円\n"
            result_msg += f"⚡ レバレッジ: {LEVERAGE}倍\n"
            result_msg += f"🤖 自動ロット設定: {AUTOLOT}\n\n"
            
            for symbol in symbols:
                try:
                    # ティッカーデータ取得
                    tickers = get_tickers([symbol])
                    if not tickers or 'data' not in tickers:
                        result_msg += f"❌ {symbol}: ティッカーデータ取得失敗\n\n"
                        continue
                    
                    # レート情報取得
                    rate_data = None
                    for item in tickers['data']:
                        if item['symbol'] == symbol:
                            rate_data = item
                            break
                    
                    if not rate_data:
                        result_msg += f"❌ {symbol}: レート情報取得失敗\n\n"
                        continue
                    
                    # 買い注文のロット計算
                    buy_rate = float(rate_data['ask'])
                    buy_lot = calc_auto_lot_gmobot2(balance, symbol, 'BUY', LEVERAGE)
                    
                    # 売り注文のロット計算
                    sell_rate = float(rate_data['bid'])
                    sell_lot = calc_auto_lot_gmobot2(balance, symbol, 'SELL', LEVERAGE)
                    
                    # pip値計算
                    pip_value = 0.01 if "JPY" in symbol else 0.0001
                    
                    result_msg += f"📊 {symbol}:\n"
                    result_msg += f"  買いレート: {buy_rate:.5f} → {buy_lot:,}lot\n"
                    result_msg += f"  売りレート: {sell_rate:.5f} → {sell_lot:,}lot\n"
                    result_msg += f"  pip値: {pip_value}\n\n"
                    
                except Exception as e:
                    result_msg += f"❌ {symbol}: エラー - {str(e)}\n\n"
            
            # 長いメッセージは分割
            if len(result_msg) > 2000:
                chunks = [result_msg[i:i+1900] for i in range(0, len(result_msg), 1900)]
                for i, chunk in enumerate(chunks):
                    await ctx.send(f"ロット計算テスト結果 (Part {i+1}/{len(chunks)}):\n{chunk}")
            else:
                await ctx.send(result_msg)
            
        except Exception as e:
            await ctx.send(f"❌ ロット計算テストエラー: {e}")

    @bot.command(name='debuglot')
    async def debuglot(ctx):
        """オートロット計算の詳細デバッグ"""
        try:
            await ctx.send("🔍 オートロット詳細デバッグを実行中...")
            
            # 設定値の確認
            debug_msg = f"**設定値確認:**\n"
            debug_msg += f"• AUTOLOT: {AUTOLOT}\n"
            debug_msg += f"• LEVERAGE: {LEVERAGE}\n"
            debug_msg += f"• SPREAD_THRESHOLD: {SPREAD_THRESHOLD}\n\n"
            
            # 証拠金取得の詳細テスト
            debug_msg += f"**証拠金取得テスト:**\n"
            try:
                balance_data = get_fx_balance()
                debug_msg += f"• レスポンス型: {type(balance_data)}\n"
                
                if balance_data and 'data' in balance_data:
                    debug_msg += f"• data型: {type(balance_data['data'])}\n"
                    
                    if isinstance(balance_data['data'], list):
                        debug_msg += f"• リスト長: {len(balance_data['data'])}\n"
                        if len(balance_data['data']) > 0:
                            debug_msg += f"• 最初の要素: {balance_data['data'][0]}\n"
                            if 'availableAmount' in balance_data['data'][0]:
                                balance = float(balance_data['data'][0]['availableAmount'])
                                debug_msg += f"• 利用可能証拠金: {balance:,.0f}円\n"
                                
                                # 計算テスト
                                test_symbol = "USD_JPY"
                                debug_msg += f"\n**計算テスト ({test_symbol}):**\n"
                                debug_msg += f"• 証拠金: {balance:,.0f}円\n"
                                debug_msg += f"• レバレッジ: {LEVERAGE}倍\n"
                                
                                # ティッカーデータ取得
                                tickers = get_tickers([test_symbol])
                                if tickers and 'data' in tickers:
                                    for item in tickers['data']:
                                        if item['symbol'] == test_symbol:
                                            rate = float(item['ask'])
                                            debug_msg += f"• レート: {rate:.5f}\n"
                                            
                                            # 計算式
                                            volume = int((balance * LEVERAGE) / rate)
                                            debug_msg += f"• 計算式: int(({balance:,.0f} × {LEVERAGE}) ÷ {rate:.5f}) = {volume:,}\n"
                                            break
                    elif isinstance(balance_data['data'], dict):
                        debug_msg += f"• 辞書内容: {balance_data['data']}\n"
                        if 'availableAmount' in balance_data['data']:
                            balance = float(balance_data['data']['availableAmount'])
                            debug_msg += f"• 利用可能証拠金: {balance:,.0f}円\n"
                            
                            # 計算テスト
                            test_symbol = "USD_JPY"
                            debug_msg += f"\n**計算テスト ({test_symbol}):**\n"
                            debug_msg += f"• 証拠金: {balance:,.0f}円\n"
                            debug_msg += f"• レバレッジ: {LEVERAGE}倍\n"
                            
                            # ティッカーデータ取得
                            tickers = get_tickers([test_symbol])
                            if tickers and 'data' in tickers:
                                for item in tickers['data']:
                                    if item['symbol'] == test_symbol:
                                        rate = float(item['ask'])
                                        debug_msg += f"• レート: {rate:.5f}\n"
                                        
                                        # 計算式
                                        volume = int((balance * LEVERAGE) / rate)
                                        debug_msg += f"• 計算式: int(({balance:,.0f} × {LEVERAGE}) ÷ {rate:.5f}) = {volume:,}\n"
                                        break
                    else:
                        debug_msg += f"• エラー: 予期しないデータ型 ({type(balance_data['data'])})\n"
                else:
                    debug_msg += f"• エラー: データが不正\n"
                    
            except Exception as e:
                debug_msg += f"• エラー: {str(e)}\n"
            
            await ctx.send(debug_msg)
            
        except Exception as e:
            await ctx.send(f"❌ デバッグ実行エラー: {e}")

    @bot.command(name='command')
    async def command_list(ctx):
        """コマンド一覧と説明を表示"""
        try:
            help_msg = "**🤖 Discord Bot コマンド一覧**\n\n"
            
            help_msg += "**🔴 緊急時コマンド（管理者のみ）**\n"
            help_msg += "• `kill` - 全ポジションを即座に決済（緊急時）\n"
            help_msg += "• `stop` - システムを完全停止\n"
            help_msg += "• `restart` - システムを再起動\n\n"
            
            help_msg += "**📊 情報確認コマンド**\n"
            help_msg += "• `position` - 現在のポジション一覧表示\n"
            help_msg += "• `status` - システム状態の詳細表示\n"
            help_msg += "• `health` - システムの健全性チェック\n"
            help_msg += "• `performance` - 取引パフォーマンスレポート\n\n"
            
            help_msg += "**💾 データ管理コマンド**\n"
            help_msg += "• `backup` - 手動バックアップ実行\n"
            help_msg += "• `testlot` - ロット計算テスト実行\n"
            help_msg += "• `debuglot` - オートロット詳細デバッグ\n\n"
            
            help_msg += "**ℹ️ ヘルプコマンド**\n"
            help_msg += "• `command` - このコマンド一覧を表示\n\n"
            
            help_msg += "**📝 使用方法**\n"
            help_msg += "• コマンドは先頭に何も付けずに送信（例: `status`）\n"
            help_msg += "• 大文字・小文字は区別しません（`KILL`でも`kill`でもOK）\n"
            help_msg += "• 緊急時は `kill` コマンドで全ポジション決済可能\n"
            help_msg += "• 管理者コマンドはサーバー管理者のみ実行可能\n"
            
            await ctx.send(help_msg)
            
        except Exception as e:
            error_msg = f"❌ コマンド一覧表示エラー: {e}"
            await ctx.send(error_msg)
            logging.error(f"コマンド一覧表示エラー: {e}")

    def run_bot():
        """Discord Botを起動（エラーハンドリング強化）"""
        if not DISCORD_BOT_TOKEN or not isinstance(DISCORD_BOT_TOKEN, str) or not DISCORD_BOT_TOKEN.strip():
            logging.warning("Discord Bot Tokenが設定されていません")
            return
            
        try:
            logging.info("Discord Botを起動中...")
            bot.run(DISCORD_BOT_TOKEN)
        except discord.LoginFailure:
            logging.error("Discord Bot Tokenが無効です")
            send_discord_message("❌ Discord Bot Tokenが無効です")
        except discord.HTTPException as e:
            logging.error(f"Discord Bot HTTPエラー: {e}")
            send_discord_message(f"❌ Discord Bot HTTPエラー: {e}")
        except Exception as e:
            logging.error(f"Discord Bot起動エラー: {e}")
            send_discord_message(f"❌ Discord Bot起動エラー: {e}")
    
    # Bot起動をスレッドで実行
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logging.info("Discord Bot起動スレッドを開始しました")

def auto_restart_on_error():
    """重大なエラー時に自動再起動"""
    global restart_count, last_restart_time
    
    current_time = time.time()
    
    # クールダウン期間チェック
    if current_time - last_restart_time < restart_cooldown:
        logging.warning("再起動クールダウン期間中です")
        return False
    
    # 最大再起動回数チェック
    if restart_count >= max_restarts:
        logging.error(f"最大再起動回数({max_restarts}回)に達しました。手動介入が必要です。")
        send_discord_message(f"⚠️ 最大再起動回数({max_restarts}回)に達しました。手動介入が必要です。")
        return False
    
    restart_count += 1
    last_restart_time = current_time
    
    logging.warning(f"自動再起動を実行します (回数: {restart_count}/{max_restarts})")
    send_discord_message(f"⚠️ 自動再起動を実行します (回数: {restart_count}/{max_restarts})")
    
    # 再起動前のクリーンアップ
    try:
        # 残っているポジションを決済
        positions = get_all_positions()
        if positions:
            for pos in positions:
                try:
                    exit_side = "SELL" if pos['side'] == "BUY" else "BUY"
                    close_position(pos['symbol'], pos['positionId'], pos['size'], exit_side)
                    logging.info(f"再起動前のポジション決済: {pos['symbol']} {pos['side']}")
                except Exception as e:
                    logging.error(f"再起動前のポジション決済失敗: {e}")
    except Exception as e:
        logging.error(f"再起動前のクリーンアップエラー: {e}")
    
    # プログラム再起動
    try:
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        logging.error(f"再起動実行エラー: {e}")
        return False
    
    return True

def collect_metrics():
    """取引パフォーマンスの統計を収集"""
    global performance_metrics
    
    # 取引結果から統計を計算
    if trade_results:
        total_profit_pips = sum(trade['profit_pips'] for trade in trade_results)
        total_profit_amount = sum(trade.get('profit_amount', 0) for trade in trade_results)
        successful_trades = len([t for t in trade_results if t['profit_pips'] > 0])
        failed_trades = len([t for t in trade_results if t['profit_pips'] <= 0])
        
        performance_metrics.update({
            'total_trades': len(trade_results),
            'successful_trades': successful_trades,
            'failed_trades': failed_trades,
            'total_profit_pips': total_profit_pips,
            'total_profit_amount': total_profit_amount,
            'average_profit_pips': total_profit_pips / len(trade_results) if trade_results else 0,
            'win_rate': (successful_trades / len(trade_results) * 100) if trade_results else 0
        })
        
        # 最大ドローダウン計算
        running_profit_pips = 0
        running_profit_amount = 0
        max_profit_pips = 0
        max_profit_amount = 0
        max_drawdown_pips = 0
        max_drawdown_amount = 0
        
        for trade in trade_results:
            # 累積利益を更新
            running_profit_pips += trade['profit_pips']
            running_profit_amount += trade.get('profit_amount', 0)
            
            # ピーク利益を更新
            if running_profit_pips > max_profit_pips:
                max_profit_pips = running_profit_pips
            
            if running_profit_amount > max_profit_amount:
                max_profit_amount = running_profit_amount
            
            # ドローダウンを計算
            drawdown_pips = max_profit_pips - running_profit_pips
            drawdown_amount = max_profit_amount - running_profit_amount
            
            # 最大ドローダウンを更新
            if drawdown_pips > max_drawdown_pips:
                max_drawdown_pips = drawdown_pips
            
            if drawdown_amount > max_drawdown_amount:
                max_drawdown_amount = drawdown_amount
        
        performance_metrics.update({
            'max_drawdown_pips': max_drawdown_pips,
            'max_drawdown_amount': max_drawdown_amount
        })
    
    return performance_metrics

def get_performance_report():
    """パフォーマンスレポートを生成"""
    metrics = collect_metrics()
    uptime = datetime.now() - metrics['start_time']
    # 口座残高取得
    try:
        balance_data = get_fx_balance()
        data = balance_data.get('data')
        if isinstance(data, list) and len(data) > 0:
            balance_amount = float(data[0].get('balance', 0))
        elif isinstance(data, dict):
            balance_amount = float(data.get('balance', 0))
        else:
            balance_amount = 0
    except Exception as e:
        logging.error(f"パフォーマンスレポート用の口座残高取得エラー: {e}")
        balance_amount = 0
    report = f"**パフォーマンスレポート**\n"
    report += f"稼働時間: {uptime.days}日 {uptime.seconds//3600}時間 {(uptime.seconds%3600)//60}分\n"
    report += f"総取引数: {metrics['total_trades']}件\n"
    report += f"勝利数: {metrics['successful_trades']}件\n"
    report += f"敗北数: {metrics['failed_trades']}件\n"
    report += f"勝率: {metrics['win_rate']:.1f}%\n"
    report += f"総損益pips: {'+' if metrics['total_profit_pips'] >= 0 else ''}{metrics['total_profit_pips']:.1f}\n"
    report += f"総損益金額: {'+' if metrics['total_profit_amount'] >= 0 else ''}{metrics['total_profit_amount']:.0f}円\n"
    report += f"FX口座残高: {balance_amount:.0f}円\n"
    report += f"平均損益pips: {'+' if metrics['average_profit_pips'] >= 0 else ''}{metrics['average_profit_pips']:.1f}\n"
    report += f"最大ドローダウンpips: -{metrics['max_drawdown_pips']:.1f}\n"
    report += f"最大ドローダウン金額: -{metrics['max_drawdown_amount']:.0f}円\n"
    report += f"API呼び出し数: {metrics['api_calls']}回\n"
    report += f"APIエラー数: {metrics['api_errors']}回\n"
    report += f"API成功率: {((metrics['api_calls'] - metrics['api_errors']) / metrics['api_calls'] * 100):.1f}%" if metrics['api_calls'] > 0 else "API成功率: N/A"
    return report

def backup_config_and_data():
    """設定ファイルとデータの自動バックアップ"""
    try:
        # バックアップディレクトリ作成
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # 現在時刻でバックアップディレクトリ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'backup_{timestamp}')
        os.makedirs(backup_path)
        
        # バックアップ対象ファイル
        files_to_backup = [
            'config.json',
            'trades.csv',
            'main.py'
        ]
        
        # 日次結果ファイルもバックアップ
        daily_results_dir = 'daily_results'
        if os.path.exists(daily_results_dir):
            for file in os.listdir(daily_results_dir):
                if file.startswith('daily_results_') and file.endswith('.csv'):
                    files_to_backup.append(os.path.join(daily_results_dir, file))
        
        # ファイルコピー
        import shutil
        for file in files_to_backup:
            if os.path.exists(file):
                shutil.copy2(file, backup_path)
                logging.info(f"バックアップ完了: {file}")
        
        # ログファイルもバックアップ
        if os.path.exists('logs'):
            shutil.copytree('logs', os.path.join(backup_path, 'logs'))
            logging.info("ログファイルバックアップ完了")
        
        # daily_resultsディレクトリもバックアップ
        if os.path.exists('daily_results'):
            shutil.copytree('daily_results', os.path.join(backup_path, 'daily_results'))
            logging.info("daily_resultsディレクトリバックアップ完了")
        
        # 古いバックアップを削除（30日以上前）
        cleanup_old_backups(backup_dir, days=30)
        
        logging.info(f"バックアップ完了: {backup_path}")
        return backup_path
        
    except Exception as e:
        logging.error(f"バックアップエラー: {e}")
        return None

def cleanup_old_backups(backup_dir, days=30):
    """古いバックアップを削除"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            if os.path.isdir(item_path):
                # ディレクトリ名から日付を抽出
                if item.startswith('backup_'):
                    try:
                        date_str = item[7:]  # 'backup_' を除去
                        backup_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                        if backup_date < cutoff_date:
                            import shutil
                            shutil.rmtree(item_path)
                            logging.info(f"古いバックアップを削除: {item}")
                    except ValueError:
                        continue
    except Exception as e:
        logging.error(f"バックアップクリーンアップエラー: {e}")

def health_check():
    """システムの健全性をチェック"""
    health_status = {
        'api_connection': False,
        'discord_connection': False,
        'disk_space': True,
        'memory_usage': True,
        'file_access': True,
        'overall_health': False
    }
    
    try:
        # API接続テスト
        try:
            balance_data = get_fx_balance()
            if balance_data and 'data' in balance_data:
                health_status['api_connection'] = True
                logging.info("API接続テスト: 成功")
            else:
                logging.warning("API接続テスト: 失敗 - データ形式が不正")
        except Exception as e:
            logging.error(f"API接続テスト: 失敗 - {e}")
        
        # Discord接続テスト
        try:
            if webhook:
                webhook.send("ヘルスチェック: システムは正常に動作しています")
                health_status['discord_connection'] = True
                logging.info("Discord接続テスト: 成功")
            else:
                logging.warning("Discord接続テスト: 失敗 - Webhookが初期化されていません")
        except Exception as e:
            logging.error(f"Discord接続テスト: 失敗 - {e}")
        
        # ディスク容量チェック
        try:
            disk_usage = psutil.disk_usage('.')
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 1.0:  # 1GB未満の場合
                health_status['disk_space'] = False
                logging.warning(f"ディスク容量不足: {free_gb:.2f}GB")
            else:
                logging.info(f"ディスク容量: {free_gb:.2f}GB")
        except Exception as e:
            logging.error(f"ディスク容量チェック: 失敗 - {e}")
            health_status['disk_space'] = False
        
        # メモリ使用量チェック
        try:
            memory_usage = get_memory_usage()
            if memory_usage['rss'] > 500:  # 500MB超の場合
                health_status['memory_usage'] = False
                logging.warning(f"メモリ使用量が高すぎます: {memory_usage['rss']:.1f}MB")
            else:
                logging.info(f"メモリ使用量: {memory_usage['rss']:.1f}MB")
        except Exception as e:
            logging.error(f"メモリ使用量チェック: 失敗 - {e}")
            health_status['memory_usage'] = False
        
        # ファイルアクセスチェック
        try:
            required_files = ['config.json', 'trades.csv']
            for file in required_files:
                if not os.path.exists(file):
                    health_status['file_access'] = False
                    logging.error(f"必須ファイルが見つかりません: {file}")
                    break
            
            # daily_resultsディレクトリの存在チェック
            if not os.path.exists('daily_results'):
                try:
                    os.makedirs('daily_results')
                    logging.info("daily_resultsディレクトリを作成しました")
                except Exception as e:
                    health_status['file_access'] = False
                    logging.error(f"daily_resultsディレクトリの作成に失敗: {e}")
            
            if health_status['file_access']:
                logging.info("ファイルアクセステスト: 成功")
        except Exception as e:
            logging.error(f"ファイルアクセステスト: 失敗 - {e}")
            health_status['file_access'] = False
        
        # 全体の健全性判定
        health_status['overall_health'] = all([
            health_status['api_connection'],
            health_status['discord_connection'],
            health_status['disk_space'],
            health_status['memory_usage'],
            health_status['file_access']
        ])
        
        return health_status
        
    except Exception as e:
        logging.error(f"ヘルスチェック全体エラー: {e}")
        health_status['overall_health'] = False
        return health_status

def get_system_status():
    """システム状態を取得"""
    try:
        memory_usage = get_memory_usage()
        positions = get_all_positions()
        
        status = {
            'memory_usage_mb': memory_usage['rss'],
            'memory_percent': memory_usage['percent'],
            'active_positions': len(positions),
            'rate_limit': current_rate_limit,
            'rate_limit_errors': rate_limit_errors,
            'trade_results_count': len(trade_results),
            'total_api_fee': total_api_fee
        }
        return status
    except Exception as e:
        logging.error(f"システム状態取得エラー: {e}")
        return None

def test_lot_calculation():
    """
    ロット計算のテスト関数
    """
    try:
        print("=== ロット計算テスト開始 ===")
        
        # 証拠金取得テスト
        print("1. 証拠金取得テスト")
        balance_data = get_fx_balance()
        print(f"証拠金データ: {balance_data}")
        
        if balance_data and 'data' in balance_data and balance_data['data']:
            if isinstance(balance_data['data'], list) and len(balance_data['data']) > 0:
                balance = float(balance_data['data'][0]['availableAmount'])
            elif isinstance(balance_data['data'], dict):
                balance = float(balance_data['data']['availableAmount'])
            else:
                print("証拠金データの形式が不正です")
                return
            
            print(f"利用可能証拠金: {balance}円")
            
            # 各種通貨ペアでのロット計算テスト
            test_pairs = ["USD_JPY", "EUR_USD", "GBP_JPY", "CAD_JPY", "CHF_JPY", "GBP_AUD"]
            test_leverage = LEVERAGE
            
            for pair in test_pairs:
                print(f"\n2. {pair}でのロット計算テスト")
                try:
                    # 買い注文のテスト
                    buy_lot = calc_auto_lot_gmobot2(balance, pair, "BUY", test_leverage)
                    print(f"  {pair} BUY: {buy_lot}ロット")
                    
                    # 売り注文のテスト
                    sell_lot = calc_auto_lot_gmobot2(balance, pair, "SELL", test_leverage)
                    print(f"  {pair} SELL: {sell_lot}ロット")
                    
                except Exception as e:
                    print(f"  {pair}での計算エラー: {e}")
        
        print("\n=== ロット計算テスト完了 ===")
        
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        logging.error(f"ロット計算テストエラー: {e}")

def test_auto_lot_debug():
    """
    オートロット計算の詳細デバッグ関数
    """
    try:
        print("=== オートロット詳細デバッグ開始 ===")
        
        # 設定値の確認
        print(f"現在の設定:")
        print(f"  AUTOLOT: {AUTOLOT}")
        print(f"  LEVERAGE: {LEVERAGE}")
        print(f"  SPREAD_THRESHOLD: {SPREAD_THRESHOLD}")
        
        # 証拠金取得の詳細テスト
        print(f"\n証拠金取得テスト:")
        balance_data = get_fx_balance()
        print(f"  レスポンス型: {type(balance_data)}")
        print(f"  レスポンス内容: {balance_data}")
        
        if balance_data and 'data' in balance_data:
            print(f"  data型: {type(balance_data['data'])}")
            print(f"  data内容: {balance_data['data']}")
            
            if isinstance(balance_data['data'], list):
                print(f"  リスト長: {len(balance_data['data'])}")
                if len(balance_data['data']) > 0:
                    print(f"  最初の要素: {balance_data['data'][0]}")
                    if 'availableAmount' in balance_data['data'][0]:
                        balance = float(balance_data['data'][0]['availableAmount'])
                        print(f"  利用可能証拠金: {balance}円")
                        
                        # 計算テスト
                        test_symbol = "USD_JPY"
                        test_side = "BUY"
                        
                        print(f"\n計算テスト ({test_symbol} {test_side}):")
                        print(f"  証拠金: {balance}")
                        print(f"  レバレッジ: {LEVERAGE}")
                        
                        # ティッカーデータ取得
                        tickers = get_tickers([test_symbol])
                        print(f"  ティッカーデータ: {tickers}")
                        
                        if tickers and 'data' in tickers:
                            for item in tickers['data']:
                                if item['symbol'] == test_symbol:
                                    rate = float(item['ask']) if test_side == "BUY" else float(item['bid'])
                                    print(f"  レート: {rate}")
                                    
                                    # 計算式
                                    volume = int((balance * LEVERAGE) / rate)
                                    print(f"  計算式: int(({balance} * {LEVERAGE}) / {rate}) = {volume}")
                                    break
        
        print("\n=== オートロット詳細デバッグ完了 ===")
        
    except Exception as e:
        print(f"デバッグ実行エラー: {e}")
        logging.error(f"オートロットデバッグエラー: {e}")

def get_all_positions():
    timestamp = generate_timestamp()
    method = 'GET'
    path = '/v1/openPositions'
    url = 'https://forex-api.coin.z.com/private' + path
    headers = {
        "API-KEY": GMO_API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": generate_signature(timestamp, method, path)
    }
    res = retry_request(method, url, headers)
    if isinstance(res, dict) and 'data' in res and 'list' in res['data']:
        return res['data']['list']
    return []

def load_trades_schedule():
    """
    trades.csvからエントリー・決済時刻のリストを取得
    戻り値: [(entry_datetime, exit_datetime), ...]
    """
    schedule = []
    try:
        with open('trades.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            now = datetime.now()
            for row in reader:
                if len(row) >= 5 and row[3].strip() and row[4].strip():
                    try:
                        entry_time = datetime.strptime(row[3].strip(), '%H:%M:%S').replace(year=now.year, month=now.month, day=now.day)
                        exit_time = datetime.strptime(row[4].strip(), '%H:%M:%S').replace(year=now.year, month=now.month, day=now.day)
                        
                        # 日を跨ぐ取引の場合、現在時刻を考慮して日付を調整
                        if exit_time <= entry_time:
                            exit_time += timedelta(days=1)
                            # 現在時刻が0:00-6:00の範囲で、エントリー時刻も0:00-6:00の場合は前日として扱う
                            if (now.hour < 6 and entry_time.hour < 6):
                                entry_time -= timedelta(days=1)
                                exit_time -= timedelta(days=1)
                            # さらに、現在時刻が決済時刻を過ぎていない場合も前日として扱う
                            elif now.hour < exit_time.hour:
                                entry_time -= timedelta(days=1)
                                exit_time -= timedelta(days=1)
                        
                        schedule.append((entry_time, exit_time))
                    except Exception:
                        continue
    except Exception as e:
        logging.error(f"trades.csvスケジュール取得エラー: {e}")
    return schedule


def is_in_trades_schedule(now, schedule):
    """
    現在時刻がtrades.csvのいずれかのエントリー～決済時間内か判定
    """
    for entry, exit in schedule:
        if entry <= now <= exit:
            return True
    return False


def force_kill_all_positions_and_notify():
    """
    全ポジションを強制決済し、損益情報をdiscord通知
    """
    positions = get_all_positions()
    if not positions:
        return
    total_pips = 0
    total_amount = 0
    msg = "🚨 強制決済（kill）を実行しました\n"
    for pos in positions:
        try:
            entry_price = float(pos.get('price'))
            size = float(pos.get('size'))
            symbol = pos.get('symbol')
            side = pos.get('side')
            # 現在価格取得
            tickers = get_tickers([symbol])
            if not tickers or 'data' not in tickers:
                continue
            rate_data = None
            for item in tickers['data']:
                if item['symbol'] == symbol:
                    rate_data = item
                    break
            if not rate_data:
                continue
            current_price = float(rate_data['bid']) if side == 'BUY' else float(rate_data['ask'])
            # 損益計算
            profit_pips = calculate_profit_pips(entry_price, current_price, side, symbol)
            profit_amount = calculate_profit_amount(entry_price, current_price, side, symbol, size)
            total_pips += profit_pips
            total_amount += profit_amount
            # 決済
            exit_side = 'SELL' if side == 'BUY' else 'BUY'
            close_position(symbol, pos['positionId'], size, exit_side)
            msg += f"{symbol} {side} {size}lot: {profit_pips:.1f}pips, {profit_amount:.0f}円\n"
        except Exception as e:
            logging.error(f"強制決済エラー: {e}\n{traceback.format_exc()}")
    msg += f"\n合計損益: {total_pips:.1f}pips, {total_amount:.0f}円"
    send_discord_message(msg)


def periodic_position_check():
    """
    指定分ごとにposition監視。trades.csvの時間外でポジションがあればkill＆discord通知。
    """
    def loop():
        while True:
            try:
                now = datetime.now()
                schedule = load_trades_schedule()
                positions = get_all_positions()
                # trades.csvの時間外でポジションが存在する場合のみkill
                if positions and not is_in_trades_schedule(now, schedule):
                    force_kill_all_positions_and_notify()
                # 通常監視時はdiscord通知しない
            except Exception as e:
                logging.error(f"定期ポジション監視エラー: {e}\n{traceback.format_exc()}")
            time.sleep(POSITION_CHECK_INTERVAL_MINUTES * 60)
    t = threading.Thread(target=loop, daemon=True)
    t.start()

# main()の最初でperiodic_position_check()を呼び出す
# ... existing code ...

if __name__ == '__main__':
    main()