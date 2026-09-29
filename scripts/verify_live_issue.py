from urllib.request import urlopen

from news.models import Article


issue = Article.objects.filter(published_at__date="2026-09-28").order_by(
    "published_at", "pk"
)
bad_tokens = ["à¤", "ï¿½", "विस्तृत मूल रिपोर्ट", "�"]

print("ISSUE_ARTICLES", issue.count())
print("EMPTY_BODIES", issue.filter(body="").count())
print("WITH_HEADINGS", sum("<h2>" in article.body for article in issue))
print(
    "NO_HEADINGS",
    [(article.pk, article.title) for article in issue if "<h2>" not in article.body],
)
print(
    "BAD_TEXT_HITS",
    {token: sum(token in article.body for article in issue) for token in bad_tokens},
)

results = []
for article in Article.objects.filter(status="published"):
    status = urlopen(
        "https://ddsamvad.com" + article.get_absolute_url(), timeout=10
    ).status
    results.append((article.pk, status))

print("LIVE_URLS", len(results))
print("NON_200", [result for result in results if result[1] != 200])

all_articles = Article.objects.filter(status="published")
print(
    "GLOBAL_BAD_TEXT_HITS",
    {
        token: sum(
            token in f"{article.title} {article.summary} {article.body}"
            for article in all_articles
        )
        for token in bad_tokens
    },
)
