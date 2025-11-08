"""
Helper utility functions for Paper Companion
"""

from typing import List


def format_authors(creators: List) -> str:
    """
    Format author list for display.

    Args:
        creators: List of creator dicts from Zotero

    Returns:
        Formatted author string
    """
    if not creators:
        return "No authors"

    authors = []
    for c in creators[:3]:  # First 3 authors
        if 'lastName' in c:
            authors.append(f"{c.get('firstName', '')} {c['lastName']}".strip())
        elif 'name' in c:
            authors.append(c['name'])

    if len(creators) > 3:
        authors.append("et al.")

    return ", ".join(authors)


def parse_selection(selection: str, max_val: int) -> List[int]:
    """
    Parse selection string like '1,3,5-7' into list of indices.

    Args:
        selection: Selection string (e.g., "1,3,5-7")
        max_val: Maximum allowed value

    Returns:
        List of selected indices
    """
    from rich.console import Console
    console = Console()

    indices = set()

    # Split by comma
    parts = selection.replace(' ', '').split(',')

    for part in parts:
        if '-' in part:
            # Range selection (e.g., "2-5")
            try:
                start, end = part.split('-')
                start, end = int(start), int(end)
                if start <= end:
                    indices.update(range(start, min(end + 1, max_val + 1)))
            except ValueError:
                console.print(f"[yellow]Invalid range: {part}[/yellow]")
        else:
            # Single number
            try:
                num = int(part)
                if 1 <= num <= max_val:
                    indices.add(num)
            except ValueError:
                console.print(f"[yellow]Invalid number: {part}[/yellow]")

    return sorted(list(indices))
