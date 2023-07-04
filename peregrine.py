#!/usr/bin/env python

import sys
from indexer import *
import argparse
import os
from codes import *
from error import ErrorHandler

PEREGRINE_DIR_NAME = ".peregrine"
PEREGRINE_FILE_NAME = "peregrinefile"

errorhandler = ErrorHandler()


def check_env():
    cwd = os.getcwd()
    at_cwd = os.path.join(cwd, PEREGRINE_DIR_NAME)

    exists_in_current = os.path.isdir(at_cwd)
    if not exists_in_current:
        return NO_PEREGRINE_DIR

    return check_phome(at_cwd)


def check_phome(dirpath):
    has_peregrinefile = os.path.isfile(os.path.join(dirpath, PEREGRINE_FILE_NAME))

    if not has_peregrinefile:
        return NO_PEREGRINEFILE
    return SUCCESS


def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.

    reference: https://stackoverflow.com/a/22254892
    """
    plat = sys.platform
    supported_platform = plat != "Pocket PC" and (
        plat != "win32" or "ANSICON" in os.environ
    )
    is_a_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    return supported_platform and is_a_tty


class CommandHandler:
    # Create the argument parser
    parser = argparse.ArgumentParser(
        prog="peregrine",
        description="Command-line tool for indexing and searching files.",
    )

    # Add the 'init' command
    subparser = parser.add_subparsers(dest="command")
    init_parser = subparser.add_parser("init", help="Initialize the tool")
    init_parser.add_argument(
        "path",
        nargs="?",
        default=os.getcwd(),
        help="Path to initialize the tool (default: current directory)",
    )
    init_parser.add_argument(
        "--force", action="store_true", help="Forcefully initialize the tool"
    )

    # Add the 'ls' command
    subparser.add_parser("ls", help="List files and directories")

    # Add the 'cd' command
    cd_parser = subparser.add_parser("cd", help="Change directory")
    cd_parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Path to the directory (default: current directory)",
    )

    # Add the 'pwd' command
    pwd_parser = subparser.add_parser("pwd", help="Print current working directory")

    # Add the 'meta' command
    meta_parser = subparser.add_parser("meta", help="Perform meta operations")
    meta_parser.add_argument("path", help="Path for meta operation")
    meta_group = meta_parser.add_mutually_exclusive_group()
    meta_group.add_argument("--add", nargs="+", help="Add keywords to a file")
    meta_group.add_argument("--rm", nargs="+", help="Remove keywords from a file")
    meta_group.add_argument(
        "--clear", action="store_true", help="Clear all keywords from a file"
    )

    # Add the 'search' command
    search_parser = subparser.add_parser("search", help="Search for files")
    search_parser.add_argument(
        "query", help="Query string for searching by name or keywords"
    )
    search_parser.add_argument(
        "--date",
        nargs=2,
        metavar=("OPERATOR", "DATE"),
        help="Search by date (before, after, on)",
    )
    search_parser.add_argument(
        "--time",
        nargs=2,
        metavar=("OPERATOR", "TIME"),
        help="Search by time (before, after, on)",
    )
    search_parser.add_argument(
        "--name", action="store_true", help="Search by name only"
    )
    search_parser.add_argument(
        "--keyword", action="store_true", help="Search by keyword only"
    )

    # Add 'help' command
    help_parser = subparser.add_parser("help", help="Show help for a specific command")
    help_parser.add_argument(
        "help_command",
        nargs="?",
        choices=subparser.choices.keys(),
        help="Command to show help for",
    )

    # Variables
    PWD = None
    HOME = None

    # Methods
    def check_env_and_exit(self):
        check_env_status = check_env()
        if check_env_status != SUCCESS:
            errorhandler.log(check_env_status)
            exit(1)

    def set_paths(self):
        self.check_env_and_exit()
        self.HOME = os.getcwd()
        if self.PWD is None:
            self.PWD = self.HOME

    def parse(self, args):
        func_mapping = {
            "init": self.init,
            "help": self.help,
            "pwd": self.pwd,
            "ls": self.ls,
        }
        if args.command is not None:
            if args.command not in {"init", "help"}:
                self.set_paths()
            func_mapping[args.command](args)

    def init(self, args):
        path = args.path
        force = args.force
        check_env_status = check_env()
        if check_env_status == NO_PEREGRINE_DIR:
            new_directory_path = os.path.join(path, PEREGRINE_DIR_NAME)
            os.mkdir(new_directory_path)

            open(
                os.path.join(path, PEREGRINE_DIR_NAME, PEREGRINE_FILE_NAME), "w"
            ).close()
        elif check_env_status == NO_PEREGRINEFILE:
            if not force:
                errorhandler.log_warning("Peregrine file not found. Use `init --force`")
            else:
                open(
                    os.path.join(path, PEREGRINE_DIR_NAME, PEREGRINE_FILE_NAME), "w"
                ).close()
        elif check_env_status == SUCCESS:
            print("peregrine exists.")
        else:
            raise Exception("Implementation error.")

    def pwd(self, args):
        print(self.PWD)

    def ls(self, args):
        for i in os.listdir(self.PWD):
            name = f"\033[1;34m{i}\033[0m" if os.path.isdir(i) else i
            print(name)

    def help(self, args):
        if args.help_command:
            self.subparser.choices[args.help_command].print_help()
        else:
            self.parser.print_help()


commandhandler = CommandHandler()
args = commandhandler.parser.parse_args()
commandhandler.parse(args)


def interactive():
    pass

interactive()