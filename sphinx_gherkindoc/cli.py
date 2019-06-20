#!/usr/bin/env python3
"""Module for running the tool from the CLI."""
import argparse
import os.path
import shutil

import sphinx
from qecommon_tools import get_file_contents

from .files import is_feature_file, is_rst_file, scan_tree
from .glossary import make_steps_glossary
from .utils import make_flat_name, set_dry_run, set_verbose, verbose
from .writer import feature_to_rst, toctree

# This is a pretty arbitrary number controlling how much detail
# will show up in the various TOCs.
DEFAULT_TOC_DEPTH = 4


def process_args(args):
    """Process the supplied CLI args."""
    work_to_do = scan_tree(args.gherkin_path, args.private, args.exclude_patterns)
    maxtocdepth = args.maxtocdepth
    output_path = args.output_path
    toc_name = args.toc_name
    step_glossary_name = args.step_glossary_name
    doc_project = args.doc_project
    root_path = os.path.dirname(os.path.abspath(args.gherkin_path))

    top_level_toc_filename = os.path.join(output_path, toc_name) + ".rst"

    non_empty_dirs = set()

    while work_to_do:
        a_dir, a_dir_list, subdirs, files = work_to_do.pop()
        new_subdirs = []
        for subdir in subdirs:
            subdir_path = os.path.join(a_dir, subdir)
            if subdir_path in non_empty_dirs:
                new_subdirs.append(subdir)

        if not (files or new_subdirs):
            continue

        non_empty_dirs.add(a_dir)

        if args.dry_run:
            continue

        toc_file = toctree(a_dir_list, new_subdirs, files, maxtocdepth, root_path)
        # Check to see if we are at the last item to be processed
        # (which has already been popped)
        # to write the asked for master TOC file name.
        if not work_to_do:
            toc_filename = top_level_toc_filename
        else:
            toc_filename = os.path.join(
                output_path, make_flat_name(a_dir_list, is_dir=True)
            )
        toc_file.write_to_file(toc_filename)

        for a_file in files:
            a_file_list = a_dir_list + [a_file]
            source_name = os.path.join(*a_file_list)
            source_path = os.path.join(root_path, source_name)
            if is_feature_file(a_file):
                dest_name = os.path.join(
                    output_path, make_flat_name(a_file_list, is_dir=False)
                )
                feature_rst_file = feature_to_rst(source_path, root_path)
                verbose('converting "{}" to "{}"'.format(source_name, dest_name))
                feature_rst_file.write_to_file(dest_name)
            elif not is_rst_file(a_file):
                dest_name = os.path.join(
                    output_path, make_flat_name(a_file_list, is_dir=False, ext=None)
                )
                verbose('copying "{}" to "{}"'.format(source_name, dest_name))
                shutil.copy(source_path, dest_name)

    if step_glossary_name:
        glossary_filename = os.path.join(
            output_path, "{}.rst".format(step_glossary_name)
        )
        glossary = make_steps_glossary(doc_project)

        if args.dry_run:
            verbose("No glossary generated")
            return

        if glossary is None:
            print("No steps to include in the glossary: no glossary generated")
            return

        verbose("Writing sphinx glossary: {}".format(glossary_filename))
        glossary.write_to_file(glossary_filename)


def main():
    """Convert a directory-tree of Gherking Feature files to rST files."""
    description = (
        "Look recursively in <gherkin_path> for Gherkin files and create one "
        "reST file for each. Other rST files found along the way will be included "
        "as prologue content above each TOC."
    )
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("gherkin_path", help="Directory to search for Gherkin files")
    parser.add_argument("output_path", help="Directory to place all output")
    parser.add_argument(
        "exclude_patterns",
        nargs="*",
        help="file and/or directory patterns that will be excluded",
    )
    parser.add_argument(
        "-d",
        "--maxtocdepth",
        type=int,
        default=DEFAULT_TOC_DEPTH,
        help="Maximum depth of submodules to show in the TOC",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Run the script without creating files",
    )
    parser.add_argument(
        "-P", "--private", action="store_true", help='Include "_private" folders'
    )
    parser.add_argument("-N", "--toc-name", help="File name for TOC", default="gherkin")
    parser.add_argument(
        "-H", "--doc-project", help="Project name (default: root module name)"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Silence any output to screen"
    )
    parser.add_argument(
        "-G",
        "--step-glossary-name",
        default=None,
        help="Include steps glossary under the given name."
        " If not specified, no glossary will be created.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print files created and actions taken",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show version information and exit"
    )

    args = parser.parse_args()

    if args.version:
        parser.exit(
            message="Sphinx (sphinx-gherkindoc) {}".format(sphinx.__display_version__)
        )

    if args.dry_run:
        set_dry_run(True)

    if args.verbose:
        set_verbose(True)

    if args.doc_project is None:
        args.doc_project = os.path.abspath(args.gherkin_path).split(os.path.sep)[-1]

    if not os.path.isdir(args.gherkin_path):
        parser.error("{} is not a directory.".format(args.gherkin_path))

    args.output_path = os.path.abspath(args.output_path)
    if not os.path.isdir(args.output_path):
        if not args.dry_run:
            verbose("creating directory: {}".format(args.output_path))
            os.makedirs(args.output_path)

    process_args(args)


def config():
    """Emit a customized version of the sample sphinx config file."""
    description = (
        "Create a default Sphinx configuration for producing nice"
        " Gherkin-based documentation"
    )
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "project_name", default="Your Project Name Here", help="Name of your project"
    )
    parser.add_argument(
        "author", default="Your Team Name Here", help="Directory to place all output"
    )
    parser.add_argument("--version", default="", help="version of your project, if any")
    parser.add_argument("--release", default="", help="release of your project, if any")
    args = parser.parse_args()

    substitutions = {
        "%%PROJECT%%": args.project_name,
        "%%AUTHOR%%": args.author,
        "%%VERSION%%": args.version,
        "%%RELEASE%%": args.release,
    }
    source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    sample_contents = get_file_contents(source_dir, "sample-conf.py")
    for old_value, new_value in substitutions.items():
        sample_contents = sample_contents.replace(old_value, new_value)

    print(sample_contents)


if __name__ == "__main__":
    main()
