def search(query: str, num_results: int = 3) -> str:
    """Search for information on a topic (returns mock search results)"""
    # Mock search results for demo
    mock_results = [
        {
            "title": f"Understanding {query.title()}",
            "snippet": f"A comprehensive guide to {query}. Learn everything you need to know about this topic with expert insights and practical examples.",
            "url": f"https://example.com/article/{query.lower().replace(' ', '-')}"
        },
        {
            "title": f"{query.title()} - Complete Overview",
            "snippet": f"Discover the latest information about {query}. This article covers key concepts, best practices, and real-world applications.",
            "url": f"https://example.com/guide/{query.lower().replace(' ', '-')}"
        },
        {
            "title": f"Top 10 Facts About {query.title()}",
            "snippet": f"Fascinating facts and statistics about {query}. Updated information from reliable sources with detailed explanations.",
            "url": f"https://example.com/facts/{query.lower().replace(' ', '-')}"
        },
        {
            "title": f"How to Master {query.title()}",
            "snippet": f"Step-by-step tutorial on {query}. Perfect for beginners and experts alike, with practical tips and common pitfalls to avoid.",
            "url": f"https://example.com/tutorial/{query.lower().replace(' ', '-')}"
        },
        {
            "title": f"{query.title()} in 2025: What You Need to Know",
            "snippet": f"Latest trends and developments in {query}. Expert analysis and predictions for the future of this important topic.",
            "url": f"https://example.com/trends/{query.lower().replace(' ', '-')}"
        }
    ]

    num_results = min(max(1, num_results), len(mock_results))
    results_text = f"Search results for '{query}':\n\n"

    for i, result in enumerate(mock_results[:num_results], 1):
        results_text += f"{i}. {result['title']}\n"
        results_text += f"   {result['snippet']}\n"
        results_text += f"   {result['url']}\n\n"

    return results_text.strip()
