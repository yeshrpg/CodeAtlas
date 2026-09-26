"""Measure real precision/recall once API is ready."""

import json
from pathlib import Path


def load_reference_edges(repo_path: str):
    """Load reference edges from madge/grimp."""
    ref_file = Path(repo_path) / "reference.json"
    if ref_file.exists():
        with open(ref_file) as f:
            return json.load(f)
    return {}


def calculate_recall(reference_edges: dict, api_edges: list) -> float:
    """Calculate % of reference edges we found."""
    if not reference_edges:
        return 100.0
    
    ref_count = sum(len(v) if isinstance(v, list) else 0 for v in reference_edges.values())
    found_count = len(api_edges)
    
    if ref_count == 0:
        return 100.0
    
    return round((found_count / ref_count) * 100, 1)


def measure_repo(repo_name: str, repo_path: str, api_result: dict):
    """Measure one repo against reference."""
    
    # Load reference edges
    reference = load_reference_edges(repo_path)
    
    # Extract API edges
    api_edges = api_result.get('edges', [])
    api_components = len(api_result.get('components', []))
    
    # Calculate recall
    ref_count = sum(len(v) if isinstance(v, list) else 0 for v in reference.values())
    recall = calculate_recall(reference, api_edges)
    
    return {
        'repo': repo_name,
        'reference_edges': ref_count,
        'found_edges': len(api_edges),
        'components': api_components,
        'recall': recall,
        'precision': '—',  # To be filled by manual verification
    }


def print_results(results: list):
    """Print measurement results."""
    print("\n" + "="*120)
    print("PRECISION/RECALL MEASUREMENTS")
    print("="*120)
    print(f"{'Repo':<30} {'Ref Edges':<15} {'Found Edges':<15} {'Recall %':<12} {'Precision %':<12}")
    print("-"*120)
    
    for r in results:
        print(f"{r['repo']:<30} {r['reference_edges']:<15} {r['found_edges']:<15} {r['recall']:.1f}%{'':<8} {r['precision']:<12}")
    
    print("="*120)


if __name__ == "__main__":
    print("⏳ Waiting for YESH's real /analyze endpoint...")
    print("Once API is ready, this script will:")
    print("  1. Compare CodeAtlas output vs madge/grimp reference")
    print("  2. Calculate recall % (edges found)")
    print("  3. Report for manual precision verification")