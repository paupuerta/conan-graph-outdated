# Conan Graph Outdated

Custom Conan command: `conan graph-outdated` - A placeholder project to begin development.

## Description

This extension provides a custom Conan command to check for outdated dependencies in a Conan dependency graph.

## Installation

To install this extension, copy the command file to your Conan home extensions directory:

```bash
mkdir -p ~/.conan2/extensions/commands
cp extensions/commands/cmd_graph_outdated.py ~/.conan2/extensions/commands/
```

Alternatively, you can configure Conan to use this repository directly by setting the `_CONAN_INTERNAL_CUSTOM_COMMANDS_PATH` environment variable (for development/testing purposes only).

## Usage

After installation, the command will be available as:

```bash
conan graph-outdated
```

## Development

This is a placeholder implementation. The command currently prints a simple message indicating it is a placeholder for the `conan graph outdated` functionality.

## Project Structure

```
conan-graph-outdated/
├── README.md
└── extensions/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── cmd_graph_outdated.py
```

## Requirements

- Conan 2.x