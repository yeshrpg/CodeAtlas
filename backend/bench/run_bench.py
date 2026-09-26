"""Benchmark script to measure precision/recall."""

import json
import subprocess
import time
from typing import Dict, List


def get_reference_edges_js(repo_path: str) -> Dict[str, List[str]]:
    """Get reference edges using madge for JS/TS repos."""
    try:
        result = subprocess.run(
            ['npx', 'madge', '--extensions', 'js,jsx,ts,tsx', '--json', repo_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Error running madge: {e}")
    return {}


def get_reference_edges_python(repo_path: str) -> Dict[str, List[str]]:
    """Get reference edges using grimp for Python repos."""
    try:
        import grimp
        graph = grimp.build_graph(repo_path)
        return {
            node: list(graph.find_modules_directly_imported_by(node))
            for node in graph.modules
        }
    except Exception as e:
        print(f"Error running grimp: {e}")
    return {}


def calculate_recall(reference: Dict, found: Dict) -> float:
    """Calculate recall: % of reference edges found."""
    if not reference:
        return 100.0
    
    ref_edges = set()
    for src, dests in reference.items():
        for dst in dests:
            ref_edges.add((src, dst))
    
    found_edges = set()
    for src, dests in found.items():
        for dst in dests:
            found_edges.add((src, dst))
    
    if not ref_edges:
        return 100.0
    
    matching = len(ref_edges & found_edges)
    return (matching / len(ref_edges)) * 100


def measure_repo(repo_name: str, repo_path: str, is_python: bool = True):
    """Measure precision/recall for one repo."""
    
    print(f"\n📊 Benchmarking {repo_name}...")
    
    # Get reference edges
    if is_python:
        reference = get_reference_edges_python(repo_path)
    else:
        reference = get_reference_edges_js(repo_path)
    
    print(f"  Reference edges: {sum(len(v) for v in reference.values())}")
    
    # TODO: Call CodeAtlas /analyze endpoint here
    # For now, this is a placeholder
    found = {}  # This would be your parser output
    
    # Calculate metrics
    recall = calculate_recall(reference, found)
    
    return {
        'repo': repo_name,
        'reference_edges': sum(len(v) for v in reference.values()),
        'found_edges': sum(len(v) for v in found.values()),
        'recall': round(recall, 1),
        'precision': 0.0,  # Will measure after testing
        'time_ms': 0
    }


def print_benchmark_table(results: List[Dict]):
    """Print results as a markdown table."""
    
    print("\n" + "="*100)
    print("BENCHMARK RESULTS")
    print("="*100)
    print(f"{'Repo':<30} {'Recall':<12} {'Precision':<12} {'Unresolved %':<15} {'Time (ms)':<12}")
    print("-"*100)
    
    for r in results:
        print(f"{r['repo']:<30} {r['recall']:.1f}%{'':<8} {r.get('precision', 0.0):.1f}%{'':<8} {r.get('unresolved', 0.0):.1f}%{'':<10} {r.get('time_ms', 0)}")
    
    print("="*100)


if __name__ == "__main__":
    print("⏳ Waiting for CodeAtlas API to be ready...")
    print("Once /analyze endpoint is live, we'll measure precision/recall on 5 repos")
    print("\nRepos to benchmark:")
    print("  1. fastapi/full-stack-fastapi-template (Python)")
    print("  2. expressjs/express (JavaScript)")
    print("  3. pallets/flask (Python)")
    print("  4. vuejs/vue (JavaScript, alias-heavy)")
    print("  5. facebook/react (JavaScript, large)")
    print("\n📝 Run this script after API is ready")