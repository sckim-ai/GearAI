# Claude Code Project Setup
 
## Version Control
* Whenever code changes are made, you must record a one-line description with emoji in korean of the change in `.commit_message.txt` with Edit Tool.
   - Read `.commit_message.txt` first, and then Edit.
   - Overwrite regardless of existing content.
   - If it was a git revert related operation, make the .commit_message.txt file empty.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Virtual Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

### Package Installation
```bash
# Main dependencies
pip install streamlit>=1.28.0 openai>=1.3.0 python-dotenv>=1.0.0 asyncio>=3.4.3 typing-extensions>=4.5.0

# Deep Research module dependencies
pip install openai python-dotenv firecrawl-py

# MCP Agent dependencies
pip install mcp openai-agents streamlit youtube-transcript-api python-dotenv
```

### Running Applications
```bash
# Main Streamlit app
streamlit run app.py

# Deep Research module
cd Deep_research
python main.py

# Test files
python test.py
python Deep_research/test.py
```

### Environment Variables Required
Create `.env` file with:
```
OPENAI_API_KEY="your_openai_key"
FIRECRAWL_API_KEY="your_firecrawl_key"  # For Deep Research
YOUTUBE_API_KEY="your_youtube_key"      # For MCP Agent
```

## Code Architecture

### Core Application Structure
- **app.py**: Main Streamlit interface for AI agent chat with real-time streaming responses
- **agents/**: Agent implementations following abstract base pattern
  - `base_agent.py`: Abstract base class defining agent interface with async callback support
  - `GearDesign_agent.py`: MCP server for gear design calculations
  - `gpt_agent.py`: Single LLM agent implementation
  - `deep_research_agent.py`: Multi-step research agent
- **services/**: Business logic layer
  - `agent_service.py`: Agent factory and management service
- **utils/**: Shared utilities
  - `llm.py`: OpenAI client wrapper functions
  - `prompt_chain.py`: Prompt chaining utilities

### Agent Pattern
All agents inherit from `BaseAgent` and must implement:
- `process_with_callback()`: Main processing with streaming callback support
- Configuration management through `update_config()`
- Message history management

### MCP (Model Context Protocol) Integration
- **mcp.json**: Configuration for MCP server connections
- Supports external tool integration through standardized protocol
- GearDesign agent provides mechanical engineering calculations via .NET DLL integration

### Deep Research Module
Multi-step AI research pipeline:
1. **step1_feedback/**: User feedback collection
2. **step2_research/**: Web research using Firecrawl
3. **step3_reporting/**: Report generation
- Rate limits: Firecrawl free tier has 5 requests/minute limit

### Key Dependencies
- **Streamlit**: Web interface with session state management
- **OpenAI**: LLM integration with streaming support
- **pythonnet**: .NET integration for gear design calculations
- **Firecrawl**: Web scraping for research
- **asyncio/nest_asyncio**: Async support in Streamlit environment

### Configuration Management
- Agents support dynamic configuration updates
- Settings cached in Streamlit session state
- Model selection includes GPT-4, GPT-4o variants, and o4-mini
- Temperature controls (o4-mini fixed at 1.0)

### Testing
- `test.py`: Main testing utilities with timing decorators
- `Deep_research/test.py`: Research module tests
- No formal test framework configured

### 답변
- 답변은 한글로 할 것.
