# Claude Code Project Setup
 
## Version Control
* Whenever code changes are made, you must record a one-line description with emoji in korean of the change in `.commit_message.txt` with Edit Tool.
   - Read `.commit_message.txt` first, and then Edit.
   - Overwrite regardless of existing content.
   - If it was a git revert related operation, make the .commit_message.txt file empty.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Project Setup with UV
```bash
# Install dependencies (automatically creates virtual environment)
uv sync

# Add new dependencies
uv add package_name

# Install development dependencies
uv sync --dev

# Activate virtual environment (if needed manually)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
```

### Running Applications
```bash
# Main Streamlit app (with uv)
uv run streamlit run app.py

# MCP server testing
uv run python MCP_Client_Test.py

# Individual test files
uv run python test.py
uv run python test_gear_agent.py
uv run python test_chat_agent.py

# Legacy method (if not using uv)
streamlit run app.py
```

### Environment Variables Required
Create `.env` file with:
```
OPENAI_API_KEY="your_openai_key"
FIRECRAWL_API_KEY="your_firecrawl_key"  # Optional for Deep Research
YOUTUBE_API_KEY="your_youtube_key"      # Optional for MCP Agent
```

## Code Architecture

### Core Application Structure
- **app.py**: Main Streamlit interface for AI agent chat with real-time streaming responses
- **agents/**: Agent implementations following abstract base pattern
  - `base_agent.py`: Abstract base class defining agent interface with async callback support
  - `gear_agent.py`: LangGraph-based multi-agent system for gear design
  - `gear_design_agent.py`: MCP server for gear design calculations
  - `gear_classifier_agent.py`: Gear requirement classification agent
  - `chat_agent.py`: General purpose chat agent
- **services/**: Business logic layer
  - `agent_service.py`: Agent factory and management service
- **MCP servers/**: Model Context Protocol server implementations
  - `mcp_server_gd.py`: Gear design MCP server with session management
  - `mcp_server_MASTA.py`: MASTA integration server
- **utils/**: Shared utilities including LLM wrapper functions

### Agent Pattern
All agents inherit from `BaseAgent` and must implement:
- `process_with_callback()`: Main processing with streaming callback support
- Configuration management through `update_config()`
- Message history management
- Shared data system for inter-agent communication

### MCP (Model Context Protocol) Integration
- **mcp.json**: Configuration for MCP server connections
- Session-based architecture with automatic cleanup
- External tool integration through standardized protocol
- .NET DLL integration for mechanical engineering calculations via pythonnet

### Multi-Agent System (LangGraph)
The gear_agent implements a sophisticated multi-agent workflow:
- **Planning**: Automatic planning generation from user inputs
- **Classification**: Gear requirement analysis and validation
- **Design**: Detailed gear design calculations
- **Visualization**: Graph generation and image creation using Pyppeteer
- **Reporting**: Comprehensive report generation

### Key Dependencies
- **Streamlit**: Web interface with session state management
- **OpenAI**: LLM integration with streaming support
- **LangGraph**: Multi-agent workflow orchestration
- **pythonnet**: .NET integration for gear design calculations
- **Pyppeteer**: Headless Chrome for graph image generation
- **asyncio/nest_asyncio**: Async support in Streamlit environment

### Session Management
- MCP servers implement session-based architecture
- Automatic session cleanup after timeout (1 hour)
- File tracking and cleanup for generated outputs
- Session-specific output directories for isolation

### Testing Framework
- Individual test files for different components
- Performance timing decorators in test.py
- MCP client testing with MCP_Client_Test.py
- No formal testing framework configured - uses standalone test files

### Configuration Management
- Agent settings cached in Streamlit session state
- Model selection includes GPT variants and Anthropic models
- Dynamic configuration updates supported
- Environment-based API key management

### 답변
- 답변은 한글로 간결하게 할 것.
- 줄바꿈은 "\r\n" 등으로 명확하게 정의할 것.

### 코드
- 코드는 중복되거나 너무 과하지 않고 간결하게 작성할 것.
- 코드는 메모리, 계산량을 고려하여 효율적으로 구성할 것.

