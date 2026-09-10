print("🚀 DEBUG: STEEM ANALIZ BOTU BASLADI!")

import os
import time
import json
import base64
import requests
import pandas as pd
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from beem import Steem
from beembase.operations import Comment
from beem.transactionbuilder import TransactionBuilder

# --- AYARLAR ---
STEEM_NODE = "https://api.justyy.com"
USERNAME = os.getenv("STEEM_USERNAME")
POSTING_KEY = os.getenv("STEEM_POSTING_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")

MAIN_TAG = "steem"
TAGS = ["steem", "crypto", "trading", "chart", "technicalanalysis"]
CHART_FILENAME = f"steem_chart_{time.strftime('%Y-%m-%d')}.png"

def get_steem_data():
    """CoinGecko'dan STEEM/USD saatlik verisini çeker"""
    url = "https://api.coingecko.com/api/v3/coins/steem/ohlc"
    params = {"vs_currency": "usd", "days": 7}
    
    try:
        response = requests.get(url, params=params, timeout=10).json()
        if isinstance(response, dict) and "error" in response:
            print(f"❌ CoinGecko API Hatası: {response['error']}")
            return None
        if not response or len(response) < 20:
            print(" CoinGecko'dan yeterli veri alınamadı.")
            return None
            
        df = pd.DataFrame(response, columns=['time', 'open', 'high', 'low', 'close'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.set_index('time', inplace=True)
        print(f"✅ {len(df)} satır veri başarıyla çekildi.")
        return df
    except Exception as e:
        print(f"❌ Veri çekme hatası: {e}")
        return None

def calculate_indicators(df):
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    df['SMA20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
    return df

def generate_chart(df):
    plot_df = df.tail(24)
    if plot_df.empty:
        print("❌ Çizilecek veri yok!")
        return False
    
    mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', gridcolor='#2d2d2d', facecolor='#121212', edgecolor='#121212')
    
    mpf.plot(plot_df, type='candle', style=s, volume=False, 
             title='STEEM/USD 24H Chart', 
             savefig=CHART_FILENAME, figsize=(10, 6))
    print(f"✅ Grafik çizildi: {CHART_FILENAME}")
    return True

def upload_to_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("❌ GitHub yükleme için TOKEN veya REPO bilgisi eksik.")
        return None
        
    try:
        with open(CHART_FILENAME, "rb") as f:
            content = base64.b64encode(f.read()).decode('utf-8')
            
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CHART_FILENAME}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        check_response = requests.get(url, headers=headers)
        data = {
            "message": "chore: update daily steem analysis chart",
            "content": content,
            "branch": "main"
        }
        
        if check_response.status_code == 200:
            data["sha"] = check_response.json()["sha"]
            
        put_response = requests.put(url, json=data, headers=headers)
        
        if put_response.status_code in [200, 201]:
            image_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{CHART_FILENAME}"
            print(f"✅ Resim GitHub'a yüklendi: {image_url}")
            return image_url
        else:
            print(f"❌ GitHub API Hatası: {put_response.status_code} - {put_response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Resim yükleme hatası: {e}")
        return None

def generate_text(current_price, rsi, sma, support, resistance, image_url):
    rsi_status = "oversold" if rsi < 30 else ("overbought" if rsi > 70 else "neutral")
    trend_status = "bullish" if current_price > sma else "bearish"
    
    image_md = f"![STEEM 24h Chart]({image_url})" if image_url else "*(Chart image upload failed)*"
    
    text = f"""# STEEM/USD 24 Hour Market Update

Hello Steem friends.

Here is the daily technical look at STEEM. I pulled the 1-hour chart data from CoinGecko to see what the buyers and sellers are doing today.

{image_md}

### Current Price Action
STEEM is trading at ${current_price:.4f}. The 24-hour trend shows clear momentum in the market.

### Technical Indicators
The 14-period RSI is at {rsi:.2f}. This level tells us the asset is currently in the {rsi_status} zone. 

The 20-period Simple Moving Average is at ${sma:.4f}. Price is currently {trend_status} against this line. This usually means the short-term trend is {trend_status}.

### Key Levels to Watch
Support is sitting around ${support:.4f}. Resistance is near ${resistance:.4f}. 

What do you think about the chart today? Let me know in the comments.

#steem #crypto #trading #chart
"""
    return f"STEEM/USD 24H Technical Analysis - {time.strftime('%Y-%m-%d')}", text

def publish_post(title, body):
    try:
        steem = Steem(node=STEEM_NODE, nobroadcast=False)
        permlink = f"steem-analysis-{time.strftime('%Y-%m-%d')}"
        json_metadata = json.dumps({"tags": TAGS, "app": "steem-analysis-bot/1.0"})
        
        print(" Publishing to Steem...")
        
        op = Comment(
            parent_author="",
            parent_permlink=MAIN_TAG,
            author=USERNAME,
            permlink=permlink,
            title=title,
            body=body,
            json_metadata=json_metadata
        )
        
        tx = TransactionBuilder(blockchain_instance=steem)
        tx.appendOps(op)
        tx.appendWif(POSTING_KEY)
        tx.sign()
        response = tx.broadcast()
        
        if response and isinstance(response, dict) and "signatures" in response:
            print(f"✅ SUCCESSFULLY PUBLISHED!")
        else:
            print(f"⚠️ Blockchain yanıtı alındı.")
            
    except Exception as e:
        print(f"❌ Publishing Error: {e}")

def main():
    print("=" * 60)
    print("🐝 Steem Analysis Bot Starting...")
    print("=" * 60)
    
    if not USERNAME or not POSTING_KEY:
        print("❌ ERROR: STEEM_USERNAME or STEEM_POSTING_KEY is missing!")
        return
    
    print("📡 Fetching CoinGecko Data...")
    df = get_steem_data()
    if df is None or df.empty:
        print("❌ Veri alınamadı, bot durduruldu.")
        return
        
    print(" Calculating Indicators...")
    df = calculate_indicators(df)
    
    print(" Generating Chart...")
    if not generate_chart(df):
        print("❌ Grafik oluşturulamadı, bot durduruldu.")
        return
    
    current_price = df['close'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    sma = df['SMA20'].iloc[-1]
    support = df['low'].tail(24).min()
    resistance = df['high'].tail(24).max()
    
    print(f"   Price: {current_price}, RSI: {rsi:.2f}, SMA: {sma:.4f}")
    
    print(" Uploading Image to GitHub...")
    image_url = upload_to_github()
    
    print("📝 Generating Text...")
    title, body = generate_text(current_price, rsi, sma, support, resistance, image_url)
    
    print(" Publishing...")
    publish_post(title, body)
    print("=" * 60)
    print("✅ Bot finished successfully!")

if __name__ == "__main__":
    main()
