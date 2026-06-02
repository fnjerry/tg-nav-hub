import sqlite3
from datetime import datetime

c = sqlite3.connect("data/nav.db")
count = c.execute("SELECT COUNT(*) FROM link").fetchone()[0]
min_at, max_at = c.execute("SELECT MIN(created_at), MAX(created_at) FROM link").fetchone()
n_today = c.execute(
    "SELECT COUNT(*) FROM link WHERE date(created_at) = date('now', 'localtime')"
).fetchone()[0]
cursors = c.execute("SELECT channel_username, last_message_id FROM channelcursor").fetchall()
c.close()

print(f"total_links={count}")
print(f"first_created={min_at}")
print(f"last_created={max_at}")
print(f"added_today_local={n_today}")
print(f"today_local={datetime.now().date().isoformat()}")
print("cursors=", cursors)
