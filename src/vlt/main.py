import typer
from rich import print
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
import json
import os
import time
from vlt.core.migrations import init_db
from vlt.core.service import SqliteVaultService
from vlt.core.librarian import Librarian
from vlt.lib.llm import OpenRouterLLMProvider

APP_HELP = """
Vault CLI (vlt): External Memory and Thought Management for AI Agents.

Use this tool to offload your "stream of consciousness" and prevent context window bloat.
It acts as a persistent, searchable brain that runs locally.

STRENGTHS:
1. Low-Latency Logging (<50ms): Use 'vlt thread push' to log thoughts instantly without breaking flow.
2. Asynchronous Summarization: A background 'Librarian' condenses your history into concise state objects.
3. Semantic Search: Recall past decisions or errors using natural language queries.

CORE CONCEPTS:
- Project: A high-level goal (e.g., 'crypto-bot').
- Thread: A specific stream of work (e.g., 'optimization-strategy').
- Node: A single thought or log entry.
- State: The condensed summary of a thread.

WORKFLOW:
1. Start: `vlt thread new <project> <thread> "<goal>"`
2. Work:  `vlt thread push <thread> "<thought>"`
3. Check: `vlt thread read <thread>` (to see summary)
4. Recall:`vlt thread seek "<query>"`
"""

app = typer.Typer(name="vlt", help=APP_HELP, no_args_is_help=True)
thread_app = typer.Typer(name="thread", help="Manage thought streams (create, push, read, search).")
app.add_typer(thread_app, name="thread")

service = SqliteVaultService()

@app.command()
def init():
    """
    Initialize the local database (~/.vlt/vault.db).
    
    Run this once before using the tool. It creates the necessary tables.
    """
    print("[bold green]Initializing Vault database...[/bold green]")
# ...
@thread_app.command("new")
def new_thread(project: str, name: str, initial_thought: str):
    """
    Create a new thread within a project.
    
    Arguments:
    - project: The project slug (e.g., 'crypto-bot'). Auto-created if missing.
    - name: The thread slug (e.g., 'optim-strategy').
    - initial_thought: The first entry in the log.
    """
    # Ensure project exists (auto-create for MVP)
# ...
@thread_app.command("push")
def push_thought(thread_id: str, content: str):
    """
    Append a new thought to a thread.
    
    This command is optimized for speed (<50ms). Use it frequently to log your internal monologue.
    
    Arguments:
    - thread_id: The thread slug (e.g., 'optim-strategy') or full path 'project/thread'.
    - content: The text to log.
    """
    # Assuming thread_id format is project/thread or just thread if unique? 
# ...
@app.command("overview")
def overview(project_id: str = "default", json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """
    Show a high-level overview of a project.
    
    Displays the AI-generated summary of the project state and a list of active threads.
    Use this when 'waking up' to get context.
    """
    # Assuming 'default' or user passed arg.
# ...
@thread_app.command("read")
def read_thread(thread_id: str, json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """
    Read the current state and recent thoughts of a thread.
    
    Displays the AI-generated summary (State) followed by the 10 most recent raw nodes.
    Use this to re-orient yourself within a specific task.
    """
    view = service.get_thread_state(thread_id)
# ...
librarian_app = typer.Typer(name="librarian", help="Background daemon for summarization and embeddings.")
app.add_typer(librarian_app, name="librarian")

@librarian_app.command("run")
def run_librarian(daemon: bool = False, interval: int = 10):
    """
    Run the Librarian service.
    
    This process monitors the database for new nodes, generates summaries using an LLM,
    and calculates embeddings for search.
    
    Options:
    - --daemon: Run continuously in a loop (default: run once and exit).
    - --interval: Sleep time in seconds between cycles (default: 10).
    """
    llm = OpenRouterLLMProvider()
# ...
@thread_app.command("seek")
def seek(query: str, project: str = typer.Option(None, "--project", "-p", help="Filter by project")):
    """
    Search for past thoughts using semantic search.
    
    Requires the Librarian to have processed the nodes (generated embeddings).
    """
    results = service.search(query, project_id=project)
# ...
