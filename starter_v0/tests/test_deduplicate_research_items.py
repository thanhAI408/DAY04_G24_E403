from tools.deduplicate_research_items.tool import deduplicate_research_items


def test_url_tracking_params_are_duplicates():
    result = deduplicate_research_items(items=[
        {"title": "AI update", "url": "https://Example.com/story/?utm_source=x"},
        {"title": "AI update", "url": "https://example.com/story/"},
    ])
    assert result["unique_count"] == 1
    assert result["removed_count"] == 1


def test_similar_titles_without_urls_are_duplicates():
    result = deduplicate_research_items(items=[
        {"title": "New AI research results", "summary": "a"},
        {"title": "New AI research results!", "summary": "b"},
    ])
    assert result["unique_count"] == 1


def test_missing_url_is_safe():
    result = deduplicate_research_items(items=[{"title": "One"}, {"title": "Two"}])
    assert result["original_count"] == 2


def test_empty_list():
    result = deduplicate_research_items(items=[])
    assert result["unique_items"] == []
    assert result["removed_count"] == 0
