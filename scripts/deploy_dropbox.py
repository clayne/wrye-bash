#!/usr/bin/env python2

import argparse
import json
import logging
import os
import re

import dropbox

import utils

LOGGER = logging.getLogger(__name__)

# constants
SHARED_FOLDER_ID = "4796182912"
ROOT_FOLDER = os.path.dirname(os.path.abspath(__file__))

# regex
FILE_REGEX = r"Wrye Bash \d{3,}\.\d{12,12} - (Installer.exe|Python Source.7z|Standalone Executable.7z)"
COMPILED = re.compile(FILE_REGEX)


def setup_parser(parser):
    parser.add_argument(
        "-t",
        "--access-token",
        default=argparse.SUPPRESS,
        help="The dropbox API access token.\n"
        "  To get your own access token\n"
        "  go to https://www.dropbox.com/developers/apps\n"
        "  register an app and generate your token.",
    )
    parser.add_argument(
        "-b",
        "--branch",
        default="",
        help="Upload a specific branch.\n"
        "  Will upload to a separate folder\n"
        "  within the shared folder.",
    )


def remove_files(dbx, path, dry_run=False):
    # get all files in folder
    files = []
    for entry in dbx.files_list_folder(path).entries:
        if isinstance(entry, dropbox.files.FileMetadata):
            files.append(entry.name)
            LOGGER.debug("Found '{}' under shared folder.".format(entry.name))
    # delete the previous nightly files
    filtered = filter(COMPILED.match, files)
    for fname in filtered:
        fpath = path + "/" + fname
        if dry_run:
            LOGGER.info("Would remove '{}'.".format(fpath))
            continue
        LOGGER.info("Removing '{}'...".format(fpath))
        dbx.files_delete_v2(fpath)


def upload_file(dbx, fpath, folder_path, dry_run=False):
    fname = os.path.basename(fpath)
    LOGGER.debug("Found '{}' under distributable folder.".format(fname))
    if dry_run:
        LOGGER.info("Would upload '{}'.".format(os.path.relpath(fpath, os.getcwd())))
        return
    LOGGER.info("Uploading '{}'...".format(os.path.relpath(fpath, os.getcwd())))
    with open(fpath, "rb") as fopen:
        upload_path = folder_path + "/" + fname
        dbx.files_upload(fopen.read(), upload_path)


def main(args):
    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=args.logfile)
    creds = utils.parse_deploy_credentials(args, ["access_token"], args.save_config)
    # setup dropbox instance
    dbx = dropbox.Dropbox(creds["access_token"])
    shared_folder_path = dbx.sharing_get_folder_metadata(SHARED_FOLDER_ID).path_lower
    LOGGER.debug("Found shared folder path at '{}'.".format(shared_folder_path))
    # create folder inside shared folder if needed for branch nightly
    if args.branch:
        shared_folder_path += "/" + args.branch
        try:
            dbx.files_create_folder_v2(shared_folder_path)
        except dropbox.exceptions.ApiError:
            pass
        LOGGER.debug(
            "Using branch folder '{}' at '{}'.".format(args.branch, shared_folder_path)
        )
    remove_files(dbx, shared_folder_path, args.dry_run)
    for fname in os.listdir(args.dist_folder):
        fpath = os.path.join(args.dist_folder, fname)
        if not os.path.isfile(fpath):
            continue
        upload_file(dbx, fpath, shared_folder_path, args.dry_run)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    utils.setup_deploy_parser(argparser)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    open(parsed_args.logfile, "w").close()
    main(parsed_args)
