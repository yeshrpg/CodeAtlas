"""Helper script to test /analyze endpoint and save demo JSONs."""

import requests
import json
from pathlib import Path


def test_analyze_endpoint(repo_url: str, repo_name: str, api_url: str = "http://localhost:8000"):
    """
    Test /analyze endpoint and save result as JSON.
    
    Args:
        repo_url: GitHub repo URL
        repo_name: Name for the JSON file
        api_url: Backend API URL
    
    Returns:
        Analysis result or None if failed
    """
    
    print(f"\n📊 Analyzing {repo_url}...")
    
    try:
        # Call /analyze endpoint
        response = requests.post(
            f"{api_url}/analyze",
            json={
                "repo_url": repo_url,
                "ref": "main",
                "use_llm": True
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return None
        
        result = response.json()
        
        # Save to demo_data
        demo_data_path = Path("demo_data")
        demo_data_path.mkdir(exist_ok=True)
        
        output_file = demo_data_path / f"{repo_name}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Saved to {output_file}")
        
        # Print summary
        stats = result.get('stats', {})
        print(f"   Files: {stats.get('files')}")
        print(f"   Components: {len(result.get('components', []))}")
        print(f"   Edges: {stats.get('edges')}")
        print(f"   Time: {stats.get('ms')}ms")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is backend running?")
        print(f"   Expected: {api_url}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    print("="*60)
    print("CodeAtlas API Test Helper")
    print("="*60)
    
    # Demo repos to test
    demo_repos = [
        ("https://github.com/fastapi/full-stack-fastapi-template", "fastapi-full-stack"),
        ("https://github.com/gothinkster/node-express-realworld-example-app", "express-realworld"),
        ("https://github.com/pallets/flask", "flask"),
    ]
    
    print("\n⚠️  Make sure backend API is running on http://localhost:8000")
    print("    (Run: python -m uvicorn app.main:app --reload)")
    
    input("\n👉 Press Enter to start testing...\n")
    
    results = []
    for repo_url, repo_name in demo_repos:
        result = test_analyze_endpoint(repo_url, repo_name)
        if result:
            results.append((repo_name, "✅ Success"))
        else:
            results.append((repo_name, "❌ Failed"))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, status in results:
        print(f"{name:<30} {status}")
    print("="*60)