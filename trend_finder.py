"""
trend_finder.py
----------------
Turkiye'de o an trend olan YouTube videolarini cekip Telegram'a
icerik fikri olarak listeleyen bot.

ONEMLI: Bu bot "bu konuda icerik yaparsan kesin kazanirsin" demiyor.
Sadece su an gercekten cok izlenen konulari gosteriyor - ilham/veri
kaynagi olarak kullan, kesin gelir garantisi degildir.

YouTube Data API v3 (resmi, ucretsiz, guvenilir) kullanir.
Google Trends gibi scraping'e dayali kaynaklar yerine bunu tercih
ettim cunku onlar bulut sunuculardan (GitHub Actions gibi) sik sik
engellenebiliyor (Binance'te yasadigimiz sorunun ayni turu).

Ortam degiskenleri:
    YOUTUBE_API_KEY                        (zorunlu)
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID    (zorunlu)
    REGION_CODE                            (opsiyonel, varsayilan: TR)
    MAX_RESULTS                            (opsiyonel, varsayilan: 10)
"""

import os
import sys

import requests

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
REGION_CODE = os.getenv("REGION_CODE", "TR")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))

# Kabaca "ticari/parasal ilgi" tasiyabilecek kategoriler icin YouTube
# kategori ID'leri (bilgi amacli isaretleme - kesinlik iddia etmez).
CATEGORY_NAMES = {
    "1": "Film ve Animasyon", "2": "Otomobil", "10": "Muzik",
    "15": "Evcil Hayvanlar", "17": "Spor", "19": "Seyahat",
    "20": "Oyun", "22": "Kisiler ve Bloglar", "23": "Komedi",
    "24": "Eglence", "25": "Haber ve Politika", "26": "Nasil Yapilir ve Stil",
    "27": "Egitim", "28": "Bilim ve Teknoloji",
}


def send_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("UYARI: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID tanimli degil, mesaj gonderilemedi.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Telegram gonderim hatasi: {resp.status_code} {resp.text}")


def fetch_trending_videos(region: str, max_results: int) -> list:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY tanimli degil.")

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube API hatasi {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    videos = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        videos.append({
            "title": snippet.get("title", "?"),
            "channel": snippet.get("channelTitle", "?"),
            "category": CATEGORY_NAMES.get(snippet.get("categoryId", ""), "Diger"),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
            "video_id": item.get("id", ""),
        })
    return videos


def format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def build_message(videos: list, region: str) -> str:
    lines = [f"\U0001F4C8 {region} Trend Videolar - Icerik Fikirleri\n"]
    for i, v in enumerate(videos, 1):
        lines.append(
            f"{i}. {v['title']}\n"
            f"   {v['channel']} | {v['category']}\n"
            f"   \U0001F441 {format_number(v['views'])} goruntulenme"
            + (f" | \U0001F44D {format_number(v['likes'])}" if v["likes"] is not None else "")
        )
    lines.append(
        "\n(Bunlar su an gercekten cok izlenen videolar - ilham kaynagi "
        "olarak kullan. Bir konunun trend olmasi, ayni konuda ureteceğin "
        "icerigin de kazanc getirecegi anlamina gelmez.)"
    )
    return "\n".join(lines)


def main():
    try:
        videos = fetch_trending_videos(REGION_CODE, MAX_RESULTS)
    except Exception as e:
        print(f"HATA: Trend videolar cekilemedi -> {e}")
        sys.exit(1)

    if not videos:
        print("HATA: Hic video donmedi.")
        sys.exit(1)

    for v in videos:
        print(f"{v['views']:>10}  {v['title'][:60]}")

    message = build_message(videos, REGION_CODE)
    send_telegram(message)
    print(f"\n{len(videos)} video Telegram'a gonderildi.")


if __name__ == "__main__":
    main()
