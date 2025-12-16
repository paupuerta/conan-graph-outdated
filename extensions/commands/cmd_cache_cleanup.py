"""
Conan custom command: conan cache-cleanup

This command searches the Conan cache for recipes without binary packages
and removes them automatically.

Usage:
    conan cache-cleanup [options]

Options:
    -f, --format {text,json}  - Select the output format (text or json)
    --dry-run                 - Show what would be removed without actually removing
    -c, --confirm             - Confirm before removing each recipe/revision
"""

import json
import subprocess
import sys

from conan.api.output import cli_out_write, ConanOutput, Color
from conan.cli.command import conan_command
from conan.errors import ConanException


def _run_conan_command(cmd):
    """
    Execute a conan command and return its output.
    
    Args:
        cmd: List of command arguments
        
    Returns:
        str: Command output
        
    Raises:
        ConanException: If command fails
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise ConanException(f"Failed to execute command: {' '.join(cmd)}\n{e.stderr}")
    except FileNotFoundError:
        raise ConanException("Conan command not found. Please ensure Conan is installed.")


def _list_cache_recipes():
    """
    List all recipes and their packages from the Conan cache.
    
    Returns:
        dict: Parsed JSON output from 'conan list' command
        
    Raises:
        ConanException: If listing fails
    """
    cmd = ["conan", "list", "*:*", "-c", "-f", "json"]
    output = _run_conan_command(cmd)
    
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise ConanException(f"Failed to parse JSON output: {e}")


def _identify_recipes_without_binaries(cache_data):
    """
    Identify recipes/revisions that have no binary packages.
    
    Args:
        cache_data: Dictionary containing cache information
        
    Returns:
        dict: Dictionary with three lists:
            - recipes_to_remove: List of recipes/revisions without binaries
            - recipes_with_binaries: List of recipes/revisions with binaries
            - total_inspected: Total number of recipes inspected
    """
    recipes_to_remove = []
    recipes_with_binaries = []
    
    # The structure of conan list output is:
    # {
    #   "Local Cache": {
    #     "recipe_name/version[@user/channel]": {
    #       "revisions": {
    #         "revision_hash": {
    #           "packages": {
    #             "package_id": { ... }
    #           }
    #         }
    #       }
    #     }
    #   }
    # }
    
    local_cache = cache_data.get("Local Cache", {})
    
    for recipe_ref, recipe_data in local_cache.items():
        revisions = recipe_data.get("revisions", {})
        
        for revision_hash, revision_data in revisions.items():
            packages = revision_data.get("packages", {})
            full_ref = f"{recipe_ref}#{revision_hash}"
            
            if not packages or len(packages) == 0:
                # No binary packages for this revision
                recipes_to_remove.append(full_ref)
            else:
                # Has binary packages
                recipes_with_binaries.append(full_ref)
    
    return {
        "recipes_to_remove": recipes_to_remove,
        "recipes_with_binaries": recipes_with_binaries,
        "total_inspected": len(recipes_to_remove) + len(recipes_with_binaries)
    }


def _remove_recipe(recipe_ref, confirm=False):
    """
    Remove a recipe from the Conan cache.
    
    Args:
        recipe_ref: Full recipe reference (e.g., 'name/version#revision')
        confirm: Whether to confirm before removing
        
    Returns:
        bool: True if removed, False if skipped
        
    Raises:
        ConanException: If removal fails
    """
    if confirm:
        response = input(f"Remove {recipe_ref}? (y/n): ").strip().lower()
        if response != 'y':
            return False
    
    cmd = ["conan", "remove", recipe_ref, "-c"]
    _run_conan_command(cmd)
    return True


def _format_text_output(result):
    """Format output in text format."""
    cli_out_write("======== Cache Cleanup Results ========", fg=Color.BRIGHT_MAGENTA)
    cli_out_write(f"Total recipes/revisions inspected: {result['total_inspected']}", 
                  fg=Color.BRIGHT_CYAN)
    cli_out_write(f"Recipes/revisions with binaries (kept): {len(result['recipes_with_binaries'])}", 
                  fg=Color.BRIGHT_GREEN)
    cli_out_write(f"Recipes/revisions without binaries (removed): {len(result['removed'])}", 
                  fg=Color.BRIGHT_YELLOW)
    cli_out_write(f"Recipes/revisions skipped: {len(result['skipped'])}", 
                  fg=Color.BRIGHT_BLUE)
    
    if result.get("dry_run"):
        cli_out_write("\n[DRY RUN] No recipes were actually removed", fg=Color.BRIGHT_MAGENTA)
    
    if result['removed']:
        cli_out_write("\nRemoved recipes/revisions:", fg=Color.BRIGHT_YELLOW)
        for recipe in result['removed']:
            cli_out_write(f"  - {recipe}", fg=Color.BRIGHT_CYAN)
    
    if result['skipped']:
        cli_out_write("\nSkipped recipes/revisions:", fg=Color.BRIGHT_BLUE)
        for recipe in result['skipped']:
            cli_out_write(f"  - {recipe}", fg=Color.BRIGHT_CYAN)
    
    if result['recipes_with_binaries']:
        cli_out_write("\nRecipes/revisions kept (have binaries):", fg=Color.BRIGHT_GREEN)
        for recipe in result['recipes_with_binaries']:
            cli_out_write(f"  - {recipe}", fg=Color.BRIGHT_CYAN)


def _format_json_output(result):
    """Format output in JSON format."""
    output = {
        "total_inspected": result["total_inspected"],
        "recipes_with_binaries": result["recipes_with_binaries"],
        "removed": result["removed"],
        "skipped": result["skipped"],
        "dry_run": result.get("dry_run", False)
    }
    cli_out_write(json.dumps(output, indent=2))


@conan_command(group="Custom commands")
def cache_cleanup(conan_api, parser, *args):
    """
    Search the Conan cache for recipes without binary packages and remove them.
    
    This command helps clean up the cache by removing recipe revisions that
    have no associated binary packages.
    """
    parser.add_argument("-f", "--format", 
                       choices=["text", "json"],
                       default="text",
                       help="Select the output format (text or json)")
    parser.add_argument("--dry-run",
                       action="store_true",
                       default=False,
                       help="Show what would be removed without actually removing")
    parser.add_argument("-c", "--confirm",
                       action="store_true",
                       default=False,
                       help="Confirm before removing each recipe/revision")
    
    parsed_args = parser.parse_args(*args)
    
    try:
        # List all recipes in the cache
        ConanOutput().info("Listing recipes in cache...")
        cache_data = _list_cache_recipes()
        
        # Identify recipes without binaries
        ConanOutput().info("Analyzing recipes...")
        analysis = _identify_recipes_without_binaries(cache_data)
        
        removed = []
        skipped = []
        
        # Remove recipes without binaries (unless dry-run)
        if not parsed_args.dry_run:
            ConanOutput().info(f"Removing {len(analysis['recipes_to_remove'])} recipe(s) without binaries...")
            for recipe_ref in analysis['recipes_to_remove']:
                try:
                    if _remove_recipe(recipe_ref, confirm=parsed_args.confirm):
                        removed.append(recipe_ref)
                        ConanOutput().success(f"Removed: {recipe_ref}")
                    else:
                        skipped.append(recipe_ref)
                        ConanOutput().info(f"Skipped: {recipe_ref}")
                except ConanException as e:
                    skipped.append(recipe_ref)
                    ConanOutput().warning(f"Failed to remove {recipe_ref}: {e}")
        else:
            # In dry-run mode, list what would be removed
            ConanOutput().info(f"[DRY RUN] Would remove {len(analysis['recipes_to_remove'])} recipe(s)")
            removed = analysis['recipes_to_remove']
        
        # Prepare result
        result = {
            "total_inspected": analysis["total_inspected"],
            "recipes_with_binaries": analysis["recipes_with_binaries"],
            "removed": removed,
            "skipped": skipped,
            "dry_run": parsed_args.dry_run
        }
        
        # Format output
        if parsed_args.format == "json":
            _format_json_output(result)
        else:
            _format_text_output(result)
        
        return result
        
    except ConanException as e:
        ConanOutput().error(str(e))
        sys.exit(1)
    except Exception as e:
        ConanOutput().error(f"Unexpected error: {e}")
        sys.exit(1)
