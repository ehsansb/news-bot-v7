import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from scraper_engine import fetch_rss_entries

# دریافت آدرس دیتابیس از تنظیمات امنیتی
DB_URI = os.getenv("DB_URI")

def get_db_connection():
    return psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)

def main():
    try:
        if not DB_URI:
            print("❌ Error: DB_URI is missing.")
            return

        conn = get_db_connection()
        cur = conn.cursor()
        
        # دریافت کانال‌های فعال
        cur.execute("SELECT * FROM channels WHERE active = TRUE")
        channels = cur.fetchall()
        print(f"🔄 Found {len(channels)} active channels.")

        for channel in channels:
            print(f"Checking: {channel['name']}")
            try:
                # خواندن تنظیمات RSS
                rss_config = channel.get('rss_config', [])
                if rss_config:
                    # اگر فرمت جیسون بود تبدیل کن
                    if isinstance(rss_config, str): rss_config = json.loads(rss_config)
                    
                    for src in rss_config:
                        url = src.get('url')
                        if not url: continue
                        
                        entries = fetch_rss_entries(url)
                        for entry in entries:
                            link = entry.link
                            title = entry.title
                            # ذخیره در صف (اگر تکراری نباشد)
                            cur.execute("""
                                INSERT INTO news_queue (source_url, title, channel_ref_id)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (source_url) DO NOTHING
                            """, (link, title, channel['id']))
                conn.commit()
            except Exception as e:
                print(f"⚠️ Error in channel {channel['name']}: {e}")
                conn.rollback()

        print("✅ Cycle finished.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()
