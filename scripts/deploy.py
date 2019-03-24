#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""
Deploy nightly builds.


To deploy to dropbox you need:
- Access to the wrye bash shared folder in your dropbox
- A dropbox API access token
  See: https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/

To deploy to nexus you need:
- Your favourite browser installed
- A drive for your favourite browser available in PATH
  Chrome: https://sites.google.com/a/chromium.org/chromedriver/downloads
  Firefox: https://github.com/mozilla/geckodriver/releases
  Edge: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
  Place it in PATH (e.g. in this script's folder or C:\Windows)
- To be logged in to nexusmods.com in your favourite browser
- A way to check cookie values in your favourite browser
  Chrome: chrome://settings/siteData
  Firefox: Shift+F9 when at nexusmods.com

Unless '--no-config' is supplied, all values are saved to a
configuration file at './deploy_config.json'. Values are
stored as a dictionary with the format (keys in lowercase):
    '%SUBCOMMAND%_%ARGUMENT%': '%VALUE%'
"""

import argparse

import deploy_dropbox
import deploy_nexus
import utils

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    utils.setup_deploy_parser(parser)
    parser.add_argument(
        "--no-dropbox",
        action="store_false",
        dest="dropbox",
        help="Do not deploy to dropbox.",
    )
    parser.add_argument(
        "--no-nexus",
        action="store_false",
        dest="nexus",
        help="Do not deploy to nexusmods.",
    )
    dropbox_parser = parser.add_argument_group("dropbox arguments")
    deploy_dropbox.setup_parser(dropbox_parser)
    nexus_parser = parser.add_argument_group("nexus arguments")
    deploy_nexus.setup_parser(nexus_parser)
    args = parser.parse_args()
    open(args.logfile, "w").close()
    if args.dropbox:
        deploy_dropbox.main(args)
        print
    if args.nexus:
        deploy_nexus.main(args)
