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
vlt (Vault): Persistent Cognitive State & Semantic Threading for Agents.

'vlt' acts as your Long-Term Semantic Memory, allowing you to decouple your
reasoning state from your immediate context window. It helps you pick up exactly
where you left off, even across different sessions.

THE ARCHITECTURE:
1. STATE PERSISTENCE: Threads are stored permanently. You can retrieve them
   at any time to restore context.
2. COMPRESSED COGNITION: The 'Librarian' background process compresses raw
   thoughts into dense summaries (State Objects), so you don't have to re-read
   entire logs.
3. FAST LOGGING: 'thread push' is optimized for speed (<50ms). Log intermediate
   thoughts freely without slowing down.

PRIMITIVES:
- PROJECT: The bounded context (e.g., 'crypto-bot').
- THREAD:  A specific reasoning chain (e.g., 'optimization-strategy').
- NODE:    An atomic thought or event.
- STATE:   The computed, current truth of a thread (lossy compression).

CORE WORKFLOW:
1. WAKE UP: Run `vlt overview` to see active projects and states.
2. RESUME:  Run `vlt thread read <thread_id>` to load the semantic state.
3. THINK:   Run `vlt thread push <thread_id> "<thought>"` to log progress.
4. SEARCH:  Run `vlt thread seek "<concept>"` to find past solutions.
"""

app = typer.Typer(name="vlt", help=APP_HELP, no_args_is_help=True)
thread_app = typer.Typer(name="thread", help="Manage thought streams (create, push, read, search).")
app.add_typer(thread_app, name="thread")

service = SqliteVaultService()

@app.command()
def init():
    """
    Initialize the Vault DB. (Run this once).
    
    Establishes the local SQLite database. Required before any cognitive persistence can occur.
    """
    print("[bold green]Initializing Vault database...[/bold green]")
    init_db()
    
    # Simple wizard
    if not os.environ.get("VLT_OPENROUTER_API_KEY"):
        key = typer.prompt("Enter OpenRouter API Key (optional)", default="", hide_input=True)
        if key:
            # In a real app we'd write to .env or config file.
            # For MVP just print instruction.
            print(f"[yellow]Please export VLT_OPENROUTER_API_KEY='{key}' in your shell configuration.[/yellow]")
            
    print("[bold green]Done.[/bold green]")

@thread_app.command("new")
def new_thread(project: str, name: str, initial_thought: str):
    """
    The Cognitive Loop: Start a new reasoning chain.
    
    Creates a dedicated stream for a specific problem. Links it to a Project context.
    
    Arguments:
    - project: The high-level goal (e.g., 'crypto-bot').
    - name: The specific problem (e.g., 'optim-strategy').
    - initial_thought: The starting point of your reasoning.
    """
    # Ensure project exists (auto-create for MVP)
# ...
@thread_app.command("push")
def push_thought(thread_id: str, content: str):
    """
    The Cognitive Loop: Commit a thought to permanent memory.
    
    Fire-and-forget logging. Use this to offload intermediate reasoning steps so you
    can free up context window space.
    
    Arguments:
    - thread_id: The thread slug (e.g., 'optim-strategy') or full path 'project/thread'.
    - content: The text to log.
    """
    # Assuming thread_id format is project/thread or just thread if unique? 
# ...
@app.command("overview")
def overview(project_id: str = "default", json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """
    List active Projects and their Thread States.
    
    The 'Wake Up' command. Use this to orient yourself in the broader project context
    before diving into specific threads.
    """
    # Assuming 'default' or user passed arg.
# ...
@thread_app.command("read")
def read_thread(thread_id: str, json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """
    The Cognitive Loop: Load the Semantic State.
    
    Retrieves the compressed 'Truth' of a thread (State) and the most recent raw thoughts.
    Use this to resume work on a specific problem without reading the entire history.
    """
    view = service.get_thread_state(thread_id)
# ...
librarian_app = typer.Typer(name="librarian", help="Background daemon for summarization and embeddings.")
app.add_typer(librarian_app, name="librarian")

@librarian_app.command("run")
def run_librarian(daemon: bool = False, interval: int = 10):
    """
    [System] Background process for embeddings & state compression.
    
    The 'Subconscious' that processes raw thoughts into summaries and searchable vectors.
    """
    llm = OpenRouterLLMProvider()
# ...
@thread_app.command("seek")
def seek(query: str, project: str = typer.Option(None, "--project", "-p", help="Filter by project")):
    """
    The Cognitive Loop: Semantic Search.
    
    Query your permanent memory for similar problems or solutions encountered in the past.
    """
    results = service.search(query, project_id=project)
# ...
