import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE = "https://ddsamvad.com"
PATHS = [
    "/",
    "/latest/",
    "/epaper/",
]

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
pages = {}
for path in PATHS:
    url = BASE + urllib.parse.quote(path, safe="/%-_")
    with opener.open(url, timeout=20) as response:
        body = response.read()
        pages[path] = body
        print(response.status, len(body), path)

titles = [
    "फरार CSP नेहा पच्चीसिया को हाईकोर्ट से मिलेगी राहत या जाना होगा जेल? फैसला सुरक्षित",
    "साइबर ठगी से सावधान: WhatsApp पर बैंक खाते से पैसे कटने का फर्जी अलर्ट भेजकर ठगी की कोशिश",
    "280 करोड़ की बंपर कमाई वाली 'हनुमान अंश' में भोपाल का डंका: 8 साल के सात्विक ने 'शुभंकर' बन लूटी महफिल",
]
latest = pages["/latest/"].decode("utf-8")
article_paths = []
for title in titles:
    pattern = r'href="([^"]+)"[^>]*>\s*' + re.escape(title[:18])
    match = re.search(pattern, latest)
    assert match, title
    path = match.group(1)
    with opener.open(BASE + path, timeout=20) as response:
        pages[path] = response.read()
        article_paths.append(path)
        print(response.status, len(pages[path]), path)

home = pages["/"].decode("utf-8")
epaper = pages["/epaper/"].decode("utf-8")
assert "info@ddsamvad.com" in home
for social in ["instagram.com/ddsamvad", "facebook.com/ddsamvad", "x.com/ddsamvad", "youtube.com/@ddsamvadofficial"]:
    assert social in home, social
assert "dds-news-tip-qr" in home

media_urls = set(re.findall(r'"([^"]*/media/epaper/[^"]+)"', epaper))
assert len([url for url in media_urls if "/pages/" in url]) == 8, media_urls
for path in sorted(media_urls):
    url = path if path.startswith("http") else BASE + path
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = response.read()
        assert response.status == 200 and payload
        print("MEDIA", response.status, len(payload), path)

for asset in [
    "/static/images/dds-news-tip-qr.jpeg",
    "/media/articles/2026/09/hanuman-ansh-satvik-sharma.jpg",
]:
    with urllib.request.urlopen(BASE + asset, timeout=20) as response:
        print("ASSET", response.status, response.length, asset)
        assert response.status == 200

first, second, third = [pages[path].decode("utf-8") for path in article_paths]
assert "article-media-gallery" not in first
assert "article-media-gallery" not in second
assert "hanuman-ansh-satvik-sharma.jpg" in third
print("PUBLIC RELEASE VERIFIED")
