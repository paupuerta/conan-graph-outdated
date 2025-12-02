"""
Conan custom command: conan graph-outdated

This command provides functionality to check for outdated dependencies
in a Conan dependency graph.

Replicates the `conan graph outdated` command from conan-io/conan.
"""

import json
import os

from conan.api.output import cli_out_write, ConanOutput, Color
from conan.api.model.refs import PkgReference
from conan.cli.args import common_graph_args, validate_common_graph_args
from conan.cli.command import conan_command
from conan.cli.printers.graph import print_graph_basic
from conan.errors import ConanException


def outdated_text_formatter(result):
    # Check if this is a revision check result
    if isinstance(result, dict) and result.get("_revisions"):
        data = result.get("data", {})
        packages = data.get("packages", {})
        skipped = data.get("skipped", [])
        cli_out_write("======== Package revisions ========", fg=Color.BRIGHT_MAGENTA)

        if len(packages) == 0 and len(skipped) == 0:
            cli_out_write("No packages in graph", fg=Color.BRIGHT_YELLOW)
            return

        if len(packages) == 0 and len(skipped) > 0:
            cli_out_write("No packages with revision info in graph", fg=Color.BRIGHT_YELLOW)
            cli_out_write("Packages without revision (not yet installed):", fg=Color.BRIGHT_YELLOW)
            for pkg in skipped:
                cli_out_write(f"    {pkg}", fg=Color.BRIGHT_CYAN)
            return

        for key, value in packages.items():
            is_outdated = value.get("is_outdated", False)
            status = "OUTDATED" if is_outdated else "UP-TO-DATE"
            status_color = Color.BRIGHT_RED if is_outdated else Color.BRIGHT_GREEN
            cli_out_write(f"{key} [{status}]", fg=status_color)
            cli_out_write(
                f'    Current revision:  {value["current_prev"]}',
                fg=Color.BRIGHT_CYAN)
            latest_remote = value.get("latest_remote")
            if latest_remote:
                cli_out_write(
                    f'    Latest in remote(s):  {latest_remote["prev"]} - {latest_remote["remote"]}',
                    fg=Color.BRIGHT_CYAN)
            else:
                cli_out_write(
                    '    Latest in remote(s):  Not found in remotes',
                    fg=Color.BRIGHT_CYAN)

        if len(skipped) > 0:
            cli_out_write("", fg=Color.BRIGHT_YELLOW)
            cli_out_write("Packages without revision (not yet installed):", fg=Color.BRIGHT_YELLOW)
            for pkg in skipped:
                cli_out_write(f"    {pkg}", fg=Color.BRIGHT_CYAN)
        return

    # Original outdated versions formatter
    cli_out_write("======== Outdated dependencies ========", fg=Color.BRIGHT_MAGENTA)

    if len(result) == 0:
        cli_out_write("No outdated dependencies in graph", fg=Color.BRIGHT_YELLOW)
        return

    for key, value in result.items():
        current_versions_set = list({str(v) for v in value["cache_refs"]})
        cli_out_write(key, fg=Color.BRIGHT_YELLOW)
        cli_out_write(
            f'    Current versions:  {", ".join(current_versions_set) if value["cache_refs"] else "No version found in cache"}',
            fg=Color.BRIGHT_CYAN)
        latest_remote = value.get("latest_remote")
        if latest_remote:
            cli_out_write(
                f'    Latest in remote(s):  {latest_remote["ref"]} - {latest_remote["remote"]}',
                fg=Color.BRIGHT_CYAN)
        if value["version_ranges"]:
            cli_out_write(f'    Version ranges: ' + str(value["version_ranges"])[1:-1],
                          fg=Color.BRIGHT_CYAN)


def outdated_json_formatter(result):
    # Check if this is a revision check result
    if isinstance(result, dict) and result.get("_revisions"):
        data = result.get("data", {})
        packages = data.get("packages", {})
        skipped = data.get("skipped", [])
        output = {
            "packages": {key: {"current_revision": value["current_prev"],
                              "is_outdated": value.get("is_outdated", False),
                              "latest_remote": None if value["latest_remote"] is None
                              else {"revision": value["latest_remote"]["prev"],
                                    "remote": value["latest_remote"]["remote"]}}
                        for key, value in packages.items()},
            "skipped_no_revision": skipped
        }
        cli_out_write(json.dumps(output))
        return

    # Original outdated versions formatter
    output = {key: {"current_versions": list({str(v) for v in value["cache_refs"]}),
                    "version_ranges": [str(r) for r in value["version_ranges"]],
                    "latest_remote": None if value["latest_remote"] is None
                    else {"ref": str(value["latest_remote"]["ref"]),
                          "remote": str(value["latest_remote"]["remote"])}}
              for key, value in result.items()}
    cli_out_write(json.dumps(output))


def check_outdated_revisions(conan_api, deps_graph, remotes):
    """
    Check for outdated package revisions in the dependency graph.

    For each package in the graph, compare the current package revision
    with the latest revision available in the remotes.

    Returns all packages with their revision comparison, allowing users to
    verify whether revisions match or differ.
    """
    dependencies = deps_graph.nodes[1:]
    package_revisions = {}
    skipped_packages = []

    if len(dependencies) == 0:
        return {"packages": package_revisions, "skipped": skipped_packages}

    ConanOutput().title("Checking package revisions in remotes")

    for node in dependencies:
        # Skip nodes without package info (e.g., virtual packages)
        if node.ref is None or node.package_id is None:
            continue
        if node.prev is None:
            # Track packages without revision info
            skipped_packages.append(str(node.ref))
            continue

        # Build the package reference for querying
        pref = PkgReference(ref=node.ref, package_id=node.package_id, revision=None)
        pref_key = str(pref)  # name/version:package_id

        current_prev = node.prev

        # Initialize entry for this package (each package is processed once)
        package_revisions[pref_key] = {
            "current_prev": current_prev,
            "latest_remote": None,
            "is_outdated": False
        }

        # Check each remote for package revisions
        for remote in remotes:
            try:
                latest_pref = conan_api.list.latest_package_revision(pref, remote=remote)
                if latest_pref is None:
                    continue

                latest_prev = latest_pref.revision
                latest_timestamp = latest_pref.timestamp

                # Update the latest revision info if this is newer than what we have
                existing = package_revisions[pref_key]
                existing_remote = existing["latest_remote"]
                if existing_remote is None or (latest_timestamp is not None and
                        (existing_remote["timestamp"] is None or
                         latest_timestamp > existing_remote["timestamp"])):
                    existing["latest_remote"] = {
                        "prev": latest_prev,
                        "remote": remote.name,
                        "timestamp": latest_timestamp
                    }
                    existing["is_outdated"] = latest_prev != current_prev
            except ConanException:
                # Package not found in this remote or connection error, continue to next
                continue

    return {"packages": package_revisions, "skipped": skipped_packages}


@conan_command(group="Custom commands", formatters={"text": outdated_text_formatter,
                                                     "json": outdated_json_formatter})
def graph_outdated(conan_api, parser, *args):
    """
    List the dependencies in the graph and their newer versions in the remote.

    This replicates 'conan graph outdated' command functionality.
    """
    common_graph_args(parser)
    parser.add_argument("--check-updates", default=False, action="store_true",
                        help="Check if there are recipe updates")
    parser.add_argument("--check-revisions", default=False, action="store_true",
                        help="Check if there are package revision updates (instead of version updates)")
    parser.add_argument("--build-require", action='store_true', default=False,
                        help='Whether the provided reference is a build-require')
    args = parser.parse_args(*args)
    # parameter validation
    validate_common_graph_args(args)
    cwd = os.getcwd()
    path = conan_api.local.get_conanfile_path(args.path, cwd, py=None) if args.path else None

    # Basic collaborators, remotes, lockfile, profiles
    remotes = conan_api.remotes.list(args.remote) if not args.no_remote else []
    overrides = eval(args.lockfile_overrides) if args.lockfile_overrides else None
    lockfile = conan_api.lockfile.get_lockfile(lockfile=args.lockfile,
                                               conanfile_path=path,
                                               cwd=cwd,
                                               partial=args.lockfile_partial,
                                               overrides=overrides)
    profile_host, profile_build = conan_api.profiles.get_profiles_from_args(args)

    if path:
        deps_graph = conan_api.graph.load_graph_consumer(path, args.name, args.version,
                                                         args.user, args.channel,
                                                         profile_host, profile_build, lockfile,
                                                         remotes, args.update,
                                                         check_updates=args.check_updates,
                                                         is_build_require=args.build_require)
    else:
        deps_graph = conan_api.graph.load_graph_requires(args.requires, args.tool_requires,
                                                         profile_host, profile_build, lockfile,
                                                         remotes, args.update,
                                                         check_updates=args.check_updates)
    print_graph_basic(deps_graph)

    if args.check_revisions:
        # Check for outdated package revisions instead of version updates
        outdated = check_outdated_revisions(conan_api, deps_graph, remotes)
        return {"_revisions": True, "data": outdated}

    # Data structure to store info per library
    # DO NOT USE this API call yet, it is not stable
    outdated = conan_api.list.outdated(deps_graph, remotes)

    return outdated
