#!/usr/bin/env python3
"""
Codebase Doctor - A tool to analyze codebases and generate documentation

This script analyzes a repository, generates documentation using AI,
and allows asking questions about implementing features in the codebase.

Usage:
  python codebase_doctor.py analyze /path/to/repo
  python codebase_doctor.py ask /path/to/doc.md "How do I create a new endpoint?"
  python codebase_doctor.py interactive /path/to/doc.md  # Interactive Q&A mode
"""

import os
import re
import sys
import json
import argparse
import logging
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CodebaseAnalyzer:
    """Analyzes a codebase and generates documentation."""
    
    def __init__(self, repo_path: str, api_key: str, output_file: str = "codebase_analysis.md"):
        """Initialize the analyzer."""
        self.repo_path = os.path.abspath(repo_path)
        self.api_key = api_key
        self.output_file = output_file
        self.max_files_per_type = 25  # Maximum number of files to include in the analysis per type
        self.excluded_dirs = ['.git', 'node_modules', '__pycache__', 'venv', 'dist', 'build']
        self.file_data = {}
        self.file_patterns = defaultdict(list)
        self.stats = defaultdict(int)
        
    def scan_repo(self) -> None:
        """Scan the repository and collect file information."""
        logger.info(f"Scanning repository: {self.repo_path}")
        
        for root, dirs, files in os.walk(self.repo_path):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.repo_path)
                
                # Skip binary files and very large files
                if self._is_binary_file(file_path) or os.path.getsize(file_path) > 1000000:
                    continue
                
                # Get file extension
                _, ext = os.path.splitext(file)
                ext = ext.lower()[1:] if ext else "no_extension"
                
                self.stats["total_files"] += 1
                self.stats[f"files_by_type_{ext}"] += 1
                
                # Store file info
                self.file_data[rel_path] = {
                    "path": rel_path,
                    "type": ext,
                    "size": os.path.getsize(file_path)
                }
                
                # Collect sample files for each type (limited number)
                if len(self.file_patterns[ext]) < self.max_files_per_type:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        self.file_patterns[ext].append({
                            "path": rel_path,
                            "content": content[:100000]  # Limit content size
                        })
                    except UnicodeDecodeError:
                        logger.warning(f"Unable to read file as text: {rel_path}")
        
        logger.info(f"Scanned {self.stats['total_files']} files in the repository")
    
    def analyze_architecture(self) -> Dict[str, Any]:
        """Analyze the repository architecture and return results."""
        logger.info("Analyzing repository architecture...")
        
        # Generate directory structure
        directory_structure = self._get_directory_structure()
        
        # Extract patterns by file type
        patterns_by_type = {}
        for ext, files in self.file_patterns.items():
            if len(files) > 0:
                patterns_by_type[ext] = self._extract_patterns(ext, files)
                
        # Identify entry points
        entry_points = self._identify_entry_points()
        
        # Identify common packages/imports
        dependencies = self._identify_dependencies()
        
        return {
            "directory_structure": directory_structure,
            "patterns_by_type": patterns_by_type,
            "entry_points": entry_points,
            "dependencies": dependencies,
            "stats": dict(self.stats)
        }
    
    def ai_analysis(self, architecture_data: Dict[str, Any]) -> Dict[str, str]:
        """Use Claude AI to analyze the codebase architecture."""
        logger.info("Performing AI analysis of the codebase...")
        
        # Prepare the data for the AI
        prompt = self._generate_ai_prompt(architecture_data)
        
        # Call Claude API
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 4000,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            ai_analysis = result["content"][0]["text"]
            
            # Format the AI response into sections
            analysis_sections = self._parse_ai_analysis(ai_analysis)
            
            logger.info("AI analysis complete")
            return analysis_sections
            
        except Exception as e:
            logger.error(f"Error during AI analysis: {str(e)}")
            return {
                "overview": "Error during AI analysis",
                "patterns": "Error during AI analysis",
                "recommendations": "Error during AI analysis",
                "examples": "Error during AI analysis"
            }
    
    def generate_documentation(self, architecture_data: Dict[str, Any], 
                               ai_analysis: Dict[str, str]) -> None:
        """Generate comprehensive Markdown documentation about the codebase."""
        logger.info(f"Generating documentation to {self.output_file}...")
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            # Title
            repo_name = os.path.basename(self.repo_path)
            f.write(f"# {repo_name} Codebase Analysis\n\n")
            
            # Table of contents
            f.write("## Table of Contents\n\n")
            f.write("1. [Overview](#overview)\n")
            f.write("2. [Project Structure](#project-structure)\n")
            f.write("3. [Code Patterns](#code-patterns)\n")
            f.write("4. [Dependencies](#dependencies)\n")
            f.write("5. [Implementation Examples](#implementation-examples)\n")
            f.write("6. [Best Practices](#best-practices)\n")
            f.write("7. [Recommendations](#recommendations)\n\n")
            
            # Overview
            f.write("## Overview\n\n")
            f.write(ai_analysis.get("overview", "No overview available."))
            f.write("\n\n")
            
            # Project Structure
            f.write("## Project Structure\n\n")
            f.write("```\n")
            f.write(architecture_data["directory_structure"])
            f.write("```\n\n")
            
            # File statistics
            f.write("### File Statistics\n\n")
            f.write(f"- Total files: {architecture_data['stats']['total_files']}\n")
            for key, value in architecture_data['stats'].items():
                if key.startswith('files_by_type_') and value > 0:
                    ext = key.replace('files_by_type_', '')
                    f.write(f"- {ext} files: {value}\n")
            f.write("\n")
            
            # Entry points
            if architecture_data.get("entry_points"):
                f.write("### Entry Points\n\n")
                for entry_type, entries in architecture_data["entry_points"].items():
                    f.write(f"#### {entry_type.capitalize()}\n\n")
                    for entry in entries:
                        f.write(f"- `{entry}`\n")
                f.write("\n")
            
            # Code Patterns
            f.write("## Code Patterns\n\n")
            f.write(ai_analysis.get("patterns", "No patterns detected."))
            f.write("\n\n")
            
            # Dependencies
            f.write("## Dependencies\n\n")
            if architecture_data.get("dependencies"):
                for dep_type, deps in architecture_data["dependencies"].items():
                    f.write(f"### {dep_type.capitalize()}\n\n")
                    for dep, count in deps.items():
                        f.write(f"- {dep}: {count} occurrences\n")
            else:
                f.write("No dependencies detected.\n")
            f.write("\n")
            
            # Implementation Examples
            f.write("## Implementation Examples\n\n")
            f.write(ai_analysis.get("examples", "No examples provided."))
            f.write("\n\n")
            
            # Best Practices
            f.write("## Best Practices\n\n")
            f.write(ai_analysis.get("best_practices", "No best practices defined."))
            f.write("\n\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            f.write(ai_analysis.get("recommendations", "No recommendations provided."))
            f.write("\n\n")
        
        logger.info(f"Documentation generated: {self.output_file}")
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)
                return False
        except UnicodeDecodeError:
            return True
    
    def _get_directory_structure(self) -> str:
        """Get a string representation of the directory structure."""
        try:
            result = subprocess.run(
                ["find", self.repo_path, "-type", "d", "-not", "-path", "*/\\.*", "-not", "-path", "*/node_modules/*", 
                 "-not", "-path", "*/__pycache__/*", "-not", "-path", "*/venv/*", "-not", "-path", "*/dist/*", 
                 "-not", "-path", "*/build/*"],
                capture_output=True, text=True, check=True
            )
            
            dirs = result.stdout.split('\n')
            # Remove the repo path from the beginning
            dirs = [os.path.relpath(d, self.repo_path) for d in dirs if d.strip()]
            # Filter out empty strings and sort
            dirs = [d for d in dirs if d != '.']
            dirs.sort()
            
            # Convert to tree-like structure
            tree = ".\n"  # Root directory
            for d in dirs:
                # Count depth based on path separators
                depth = d.count(os.path.sep) + 1
                indent = "  " * depth
                dirname = os.path.basename(d)
                tree += f"{indent}└── {dirname}/\n"
                
            return tree
            
        except subprocess.CalledProcessError:
            logger.error("Failed to run the find command")
            # Fallback method
            return "Directory structure unavailable."
    
    def _extract_patterns(self, ext: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract patterns from files of a specific type."""
        patterns = {}
        
        # Different analysis based on file type
        if ext in ["js", "jsx", "ts", "tsx"]:
            # JavaScript/TypeScript specific patterns
            patterns["imports"] = self._extract_js_imports(files)
            patterns["exports"] = self._extract_js_exports(files)
            patterns["components"] = self._extract_react_components(files)
            
        elif ext in ["py"]:
            # Python specific patterns
            patterns["imports"] = self._extract_python_imports(files)
            patterns["classes"] = self._extract_python_classes(files)
            patterns["functions"] = self._extract_python_functions(files)
            
        elif ext in ["java", "kt"]:
            # Java/Kotlin specific patterns
            patterns["imports"] = self._extract_java_imports(files)
            patterns["classes"] = self._extract_java_classes(files)
            
        elif ext in ["go"]:
            # Go specific patterns
            patterns["imports"] = self._extract_go_imports(files)
            patterns["functions"] = self._extract_go_functions(files)
            
        return patterns
    
    def _identify_entry_points(self) -> Dict[str, List[str]]:
        """Identify potential entry points in the codebase."""
        entry_points = {
            "backend": [],
            "frontend": [],
            "cli": [],
            "config": []
        }
        
        # Backend entry points
        backend_patterns = [
            r"(app\.py|server\.py|main\.py|index\.py|application\.py)$",
            r"(app\.js|server\.js|index\.js|main\.js)$",
            r"(app\.ts|server\.ts|index\.ts|main\.ts)$",
            r"(Program\.cs|Startup\.cs)$"
        ]
        
        # Frontend entry points
        frontend_patterns = [
            r"(index\.html)$",
            r"(index\.jsx?|App\.jsx?|main\.jsx?)$",
            r"(index\.tsx?|App\.tsx?|main\.tsx?)$"
        ]
        
        # CLI entry points
        cli_patterns = [
            r"(cli\.py|__main__\.py|bin/.+)$",
            r"(cli\.js|bin/.+\.js)$"
        ]
        
        # Config files
        config_patterns = [
            r"(config\..+|.+\.config\..+)$",
            r"(package\.json|tsconfig\.json|poetry\.toml|pyproject\.toml)$",
            r"(Dockerfile|docker-compose\.yml)$",
            r"(.+\.yaml|.+\.yml)$"
        ]
        
        for file_path in self.file_data.keys():
            # Check backend patterns
            for pattern in backend_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    entry_points["backend"].append(file_path)
                    break
                    
            # Check frontend patterns
            for pattern in frontend_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    entry_points["frontend"].append(file_path)
                    break
                    
            # Check CLI patterns
            for pattern in cli_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    entry_points["cli"].append(file_path)
                    break
                    
            # Check config patterns
            for pattern in config_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    entry_points["config"].append(file_path)
                    break
        
        # Remove empty categories
        return {k: v for k, v in entry_points.items() if v}
    
    def _identify_dependencies(self) -> Dict[str, Dict[str, int]]:
        """Identify dependencies used in the project."""
        dependencies = {
            "javascript": {},
            "python": {},
            "java": {},
            "go": {}
        }
        
        # JavaScript dependencies
        if os.path.exists(os.path.join(self.repo_path, "package.json")):
            try:
                with open(os.path.join(self.repo_path, "package.json"), 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    deps = {}
                    if "dependencies" in package_data:
                        deps.update(package_data["dependencies"])
                    if "devDependencies" in package_data:
                        deps.update(package_data["devDependencies"])
                    
                    for dep, version in deps.items():
                        dependencies["javascript"][dep] = 1
            except Exception as e:
                logger.warning(f"Error parsing package.json: {str(e)}")
        
        # Python dependencies
        python_req_files = ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py"]
        for req_file in python_req_files:
            req_path = os.path.join(self.repo_path, req_file)
            if os.path.exists(req_path):
                try:
                    with open(req_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if req_file == "requirements.txt":
                            for line in content.split("\n"):
                                if line.strip() and not line.startswith("#"):
                                    pkg = line.split("==")[0].split(">=")[0].strip()
                                    dependencies["python"][pkg] = dependencies["python"].get(pkg, 0) + 1
                except Exception as e:
                    logger.warning(f"Error parsing {req_file}: {str(e)}")
        
        # Count imports from actual code
        for ext, files in self.file_patterns.items():
            if ext in ["js", "jsx", "ts", "tsx"]:
                for file in files:
                    imports = self._extract_js_imports([file])
                    for imp in imports:
                        if not imp.startswith(".") and not imp.startswith("/"):
                            pkg = imp.split("/")[0]
                            dependencies["javascript"][pkg] = dependencies["javascript"].get(pkg, 0) + 1
            
            elif ext in ["py"]:
                for file in files:
                    imports = self._extract_python_imports([file])
                    for imp in imports:
                        pkg = imp.split(".")[0]
                        dependencies["python"][pkg] = dependencies["python"].get(pkg, 0) + 1
        
        # Remove empty categories
        return {k: v for k, v in dependencies.items() if v}
    
    def _extract_js_imports(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract import statements from JavaScript/TypeScript files."""
        import_pattern = r'(?:import|require)\s*\(?[\'"]([^\'"]*)[\'"]\)?'
        imports = []
        
        for file in files:
            content = file["content"]
            matches = re.findall(import_pattern, content)
            imports.extend(matches)
            
        return list(set(imports))
    
    def _extract_js_exports(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract export statements from JavaScript/TypeScript files."""
        export_patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const|let|var)\s+([A-Za-z0-9_$]+)',
            r'export\s+default\s+([A-Za-z0-9_$]+)'
        ]
        exports = []
        
        for file in files:
            content = file["content"]
            for pattern in export_patterns:
                matches = re.findall(pattern, content)
                exports.extend(matches)
            
        return list(set(exports))
    
    def _extract_react_components(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract React component names from JavaScript/TypeScript files."""
        component_patterns = [
            r'(?:export\s+)?(?:default\s+)?class\s+([A-Z][A-Za-z0-9_$]*)\s+extends\s+(?:React\.)?Component',
            r'(?:export\s+)?(?:const|let|var)\s+([A-Z][A-Za-z0-9_$]*)\s*=\s*(?:\([^)]*\)|[^=]*)\s*=>\s*{',
            r'function\s+([A-Z][A-Za-z0-9_$]*)\s*\(',
        ]
        components = []
        
        for file in files:
            content = file["content"]
            for pattern in component_patterns:
                matches = re.findall(pattern, content)
                components.extend(matches)
            
        return list(set(components))
    
    def _extract_python_imports(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract import statements from Python files."""
        import_patterns = [
            r'import\s+([A-Za-z0-9_.]+)',
            r'from\s+([A-Za-z0-9_.]+)\s+import'
        ]
        imports = []
        
        for file in files:
            content = file["content"]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
            
        return list(set(imports))
    
    def _extract_python_classes(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract class names from Python files."""
        class_pattern = r'class\s+([A-Za-z0-9_]+)(?:\([^)]*\))?:'
        classes = []
        
        for file in files:
            content = file["content"]
            matches = re.findall(class_pattern, content)
            classes.extend(matches)
            
        return list(set(classes))
    
    def _extract_python_functions(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract function names from Python files."""
        function_pattern = r'def\s+([A-Za-z0-9_]+)\s*\('
        functions = []
        
        for file in files:
            content = file["content"]
            matches = re.findall(function_pattern, content)
            functions.extend(matches)
            
        return list(set(functions))
    
    def _extract_java_imports(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract import statements from Java files."""
        import_pattern = r'import\s+([A-Za-z0-9_.]+);'
        imports = []
        
        for file in files:
            content = file["content"]
            matches = re.findall(import_pattern, content)
            imports.extend(matches)
            
        return list(set(imports))
    
    def _extract_java_classes(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract class names from Java files."""
        class_pattern = r'(?:public|private|protected)?\s+class\s+([A-Za-z0-9_]+)'
        classes = []
        
        for file in files:
            content = file["content"]
            matches = re.findall(class_pattern, content)
            classes.extend(matches)
            
        return list(set(classes))
    
    def _extract_go_imports(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract import statements from Go files."""
        import_pattern = r'import\s+\(\s*(.*?)\s*\)'
        single_import_pattern = r'import\s+"([^"]+)"'
        imports = []
        
        for file in files:
            content = file["content"]
            
            # Multi-line imports
            multi_imports = re.findall(import_pattern, content, re.DOTALL)
            for imp_block in multi_imports:
                lines = imp_block.split("\n")
                for line in lines:
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        imports.append(match.group(1))
            
            # Single imports
            single_imports = re.findall(single_import_pattern, content)
            imports.extend(single_imports)
            
        return list(set(imports))
    
    def _extract_go_functions(self, files: List[Dict[str, str]]) -> List[str]:
        """Extract function names from Go files."""
        function_pattern = r'func\s+(?:\([^)]+\)\s+)?([A-Za-z0-9_]+)\s*\('
        functions = []
        
        for file in files:
            content = file["content"]
            matches = re.findall(function_pattern, content)
            functions.extend(matches)
            
        return list(set(functions))
    
    def _generate_ai_prompt(self, architecture_data: Dict[str, Any]) -> str:
        """Generate a prompt for the Claude AI API."""
        prompt = f"""
        I need you to analyze a codebase and provide insights about its structure, patterns, and how to implement new features. 
        I'll provide information about the project structure and code patterns. Please analyze this and give me:

        1. An overview of the codebase architecture and design
        2. Common design patterns and coding conventions used
        3. A guide on how to implement new features (like endpoints, database models, or frontend components)
        4. Recommendations for best practices when working with this codebase

        Here's data from the codebase analysis:

        # Project Statistics
        - Total files: {architecture_data['stats']['total_files']}
        """
        
        # Add file type statistics
        for key, value in architecture_data['stats'].items():
            if key.startswith('files_by_type_') and value > 0:
                ext = key.replace('files_by_type_', '')
                prompt += f"- {ext} files: {value}\n"
        
        # Add directory structure
        prompt += f"\n# Directory Structure\n```\n{architecture_data['directory_structure']}```\n"
        
        # Add entry points
        if architecture_data.get("entry_points"):
            prompt += "\n# Entry Points\n"
            for entry_type, entries in architecture_data["entry_points"].items():
                prompt += f"\n## {entry_type.capitalize()}\n"
                for entry in entries:
                    prompt += f"- {entry}\n"
        
        # Add dependencies
        if architecture_data.get("dependencies"):
            prompt += "\n# Dependencies\n"
            for dep_type, deps in architecture_data["dependencies"].items():
                if deps:
                    prompt += f"\n## {dep_type.capitalize()}\n"
                    # Sort dependencies by occurrences
                    sorted_deps = sorted(deps.items(), key=lambda x: x[1], reverse=True)
                    for dep, count in sorted_deps[:15]:  # Show top 15
                        prompt += f"- {dep}: {count} occurrences\n"
        
        # Add patterns by file type
        if architecture_data.get("patterns_by_type"):
            prompt += "\n# Code Patterns\n"
            for ext, patterns in architecture_data["patterns_by_type"].items():
                if patterns:
                    prompt += f"\n## {ext.upper()} Files\n"
                    
                    # Add imports
                    if "imports" in patterns and patterns["imports"]:
                        prompt += "\n### Common Imports\n"
                        for imp in patterns["imports"][:10]:  # Show top 10
                            prompt += f"- {imp}\n"
                    
                    # Add exports
                    if "exports" in patterns and patterns["exports"]:
                        prompt += "\n### Exports\n"
                        for exp in patterns["exports"][:10]:  # Show top 10
                            prompt += f"- {exp}\n"
                    
                    # Add components
                    if "components" in patterns and patterns["components"]:
                        prompt += "\n### Components\n"
                        for comp in patterns["components"][:10]:  # Show top 10
                            prompt += f"- {comp}\n"
                    
                    # Add classes
                    if "classes" in patterns and patterns["classes"]:
                        prompt += "\n### Classes\n"
                        for cls in patterns["classes"][:10]:  # Show top 10
                            prompt += f"- {cls}\n"
                    
                    # Add functions
                    if "functions" in patterns and patterns["functions"]:
                        prompt += "\n### Functions\n"
                        for func in patterns["functions"][:10]:  # Show top 10
                            prompt += f"- {func}\n"
        
        prompt += """
        Please provide your analysis as structured sections:

        # Overview
        [Overall architecture and design of the codebase]

        # Patterns
        [Common design patterns and coding conventions]

        # Examples
        [Examples of implementing common features like:
        - Adding a new API endpoint
        - Creating a database model
        - Adding a new frontend component
        - Implementing a service or utility]

        # Best Practices
        [Best practices specific to this codebase]

        # Recommendations
        [Recommendations for working with this codebase effectively]
        """
        
        return prompt
    
    def _parse_ai_analysis(self, ai_analysis: str) -> Dict[str, str]:
        """Parse AI analysis into sections."""
        sections = {}
        
        # Extract sections using regex
        overview_match = re.search(r'# Overview(.*?)(?=# Patterns|# Examples|# Best Practices|# Recommendations|$)', 
                                   ai_analysis, re.DOTALL)
        patterns_match = re.search(r'# Patterns(.*?)(?=# Overview|# Examples|# Best Practices|# Recommendations|$)', 
                                  ai_analysis, re.DOTALL)
        examples_match = re.search(r'# Examples(.*?)(?=# Overview|# Patterns|# Best Practices|# Recommendations|$)', 
                                  ai_analysis, re.DOTALL)
        best_practices_match = re.search(r'# Best Practices(.*?)(?=# Overview|# Patterns|# Examples|# Recommendations|$)', 
                                        ai_analysis, re.DOTALL)
        recommendations_match = re.search(r'# Recommendations(.*?)(?=# Overview|# Patterns|# Examples|# Best Practices|$)', 
                                         ai_analysis, re.DOTALL)
        
        if overview_match:
            sections["overview"] = overview_match.group(1).strip()
        if patterns_match:
            sections["patterns"] = patterns_match.group(1).strip()
        if examples_match:
            sections["examples"] = examples_match.group(1).strip()
        if best_practices_match:
            sections["best_practices"] = best_practices_match.group(1).strip()
        if recommendations_match:
            sections["recommendations"] = recommendations_match.group(1).strip()
        
        return sections
        
    def run(self) -> None:
        """Run the complete analysis process."""
        # Scan repository
        self.scan_repo()
        
        # Analyze architecture
        architecture_data = self.analyze_architecture()
        
        # AI analysis
        ai_analysis = self.ai_analysis(architecture_data)
        
        # Generate documentation
        self.generate_documentation(architecture_data, ai_analysis)
        
        logger.info(f"Analysis complete! Documentation written to {self.output_file}")


def analyze_codebase(repo_path: str, api_key: str, output_file: str = "codebase_analysis.md") -> str:
    """
    Analyze a codebase and generate documentation.
    
    Args:
        repo_path: Path to the repository to analyze
        api_key: Claude API key
        output_file: Path to output file
        
    Returns:
        Path to the generated documentation file
    """
    print(f"Analyzing codebase at {repo_path}...")
    
    # Run the analyzer
    analyzer = CodebaseAnalyzer(repo_path, api_key, output_file)
    analyzer.run()
    
    print(f"Analysis complete! Documentation written to {output_file}")
    return output_file


def ask_ai_about_codebase(doc_path: str, query: str, api_key: str) -> str:
    """
    Ask Claude AI a question about the codebase using the generated documentation.
    
    Args:
        doc_path: Path to the generated documentation
        query: Question to ask about the codebase
        api_key: Claude API key
        
    Returns:
        AI response
    """
    print(f"Asking AI: {query}")
    
    # Read the documentation
    with open(doc_path, 'r', encoding='utf-8') as f:
        doc_content = f.read()
    
    # Prepare the prompt for Claude
    prompt = f"""
    You are a helpful assistant that helps developers understand and work with a specific codebase. 
    I'll provide you with documentation about the codebase structure, patterns, and implementation guidelines.
    
    Here's the codebase documentation:
    
    {doc_content}
    
    Please use this documentation to answer the following question about the codebase:
    
    {query}
    
    Provide a detailed and specific answer based only on the information in the documentation. 
    If the documentation doesn't contain enough information to answer the question, please say so.
    """
    
    # Call Claude API
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        answer = result["content"][0]["text"]
        
        return answer
        
    except Exception as e:
        print(f"Error querying Claude API: {str(e)}")
        return f"Error: {str(e)}"


def interactive_mode(doc_path: str, api_key: str) -> None:
    """
    Enter interactive mode to ask questions about the codebase.
    
    Args:
        doc_path: Path to the generated documentation
        api_key: Claude API key
    """
    print(f"\nEntering interactive mode using documentation from {doc_path}")
    print("Ask questions about the codebase or press Ctrl+C to exit.")
    
    while True:
        try:
            query = input("\nYour question: ")
            if not query:
                continue
                
            response = ask_ai_about_codebase(doc_path, query, api_key)
            
            print("\n=== AI Response ===\n")
            print(response)
            print("\n===================")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Codebase Doctor - Analyze, document, and query codebases using AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a codebase
  python codebase_doctor.py analyze ~/projects/my-repo

  # Ask a question about a codebase using the generated documentation
  python codebase_doctor.py ask codebase_analysis.md "How do I create a new API endpoint?"

  # Start interactive query mode
  python codebase_doctor.py interactive codebase_analysis.md
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a codebase and generate documentation")
    analyze_parser.add_argument("repo_path", help="Path to the repository to analyze")
    analyze_parser.add_argument("--api-key", help="Claude API key (or set CLAUDE_API_KEY env var)")
    analyze_parser.add_argument("--output", default="codebase_analysis.md", help="Output file path (default: codebase_analysis.md)")
    
    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question about a codebase using the documentation")
    ask_parser.add_argument("doc_path", help="Path to the codebase documentation")
    ask_parser.add_argument("query", help="Question to ask about the codebase")
    ask_parser.add_argument("--api-key", help="Claude API key (or set CLAUDE_API_KEY env var)")
    
    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Enter interactive query mode")
    interactive_parser.add_argument("doc_path", help="Path to the codebase documentation")
    interactive_parser.add_argument("--api-key", help="Claude API key (or set CLAUDE_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Get API key from args or environment variable
    api_key = args.api_key if hasattr(args, 'api_key') and args.api_key else os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        parser.error("API key is required. Provide it with --api-key or set CLAUDE_API_KEY environment variable.")
    
    # Execute the appropriate command
    if args.command == "analyze":
        analyze_codebase(args.repo_path, api_key, args.output)
        
    elif args.command == "ask":
        response = ask_ai_about_codebase(args.doc_path, args.query, api_key)
        print("\n=== AI Response ===\n")
        print(response)
        print("\n===================")
        
    elif args.command == "interactive":
        interactive_mode(args.doc_path, api_key)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()