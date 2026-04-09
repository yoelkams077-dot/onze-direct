"""
fetch_news.py
Récupère les actus foot + scores du jour et génère articles.json
Lancé automatiquement chaque matin par GitHub Actions.
"""

import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import re

RAPIDAPI_KEY = "62a185bedcmshea0bdc201e1388fp1abfe2jsn5d8c4348a9fa"

SOURCES = [
    {"id": "lequipe",  "name": "L'Équipe",     "color": "#FFD700", "url": "https://www.lequipe.fr/rss/actu_rss_Football.xml"},
    {"id": "rmc",      "name": "RMC Sport",    "color": "#e05252", "url": "https://rmcsport.bfmtv.com/rss/football/"},
    {"id": "sofoot",   "name": "So Foot",      "color": "#9b7fe8", "url": "https://www.sofoot.com/feed"},
    {"id": "mercato",  "name": "Foot Mercato", "color": "#3dbd72", "url": "https://www.footmercato.net/feed"},
    {"id": "goal",     "name": "Goal.com",     "color": "#c9a227", "url": "https://www.goal.com/feeds/fr/news"},
]

LEAGUES = [
    {"id": 61,  "name": "Ligue 1"},
    {"id": 39,  "name": "Premier League"},
    {"id": 140, "name": "Liga"},
    {"id": 2,   "name": "Champions League"},
    {"id": 78,  "name": "Bundesliga"},
    {"id": 135, "name": "Serie A"},
]

def strip_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:220]

def get_cat(title):
    t = title.lower()
    if any(w in t for w in ['transfert', 'mercato', 'recrut', 'signe', 'négocie', 'deal']):
        return 'Transfert'
    if any(w in t for w in ['champions league', 'ligue des champions', 'ucl']):
        return 'Champions League'
    if 'ligue 1' in t:
        return 'Ligue 1'
    if any(w in t for w in ['premier league']):
        return 'Premier League'
    if any(w in t for w in [' liga', 'laliga', 'espagne']):
        return 'Liga'
    if any(w in t for w in ['serie a', 'italie']):
        return 'Serie A'
    if any(w in t for w in ['équipe de france', 'bleus', 'deschamps']):
        return 'France'
    if 'real madrid' in t:
        return 'Real Madrid'
    if 'psg' in t or 'paris saint' in t:
        return 'PSG'
    return 'Football'

def time_ago(date_str):
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        now = datetime.now(timezone.utc)
        diff = now - dt
        hours = int(diff.total_seconds() // 3600)
        if hours < 1:
            return "il y a < 1h"
        if hours < 24:
            return f"il y a {hours}h"
        days = hours // 24
        return f"il y a {days}j"
    except Exception:
        return "aujourd'hui"

def fetch_rss(source):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; OnzeDirectBot/1.0)',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
    }
    req = urllib.request.Request(source['url'], headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ✗ {source['name']}: {e}")
        return []

    articles = []
    try:
        root = ET.fromstring(content)
        items = root.findall('.//item')
        for item in items:
            def get(tag):
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ''
            title = get('title')
            if not title or title == '[Removed]':
                continue
            link = get('link') or get('guid') or '#'
            desc = strip_html(get('description') or '')[:200]
            date = get('pubDate') or ''
            image = None
            enc = item.find('enclosure')
            if enc is not None and (enc.get('type','').startswith('image')):
                image = enc.get('url')
            if not image:
                mt = item.find('{http://search.yahoo.com/mrss/}thumbnail')
                if mt is not None:
                    image = mt.get('url') or mt.text
            if not image:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', get('description'))
                if img_match:
                    image = img_match.group(1)
            articles.append({
                'title': title,
                'desc': desc,
                'url': link,
                'image': image,
                'date': date,
                'time': time_ago(date) if date else "aujourd'hui",
                'source': source['name'],
                'sourceId': source['id'],
                'color': source['color'],
                'cat': get_cat(title),
            })
        print(f"  ✓ {source['name']}: {len(articles)} articles")
    except ET.ParseError as e:
        print(f"  ✗ {source['name']}: XML error — {e}")
    return articles

def fetch_scores():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    scores = []
    print(f"\n  Fetching scores for {today}...")
    for lg in LEAGUES:
        url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?league={lg['id']}&date={today}"
        req = urllib.request.Request(url, headers={
            'x-rapidapi-key': RAPIDAPI_KEY,
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            fixtures = data.get('response', [])[:4]
            for f in fixtures:
                status = f['fixture']['status']['short']
                is_live = status in ['1H','HT','2H','ET','BT','P']
                scores.append({
                    'league': lg['name'],
                    'home': f['teams']['home']['name'],
                    'away': f['teams']['away']['name'],
                    'home_logo': f['teams']['home'].get('logo',''),
                    'away_logo': f['teams']['away'].get('logo',''),
                    'score_home': f['goals']['home'],
                    'score_away': f['goals']['away'],
                    'status': status,
                    'elapsed': f['fixture']['status'].get('elapsed'),
                    'is_live': is_live,
                    'is_done': status == 'FT',
                })
            print(f"  ✓ {lg['name']}: {len(fixtures)} matchs")
        except Exception as e:
            print(f"  ✗ {lg['name']}: {e}")
    return scores

def main():
    print(f"\n{'='*50}")
    print(f"  Onze Direct — Mise à jour")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M UTC')}")
    print(f"{'='*50}")

    all_articles = []
    seen_urls = set()

    for source in SOURCES:
        print(f"\n  Fetching {source['name']}...")
        articles = fetch_rss(source)
        for a in articles:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                all_articles.append(a)

    def sort_key(a):
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(a['date'])
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    all_articles.sort(key=sort_key, reverse=True)
    all_articles = all_articles[:60]

    scores = fetch_scores()

    output = {
        'updated': datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M UTC'),
        'count': len(all_articles),
        'articles': all_articles,
        'scores': scores,
    }

    with open('articles.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"  ✅ {len(all_articles)} articles + {len(scores)} matchs sauvegardés")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    main()
