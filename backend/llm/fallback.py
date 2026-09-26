"""Fallback heuristic labels for when LLM fails."""

from typing import List, Dict, Any


def heuristic_labels(components: List[Dict]) -> Dict[str, Any]:
    """
    Generate heuristic labels for components when LLM fails.
    Returns same shape as LLM output.
    
    Args:
        components: List of component dicts with id, files, symbols, etc.
    
    Returns:
        Dict with components, repo_summary, reading_order
    """
    
    labeled_components = []
    
    for comp in components:
        comp_id = comp.get('id', '')
        
        # Label = folder name in Title Case
        label = comp_id.split('/')[-1].replace('_', ' ').title()
        
        # Layer = keyword matching
        layer = determine_layer(comp_id)
        
        # Summary = first docstring or file count
        files = comp.get('files', [])
        summary = get_summary(files)
        
        labeled_components.append({
            'id': comp_id,
            'label': label,
            'layer': layer,
            'summary': summary,
            'label_source': 'heuristic'
        })
    
    # Repo summary
    repo_summary = f"Repository with {len(labeled_components)} components"
    
    # Reading order
    reading_order = get_reading_order(components)
    
    return {
        'components': labeled_components,
        'repo_summary': repo_summary,
        'reading_order': reading_order
    }


def determine_layer(folder_id: str) -> str:
    """Determine layer from folder name keywords."""
    folder_lower = folder_id.lower()
    
    if any(kw in folder_lower for kw in ['route', 'api', 'controller', 'handler']):
        return 'api'
    elif any(kw in folder_lower for kw in ['service', 'core']):
        return 'service'
    elif any(kw in folder_lower for kw in ['model', 'schema', 'db', 'entity']):
        return 'data'
    elif any(kw in folder_lower for kw in ['util', 'helper', 'lib', 'common']):
        return 'util'
    elif any(kw in folder_lower for kw in ['component', 'page', 'view', 'ui']):
        return 'ui'
    elif any(kw in folder_lower for kw in ['config', 'setting', 'env']):
        return 'config'
    else:
        return 'other'


def get_summary(files: List[Dict]) -> str:
    """Get summary from first docstring or file count."""
    if not files:
        return "No files"
    
    # Try to get first docstring
    for file in files:
        doc = file.get('doc_first_line', '')
        if doc:
            return doc[:60]
    
    # Fallback to file count
    return f"{len(files)} files"


def get_reading_order(components: List[Dict]) -> List[Dict[str, str]]:
    """Get reading order: entry files first, then top imported files."""
    
    entry_file_names = [
        'main.py', 'app.py', 'manage.py', 'index.js', 'server.js', 'app.js'
    ]
    
    reading_order = []
    
    for comp in components:
        files = comp.get('files', [])
        if not files:
            continue
        
        # Entry files first
        for file in files:
            file_path = file.get('path', '')
            file_name = file_path.split('/')[-1]
            if file_name in entry_file_names:
                reading_order.append({
                    'path': file_path,
                    'reason': 'entry point',
                    'source': 'heuristic'
                })
        
        # Then top files by import count
        sorted_by_imports = sorted(
            files,
            key=lambda f: len(f.get('imported_by', [])),
            reverse=True
        )
        
        for file in sorted_by_imports[:5]:
            file_path = file.get('path', '')
            if not any(r['path'] == file_path for r in reading_order):
                import_count = len(file.get('imported_by', []))
                if import_count > 0:
                    reading_order.append({
                        'path': file_path,
                        'reason': f'imported by {import_count} files',
                        'source': 'heuristic'
                    })
    
    return reading_order[:5]