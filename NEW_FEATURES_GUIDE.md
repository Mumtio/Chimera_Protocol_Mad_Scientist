# New Features Guide

Quick reference for newly implemented backend features.

---

## 🆕 Team-Global Memory

Store memories that are accessible across ALL conversations for your entire team.

### Usage

```bash
# Create a team-global memory
POST /api/mcp/remember
{
  "text": "Our company uses Python and Django for backend",
  "conversation_id": "any-conversation-id",
  "scope": "team-global",
  "tags": ["company-standard", "tech-stack"]
}
```

### Benefits
- Share knowledge across all projects
- Onboard new team members faster
- Maintain consistent standards

---

## 🤖 Multi-LLM Support

Use different AI models in the same conversation.

### Supported Models

**OpenAI**: gpt-4, gpt-4-turbo, gpt-4o, gpt-3.5-turbo  
**Anthropic**: claude-3-opus, claude-3-sonnet, claude-3-haiku  
**Groq**: llama-3-70b, llama-3-8b, mixtral-8x7b  
**Demo**: echo, local

### Usage

```bash
# Use GPT-4
POST /api/chat
{
  "conversation_id": "abc123",
  "message": "Design a homepage",
  "model": "gpt-4"
}

# Switch to Claude in same conversation
POST /api/chat
{
  "conversation_id": "abc123",
  "message": "Improve the design",
  "model": "claude-3-sonnet"
}
```

### Response includes model info
```json
{
  "reply": "...",
  "model_used": "gpt-4",
  "trace": {
    "provider": "openai",
    "context_injected": true,
    "memory_hits": 5
  }
}
```

---

## 🧠 Automatic Memory Extraction

AI automatically saves important information from conversations.

### Triggers
- Keywords: "remember", "important", "prefer", "always"
- Factual statements: "I am...", "I use...", "working on..."
- Long detailed messages

### Usage

```bash
POST /api/chat
{
  "conversation_id": "abc123",
  "message": "Remember: I prefer React for frontend and always use TypeScript",
  "model": "gpt-4",
  "remember": true
}
```

### Response
```json
{
  "reply": "...",
  "memory_injected": true,
  "auto_extracted_facts": 2
}
```

---

## 📊 Statistics Endpoints

Get insights into conversations and usage.

### Conversation Stats

```bash
GET /api/stats/conversation/abc123
```

Response:
```json
{
  "conversation_id": "abc123",
  "messages": {
    "total": 45,
    "user": 23,
    "assistant": 22
  },
  "models_used": {
    "gpt-4": 15,
    "claude-3-sonnet": 7
  },
  "memories": {
    "total": 12,
    "conversation_scoped": 10,
    "team_global": 2
  }
}
```

### User Stats

```bash
GET /api/stats/user
```

Response:
```json
{
  "user_id": 1,
  "username": "john",
  "conversations": {
    "owned": 5,
    "shared": 3,
    "total": 8
  },
  "messages_sent": 234
}
```

---

## 🔄 Batch Operations

Store multiple memories at once.

### Usage

```bash
POST /api/mcp/batch-remember
{
  "memories": [
    {
      "text": "User prefers dark mode",
      "conversation_id": "abc123",
      "tags": ["preference"]
    },
    {
      "text": "Project deadline: Dec 15",
      "conversation_id": "abc123",
      "tags": ["deadline", "important"]
    },
    {
      "text": "Team uses Slack for communication",
      "conversation_id": "abc123",
      "scope": "team-global",
      "tags": ["team", "tools"]
    }
  ]
}
```

---

## 🔍 Memory Index Management

Monitor and maintain the search index.

### Check Index Status

```bash
GET /api/mcp/index/status
```

Response:
```json
{
  "total_memories": 150,
  "indexed_memories": 150,
  "index_health": "healthy",
  "vectorizer_features": 1000
}
```

### Rebuild Index

```bash
POST /api/mcp/index/rebuild
```

Response:
```json
{
  "status": "rebuilt",
  "message": "Memory search index rebuilt successfully",
  "indexed_count": 150
}
```

---

## 👥 Team Collaboration

Add team members to conversations.

### Add Member

```bash
POST /api/conversations/abc123/add-member
{
  "username": "jane"
}
```

### Benefits
- Multiple people work in same conversation
- Shared context and memory
- All LLMs see same information
- Real-time collaboration

---

## 🎯 Context Injection

Every LLM call automatically receives relevant context.

### What's Included
- Recent conversation messages
- Conversation-scoped memories
- Team-global memories
- Auto-extracted facts

### Example

When you send:
```
"Build a login page"
```

LLM receives:
```
=== Relevant Context ===
- [GLOBAL] Our company uses Python and Django for backend
- User prefers React for frontend
- User always uses TypeScript
- Previous conversation about authentication

User: Build a login page
```

---

## 🔧 Model Discovery

Find out which models are available.

### Usage

```bash
GET /api/models
```

Response:
```json
{
  "models": {
    "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus", "claude-3-sonnet"],
    "groq": ["llama-3-70b", "mixtral-8x7b"],
    "echo": ["echo", "local"]
  },
  "total": 9
}
```

---

## 🪝 Spec Hooks

Automatically update documentation when endpoints change.

### Usage

```bash
POST /api/hooks/spec-update
{
  "type": "endpoint",
  "method": "POST",
  "path": "/api/new-feature",
  "description": "New feature endpoint",
  "schema": {
    "input": "...",
    "output": "..."
  }
}
```

---

## 💡 Best Practices

### Memory Scope
- Use **conversation** scope for project-specific info
- Use **team-global** scope for company-wide standards

### Model Selection
- Use **GPT-4** for complex reasoning
- Use **Claude** for long-form content
- Use **Llama** for fast responses
- Use **echo** for testing

### Auto-Extraction
- Enable `remember: true` for important conversations
- Use keywords like "remember" and "important"
- System automatically detects facts and preferences

### Team Collaboration
- Add members to conversations early
- Use team-global memories for shared knowledge
- Check conversation stats to see team activity

---

## 🚀 Quick Start Example

```bash
# 1. Create a conversation
POST /api/conversations/create
{"title": "Homepage Redesign"}

# 2. Add team member
POST /api/conversations/{id}/add-member
{"username": "designer"}

# 3. Store team-global standard
POST /api/mcp/remember
{
  "text": "We use Material-UI for all React projects",
  "conversation_id": "{id}",
  "scope": "team-global"
}

# 4. Chat with GPT-4
POST /api/chat
{
  "conversation_id": "{id}",
  "message": "Design a modern homepage",
  "model": "gpt-4",
  "remember": true
}

# 5. Switch to Claude for refinement
POST /api/chat
{
  "conversation_id": "{id}",
  "message": "Make it more minimalist",
  "model": "claude-3-sonnet"
}

# 6. Check stats
GET /api/stats/conversation/{id}
```

---

*All features are production-ready and fully tested.*
