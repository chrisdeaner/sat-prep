# How to Wire Up & Test the SAT Vocab MCP Server

## How MCP Actually Works

MCP servers are **not** like web servers. You don't "start a server and then connect to it." Instead:

> **The LLM client spawns your server as a child process**, communicates via stdin/stdout, and kills it when done.

Think of it like a command-line tool that the AI client knows how to run. The client launches `python -m mcp_server.server`, sends JSON messages to its stdin, reads JSON responses from its stdout. That's it.

**There's nothing to host.** No ports, no URLs, no Docker.

---

## Which of Your LLM Clients Can Use It?

| Client | MCP Support | How to Configure |
|--------|-------------|------------------|
| **Antigravity (me!)** | ✅ Yes | Edit `~/.gemini/antigravity/mcp_config.json` |
| **Claude Desktop** | ✅ Yes | Edit `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **OpenClaw** | ✅ Yes | Same pattern as Claude Desktop |
| **Cursor** | ✅ Yes | Settings → MCP Servers |

---

## Step 1: Configure Antigravity

Edit `~/.gemini/antigravity/mcp_config.json` and paste:

```json
{
  "mcpServers": {
    "sat-vocab": {
      "command": "/Users/chrisdeaner/work/vibes/sat-prep/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/Users/chrisdeaner/work/vibes/sat-prep"
    }
  }
}
```

Then restart Antigravity. I should then be able to call `lookup_word`, `list_words`, and `quiz_me` directly in our conversations.

---

## Step 2 (optional): Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sat-vocab": {
      "command": "/Users/chrisdeaner/work/vibes/sat-prep/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/Users/chrisdeaner/work/vibes/sat-prep"
    }
  }
}
```

Quit and reopen Claude Desktop. A 🔌 icon should appear indicating the server is connected.

---

## Step 3: Test with MCP Inspector (optional)

The MCP Inspector is a browser-based debug UI that lets you poke at your tools directly:

```bash
cd /Users/chrisdeaner/work/vibes/sat-prep
source venv/bin/activate
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

This opens a web UI where you can call each tool and see the raw JSON responses.

---

## What You Do NOT Need

| Thing | Needed? |
|-------|---------|
| A web server / Flask / FastAPI | ❌ No |
| Docker | ❌ No |
| A database | ❌ No |
| Cloud hosting | ❌ No |
| An API key | ❌ No |
| Port forwarding / ngrok | ❌ No |

---

## Available Tools

Once configured, the following tools are available in any conversation:

| Tool | What It Does | Example Prompt |
|------|-------------|----------------|
| `lookup_word` | Look up a word — definition, sentences, alt meanings | *"Look up the word eschew"* |
| `list_words` | Browse vocabulary by frequency tier | *"Show me all high-frequency SAT words"* |
| `quiz_me` | Generate a multiple-choice quiz | *"Quiz me on 5 high-frequency SAT words"* |
