"""Quick QA test on random repos."""

import requests
import json

repos = [
    ("lodash/lodash", "https://github.com/lodash/lodash"),
    ("axios/axios", "https://github.com/axios/axios"),
    ("pallets/flask", "https://github.com/pallets/flask"),
    ("django/django", "https://github.com/django/django"),
    ("expressjs/express", "https://github.com/expressjs/express"),
    ("vuejs/vue", "https://github.com/vuejs/vue"),
    ("facebook/react", "https://github.com/facebook/react"),
    ("nodejs/node", "https://github.com/nodejs/node"),
    ("torvalds/linux", "https://github.com/torvalds/linux"),
    ("rust-lang/rust", "https://github.com/rust-lang/rust"),
]

results = []

for name, url in repos:
    try:
        print(f"Testing {name}...", end=" ")
        response = requests.post(
            "http://localhost:8000/analyze",
            json={"repo_url": url, "ref": "main", "use_llm": True},
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅")
            results.append((name, "✅ PASS"))
        else:
            print(f"⚠️ ({response.status_code})")
            results.append((name, f"⚠️ WARN ({response.status_code})"))
    except Exception as e:
        print(f"❌")
        results.append((name, f"❌ FAIL ({str(e)[:30]})"))

print("\n" + "="*60)
for name, status in results:
    print(f"{name:<30} {status}")
print("="*60)