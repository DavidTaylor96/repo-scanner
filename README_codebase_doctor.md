# Codebase Doctor

A powerful tool to analyze codebases, generate documentation, and get AI-powered implementation guidance.

## Features

- **Scan & Analyze** - Scan repository structure and analyze code patterns
- **Documentation Generation** - Create comprehensive Markdown documentation
- **AI-Powered Insights** - Get AI analysis of architecture and patterns
- **Implementation Guidance** - Learn how to implement new features
- **Interactive Q&A** - Ask questions about the codebase

## Installation

```bash
# Install required package
pip install requests

# Clone or download the script
curl -O https://raw.githubusercontent.com/yourusername/codebase-doctor/main/codebase_doctor.py
chmod +x codebase_doctor.py
```

## Usage

### Analyzing a Codebase

```bash
# Set your Claude API key as an environment variable
export CLAUDE_API_KEY=your_api_key_here

# Analyze a codebase and generate documentation
python codebase_doctor.py analyze /path/to/repo
```

### Asking Questions About the Codebase

```bash
# Ask a specific question using the generated documentation
python codebase_doctor.py ask codebase_analysis.md "How do I create a new API endpoint?"
```

### Interactive Mode

```bash
# Enter interactive mode to ask multiple questions
python codebase_doctor.py interactive codebase_analysis.md
```

## Generated Documentation

The generated documentation includes:

1. **Overview** - High-level architecture and design
2. **Project Structure** - Directory layout and organization
3. **Code Patterns** - Common patterns and conventions
4. **Dependencies** - Key libraries and frameworks
5. **Implementation Examples** - How to implement common features
6. **Best Practices** - Recommended practices
7. **Recommendations** - Tips for working with the codebase

## Example Questions

You can ask the AI questions like:

- "How do I create a new API endpoint?"
- "What's the pattern for implementing a database model?"
- "How should I structure a new frontend component?"
- "What's the project's approach to error handling?"
- "How do I implement authentication?"

## Requirements

- Python 3.6+
- Claude API key from Anthropic
- `requests` library

## How It Works

1. The tool scans your codebase to understand its structure
2. It identifies patterns, entry points, dependencies and more
3. This data is analyzed by Claude AI to generate insights
4. A comprehensive Markdown document is produced
5. You can then use this document with AI to get implementation guidance

## Use Cases

- **Onboarding** - Help new team members understand the codebase
- **Documentation** - Generate codebase documentation
- **Learning** - Understand unfamiliar codebases
- **Best Practices** - Get implementation guidance that follows project conventions

## License

MIT License