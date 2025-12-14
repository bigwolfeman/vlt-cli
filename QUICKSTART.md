# Vault CLI (vlt) - Quickstart Guide

## 1. Installation

Ensure you have Python 3.11 or higher installed.

1.  Unzip the package.
2.  Open a terminal in the `vlt-cli` directory.
3.  Install the package in editable mode (recommended for beta):

    ```bash
    pip install -e .
    ```

## 2. Configuration

1.  Initialize the local database:

    ```bash
    vlt init
    ```

2.  Set your OpenRouter API Key (Required for AI features):

    ```bash
    vlt config set-key sk-or-v1-...
    ```

    *Note: The key is stored locally in `~/.vlt/.env`.*

## 3. Core Workflow

**Scenario**: You are starting a new task to optimize a physics engine.

1.  **Start a Thread**:
    ```bash
    vlt thread new physics-engine optimization "Starting SAT implementation."
    ```

2.  **Log Thoughts (The Loop)**:
    ```bash
    vlt thread push physics-engine/optimization "SAT is too slow for concave shapes."
    vlt thread push physics-engine/optimization "Switching to GJK algorithm."
    ```

3.  **Tag Important Moments**:
    ```bash
    # Get the node ID from the push output or read command
    vlt tag <node_id> pivot
    ```

4.  **Review State**:
    ```bash
    vlt thread read physics-engine/optimization
    ```

5.  **Run the Librarian (Background)**:
    In a separate terminal, run this to process your thoughts into summaries:
    ```bash
    vlt librarian run --daemon
    ```

6.  **Search**:
    ```bash
    vlt thread seek "convex algorithm"
    ```

## 4. Advanced: The Knowledge Graph

- **Link Threads**: Connect related work.
  ```bash
  vlt link <source_node_id> <target_thread_slug> --note "Related to"
  ```

- **Project Overview**: See everything at a glance.
  ```bash
  vlt overview physics-engine
  ```
