# -*- coding: utf-8 -*-


import sys
import logging
from subprocess import CalledProcessError

from .argparse import ArgsParseFailure
from mtui.log import create_logger
from mtui.config import Config
from mtui.prompt import CommandPrompt
from mtui.display import CommandPromptDisplay
from mtui.messages import SvnCheckoutInterruptedError
from mtui.args import get_parser
from mtui.systemcheck import detect_system


def main():
    logger = create_logger()

    p = get_parser(sys)
    try:
        args = p.parse_args(sys.argv[1:])
    except ArgsParseFailure as e:
        return e.status

    if args.noninteractive and not args.prerun:
        logger.error("--noninteractive makes no sense without --prerun")
        p.print_help()
        return 1

    cfg = Config(logger)
    sys.exit(run_mtui(sys, cfg, logger, CommandPrompt, CommandPromptDisplay, args))


def run_mtui(sys, config, log, Prompt, Display, args):

    if args.debug:
        log.setLevel(level=logging.DEBUG)

    config.merge_args(args)

    update = args.review_id
    config.distro, config.distro_ver, config.distro_kernel = detect_system()

    prompt = Prompt(config, log, sys, Display)
    if update:
        try:
            prompt.load_update(update, autoconnect=not bool(args.sut))
        except (SvnCheckoutInterruptedError, CalledProcessError) as e:
            log.error(e)
            return 1

    if args.sut:
        for x in args.sut:
            try:
                prompt.do_add_host(x.print_args())
            except BaseException:
                pass

    prompt.interactive = not args.noninteractive

    if args.prerun:
        prompt.set_cmdqueue([x.rstrip()
                             for x in args.prerun.readlines()
                             if not x.startswith('#')])

    prompt.cmdloop()
    return 0
