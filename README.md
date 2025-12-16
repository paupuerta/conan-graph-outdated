# Conan Graph Outdated

Custom Conan commands for managing dependencies and cache.

## Description

This extension provides custom Conan commands:
1. **`conan graph-outdated`** - Check for outdated dependencies in a Conan dependency graph.
2. **`conan cache-cleanup`** - Search the Conan cache for recipes without binary packages and remove them.

## Installation

To install these extensions, copy the command files to your Conan home extensions directory:

```bash
mkdir -p ~/.conan2/extensions/commands
cp extensions/commands/cmd_graph_outdated.py ~/.conan2/extensions/commands/
cp extensions/commands/cmd_cache_cleanup.py ~/.conan2/extensions/commands/
```

Alternatively, you can configure Conan to use this repository directly by setting the `_CONAN_INTERNAL_CUSTOM_COMMANDS_PATH` environment variable (for development/testing purposes only).

## Commands

### conan graph-outdated

Check for outdated dependencies in a Conan dependency graph. This command replicates the `conan graph outdated` functionality from conan-io/conan and lists dependencies in the graph showing newer versions available in remotes.

#### Usage

After installation, the command will be available as:

```bash
conan graph-outdated [path] [options]
```

#### Arguments

- `path` - Path to a folder containing a recipe (conanfile.py or conanfile.txt) or to a recipe file. Defaults to the current directory when no --requires or --tool-requires is given.

#### Options

- `-f, --format {text,json}` - Select the output format (text or json)
- `--check-updates` - Check if there are recipe updates
- `--check-revisions` - Check if there are package revision updates (instead of version updates)
- `--check-recipe-revisions` - Check if there are recipe revision updates (instead of version updates)
- `--build-require` - Whether the provided reference is a build-require
- `-r, --remote` - Look in the specified remote or remotes server
- `-nr, --no-remote` - Do not use remote, resolve exclusively in the cache
- `-u, --update` - Will install newer versions and/or revisions in the local cache
- `-pr, --profile` - Apply the specified profile
- `-l, --lockfile` - Path to a lockfile
- And all other common graph arguments...

#### Examples

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

Check for outdated package revisions (instead of versions):
```bash
conan graph-outdated . --check-revisions
```

Check for outdated recipe revisions (instead of versions):
```bash
conan graph-outdated . --check-recipe-revisions
```

#### Output

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

#### Package Revision Output

When using `--check-revisions`, the output shows package revision information for all packages,
indicating whether each package is up-to-date or outdated. Packages without revision information
(not yet installed) are listed separately.

Example text output:
```
======== Package revisions ========
zlib/1.2.13#abc123:pkg456 [UP-TO-DATE]
    Current revision:  rev1
    Latest in remote(s):  rev1 - conancenter
openssl/3.0.0#def456:pkg789 [OUTDATED]
    Current revision:  rev1
    Latest in remote(s):  rev2 - conancenter

Packages without revision (not yet installed):
    boost/1.82.0
```

Example JSON output:
```json
{
    "packages": {
        "zlib/1.2.13#abc123:pkg456": {
            "current_revision": "rev1",
            "is_outdated": false,
            "latest_remote": {
                "revision": "rev1",
                "remote": "conancenter"
            }
        },
        "openssl/3.0.0#def456:pkg789": {
            "current_revision": "rev1",
            "is_outdated": true,
            "latest_remote": {
                "revision": "rev2",
                "remote": "conancenter"
            }
        }
    },
    "skipped_no_revision": ["boost/1.82.0"]
}
```

#### Recipe Revision Output

When using `--check-recipe-revisions`, the output shows recipe revision information for all recipes,
indicating whether each recipe is up-to-date or outdated. Recipes without revision information
(not yet installed) are listed separately.

Example text output:
```
======== Recipe revisions ========
zlib/1.2.13 [UP-TO-DATE]
    Current revision:  abc123
    Latest in remote(s):  abc123 - conancenter
openssl/3.0.0 [OUTDATED]
    Current revision:  def456
    Latest in remote(s):  ghi789 - conancenter

Recipes without revision (not yet installed):
    boost/1.82.0
```

Example JSON output:
```json
{
    "recipes": {
        "zlib/1.2.13": {
            "current_revision": "abc123",
            "is_outdated": false,
            "latest_remote": {
                "revision": "abc123",
                "remote": "conancenter"
            }
        },
        "openssl/3.0.0": {
            "current_revision": "def456",
            "is_outdated": true,
            "latest_remote": {
                "revision": "ghi789",
                "remote": "conancenter"
            }
        }
    },
    "skipped_no_revision": ["boost/1.82.0"]
}
```

### conan cache-cleanup

Search the Conan cache for recipes without binary packages and automatically remove them. This helps keep your cache clean by removing recipe revisions that have no associated binary packages.

#### Usage

```bash
conan cache-cleanup [options]
```

#### Options

- `-f, --format {text,json}` - Select the output format (text or json)
- `--dry-run` - Show what would be removed without actually removing anything
- `-c, --confirm` - Confirm before removing each recipe/revision

#### Examples

Clean up the cache (remove recipes without binaries):
```bash
conan cache-cleanup
```

Preview what would be removed (dry-run mode):
```bash
conan cache-cleanup --dry-run
```

Get output in JSON format:
```bash
conan cache-cleanup --format=json
```

Confirm before removing each recipe:
```bash
conan cache-cleanup --confirm
```

#### Output

The command provides detailed feedback about the cleanup operation:

**Text output example:**
```
======== Cache Cleanup Results ========
Total recipes/revisions inspected: 10
Recipes/revisions with binaries (kept): 5
Recipes/revisions without binaries (removed): 4
Recipes/revisions skipped: 1

Removed recipes/revisions:
  - zlib/1.2.11#abc123
  - openssl/1.1.1#def456
  - boost/1.75.0#ghi789
  - poco/1.10.1#jkl012

Skipped recipes/revisions:
  - libcurl/7.80.0#mno345

Recipes/revisions kept (have binaries):
  - zlib/1.2.13#xyz789
  - openssl/3.0.0#uvw012
  - boost/1.82.0#rst345
  - libcurl/7.85.0#pqr678
  - poco/1.12.0#nop901
```

**JSON output example:**
```json
{
  "total_inspected": 10,
  "recipes_with_binaries": [
    "zlib/1.2.13#xyz789",
    "openssl/3.0.0#uvw012",
    "boost/1.82.0#rst345",
    "libcurl/7.85.0#pqr678",
    "poco/1.12.0#nop901"
  ],
  "removed": [
    "zlib/1.2.11#abc123",
    "openssl/1.1.1#def456",
    "boost/1.75.0#ghi789",
    "poco/1.10.1#jkl012"
  ],
  "skipped": [
    "libcurl/7.80.0#mno345"
  ],
  "dry_run": false
}
```

#### How It Works

1. **List Cache**: Executes `conan list '*:*' -c -f json` to get all recipes, their revisions, and package information from the Conan cache
2. **Analyze**: Parses the JSON output to identify recipes/revisions with an empty `packages` field (no binaries)
3. **Remove**: Automatically removes identified recipes/revisions using `conan remove` command
4. **Report**: Provides detailed feedback about what was inspected, removed, and skipped

#### Use Cases

- **Free up disk space**: Remove recipe revisions that were downloaded but never built
- **Cache maintenance**: Clean up incomplete or failed builds that left only recipes without binaries
- **CI/CD cleanup**: Automate cache cleanup in continuous integration environments
- **Development workflow**: Keep local cache tidy during development

## Project Structure

```
conan-graph-outdated/
├── README.md
├── extensions/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       ├── cmd_graph_outdated.py
│       └── cmd_cache_cleanup.py
└── tests/
    ├── __init__.py
    └── test_cache_cleanup.py
```

## Testing

To run the unit tests for the cache-cleanup command:

```bash
python3 -m unittest tests/test_cache_cleanup.py
```

Or run all tests:

```bash
python3 -m unittest discover tests
```

## Requirements

- Conan 2.x
- Python 3.6+