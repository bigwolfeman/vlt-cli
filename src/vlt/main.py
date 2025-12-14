import typer
from pathlib import Path
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

META-COGNITION STRATEGIES:
1. PROACTIVE INTROSPECTION: Before starting a complex task, ask yourself:
   "Is this a multi-step problem where I might lose my train of thought?"
   If YES, create a thread immediately and log your plan.

2. RELEVANCE PREDICTION: When you make a decision, ask:
   "Will I need to know WHY I did this in 3 days?"
   If YES, push the reasoning (e.g., "Chose SQLite over Postgres for portability").

3. CONTEXT OFFLOADING: If your context window is filling up,
   summarize your current state into `vlt`, then clear your context.
   Trust `vlt` to hold the state while you perform the execution.
"""

app = typer.Typer(name="vlt", help=APP_HELP, no_args_is_help=True)
thread_app = typer.Typer(name="thread", help="Manage thought streams (create, push, read, search).")
config_app = typer.Typer(name="config", help="Manage configuration and keys.")
app.add_typer(thread_app, name="thread")
app.add_typer(config_app, name="config")

service = SqliteVaultService()

@config_app.command("set-key")
def set_key(key: str):
    """
    Set the OpenRouter API Key persistently.
    
    This saves the key to ~/.vlt/.env so you don't have to export it every time.
    """
    env_path = os.path.expanduser("~/.vlt/.env")
    
    # Read existing lines to preserve other configs if any
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
            
    # Remove existing key if present
    lines = [l for l in lines if not l.startswith("VLT_OPENROUTER_API_KEY=")]
    
    # Append new key
    lines.append(f"VLT_OPENROUTER_API_KEY={key}\n")
    
    with open(env_path, "w") as f:
        f.writelines(lines)
        
    print(f"[green]API Key saved to {env_path}[/green]")

from vlt.core.identity import create_vlt_toml, load_project_identity

# ...

@app.command()
def init(
    project: str = typer.Option(None, "--project", "-p", help="Initialize a vlt.toml for this directory with the given project name.")
):
    """
    Initialize the Vault DB or a Project Context.
    
    - Default: Initializes the local DB (~/.vlt/vault.db).
    - With --project: Creates a 'vlt.toml' file in the current directory, anchoring it to a project.
    """
    if project:
        # Create vlt.toml
        project_id = project.lower().replace(" ", "-")
        create_vlt_toml(Path("."), name=project, id=project_id)
        print(f"[bold green]Initialized project '{project}' (id: {project_id}) in vlt.toml[/bold green]")
        
        # Ensure project exists in DB too
        try:
            service.create_project(name=project, description="Initialized via vlt init")
        except Exception:
            pass
        return

    print("[bold green]Initializing Vault database...[/bold green]")
    init_db()
# ...

@thread_app.command("new")
def new_thread(
    name: str = typer.Argument(..., help="Thread slug (e.g. 'optim-strategy')"),
    initial_thought: str = typer.Argument(..., help="Initial thought"),
    project: str = typer.Option(None, "--project", "-p", help="Project slug. Defaults to vlt.toml context.")
):
    """
    The Cognitive Loop: Start a new reasoning chain.
    
    Creates a dedicated stream. Links it to a Project context.
    If 'vlt.toml' is present, the project is auto-detected.
    """
    # 1. Resolve Project
    if not project:
        identity = load_project_identity()
        if identity:
            project = identity.id
        else:
            print("[red]Error: No project specified and no vlt.toml found.[/red]")
            print("Usage: vlt thread new <name> <thought> --project <project>")
            print("Or run: vlt init --project <name>")
            raise typer.Exit(code=1)

    print(f"DEBUG: Creating thread {project}/{name}")
    # Ensure project exists (auto-create for MVP)
    try:
        service.create_project(name=project, description="Auto-created project")
    except Exception:
        # Project might already exist, which is fine for now
        pass
        
    thread = service.create_thread(project_id=project, name=name, initial_thought=initial_thought)
    print(f"[bold green]CREATED:[/bold green] {thread.project_id}/{thread.id}")
    print(f"STATUS: {thread.status}")
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
    # For MVP assume we pass just thread slug or handle project/thread splitting if needed.
    # The spec examples show `vlt thread push crypto-bot/optim-strategy`.
    # Our DB stores thread_id as slug.
    
    # Simple parsing if composite ID is passed
    if "/" in thread_id:
        _, thread_slug = thread_id.split("/")
    else:
        thread_slug = thread_id

    node = service.add_thought(thread_id=thread_slug, content=content)
    print(f"[bold green]OK:[/bold green] {node.thread_id}/{node.sequence_id}")
@app.command("overview")
def overview(project_id: str = typer.Argument(None, help="Project ID"), json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """
    List active Projects and their Thread States.
    
    The 'Wake Up' command. Use this to orient yourself in the broader project context
    before diving into specific threads.
    """
    if not project_id:
        identity = load_project_identity()
        if identity:
            project_id = identity.id
        else:
            # Fallback to "default" or list all?
            # For now, require it or default.
            project_id = "default"

    view = service.get_project_overview(project_id)
    
    if json_output:
        print(json.dumps(view.model_dump(), default=str))
        return

    print(Panel(Markdown(f"# Project: {view.project_id}\n\n{view.summary}"), title="Project Overview", border_style="blue"))
    
    table = Table(title="Active Threads")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="magenta")
    
    for t in view.active_threads:
        table.add_row(t["id"], t["status"])
        
    print(table)
@thread_app.command("read")
def read_thread(thread_id: str, json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """
    The Cognitive Loop: Load the Semantic State.
    
    Retrieves the compressed 'Truth' of a thread (State) and the most recent raw thoughts.
    Use this to resume work on a specific problem without reading the entire history.
    """
    view = service.get_thread_state(thread_id)
    
    if json_output:
        print(json.dumps(view.model_dump(), default=str))
        return

    print(Panel(Markdown(f"# Thread: {view.thread_id}\n\n{view.summary}"), title="Thread State", border_style="green"))
    
    if view.meta:
         print(Panel(str(view.meta), title="Meta", border_style="yellow"))

    print("\n[bold]Recent Thoughts:[/bold]")
    for node in view.recent_nodes:
        print(f"[dim]{node.sequence_id} | {node.timestamp.strftime('%H:%M:%S')}[/dim] {node.content}")
librarian_app = typer.Typer(name="librarian", help="Background daemon for summarization and embeddings.")
app.add_typer(librarian_app, name="librarian")

@librarian_app.command("run")
def run_librarian(daemon: bool = False, interval: int = 10):
    """
    [System] Background process for embeddings & state compression.
    
    The 'Subconscious' that processes raw thoughts into summaries and searchable vectors.
    """
    llm = OpenRouterLLMProvider()
    librarian = Librarian(llm_provider=llm)
    
    print("[bold blue]Librarian started.[/bold blue]")
    
    while True:
        try:
            print("Processing pending nodes...")
            nodes_count = librarian.process_pending_nodes()
            if nodes_count > 0:
                print(f"[green]Processed {nodes_count} nodes.[/green]")
                
                print("Updating project overviews...")
                proj_count = librarian.update_project_overviews()
                print(f"[green]Updated {proj_count} projects.[/green]")
            else:
                print("No new nodes.")
                
        except Exception as e:
            print(f"[red]Error:[/red] {e}")
            
        if not daemon:
            break
            
        time.sleep(interval)
@thread_app.command("seek")
def seek(query: str, project: str = typer.Option(None, "--project", "-p", help="Filter by project")):
    """
    The Cognitive Loop: Semantic Search.
    
    Query your permanent memory for similar problems or solutions encountered in the past.
    """
    if not project:
        identity = load_project_identity()
        if identity:
            project = identity.id

    results = service.search(query, project_id=project)
    
    if not results:
        print("[yellow]No matches found.[/yellow]")
        return
        
    for res in results:
        score_color = "green" if res.score > 0.8 else "yellow"
        print(f"[[{score_color}]{res.score:.2f}[/{score_color}]] [bold]{res.thread_id}[/bold] ({res.node_id[:8]}): {res.content}")

@app.command()
def tag(node_id: str, name: str):
    """
    Attach a semantic tag to a specific node (thought).
    
    Tags allow for cross-cutting taxonomy (e.g., #bug, #architecture).
    """
    try:
        tag = service.add_tag(node_id, name)
        print(f"[green]Tagged node {node_id[:8]} with #{tag.name}[/green]")
    except Exception as e:
        print(f"[red]Error tagging node: {e}[/red]")

@app.command()
def link(source_node_id: str, target_thread: str, note: str = "Relates to"):
    """
    Create a semantic link between a thought and another thread.
    
    Use this to connect reasoning chains (e.g., 'This bug relates to physics-engine').
    """
    try:
        ref = service.add_reference(source_node_id, target_thread, note)
        print(f"[green]Linked node {source_node_id[:8]} -> {target_thread} ({note})[/green]")
    except Exception as e:
        print(f"[red]Error linking node: {e}[/red]")

if __name__ == "__main__":
    app()
