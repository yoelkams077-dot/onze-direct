"""
fetch_videos.py
Récupère les résumés vidéo YouTube et génère videos.json
"""

import json
import urllib.request
from datetime import datetime, timezone

YOUTUBE_KEY = "AIzaSyAmEOvs4e2Y4b_Pv5CVIMO3Cjhfs04jxx8"

CHANNELS = [
    {"name": "UEFA Champions League", "id": "UCTVrFAtzJi6brTcnhB4HiFA"},
    {"name": "Ligue 1",               "id": "UCiMCB_e-yBqZvZRCQaVSRmw"},
    {"name": "Premier League",        "id": "UCqZQlzSHbVJrpiMTFcCVz9A"},
    {"name": "LaLiga",                "id": "UCLb9yfpOXBa0WmQUEzST8CA"},
    {"name": "Goal.com",              "id": "UCuioDA3bFMKGBHJHQBJfxiA"},
]

SEARCH_QUERIES = [
    "résumé match foot ligue 1",
    "football highlights today",
    "resume match champions league",
    "but goal ligue 1",
    "highlights premier league",
]

def search_videos(query):
    url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={urllib.parse.quote(query)}"
        f"&type=video&order=date&maxResults=6"
        f"&relevanceLanguage=fr&key={YOUTUBE_KEY}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
        videos = []
        for item in data.get('items', []):
            vid_id = item['id'].get('videoId')
            if not vid_id:
                continue
            snippet = item['snippet']
            videos.append({
                'id': vid_id,
                'title': snippet.get('title', ''),
                'channel': snippet.get('channelTitle', ''),
                'thumbnail': snippet['thumbnails'].get('medium', {}).get('url', ''),
                'published': snippet.get('publishedAt', ''),
                'url': f"https://www.youtube.com/watch?v={vid_id}",
            })
        return videos
    except Exception as e:
        print(f"  ✗ Search '{query}': {e}")
        return []

import urllib.parse

def main():
    print(f"\n{'='*50}")
    print(f"  Onze Direct — Mise à jour vidéos")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M UTC')}")
    print(f"{'='*50}\n")

    all_videos = []
    seen_ids = set()

    for query in SEARCH_QUERIES:
        print(f"  Searching: {query}...")
        videos = search_videos(query)
        for v in videos:
            if v['id'] not in seen_ids:
                seen_ids.add(v['id'])
                all_videos.append(v)
        print(f"  → {len(videos)} vidéos trouvées")

    all_videos = all_videos[:24]

    output = {
        'updated': datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M UTC'),
        'count': len(all_videos),
        'videos': all_videos,
    }

    with open('videos.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ {len(all_videos)} vidéos sauvegardées dans videos.json")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    main()
