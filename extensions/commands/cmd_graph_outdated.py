"""
Conan custom command: conan graph-outdated

This command provides functionality to check for outdated dependencies
in a Conan dependency graph.
"""

from conan.api.output import ConanOutput
from conan.cli.command import conan_command


@conan_command(group="Custom commands")
def graph_outdated(conan_api, parser, *args):
    """
    Check for outdated dependencies in the dependency graph.

    This is a placeholder for 'conan graph outdated'.
    """
    parser.parse_args(*args)
    out = ConanOutput()
    out.info("This is a placeholder for 'conan graph outdated'.")
