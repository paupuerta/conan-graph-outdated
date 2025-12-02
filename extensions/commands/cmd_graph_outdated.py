"""
Conan custom command: conan graph-outdated

This command provides functionality to check for outdated dependencies
in a Conan dependency graph.

Replicates the `conan graph outdated` command from conan-io/conan.
"""

import json
import os

from conan.api.output import cli_out_write, Color
from conan.cli.args import common_graph_args, validate_common_graph_args
from conan.cli.command import conan_command
from conan.cli.printers.graph import print_graph_basic


def outdated_text_formatter(result):
    cli_out_write("======== Outdated dependencies ========", fg=Color.BRIGHT_MAGENTA)

    if len(result) == 0:
        cli_out_write("No outdated dependencies in graph", fg=Color.BRIGHT_YELLOW)

    for key, value in result.items():
        current_versions_set = list({str(v) for v in value["cache_refs"]})
        cli_out_write(key, fg=Color.BRIGHT_YELLOW)
        cli_out_write(
            f'    Current versions:  {", ".join(current_versions_set) if value["cache_refs"] else "No version found in cache"}',
            fg=Color.BRIGHT_CYAN)
        cli_out_write(
            f'    Latest in remote(s):  {value["latest_remote"]["ref"]} - {value["latest_remote"]["remote"]}',
            fg=Color.BRIGHT_CYAN)
        if value["version_ranges"]:
            cli_out_write(f'    Version ranges: ' + str(value["version_ranges"])[1:-1],
                          fg=Color.BRIGHT_CYAN)


def outdated_json_formatter(result):
    output = {key: {"current_versions": list({str(v) for v in value["cache_refs"]}),
                    "version_ranges": [str(r) for r in value["version_ranges"]],
                    "latest_remote": [] if value["latest_remote"] is None
                    else {"ref": str(value["latest_remote"]["ref"]),
                          "remote": str(value["latest_remote"]["remote"])}}
              for key, value in result.items()}
    cli_out_write(json.dumps(output))


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

    # Data structure to store info per library
    # DO NOT USE this API call yet, it is not stable
    outdated = conan_api.list.outdated(deps_graph, remotes)

    return outdated
