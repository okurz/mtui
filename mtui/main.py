# -*- coding: utf-8 -*-

import os, glob, stat
import sys
import errno
import getopt
import logging
import shutil
import re
from traceback import format_exc
import warnings
from argparse import ArgumentParser

from mtui import log as _crap_imported_for_side_effects
from mtui.config import Config
from mtui.prompt import CommandPrompt
from mtui.template import TestReport, TestReportFactory
from mtui import __version__

def get_parser():
    """
    :covered-by: tests.test_main.test_argparser_*
    """
    # FIXME: implement -m and -s as type for argparse

    p = ArgumentParser()
    p.add_argument(
        '-l', '--location',
        type=str,
        help='override config mtui.location'
    )
    p.add_argument(
        '-a', '--autoadd',
        type=str,
        action='append',
        help='autoconnect to hosts defined by cumulative attributes'
    )
    p.add_argument(
        '-t', '--template_dir',
        type=str,
        help='override config mtui.template_dir'
    )
    p.add_argument(
        '-m', '--md5',
        type=str,
        help='md5 update identifier'
    )
    p.add_argument(
        '-s', '--sut',
        type=str,
        action='append',
        help='cumulatively override default hosts from template \n'
            "format: hostname,system"
    )
    p.add_argument(
        '-p', '--prerun',
        type=file,
        help='script with a set of MTUI commands to run at start'
    )
    p.add_argument(
        '-w', '--connection_timeout',
        type=int,
        help= 'override config mtui.connection_timeout'
    )
    p.add_argument(
        '-n', '--non-interactive',
        action='store_true',
        default=False,
        help='non-interactive update shell'
    )
    p.add_argument(
        '-d', '--debug',
        action='store_true',
        default=False,
        help='enable debugging output'
    )
    p.add_argument(
        '-V', '--version',
        action='store_true',
        default=False,
        help='print version and exit'
    )
    return p

def main():
    sys.exit(run_mtui(
      sys
    , Config()
    , logging.getLogger('mtui')
    , TestReportFactory
    , CommandPrompt
    ))

def run_mtui(
  sys
, config
, log
, TestReportFactory
, Prompt
):
    p = get_parser()
    args = p.parse_args(sys.argv[1:])

    if args.md5:
        if not re.match(r'^([a-fA-F\d]{32})$', args.md5):
            raise ValueError('invalid --md5 value')

    if args.non_interactive and not args.prerun:
        log.error("--non-interactive makes no sense without --prerun")
        p.print_help()
        return 1

    if args.version:
        sys.stdout.write(__version__ + "\n")
        return 0

    if args.debug:
        log.setLevel(level=logging.DEBUG)

    config.merge_args(args)

    tr = TestReportFactory(config, log, args.md5)
    if args.sut:
        tr.systems = dict([tuple(x.split(",")) for x in args.sut])
    else:
        tr.load_systems_from_testplatforms()

    targets = tr.connect_targets()
    prompt = Prompt(targets, tr, config, log)

    if args.autoadd:
        prompt.do_autoadd(" ".join(args.autoadd))

    prompt.interactive = not args.non_interactive

    if args.prerun:
        prompt.set_cmdqueue([x.rstrip()
            for x in args.prerun.readlines()
            if not x.startswith('#')])

    prompt.cmdloop()
    return 0
