"""
Lilith Tool Registry v1.0
Centralized management of all available tools for the planning engine
Provides metadata, auto-discovery, and intelligent tool selection
"""

import inspect
import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("ToolRegistry")


class ToolCategory(str, Enum):
    CODE_ANALYSIS = "code_analysis"
    VERSION_CONTROL = "version_control"
    SYSTEM_EXECUTION = "system_execution"
    FILE_MANAGEMENT = "file_management"
    WEB_AUTOMATION = "web_automation"
    MEDIA_PROCESSING = "media_processing"
    RESEARCH = "research"
    UNKNOWN = "unknown"


class ToolRisk(str, Enum):
    LOW = "low"  # Read-only operations, safe queries
    MEDIUM = "medium"  # File modifications, git operations
    HIGH = "high"  # System changes, deletions, network operations
    CRITICAL = "critical"  # Destructive operations, production changes


@dataclass
class ToolMetadata:
    """Metadata for a tool that helps planning and execution"""

    name: str
    category: ToolCategory
    description: str
    long_description: str
    risk_level: ToolRisk

    # Parameters specification
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Example usage
    example_usage: str = ""

    # Dependencies (if any)
    dependencies: List[str] = field(default_factory=list)

    # Performance characteristics
    typical_duration_seconds: int = 10
    requires_approval: bool = False
    can_stream_output: bool = False

    # When to use this tool
    when_to_use: str = ""

    # Capabilities
    capabilities: List[str] = field(default_factory=list)


class ToolRegistry:
    """
    Central registry for all tools available to Lilith
    Provides discovery, metadata, and selection capabilities
    """

    def __init__(self):
        self._tools: Dict[str, object] = {}  # name -> tool instance
        self._metadata: Dict[str, ToolMetadata] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}
        self._initialized = False
        logger.info("ToolRegistry initialized")

    def initialize(self):
        """Initialize all standard tools"""
        if self._initialized:
            logger.warning("ToolRegistry already initialized")
            return

        logger.info("Initializing standard tools...")

        # Import tools (lazy to avoid circular imports)
        try:
            from src.capabilities.system_executor import SystemExecutor
            from src.core.planning.planning_engine import PlanningEngine
            from src.tools.enhanced.code_analyzer import CodeAnalyzer
            from src.tools.enhanced.code_editor import CodeEditor
            from src.tools.enhanced.grep_tool import GrepTool

            # Register SystemExecutor
            sys_executor = SystemExecutor()
            self.register_tool(
                name="SystemExecutor",
                tool_instance=sys_executor,
                metadata=ToolMetadata(
                    name="SystemExecutor",
                    category=ToolCategory.SYSTEM_EXECUTION,
                    description="Execute system commands",
                    long_description="Execute system commands and shell operations",
                    risk_level=ToolRisk.HIGH,
                    parameters={
                        "command": {
                            "type": "string",
                            "description": "Command to execute",
                            "required": True,
                        },
                        "timeout": {
                            "type": "int",
                            "description": "Timeout in seconds",
                            "required": False,
                        },
                    },
                    example_usage="@run echo 'Hello World'",
                    typical_duration_seconds=10,
                    can_stream_output=True,
                    when_to_use="Use for system operations, file manipulation, running scripts",
                    capabilities=[
                        "execute_command",
                        "file_operations",
                        "process_management",
                    ],
                ),
            )

            # Register CodeAnalyzer
            code_analyzer = CodeAnalyzer()
            self.register_tool(
                name="CodeAnalyzer",
                tool_instance=code_analyzer,
                metadata=ToolMetadata(
                    name="CodeAnalyzer",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Analyze Python code structure",
                    long_description="Analyze Python projects to understand structure, dependencies, and symbols",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "analyze_project",
                                "analyze_file",
                                "find_definition",
                                "find_references",
                            ],
                            "required": True,
                        },
                        "path": {
                            "type": "string",
                            "description": "Project or file path",
                            "required": True,
                        },
                        "symbol": {
                            "type": "string",
                            "description": "Symbol name to find",
                            "required": False,
                        },
                    },
                    example_usage="@plan analyze the codebase structure",
                    typical_duration_seconds=30,
                    can_stream_output=False,
                    when_to_use="Use for understanding code structure, finding definitions, analyzing dependencies",
                    capabilities=[
                        "analyze_project",
                        "analyze_file",
                        "find_symbol",
                        "dependency_graph",
                    ],
                ),
            )

            # Register CodeEditor
            code_editor = CodeEditor()
            self.register_tool(
                name="CodeEditor",
                tool_instance=code_editor,
                metadata=ToolMetadata(
                    name="CodeEditor",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Edit and write code files",
                    long_description="Insert, replace, or overwrite code in files with automatic backups",
                    risk_level=ToolRisk.HIGH,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": ["edit", "write", "insert"],
                            "required": True,
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Target file path",
                            "required": True,
                        },
                        "target": {
                            "type": "string",
                            "description": "Text to replace (for edit)",
                            "required": False,
                        },
                        "replacement": {
                            "type": "string",
                            "description": "New text (for edit)",
                            "required": False,
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write/insert",
                            "required": False,
                        },
                        "line_number": {
                            "type": "integer",
                            "description": "Line number (for insert)",
                            "default": 1,
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Overwrite existing file (for write)",
                            "default": False,
                        },
                    },
                    example_usage="@plan edit web_api.py to add a new endpoint",
                    typical_duration_seconds=5,
                    can_stream_output=False,
                    when_to_use="Use for modifying existing code, creating new files, or inserting code snippets",
                    capabilities=[
                        "edit_file",
                        "write_file",
                        "insert_code",
                        "file_backups",
                    ],
                ),
            )

            # Register GrepTool
            grep_tool = GrepTool()
            self.register_tool(
                name="GrepTool",
                tool_instance=grep_tool,
                metadata=ToolMetadata(
                    name="GrepTool",
                    category=ToolCategory.FILE_MANAGEMENT,
                    description="Project-wide search and globbing",
                    long_description="Search for patterns in files or list files using globs",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": ["grep", "list_files"],
                            "required": True,
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Text pattern to search",
                            "required": False,
                        },
                        "glob_pattern": {
                            "type": "string",
                            "description": "File glob (e.g. **/*.py)",
                            "default": "*",
                        },
                        "is_regex": {
                            "type": "boolean",
                            "description": "Use regex for search",
                            "default": False,
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Lines of context around matches",
                            "default": 2,
                        },
                    },
                    example_usage="@plan search for 'main' in all python files",
                    typical_duration_seconds=10,
                    can_stream_output=False,
                    when_to_use="Use for finding where specific text is used across the project or listing project files",
                    capabilities=["project_grep", "file_globbing", "context_search"],
                ),
            )

            # Register PlanningEngine
            from src.core.planning.planning_engine import PlanningEngine

            planning_instance = PlanningEngine(llm_client=None)
            self.register_tool(
                name="PlanningEngine",
                tool_instance=planning_instance,
                metadata=ToolMetadata(
                    name="PlanningEngine",
                    category=ToolCategory.SYSTEM_EXECUTION,
                    description="Generate multi-step plans for complex goals",
                    long_description="Breaks down complex requests into a sequence of executable tool calls with dependency tracking.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "task_description": {
                            "type": "string",
                            "description": "The goal to plan for",
                            "required": True,
                        },
                        "limitations": {
                            "type": "string",
                            "description": "Optional constraints",
                            "required": False,
                        },
                    },
                    example_usage="@plan refactor the authentication module",
                    typical_duration_seconds=15,
                    can_stream_output=False,
                    when_to_use="Use for complex tasks that require multiple steps across different tools",
                    capabilities=[
                        "multi_step_planning",
                        "goal_decomposition",
                        "dependency_management",
                    ],
                ),
            )

            # Register AutoHealer
            from src.tools.enhanced.auto_healer import AutoHealer

            healer_instance = AutoHealer()
            self.register_tool(
                name="AutoHealer",
                tool_instance=healer_instance,
                metadata=ToolMetadata(
                    name="AutoHealer",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Autonomous error diagnosis and repair",
                    long_description="Analyzes execution errors and suggest/applies fixes using CodeEditor or SystemExecutor.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": ["analyze"],
                            "required": True,
                        },
                        "error_msg": {
                            "type": "string",
                            "description": "The error message to analyze",
                            "required": True,
                        },
                        "context": {
                            "type": "string",
                            "description": "Context about the failed step",
                            "required": False,
                        },
                    },
                    example_usage="@plan heal the last failed command",
                    typical_duration_seconds=10,
                    can_stream_output=False,
                    when_to_use="Use when a task step fails and needs diagnosis or a fix",
                    capabilities=[
                        "error_analysis",
                        "auto_correction",
                        "fix_suggestion",
                    ],
                ),
            )

            # Register VisualAnalyzer
            from src.tools.enhanced.visual_analyzer import VisualAnalyzer

            visual_instance = VisualAnalyzer()
            self.register_tool(
                name="VisualAnalyzer",
                tool_instance=visual_instance,
                metadata=ToolMetadata(
                    name="VisualAnalyzer",
                    category=ToolCategory.MEDIA_PROCESSING,
                    description="Analyze screen content and UI issues",
                    long_description="Captures screenshots and uses vision LLMs to analyze UI, debug visual issues, or describe screen content.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": ["analyze_screen", "capture_only"],
                            "required": True,
                        },
                        "prompt": {
                            "type": "string",
                            "description": "What to look for or analyze",
                            "required": False,
                        },
                    },
                    example_usage="@plan describe what is on my screen right now",
                    typical_duration_seconds=20,
                    can_stream_output=False,
                    when_to_use="Use for UI debugging, checking layout, or when the user asks 'what do you see' or 'fix this UI error'",
                    capabilities=["screen_capture", "ui_analysis", "visual_debugging"],
                ),
            )

            # ===== AUTONOMOUS TOOLS (NEW) =====
            logger.info("Registering autonomous tools...")

            # Register FileManager
            from src.tools.autonomous.file_manager import FileManager

            file_manager = FileManager()
            self.register_tool(
                name="FileManager",
                tool_instance=file_manager,
                metadata=ToolMetadata(
                    name="FileManager",
                    category=ToolCategory.FILE_MANAGEMENT,
                    description="Autonomous file and directory management",
                    long_description="Read, write, list, search, and manage files and directories with safety checks and path validation.",
                    risk_level=ToolRisk.MEDIUM,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "read",
                                "write",
                                "list",
                                "search",
                                "info",
                                "mkdir",
                                "delete",
                            ],
                            "required": True,
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to file",
                            "required": False,
                        },
                        "dir_path": {
                            "type": "string",
                            "description": "Path to directory",
                            "required": False,
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write",
                            "required": False,
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query",
                            "required": False,
                        },
                        "pattern": {
                            "type": "string",
                            "description": "File pattern filter",
                            "required": False,
                        },
                    },
                    example_usage="@plan read the contents of config.json",
                    typical_duration_seconds=5,
                    can_stream_output=False,
                    when_to_use="Use for file operations: reading files, writing files, listing directories, searching for files or content within files",
                    capabilities=[
                        "read_files",
                        "write_files",
                        "list_directories",
                        "search_files",
                        "file_info",
                        "create_directories",
                    ],
                ),
            )

            # Register ProjectScanner
            from src.tools.autonomous.project_scanner import ProjectScanner

            project_scanner = ProjectScanner()
            self.register_tool(
                name="ProjectScanner",
                tool_instance=project_scanner,
                metadata=ToolMetadata(
                    name="ProjectScanner",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Intelligent project analysis and detection",
                    long_description="Analyze project structure, detect programming languages, frameworks, entry points, dependencies, and generate recommendations.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": ["scan"],
                            "required": True,
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root",
                            "required": False,
                        },
                    },
                    example_usage="@plan analyze the project structure",
                    typical_duration_seconds=10,
                    can_stream_output=False,
                    when_to_use="Use when you need to understand a codebase: detecting project type, finding entry points, analyzing dependencies, or getting project recommendations",
                    capabilities=[
                        "project_detection",
                        "language_detection",
                        "framework_detection",
                        "dependency_analysis",
                        "entry_point_detection",
                    ],
                ),
            )

            # Register TaskTracker
            from src.tools.autonomous.task_tracker import TaskTracker

            task_tracker = TaskTracker()
            self.register_tool(
                name="TaskTracker",
                tool_instance=task_tracker,
                metadata=ToolMetadata(
                    name="TaskTracker",
                    category=ToolCategory.SYSTEM_EXECUTION,
                    description="Multi-step task planning and execution tracking",
                    long_description="Create plans with multiple tasks, track execution progress, handle dependencies between tasks, and persist state between sessions.",
                    risk_level=ToolRisk.MEDIUM,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "create_plan",
                                "add_task",
                                "execute_plan",
                                "get_summary",
                                "list_plans",
                                "cancel_plan",
                                "retry_failed",
                                "delete_plan",
                            ],
                            "required": True,
                        },
                        "plan_id": {
                            "type": "string",
                            "description": "Plan identifier",
                            "required": False,
                        },
                        "name": {
                            "type": "string",
                            "description": "Plan/task name",
                            "required": False,
                        },
                        "description": {
                            "type": "string",
                            "description": "Description",
                            "required": False,
                        },
                        "tool": {
                            "type": "string",
                            "description": "Tool to use for task",
                            "required": False,
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Tool parameters",
                            "required": False,
                        },
                        "depends_on": {
                            "type": "array",
                            "description": "Task dependencies",
                            "required": False,
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "required": False,
                        },
                    },
                    example_usage="@plan create a plan to refactor the authentication module",
                    typical_duration_seconds=30,
                    can_stream_output=True,
                    when_to_use="Use for complex multi-step operations that require planning, task dependencies, progress tracking, or execution across multiple tools",
                    capabilities=[
                        "plan_creation",
                        "task_scheduling",
                        "progress_tracking",
                        "dependency_management",
                        "retry_logic",
                        "persistence",
                    ],
                ),
            )

            # Register CodeRefactor
            from src.tools.autonomous.code_refactor import CodeRefactor

            code_refactor = CodeRefactor()
            self.register_tool(
                name="CodeRefactor",
                tool_instance=code_refactor,
                metadata=ToolMetadata(
                    name="CodeRefactor",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Intelligent code refactoring with impact analysis",
                    long_description="Rename symbols, extract methods, optimize imports, convert to async, add type hints, and perform other automated code refactoring operations with automatic backup creation.",
                    risk_level=ToolRisk.MEDIUM,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "rename",
                                "extract_method",
                                "optimize_imports",
                                "convert_to_async",
                                "add_type_hints",
                                "convert_to_comprehension",
                            ],
                            "required": True,
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to file to refactor",
                            "required": True,
                        },
                        "old_name": {
                            "type": "string",
                            "description": "Current name (for rename)",
                            "required": False,
                        },
                        "new_name": {
                            "type": "string",
                            "description": "New name (for rename)",
                            "required": False,
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Start line number",
                            "required": False,
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "End line number",
                            "required": False,
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Function name (for async conversion)",
                            "required": False,
                        },
                    },
                    example_usage="@plan rename calculate_sum to sum_numbers in utils.py",
                    typical_duration_seconds=10,
                    can_stream_output=False,
                    when_to_use="Use for code refactoring operations: renaming symbols, extracting methods, cleaning up imports, converting code patterns, adding type hints",
                    capabilities=[
                        "rename_symbol",
                        "extract_method",
                        "optimize_imports",
                        "convert_to_async",
                        "add_type_hints",
                        "convert_to_comprehension",
                        "backup_creation",
                    ],
                ),
            )

            # Register TestRunner
            from src.tools.autonomous.test_runner import TestRunner

            test_runner = TestRunner()
            self.register_tool(
                name="TestRunner",
                tool_instance=test_runner,
                metadata=ToolMetadata(
                    name="TestRunner",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Test execution and coverage analysis",
                    long_description="Detect testing frameworks, run tests, analyze code coverage, identify missing tests, and generate basic test templates automatically.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "run",
                                "run_tests",
                                "coverage",
                                "analyze_coverage",
                                "find_missing",
                                "missing_tests",
                            ],
                            "required": True,
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root",
                            "required": True,
                        },
                        "test_path": {
                            "type": "string",
                            "description": "Specific test path (optional)",
                            "required": False,
                        },
                        "framework": {
                            "type": "string",
                            "enum": ["pytest", "unittest", "jest", "mocha", "vitest"],
                            "required": False,
                        },
                    },
                    example_usage="@plan run tests and check coverage",
                    typical_duration_seconds=60,
                    can_stream_output=True,
                    when_to_use="Use for running tests, analyzing test coverage, finding modules without tests, or detecting test frameworks",
                    capabilities=[
                        "detect_framework",
                        "run_tests",
                        "coverage_analysis",
                        "find_missing_tests",
                        "test_reporting",
                    ],
                ),
            )

            # Register DependencyManager
            from src.tools.autonomous.dependency_manager import DependencyManager

            dep_manager = DependencyManager()
            self.register_tool(
                name="DependencyManager",
                tool_instance=dep_manager,
                metadata=ToolMetadata(
                    name="DependencyManager",
                    category=ToolCategory.SYSTEM_EXECUTION,
                    description="Manage project dependencies (pip, npm, poetry)",
                    long_description="Detect package managers, install/update dependencies, audit security vulnerabilities, find unused dependencies, and search package information.",
                    risk_level=ToolRisk.MEDIUM,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "list",
                                "list_dependencies",
                                "install",
                                "add",
                                "update",
                                "upgrade",
                                "audit",
                                "check_security",
                                "find_unused",
                                "unused",
                                "search",
                                "search_package",
                            ],
                            "required": True,
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root",
                            "required": True,
                        },
                        "package_name": {
                            "type": "string",
                            "description": "Package name to install/update",
                            "required": False,
                        },
                        "version": {
                            "type": "string",
                            "description": "Specific version",
                            "required": False,
                        },
                        "dev": {
                            "type": "boolean",
                            "description": "Is dev dependency",
                            "default": False,
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query",
                            "required": False,
                        },
                    },
                    example_usage="@plan install requests and check for vulnerabilities",
                    typical_duration_seconds=45,
                    can_stream_output=True,
                    when_to_use="Use for managing dependencies: installing packages, updating versions, auditing security, finding unused deps, or searching packages",
                    capabilities=[
                        "detect_package_manager",
                        "install_dependencies",
                        "update_dependencies",
                        "audit_security",
                        "find_unused_deps",
                        "search_packages",
                    ],
                ),
            )

            # Register GitTools (Autonomous Skill)
            from src.tools.autonomous.git_tools import GitTools

            git_tool = GitTools()
            self.register_tool(
                name="GitTools",
                tool_instance=git_tool,
                metadata=ToolMetadata(
                    name="GitTools",
                    category=ToolCategory.VERSION_CONTROL,
                    description="Git repository management",
                    long_description="Execute git operations: status, log, diff, branch management, commits, clone, and remote operations. Includes safety checks for protected branches.",
                    risk_level=ToolRisk.MEDIUM,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "status",
                                "log",
                                "diff",
                                "branch",
                                "commit",
                                "clone",
                                "remote",
                                "pull",
                                "push",
                            ],
                            "required": True,
                        },
                        "repo_path": {
                            "type": "string",
                            "description": "Path to git repository",
                            "required": False,
                        },
                        "repo_url": {
                            "type": "string",
                            "description": "Repository URL for clone",
                            "required": False,
                        },
                        "message": {
                            "type": "string",
                            "description": "Commit message",
                            "required": False,
                        },
                        "branch_name": {
                            "type": "string",
                            "description": "Branch name",
                            "required": False,
                        },
                        "sub_action": {
                            "type": "string",
                            "enum": ["list", "create", "switch"],
                            "description": "Branch sub-action",
                            "required": False,
                        },
                        "target": {
                            "type": "string",
                            "description": "Diff target (commit/branch)",
                            "required": False,
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "Preview without executing",
                            "default": False,
                        },
                    },
                    example_usage="@plan check git status and show recent commits",
                    typical_duration_seconds=10,
                    can_stream_output=False,
                    when_to_use="Use for git operations: checking status, viewing history, comparing changes, managing branches, creating commits, or cloning repositories",
                    capabilities=[
                        "git_status",
                        "git_log",
                        "git_diff",
                        "git_branch",
                        "git_commit",
                        "git_clone",
                        "git_remote",
                        "git_pull",
                        "git_push",
                    ],
                ),
            )

            # Register DocManager (Autonomous Skill)
            from src.tools.autonomous.doc_manager import DocManager

            doc_manager = DocManager()
            self.register_tool(
                name="DocManager",
                tool_instance=doc_manager,
                metadata=ToolMetadata(
                    name="DocManager",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Documentation generation and management",
                    long_description="Generate README files, add docstrings to code, create API documentation, check documentation coverage, and update changelogs automatically.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "generate_readme",
                                "add_docstrings",
                                "generate_api_docs",
                                "document_module",
                                "update_changelog",
                                "check_doc_coverage",
                            ],
                            "required": True,
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to project",
                            "required": False,
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to specific file",
                            "required": False,
                        },
                        "module_path": {
                            "type": "string",
                            "description": "Path to module",
                            "required": False,
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output file path",
                            "required": False,
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "Preview without changes",
                            "default": True,
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Process recursively",
                            "default": False,
                        },
                    },
                    example_usage="@plan generate README for this project",
                    typical_duration_seconds=15,
                    can_stream_output=False,
                    when_to_use="Use for generating documentation: README files, docstrings, API docs, or checking documentation coverage",
                    capabilities=[
                        "generate_readme",
                        "add_docstrings",
                        "generate_api_docs",
                        "document_module",
                        "update_changelog",
                        "check_doc_coverage",
                    ],
                ),
            )

            # Register GraphManager (Autonomous Skill)
            from src.tools.autonomous.graph_manager import GraphManager

            graph_manager = GraphManager()
            self.register_tool(
                name="GraphManager",
                tool_instance=graph_manager,
                metadata=ToolMetadata(
                    name="GraphManager",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Graph visualization and dependency analysis",
                    long_description="Generate dependency graphs between files, class diagrams, call graphs, project structure visualization, metrics charts, and plan flow diagrams.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "dependency_graph",
                                "class_diagram",
                                "call_graph",
                                "project_structure",
                                "metrics_chart",
                                "plan_flow",
                                "git_history_graph",
                                "coverage_heatmap",
                            ],
                            "required": True,
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to project",
                            "required": False,
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to specific file",
                            "required": False,
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Analysis depth",
                            "default": 3,
                        },
                        "chart_type": {
                            "type": "string",
                            "enum": ["complexity", "lines"],
                            "description": "Chart type",
                            "default": "complexity",
                        },
                    },
                    example_usage="@plan show me the dependency graph of this project",
                    typical_duration_seconds=10,
                    can_stream_output=False,
                    when_to_use="Use for visualizing project structure, dependencies between files, class hierarchies, or generating metrics charts",
                    capabilities=[
                        "dependency_graph",
                        "class_diagram",
                        "call_graph",
                        "project_structure",
                        "metrics_chart",
                        "plan_flow",
                        "git_history_graph",
                        "coverage_heatmap",
                    ],
                ),
            )

            logger.info("Autonomous tools registered successfully")

            # Register WorkspaceManager (Phase 4)
            from src.tools.enhanced.workspace_manager import WorkspaceManager

            workspace_instance = WorkspaceManager()
            self.register_tool(
                name="WorkspaceManager",
                tool_instance=workspace_instance,
                metadata=ToolMetadata(
                    name="WorkspaceManager",
                    category=ToolCategory.FILE_MANAGEMENT,
                    description="Manage your own Workspace (Alma, Mente, Destrezas, Taller)",
                    long_description="Autonomous engine to record learnings, write experimental scripts in Taller, and read your own Persona in Alma.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "read_file",
                                "write_file",
                                "append_learning",
                                "list_contents",
                            ],
                            "required": True,
                        },
                        "filepath": {
                            "type": "string",
                            "description": "Path relative to Workspace root",
                            "required": False,
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write",
                            "required": False,
                        },
                        "topic": {
                            "type": "string",
                            "description": "Topic to learn",
                            "required": False,
                        },
                        "insight": {
                            "type": "string",
                            "description": "What you learned about the topic",
                            "required": False,
                        },
                        "folder": {
                            "type": "string",
                            "description": "Folder to list",
                            "required": False,
                        },
                    },
                    example_usage="@plan Record a learning about python asyncio in my Mente",
                    typical_duration_seconds=5,
                    can_stream_output=False,
                    when_to_use="Always use this when saving a learning, experimenting with scripts, or reading your own rules.",
                    capabilities=[
                        "self_reflection",
                        "autonomous_learning",
                        "workspace_management",
                    ],
                ),
            )

            # ===== PHASE 3: ECOSYSTEM TOOLS =====
            logger.info("Registering Phase 3 ecosystem tools...")

            try:
                # WebBrowser (autonomous skill using requests/bs4)
                from src.tools.autonomous.web_browser import WebBrowser

                web_browser = WebBrowser()
                self.register_tool(
                    name="WebBrowser",
                    tool_instance=web_browser,
                    metadata=ToolMetadata(
                        name="WebBrowser",
                        category=ToolCategory.WEB_AUTOMATION,
                        description="Autonomous web browsing and content extraction",
                        long_description="Visit websites, extract text content, extract links, search the web using DuckDuckGo, and get page titles. Uses requests and BeautifulSoup (fallback to regex if not available).",
                        risk_level=ToolRisk.MEDIUM,
                        parameters={
                            "action": {
                                "type": "string",
                                "enum": [
                                    "visit",
                                    "search",
                                    "extract_links",
                                    "extract_text",
                                    "find_element",
                                    "get_title",
                                ],
                                "required": True,
                            },
                            "url": {
                                "type": "string",
                                "description": "Website URL",
                                "required": False,
                            },
                            "query": {
                                "type": "string",
                                "description": "Search query",
                                "required": False,
                            },
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for targeting elements",
                                "required": False,
                            },
                            "extract_text": {
                                "type": "boolean",
                                "description": "Extract clean text content",
                                "default": True,
                            },
                            "extract_links": {
                                "type": "boolean",
                                "description": "Extract all links",
                                "default": True,
                            },
                        },
                        example_usage="@plan visit https://example.com and extract all links",
                        typical_duration_seconds=10,
                        can_stream_output=False,
                        when_to_use="Use for visiting websites, extracting content, searching the web, or getting page information",
                        capabilities=[
                            "visit_url",
                            "web_search",
                            "extract_links",
                            "extract_text",
                            "find_elements",
                            "get_title",
                        ],
                    ),
                )

                # Research (Autonomous deep research tool)
                from src.tools.autonomous.research import Research

                research = Research()
                self.register_tool(
                    name="Research",
                    tool_instance=research,
                    metadata=ToolMetadata(
                        name="Research",
                        category=ToolCategory.RESEARCH,
                        description="Deep research with synthesis and fact-checking",
                        long_description="Perform deep research on topics, synthesize information from multiple sources, fact-check claims, compare sources, and identify contradictions. Includes credibility scoring.",
                        risk_level=ToolRisk.LOW,
                        parameters={
                            "action": {
                                "type": "string",
                                "enum": [
                                    "quick_search",
                                    "deep_research",
                                    "fact_check",
                                    "compare_sources",
                                    "summarize_topic",
                                    "find_expert_sources",
                                ],
                                "required": True,
                            },
                            "query": {
                                "type": "string",
                                "description": "Research query",
                                "required": False,
                            },
                            "topic": {
                                "type": "string",
                                "description": "Topic for summarization",
                                "required": False,
                            },
                            "claim": {
                                "type": "string",
                                "description": "Claim to fact-check",
                                "required": False,
                            },
                            "urls": {
                                "type": "array",
                                "description": "URLs to compare",
                                "required": False,
                            },
                            "num_sources": {
                                "type": "integer",
                                "description": "Number of sources to analyze",
                                "default": 5,
                            },
                            "include_synthesis": {
                                "type": "boolean",
                                "description": "Include synthesized summary",
                                "default": True,
                            },
                        },
                        example_usage="@plan research Python asyncio best practices with deep analysis",
                        typical_duration_seconds=30,
                        can_stream_output=False,
                        when_to_use="Use for deep research, fact-checking claims, comparing multiple sources, finding authoritative sources, or synthesizing information on a topic",
                        capabilities=[
                            "quick_search",
                            "deep_research",
                            "fact_check",
                            "compare_sources",
                            "summarize_topic",
                            "find_expert_sources",
                            "credibility_scoring",
                            "contradiction_detection",
                        ],
                    ),
                )

                # ImageProcessor (requires ComfyUI)
                from src.tools.ecosystem import ImageProcessor

                if False:  # Temporarily disabled as per user request
                    image_proc = ImageProcessor()
                    self.register_tool(
                        name="ImageProcessor",
                        tool_instance=image_proc,
                        metadata=ToolMetadata(
                            name="ImageProcessor",
                            category=ToolCategory.MEDIA_PROCESSING,
                            description="Generate and edit images",
                            long_description="Generate images from text prompts using Stable Diffusion via ComfyUI",
                            risk_level=ToolRisk.LOW,
                            parameters={
                                "prompt": {
                                    "type": "string",
                                    "description": "Text prompt for generation",
                                    "required": True,
                                },
                                "width": {
                                    "type": "integer",
                                    "description": "Image width",
                                    "default": 512,
                                },
                                "height": {
                                    "type": "integer",
                                    "description": "Image height",
                                    "default": 512,
                                },
                                "steps": {
                                    "type": "integer",
                                    "description": "Quality steps",
                                    "default": 20,
                                },
                                "output_path": {
                                    "type": "string",
                                    "description": "Save path",
                                    "required": False,
                                },
                            },
                            example_usage="@plan generate concept art for dark fantasy castle",
                            typical_duration_seconds=30,
                            can_stream_output=False,
                            when_to_use="Use for generating concept art, illustrations, diagrams, creative visuals from text descriptions",
                            capabilities=[
                                "text2image",
                                "image_generation",
                                "creative_art",
                            ],
                        ),
                    )
                else:
                    logger.info("ImageProcessor not available (missing dependencies)")

                logger.info("Phase 3 ecosystem tools registered successfully")

            except Exception as e:
                logger.warning(f"Some Phase 3 tools failed to register: {e}")
                logger.info("Continuing with available tools...")

            # ===== END PHASE 3 =====

            # ===== NEW SKILLS (2026-03-04) =====
            logger.info("Registering new skills...")

            # Register NoteTaker
            from src.tools.autonomous.note_taker import NoteTaker

            note_taker = NoteTaker()
            self.register_tool(
                name="NoteTaker",
                tool_instance=note_taker,
                metadata=ToolMetadata(
                    name="NoteTaker",
                    category=ToolCategory.SYSTEM_EXECUTION,
                    description="Take notes and extract TODOs automatically",
                    long_description="Create notes during conversations, extract TODOs and decisions from text, search previous notes, and manage reminders with persistent storage.",
                    risk_level=ToolRisk.LOW,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": [
                                "create",
                                "extract_todos",
                                "extract_decisions",
                                "search",
                                "list",
                                "get",
                                "update",
                                "delete",
                                "stats",
                            ],
                            "required": True,
                        },
                        "content": {
                            "type": "string",
                            "description": "Note content",
                            "required": False,
                        },
                        "note_type": {
                            "type": "string",
                            "enum": [
                                "general",
                                "todo",
                                "decision",
                                "idea",
                                "code_snippet",
                                "link",
                                "reminder",
                            ],
                            "default": "general",
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to analyze for extraction",
                            "required": False,
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query",
                            "required": False,
                        },
                        "note_id": {
                            "type": "string",
                            "description": "Note ID for get/update/delete",
                            "required": False,
                        },
                        "tags": {
                            "type": "array",
                            "description": "List of tags",
                            "required": False,
                        },
                        "project": {
                            "type": "string",
                            "description": "Project name",
                            "required": False,
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "required": False,
                        },
                    },
                    example_usage="@plan take a note about the authentication refactor",
                    typical_duration_seconds=2,
                    can_stream_output=False,
                    when_to_use="Use for taking notes during conversations, extracting TODOs from text, saving decisions, or searching previous notes",
                    capabilities=[
                        "create_notes",
                        "extract_todos",
                        "extract_decisions",
                        "search_notes",
                        "tag_management",
                    ],
                ),
            )

            # Register AutoFixer
            from src.tools.autonomous.auto_fixer import AutoFixer

            auto_fixer = AutoFixer()
            self.register_tool(
                name="AutoFixer",
                tool_instance=auto_fixer,
                metadata=ToolMetadata(
                    name="AutoFixer",
                    category=ToolCategory.CODE_ANALYSIS,
                    description="Detect and auto-fix code errors",
                    long_description="Analyze Python code for syntax errors, missing imports, indentation issues, common bugs, and style problems. Can suggest or automatically apply fixes with backup creation.",
                    risk_level=ToolRisk.MEDIUM,
                    parameters={
                        "action": {
                            "type": "string",
                            "enum": ["analyze", "fix", "fix_file"],
                            "required": True,
                        },
                        "code": {
                            "type": "string",
                            "description": "Python code to analyze",
                            "required": False,
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file",
                            "required": False,
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "Preview changes without applying",
                            "default": True,
                        },
                    },
                    example_usage="@plan analyze and fix syntax errors in this file",
                    typical_duration_seconds=5,
                    can_stream_output=False,
                    when_to_use="Use when code has syntax errors, missing imports, indentation problems, or style issues that need correction",
                    capabilities=[
                        "syntax_analysis",
                        "import_detection",
                        "indentation_fix",
                        "style_correction",
                        "auto_fix",
                        "backup_creation",
                    ],
                ),
            )

            logger.info("New skills registered successfully")
            # ===== END NEW SKILLS =====

            # ===== FASES A-E INTEGRATION =====
            logger.info("Registering Fases A-E tools...")
            try:
                from src.tools.fases_integration import register_all_fases_tools

                fases_count = register_all_fases_tools(self)
                logger.info(f"Registered {fases_count} Fases A-E tools")
            except Exception as e:
                logger.warning(f"Some Fases A-E tools failed to register: {e}")
                logger.info("Continuing with available tools...")
            # ===== END FASES A-E =====

            # ===== PYTORCH GAUNTLET TOOL (FASE A+B) =====
            logger.info("Registering PyTorch Tool...")
            try:
                from src.tools.autonomous.pytorch_tool import PyTorchTool

                pytorch_tool = PyTorchTool()
                self.register_tool(
                    name="PyTorchTool",
                    tool_instance=pytorch_tool,
                    metadata=ToolMetadata(
                        name="PyTorchTool",
                        category=ToolCategory.CODE_ANALYSIS,
                        description="Generate and train PyTorch models (Gauntlet Mode)",
                        long_description="Generate PyTorch neural network code, save models, and execute full training pipelines. Supports templates like SimpleClassifier, DeepClassifier, and WideResNet_CIFAR. Gauntlet mode provides end-to-end automation from generation to training.",
                        risk_level=ToolRisk.MEDIUM,
                        parameters={
                            "action": {
                                "type": "string",
                                "enum": [
                                    "generate_model",
                                    "save_model",
                                    "run_training",
                                    "gauntlet",
                                    "list_templates",
                                    "stop_training",
                                ],
                                "required": True,
                                "description": "Action to execute",
                            },
                            # Model generation params
                            "model_name": {
                                "type": "string",
                                "description": "Name for the model class",
                                "required": False,
                            },
                            "input_size": {
                                "type": "integer",
                                "description": "Input layer size",
                                "default": 784,
                            },
                            "hidden_size": {
                                "type": "integer",
                                "description": "Hidden layer size",
                                "default": 128,
                            },
                            "output_size": {
                                "type": "integer",
                                "description": "Output layer size",
                                "default": 10,
                            },
                            "layers": {
                                "type": "integer",
                                "description": "Number of hidden layers",
                                "default": 2,
                            },
                            # Training params
                            "template": {
                                "type": "string",
                                "enum": [
                                    "SimpleClassifier",
                                    "DeepClassifier",
                                    "WideResNet_CIFAR",
                                ],
                                "description": "Template for gauntlet mode",
                                "default": "WideResNet_CIFAR",
                            },
                            "script_path": {
                                "type": "string",
                                "description": "Path to training script (for run_training)",
                            },
                            "epochs": {
                                "type": "integer",
                                "description": "Number of training epochs",
                                "default": 50,
                            },
                            "batch_size": {
                                "type": "integer",
                                "description": "Training batch size",
                                "default": 128,
                            },
                            "lr": {
                                "type": "number",
                                "description": "Learning rate",
                                "default": 0.1,
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Training timeout in seconds",
                                "default": 1800,
                            },
                            "live_output": {
                                "type": "boolean",
                                "description": "Capture live training output",
                                "default": True,
                            },
                            "auto": {
                                "type": "boolean",
                                "description": "Auto-execute gauntlet pipeline",
                                "default": True,
                            },
                            # File params
                            "filename": {
                                "type": "string",
                                "description": "Filename to save model",
                                "required": False,
                            },
                            "dataset": {
                                "type": "string",
                                "description": "Dataset for training",
                                "default": "cifar10",
                            },
                        },
                        example_usage="@pytorch gauntlet --template WideResNet_CIFAR --epochs 50 --auto",
                        typical_duration_seconds=1200,
                        can_stream_output=True,
                        when_to_use="Use for generating PyTorch code, training models end-to-end, or running ML experiments. Gauntlet mode automates the full pipeline.",
                        capabilities=[
                            "generate_pytorch_code",
                            "save_models",
                            "create_templates",
                            "ml_workflow",
                            "neural_network_generation",
                            "training_execution",
                            "gauntlet_pipeline",
                            "live_metrics",
                        ],
                    ),
                )
                logger.info("PyTorch Tool registered successfully (Fase A+B)")
            except Exception as e:
                logger.warning(f"PyTorch Tool failed to register: {e}")
            # ===== END PYTORCH TOOL =====

            # ===== PANTHEON AGENTS (Fase Multi-Agente) =====
            try:
                from src.core.agent_loop import AgentLoop
                from src.core.agent_router import AgentRouter

                agent_router = AgentRouter()
                self.register_tool(
                    name="AgentRouter",
                    tool_instance=agent_router,
                    metadata=ToolMetadata(
                        name="AgentRouter",
                        category=ToolCategory.RESEARCH,
                        description="Router de agentes del Panteón (Eva, Adán, Lucifer)",
                        long_description="Decide qué agente especializado usar basado en la tarea: Eva (análisis), Adán (código), Lucifer (creativo)",
                        risk_level=ToolRisk.LOW,
                        parameters={
                            "task": {
                                "type": "string",
                                "description": "Tarea a ejecutar",
                                "required": True,
                            },
                            "agent_name": {
                                "type": "string",
                                "description": "Nombre del agente (eva, adan, lucifer, grok)",
                                "required": False,
                            },
                            "context": {
                                "type": "string",
                                "description": "Contexto adicional",
                                "required": False,
                            },
                        },
                        example_usage="@plan route this analysis task to the appropriate agent",
                        typical_duration_seconds=60,
                        when_to_use="Use when you need to delegate to specialized agents based on task type",
                        capabilities=[
                            "agent_selection",
                            "task_delegation",
                            "eva_agent",
                            "adan_agent",
                            "odin_agent",
                        ],
                    ),
                )
                logger.info("AgentRouter registered successfully (Panteón)")

                agent_loop = AgentLoop(tool_registry=self)
                self.register_tool(
                    name="AgentLoop",
                    tool_instance=agent_loop,
                    metadata=ToolMetadata(
                        name="AgentLoop",
                        category=ToolCategory.RESEARCH,
                        description="Loop de ejecución multi-agente",
                        long_description="Encadena agentes del Panteón para completar objetivos complejos",
                        risk_level=ToolRisk.MEDIUM,
                        parameters={
                            "objetivo": {
                                "type": "string",
                                "description": "Objetivo a cumplir",
                                "required": True,
                            },
                            "context": {
                                "type": "string",
                                "description": "Contexto inicial",
                                "required": False,
                            },
                        },
                        example_usage="@plan run agent loop for comprehensive analysis",
                        typical_duration_seconds=120,
                        when_to_use="Use for complex tasks requiring multiple agent capabilities",
                        capabilities=[
                            "multi_agent",
                            "agent_chaining",
                            "iterative_execution",
                        ],
                    ),
                )
                logger.info("AgentLoop registered successfully (Panteón)")

            except Exception as e:
                logger.warning(f"Panteón Agents failed to register: {e}")
            # ===== END PANTHEON AGENTS =====

            self._initialized = True
            logger.info(f"ToolRegistry initialized with {len(self._tools)} tools")

        except ImportError as e:
            logger.error(f"Failed to import tools: {e}")
            raise

    def register_tool(self, name: str, tool_instance: object, metadata: ToolMetadata):
        """
        Register a new tool in the registry

        Args:
            name: Unique tool name
            tool_instance: Tool instance with execute() method
            metadata: Tool metadata
        """
        logger.info(f"Registering tool: {name}")

        if name in self._tools:
            logger.warning(f"Tool {name} already registered, overwriting")

        self._tools[name] = tool_instance
        self._metadata[name] = metadata

        # Index by category
        if metadata.category not in self._categories:
            self._categories[metadata.category] = []
        self._categories[metadata.category].append(name)

        logger.debug(f"Tool {name} registered successfully")

    def get_tool(self, name: str) -> Optional[object]:
        """Get tool instance by name"""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name"""
        return self._metadata.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get tool names in a specific category"""
        return self._categories.get(category, [])

    def get_all_metadata(self) -> Dict[str, ToolMetadata]:
        """Get metadata for all tools"""
        return self._metadata.copy()

    def select_tool(
        self, description: str, required_category: Optional[ToolCategory] = None
    ) -> List[str]:
        """
        Select appropriate tools based on description and category

        Args:
            description: Description of what needs to be done
            required_category: Optional category filter

        Returns:
            List of tool names that match the description
        """
        # Filter by category first if specified
        tool_names = []
        if required_category:
            tool_names = self.get_tools_by_category(required_category)
        else:
            tool_names = self.list_tools()

        # Score based on description keywords
        desc_lower = description.lower()
        scored_tools = []

        for tool_name in tool_names:
            metadata = self.get_metadata(tool_name)
            if not metadata:
                continue

            score = 0

            # Check name matches
            if tool_name.lower() in desc_lower:
                score += 10

            # Check description matches
            if any(
                keyword in desc_lower
                for keyword in metadata.description.lower().split()
            ):
                score += 5

            # Check capabilities match
            for capability in metadata.capabilities:
                if capability.lower() in desc_lower:
                    score += 7

            # Check when_to_use matches
            if any(
                keyword in desc_lower
                for keyword in metadata.when_to_use.lower().split()
            ):
                score += 3

            scored_tools.append((tool_name, score))

        # Sort by score and return top matches
        scored_tools.sort(key=lambda x: x[1], reverse=True)

        # Return only tools with positive score
        top_tools = [tool for tool, score in scored_tools if score > 5]

        # If no high-confidence matches, return all tools as fallback
        return top_tools if top_tools else tool_names

    def get_tools_for_planning(self) -> List[Dict[str, Any]]:
        """
        Get all tools formatted for planning context

        Returns:
            List of tool descriptions for LLM context
        """
        tools_info = []

        for tool_name, metadata in self._metadata.items():
            tool_info = {
                "name": metadata.name,
                "category": metadata.category.value,
                "description": metadata.description,
                "long_description": metadata.long_description,
                "risk_level": metadata.risk_level.value,
                "when_to_use": metadata.when_to_use,
                "example_usage": metadata.example_usage,
                "typical_duration": metadata.typical_duration_seconds,
                "capabilities": metadata.capabilities,
            }
            tools_info.append(tool_info)

        return tools_info


# Global singleton instance
_tool_registry = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry singleton"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


# === Usage Example ===

if __name__ == "__main__":
    """Demonstrate ToolRegistry functionality"""
    print("Lilith Tool Registry v1.0 Demo")
    print("=" * 60)

    # Initialize registry
    registry = get_tool_registry()
    registry.initialize()

    print(f"\nâœ“ Registered tools: {registry.list_tools()}")
    print(f"âœ“ Tool categories: {list(registry._categories.keys())}")

    # Show metadata for each tool
    print("\n--- TOOL METADATA ---")
    for tool_name in registry.list_tools():
        metadata = registry.get_metadata(tool_name)
        if metadata:
            print(f"\n{tool_name}:")
            print(f"  Category: {metadata.category.value}")
            print(f"  Description: {metadata.description}")
            print(f"  Risk Level: {metadata.risk_level.value}")
            print(f"  Typical Duration: {metadata.typical_duration_seconds}s")
            print(f"  Example: {metadata.example_usage}")
            print(f"  Capabilities: {', '.join(metadata.capabilities[:3])}")

    # Test tool selection
    print("\n--- TOOL SELECTION ---")
    test_descriptions = [
        "I need to check git status",
        "Analyze the project structure",
        "Run a system command",
    ]

    for desc in test_descriptions:
        tools = registry.select_tool(desc)
        print(f"Description: '{desc}' -> Tools: {tools}")

    # Get tools for planning context
    print("\n--- TOOLS FOR PLANNING CONTEXT ---")
    planning_tools = registry.get_tools_for_planning()
    print(f"Tools available: {len(planning_tools)}")
    for tool in planning_tools:
        print(f"  - {tool['name']}: {tool['description']}")

    print("\nâœ“ ToolRegistry demo complete!")
