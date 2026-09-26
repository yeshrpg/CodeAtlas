"""Helper script to run benchmark on 5 repos."""

import requests
import json
import time
from pathlib import Path


def measure_repo(repo_url: str, repo_name: str, api_url: str = "http://localhost:8000"):
    """
    Analyze one repo and measure time.
    
    Args:
        repo_url: GitHub repo URL
        repo_name: Friendly name
        api_url: Backend API URL
    
    Returns:
        Dict with metrics
    """
    
    print(f"\n⏱️  Measuring {repo_name}...")
    
    try:
        start = time.time()
        
        response = requests.post(
            f"{api_url}/analyze",
            json={
                "repo_url": repo_url,
                "ref": "main",
                "use_llm": True
            },
            timeout=120
        )
        
        elapsed_ms = int((time.time() - start) * 1000)
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            return None
        
        result = response.json()
        stats = result.get('stats', {})
        
        # Extract metrics
        metrics = {
            'repo': repo_name,
            'recall': '—',  # Will fill after comparing with madge/grimp
            'precision': '—',
            'unresolved_pct': stats.get('unresolved_pct', 0),
            'time_ms': elapsed_ms,
            'tokens': stats.get('llm_used', False),
            'components': len(result.get('components', [])),
            'edges': stats.get('edges', 0)
        }
        
        print(f"   ✅ {elapsed_ms}ms | {metrics['components']} components | {metrics['edges']} edges")
        
        return metrics
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def print_benchmark_table(results):
    """Print results as markdown table."""
    
    print("\n" + "="*120)
    print("BENCHMARK RESULTS")
    print("="*120)
    print(f"{'Repo':<30} {'Recall':<12} {'Precision':<12} {'Unresolved %':<15} {'Time (ms)':<12} {'Components':<12}")
    print("-"*120)
    
    for r in results:
        if r:
            print(f"{r['repo']:<30} {r['recall']:<12} {r['precision']:<12} {r['unresolved_pct']:.1f}%{'':<10} {r['time_ms']:<12} {r['components']:<12}")
    
    print("="*120)


if __name__ == "__main__":
    print("="*60)
    print("CodeAtlas Benchmark Measurement")
    print("="*60)
    
    # Benchmark repos
    repos = [
        ("https://github.com/fastapi/full-stack-fastapi-template", "fastapi-full-stack"),
        ("https://github.com/expressjs/express", "expressjs-express"),
        ("https://github.com/pallets/flask", "pallets-flask"),
        ("https://github.com/vuejs/vue", "vuejs-vue"),
        ("https://github.com/facebook/react", "facebook-react"),
    ]
    
    print("\n⚠️  Make sure backend API is running on http://localhost:8000")
    print("    (Run: python -m uvicorn app.main:app --reload)")
    
    input("\n👉 Press Enter to start benchmark...\n")
    
    results = []
    for repo_url, repo_name in repos:
        result = measure_repo(repo_url, repo_name)
        if result:
            results.append(result)
    
    # Print table
    print_benchmark_table(results)
    
    # Save to results.md
    print("\n📝 Update backend/bench/results.md with these values")