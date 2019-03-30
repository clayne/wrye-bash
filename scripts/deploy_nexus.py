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

import argparse
import json
import logging
import os
import re
import textwrap
from contextlib import closing, contextmanager

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait

import utils

LOGGER = logging.getLogger(__name__)

COOKIES_TEMPLATE = {
    "domain": ".nexusmods.com",
    "expiry": None,
    "httpOnly": False,
    "name": None,
    "path": "/",
    "secure": True,
    "value": None,
}
ID_DICT = {
    # oblivion
    101: 22368,
    # skyrim
    110: 1840,
    # skyrim special edition
    1704: 6837,
    # fallout 3
    120: 22934,
    # fallout new vegas
    130: 64580,
    # fallout 4
    1151: 20032,
}
DESC_DICT = {
    "Installer": (
        "Executable automated Installer. This will by default install just "
        "the Standalone Wrye Bash. It can also install all requirements for a "
        "full Python setup if you have any plans to join in with development."
    ),
    "Python Source": (
        "This is a manual installation of Wrye Bash Python files, requiring "
        "the full Python setup files to also be manually installed first."
    ),
    "Standalone Executable": (
        "This is a manual installation of the Wrye Bash Standalone files."
    ),
}
DRIVER_DOWNLOAD = (
    "Download the {} driver from {} and place it in PATH.\n"
    "Press Enter to continue..."
)
CATEGORY = "Updates"
FILE_REGEX = (
    r"Wrye Bash \d{3,}\.\d{12,12} - (Installer|Python Source|Standalone Executable)"
)
COMPILED_REGEX = re.compile(FILE_REGEX)


def check_executable(exename):
    return any(
        os.access(os.path.join(path, exename), os.X_OK)
        for path in os.environ["PATH"].split(os.pathsep)
    )


# https://blog.codeship.com/get-selenium-to-wait-for-page-load/
@contextmanager
def wait_for_page_load(browser, timeout=30):
    old_page = browser.find_element_by_tag_name("html")
    yield
    WebDriverWait(browser, timeout).until(ec.staleness_of(old_page))


def setup_parser(parser):
    parser.add_argument(
        "-d",
        "--driver",
        default="firefox",
        help="Choose a browser to use: firefox, chrome or edge [default: firefox].",
    )
    parser.add_argument(
        "-m",
        "--member-id",
        default=argparse.SUPPRESS,
        help="The 'value' from the cookie 'member_id' in the domain 'nexusmods.com'",
    )
    parser.add_argument(
        "-p",
        "--pass-hash",
        default=argparse.SUPPRESS,
        help="The 'value' from the cookie 'pass_hash' in the domain 'nexusmods.com'",
    )
    parser.add_argument(
        "-s",
        "--sid",
        default=argparse.SUPPRESS,
        help="The 'value' from the cookie 'sid' in the domain 'nexusmods.com'",
    )


def setup_driver(driver_name):
    if driver_name == "chrome":
        while not check_executable("chromedriver.exe"):
            raw_input(
                DRIVER_DOWNLOAD.format(
                    "chrome",
                    "https://sites.google.com/a/chromium.org/chromedriver/downloads",
                )
            )
        options = webdriver.ChromeOptions()
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        driver = webdriver.Chrome(chrome_options=options)
        LOGGER.debug("Successfully created a new chrome driver")
        return driver
    elif driver_name == "firefox":
        while not check_executable("geckodriver.exe"):
            raw_input(
                DRIVER_DOWNLOAD.format(
                    "firefox", "https://github.com/mozilla/geckodriver/releases/latest"
                )
            )
        profile = webdriver.FirefoxProfile()
        profile.accept_untrusted_certs = True
        driver = webdriver.Firefox(firefox_profile=profile)
        LOGGER.debug("Successfully created a new firefox driver")
        return driver
    else:
        while not check_executable("MicrosoftWebDriver.exe"):
            raw_input(
                DRIVER_DOWNLOAD.format(
                    "edge",
                    "https://developer.microsoft.com/en-us/microsoft-edge"
                    "/tools/webdriver/#downloads",
                )
            )
        capabilities = webdriver.DesiredCapabilities().INTERNETEXPLORER
        capabilities["acceptSslCerts"] = True
        driver = webdriver.Ie(capabilities=capabilities)
        LOGGER.debug("Successfully created a new edge driver")
        return driver


def load_cookies(driver, creds):
    cookies = []
    for name, value in creds.iteritems():
        cookie = dict(COOKIES_TEMPLATE)
        cookie["name"] = name
        cookie["value"] = value
        cookies.append(cookie)
    driver.get("https://www.nexusmods.com")
    for cookie in cookies:
        driver.add_cookie(cookie)


def set_file_to_replace(driver, name, dry_run=False):
    LOGGER.debug("Looking for old files to replace...")
    xpath = "//div[@class='file-category']/h3[text()='{}']/../ol/li".format(CATEGORY)
    file_entries = driver.find_elements_by_xpath(xpath)
    for entry in file_entries:
        fname_xpath = "div[@class='file-head']/h4"
        fname = entry.find_element_by_xpath(fname_xpath).text
        LOGGER.debug("Checking file '{}'...".format(fname))
        if COMPILED_REGEX.match(fname) is None or not fname.endswith(name.split()[-1]):
            continue
        LOGGER.debug("File '{}' has matched...".format(fname))
        fversion_xpath = "div[@class='file-head']/div/span"
        fversion = entry.find_element_by_xpath(fversion_xpath).text
        freplace = " ".join((fname, fversion))
        if dry_run:
            LOGGER.info("Would replace file '{}'.".format(freplace))
            break
        LOGGER.info("Replacing file '{}'...".format(freplace))
        driver.find_element_by_id("new-existing-version").click()
        Select(
            driver.find_element_by_id("select-original-file")
        ).select_by_visible_text(freplace)
        driver.find_element_by_id("remove-old-version").click()
        break


def upload_file(driver, fpath, dry_run=False):
    fname = os.path.basename(fpath)
    name = os.path.splitext(fname)[0]
    version = name.split()[2]
    try:
        # handle cookies banner
        LOGGER.debug("Removing cookies banner...")
        xpath = "//a[@class='banner_continue--2NyXA']"
        banner = WebDriverWait(driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, xpath))
        )
        banner.click()
    except (
        TimeoutException,
        ElementNotInteractableException,
        ElementClickInterceptedException,
    ):
        LOGGER.debug("Cookies banner not found.")
    # mod name
    LOGGER.info("File name: '{}'".format(name))
    if not dry_run:
        driver.find_element_by_name("name").send_keys(name)
    # mod version
    LOGGER.info("File version: '{}'".format(version))
    if not dry_run:
        driver.find_element_by_name("file-version").send_keys(version)
    # mod category
    LOGGER.info("File category: '{}'".format(CATEGORY))
    if not dry_run:
        Select(
            driver.find_element_by_id("select-file-category")
        ).select_by_visible_text(CATEGORY)
    # check if it is necessary to replace a previous file
    set_file_to_replace(driver, name, dry_run)
    # mod description
    mod_desc = next(value for key, value in DESC_DICT.iteritems() if key in name)
    LOGGER.info("File description:")
    LOGGER.info(textwrap.fill(mod_desc, initial_indent="  ", subsequent_indent="  "))
    if not dry_run:
        driver.find_element_by_id("file-description").send_keys(mod_desc)
    # remove download with manager button
    if not dry_run:
        driver.find_element_by_id("option-dlbutton").click()
    # upload the actual file
    if dry_run:
        LOGGER.info(
            "Would upload file '{}'.".format(os.path.relpath(fpath, os.getcwd()))
        )
        return
    LOGGER.info("Uploading file '{}'...".format(os.path.relpath(fpath, os.getcwd())))
    driver.find_element_by_xpath("//input[@type='file']").send_keys(fpath)
    # Will wait 1 hour for file upload - no point in doing timeouts if goal is ci
    WebDriverWait(driver, 3600).until(
        ec.text_to_be_present_in_element(
            (By.XPATH, "//div[@id='file_uploader']/p"), fname + " has been uploaded."
        )
    )
    LOGGER.debug("Upload finished.")
    # page will auto refresh after "saving" the new file
    with wait_for_page_load(driver):
        driver.find_element_by_xpath("//div[@class='btn inline mod-add-file']").click()


def main(args):
    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=args.logfile)
    creds = utils.parse_deploy_credentials(
        args, ["member_id", "pass_hash", "sid"], args.save_config
    )
    driver = setup_driver(args.driver)
    driver.maximize_window()
    load_cookies(driver, creds)
    with closing(driver):
        for game_id, mod_id in ID_DICT.iteritems():
            driver.get(
                "https://www.nexusmods.com/mods/edit/?step=files"
                "&id={}&game_id={}".format(mod_id, game_id)
            )
            LOGGER.info("Uploading files for game {}.".format(game_id))
            for fname in os.listdir(args.dist_folder):
                fpath = os.path.join(args.dist_folder, fname)
                if not os.path.isfile(fpath):
                    continue
                upload_file(driver, fpath, args.dry_run)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    utils.setup_deploy_parser(argparser)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    open(parsed_args.logfile, "w").close()
    main(parsed_args)
