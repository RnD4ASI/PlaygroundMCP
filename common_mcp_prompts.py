from mcp.server.fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("common_prompts_server")

# --- General Prompts ---
@mcp.prompt()
def basic_question_prompt(question_text: str) -> str:
    """
    A simple prompt that just returns the question.
    Useful for direct passthrough to an LLM or for testing.
    Args:
        question_text: The question to be asked.
    """
    return question_text

@mcp.prompt()
def math_problem_prompt(problem_description: str, tool_name: Optional[str] = "calculator") -> str:
    """
    Generates a prompt for an LLM to solve a math problem, suggesting a tool.
    Args:
        problem_description: The math problem (e.g., "what is 100 divided by 25?").
        tool_name: The suggested tool to use (defaults to 'calculator').
    """
    return (
        f"Please solve the following math problem: '{problem_description}'. "
        f"If helpful, you can use the '{tool_name}' tool."
    )

@mcp.prompt()
def request_current_time_prompt(time_zone: Optional[str] = None, desired_format: Optional[str] = None) -> str:
    """
    Generates a prompt to ask for the current time, potentially for a specific timezone
    and in a specific format, suggesting the 'get_current_datetime' tool.
    Args:
        time_zone: Optional. The timezone for which the time is requested (e.g., "PST", "UTC").
        desired_format: Optional. The desired strftime format for the time.
    """
    prompt_text = "What is the current time?"
    if time_zone:
        prompt_text += f" in {time_zone}?"

    tool_suggestion = "You can use the 'get_current_datetime' tool"
    if desired_format:
        tool_suggestion += f" with format_str='{desired_format}'"
    tool_suggestion += "."

    return f"{prompt_text} {tool_suggestion}"

# --- ArXiv Research Prompt (from original research_server.py) ---
@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    """
    Generate a prompt for an LLM (like Claude) to find and discuss academic papers
    on a specific topic using tools available on the 'common_tools_server'.
    Args:
        topic: The topic to search for papers on.
        num_papers: The desired number of papers to find (default: 5).
    """
    return f"""\
Search for {num_papers} academic papers about '{topic}' using the 'search_papers' tool.

Follow these instructions:
1. First, use the 'search_papers' tool with arguments: topic='{topic}', max_results={num_papers}. This will return a list of paper IDs.
2. For each paper ID found, use the 'extract_info' tool to get detailed information about that paper.
3. After gathering information for all papers, present a consolidated summary. For each paper, include:
   - Paper title
   - Authors
   - Publication date (if available)
   - A brief summary of its key findings or abstract.
4. Conclude with a high-level overview of the research landscape in '{topic}' based on the papers found, if possible. \
Mention any common themes or particularly interesting points.

Organize your findings in a clear, structured format with headings and bullet points for easy readability.
Example of calling a tool (for your internal thought process, you don't output this part):
If I need to search for papers, I will use:
{{
  "tool_name": "search_papers",
  "tool_input": {{ "topic": "{topic}", "max_results": {num_papers} }}
}}
If I need to extract info for a paper ID '1234.5678', I will use:
{{
  "tool_name": "extract_info",
  "tool_input": {{ "paper_id": "1234.5678" }}
}}
Present only the requested information and analysis in your final response.
"""

if __name__ == "__main__":
    print("Starting Common Prompts MCP Server (with ArXiv search prompt)...")
    mcp.run(transport='stdio')
