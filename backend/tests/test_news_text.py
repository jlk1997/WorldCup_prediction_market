from app.utils.news_text import clean_news_summary, extract_news_thumbnail


def test_clean_entity_encoded_html():
    raw = (
        "&lt;p&gt;&lt;div data-hupu-node=&quot;image&quot;&gt;"
        "&lt;img src=&quot;https://cdn.example.com/a.jpg&quot; alt=&quot;莱奥采访&quot;&gt;"
        "&lt;/div&gt;&lt;p&gt;莱奥表示自己在米兰很开心&lt;/p&gt;"
    )
    assert "莱奥表示自己在米兰很开心" in clean_news_summary(raw)
    assert "&lt;" not in clean_news_summary(raw)
    assert "https://" not in clean_news_summary(raw)


def test_extract_thumbnail_from_encoded_html():
    raw = '&lt;img src=&quot;https://i10.hoopchina.com.cn/news/a.webp&quot; alt=&quot;x&quot;&gt;'
    assert extract_news_thumbnail(raw) == "https://i10.hoopchina.com.cn/news/a.webp"
