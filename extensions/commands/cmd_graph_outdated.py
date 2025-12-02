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


def outdated_text_formatter(result):
    # Check if this is a revision check result
    if isinstance(result, dict) and result.get("_revisions"):
        data = result.get("data", {})
        cli_out_write("======== Outdated package revisions ========", fg=Color.BRIGHT_MAGENTA)

        if len(data) == 0:
            cli_out_write("No outdated package revisions in graph", fg=Color.BRIGHT_YELLOW)
            return

        for key, value in data.items():
            cli_out_write(key, fg=Color.BRIGHT_YELLOW)
            cli_out_write(
                f'    Current revision:  {value["current_prev"]}',
                fg=Color.BRIGHT_CYAN)
            latest_remote = value.get("latest_remote")
            if latest_remote:
                cli_out_write(
                    f'    Latest in remote(s):  {latest_remote["prev"]} - {latest_remote["remote"]}',
                    fg=Color.BRIGHT_CYAN)
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
        output = {key: {"current_revision": value["current_prev"],
                        "latest_remote": None if value["latest_remote"] is None
                        else {"revision": value["latest_remote"]["prev"],
                              "remote": value["latest_remote"]["remote"]}}
                  for key, value in data.items()}
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
    """
    dependencies = deps_graph.nodes[1:]
    outdated_revisions = {}

    if len(dependencies) == 0:
        return outdated_revisions

    ConanOutput().title("Checking package revisions in remotes")

    for node in dependencies:
        # Skip nodes without package info (e.g., virtual packages)
        if node.ref is None or node.package_id is None or node.prev is None:
            continue

        # Build the package reference for querying
        pref = PkgReference(ref=node.ref, package_id=node.package_id, revision=None)
        pref_key = str(pref)  # name/version#rrev:package_id

        current_prev = node.prev

        # Check each remote for newer package revisions
        for remote in remotes:
            try:
                latest_pref = conan_api.list.latest_package_revision(pref, remote=remote)
                if latest_pref is None:
                    continue

                latest_prev = latest_pref.revision
                latest_timestamp = latest_pref.timestamp

                # Compare revisions: if they differ and the remote has a newer timestamp
                if latest_prev != current_prev:
                    # If we already have a latest_remote, check if this one is newer
                    existing = outdated_revisions.get(pref_key)
                    if existing is None or (latest_timestamp is not None and
                            (existing["latest_remote"]["timestamp"] is None or
                             latest_timestamp > existing["latest_remote"]["timestamp"])):
                        outdated_revisions[pref_key] = {
                            "current_prev": current_prev,
                            "latest_remote": {
                                "prev": latest_prev,
                                "remote": remote.name,
                                "timestamp": latest_timestamp
                            }
                        }
            except Exception:
                # Package not found in this remote, continue to next
                continue

    return outdated_revisions


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
