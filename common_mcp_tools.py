from mcp.server.fastmcp import FastMCP
import datetime
import json
import os
import arxiv # Ensure arxiv is installed: pip install arxiv
from typing import List, Dict, Any, Optional

mcp = FastMCP("common_tools_server")

PAPER_DIR = "papers" # Used by ArXiv tools

# --- Simple General Tools ---
@mcp.tool()
def calculator(expression: str) -> str:
    """
    Evaluates a simple mathematical expression.
    Supports +, -, *, / operations.
    Example: "2 + 2" or "10 * 5 / 2 - 3"
    Args:
        expression: The mathematical expression string.
    Returns:
        The result of the calculation as a string, or an error message.
    """
    try:
        allowed_chars = "0123456789+-*/. ()"
        if not all(char in allowed_chars for char in expression):
            return "Error: Invalid characters in expression."
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

@mcp.tool()
def get_current_datetime(format_str: Optional[str] = None) -> str:
    """
    Returns the current date and time, optionally formatted.
    Args:
        format_str: An optional strftime format string.
                    Defaults to ISO 8601 format if None.
                    Example: "%Y-%m-%d %H:%M:%S"
    Returns:
        The current date and time as a formatted string.
    """
    now = datetime.datetime.now()
    if format_str:
        try:
            return now.strftime(format_str)
        except Exception as e:
            return f"Error formatting date: {str(e)}. Using default format."
    return now.isoformat()

# --- ArXiv Research Tools (from original research_server.py) ---
@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    Information is saved locally in the './papers/{topic}/papers_info.json' file.
    Args:
        topic: The topic to search for.
        max_results: Maximum number of results to retrieve (default: 5).
    Returns:
        List of paper IDs found and processed.
    """
    os.makedirs(PAPER_DIR, exist_ok=True) # Ensure base paper directory exists
    client = arxiv.Client()
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    papers_iterator = client.results(search)

    topic_slug = topic.lower().replace(" ", "_")
    topic_path = os.path.join(PAPER_DIR, topic_slug)
    os.makedirs(topic_path, exist_ok=True)

    file_path = os.path.join(topic_path, "papers_info.json")

    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    processed_paper_ids = []
    for paper in papers_iterator:
        paper_id = paper.get_short_id()
        processed_paper_ids.append(paper_id)
        paper_info_entry = {
            'title': paper.title,
            'authors': [author.name for author in paper.authors],
            'summary': paper.summary,
            'pdf_url': paper.pdf_url,
            'published': str(paper.published.date()) if paper.published else "N/A"
        }
        papers_info[paper_id] = paper_info_entry

    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)

    # print(f"Results for '{topic}' are saved in: {file_path}") # Server-side print
    return processed_paper_ids

@mcp.tool()
def extract_info(paper_id: str) -> str: # Returns JSON string or error message
    """
    Search for information about a specific paper ID across all locally stored topic directories.
    Args:
        paper_id: The ID of the paper to look for (e.g., "2303.08774v2").
    Returns:
        JSON string with paper information if found, or an error message string if not found.
    """
    if not os.path.exists(PAPER_DIR):
        return f"The '{PAPER_DIR}' directory does not exist. No papers have been searched and stored yet."

    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    # Log this server side, don't return to client unless it's a general failure
                    print(f"Warning: Error reading or parsing {file_path}: {str(e)}")
                    continue # Try other folders

    return f"There's no saved information related to paper ID '{paper_id}'."

# --- ArXiv Paper Resources (from original research_server.py) ---
@mcp.resource("papers://folders")
def get_available_folders() -> str: # Returns Markdown string
    """
    List all available topic folders in the local papers directory
    that contain a papers_info.json file.
    This resource provides a simple list of all available topic folders.
    """
    folders = []
    if os.path.exists(PAPER_DIR):
        for topic_dir in os.listdir(PAPER_DIR):
            topic_path = os.path.join(PAPER_DIR, topic_dir)
            if os.path.isdir(topic_path):
                papers_file = os.path.join(topic_path, "papers_info.json")
                if os.path.exists(papers_file): # Only list if json exists
                    folders.append(topic_dir)

    content = "# Available Topics (Folders with paper data)\n\n"
    if folders:
        for folder_name in sorted(folders): # Sort for consistent output
            content += f"- {folder_name}\n"
        content += f"\nUse @papers://{{topic_folder_name}} to access papers in that topic.\n"
    else:
        content += "No topic folders with paper data found.\n"
        content += f"You can try using the 'search_papers' tool to populate topics.\n"

    return content

@mcp.resource("papers://{topic}") # topic here is the folder name (slug)
def get_topic_papers(topic: str) -> str: # Returns Markdown string
    """
    Get detailed information about papers stored locally for a specific topic folder.
    Args:
        topic: The research topic folder name (e.g., "quantum_computing_basics").
    """
    topic_dir_path = os.path.join(PAPER_DIR, topic) # topic is already slug-like here
    papers_file_path = os.path.join(topic_dir_path, "papers_info.json")

    if not os.path.exists(papers_file_path):
        return f"# No papers found for topic folder: {topic}\n\n" \
               f"Ensure the folder exists and contains a 'papers_info.json' file. " \
               f"You might need to use the 'search_papers' tool first for the original topic name."

    try:
        with open(papers_file_path, 'r') as f:
            papers_data = json.load(f)

        topic_title = topic.replace('_', ' ').replace('-', ' ').title()
        content = f"# Papers on {topic_title}\n\n"
        if not papers_data:
            content += "No paper information found in this topic folder.\n"
            return content

        content += f"Total papers: {len(papers_data)}\n\n"

        for paper_id, paper_info in papers_data.items():
            content += f"## {paper_info.get('title', 'N/A')}\n"
            content += f"- **Paper ID**: {paper_id}\n"
            authors = paper_info.get('authors', [])
            content += f"- **Authors**: {', '.join(authors) if authors else 'N/A'}\n"
            content += f"- **Published**: {paper_info.get('published', 'N/A')}\n"
            pdf_url = paper_info.get('pdf_url', '')
            content += f"- **PDF URL**: [{pdf_url}]({pdf_url})\n\n"
            summary = paper_info.get('summary', 'No summary available.')
            content += f"### Summary\n{summary[:500]}...\n\n" # Display first 500 chars
            content += "---\n\n"

        return content
    except json.JSONDecodeError:
        return f"# Error reading papers data for topic folder {topic}\n\nThe 'papers_info.json' file might be corrupted."
    except Exception as e:
        return f"# An unexpected error occurred while retrieving papers for topic folder {topic}: {str(e)}"

if __name__ == "__main__":
    print("Starting Common Tools MCP Server (with ArXiv tools and resources)...")
    # Create papers directory if it doesn't exist, so server can start without error if dir is missing.
    os.makedirs(PAPER_DIR, exist_ok=True)
    mcp.run(transport='stdio')
