# Conan Graph Outdated

Custom Conan command: `conan graph-outdated` - Check for outdated dependencies in a Conan dependency graph.

## Description

This extension provides a custom Conan command that replicates the `conan graph outdated` functionality from conan-io/conan. It lists dependencies in the graph and shows newer versions available in remotes.

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
conan graph-outdated [path] [options]
```

### Arguments

- `path` - Path to a folder containing a recipe (conanfile.py or conanfile.txt) or to a recipe file. Defaults to the current directory when no --requires or --tool-requires is given.

### Options

- `-f, --format {text,json}` - Select the output format (text or json)
- `--check-updates` - Check if there are recipe updates
- `--build-require` - Whether the provided reference is a build-require
- `-r, --remote` - Look in the specified remote or remotes server
- `-nr, --no-remote` - Do not use remote, resolve exclusively in the cache
- `-u, --update` - Will install newer versions and/or revisions in the local cache
- `-pr, --profile` - Apply the specified profile
- `-l, --lockfile` - Path to a lockfile
- And all other common graph arguments...

### Examples

Check for outdated dependencies in the current directory:
```bash
conan graph-outdated .
```

Get output in JSON format:
```bash
conan graph-outdated . --format=json
```

Check for outdated dependencies with a specific profile:
```bash
conan graph-outdated . -pr:h myprofile
```

### Output

The command outputs information about outdated dependencies including:
- **Current versions**: Versions found in the local cache
- **Latest in remote(s)**: The latest version available in the configured remotes
- **Version ranges**: Any version ranges that apply to the dependency

Example text output:
```
======== Outdated dependencies ========
zlib
    Current versions:  zlib/1.2.11
    Latest in remote(s):  zlib/1.2.13 - conancenter
```

Example JSON output:
```json
{
    "zlib": {
        "current_versions": ["zlib/1.2.11"],
        "version_ranges": [],
        "latest_remote": {
            "ref": "zlib/1.2.13",
            "remote": "conancenter"
        }
    }
}
```

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