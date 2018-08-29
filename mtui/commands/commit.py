# -*- coding: utf-8 -*-

import subprocess

from argparse import REMAINDER
from traceback import format_exc

from mtui.commands import Command
from mtui.utils import requires_update, complete_choices

# TODO: when move to Path-like objects refactor is needed
from pathlib import Path


class Commit(Command):

    """
    Commits testing template to the SVN. This can be run after the
    testing has finished an the template is in the final state.
    """

    command = "commit"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument(
            "-m",
            "--msg",
            action="append",
            nargs=REMAINDER,
            help='commit message')
        return parser

    @requires_update
    def run(self):

        checkout = Path(self.metadata.report_wd())
        cwd = str(checkout)

        msg = []
        if self.args.msg:
            msg = ["-m"] + ['"' + " ".join([x for x in self.args.msg[0]]) + '"']

        try:
            subprocess.check_call(
                'svn add --force {}'.format(self.config.install_logs).split(),
                cwd=cwd)
            if checkout.joinpath("checkers.log").exists():
                subprocess.check_call('svn add --force {}'.format(checkout / "checkers.log").split(), cwd=cwd)
            subprocess.check_call('svn up'.split(), cwd=cwd)
            subprocess.check_call('svn ci'.split() + msg, cwd=cwd)

            self.log.info(
                "Testreport in: {}".format(
                    self.metadata._testreport_url()))

        except Exception:
            self.log.error('committing template.failed')
            self.log.debug(format_exc())

    @staticmethod
    def complete(_, text, line, begidx, endidx):
        return complete_choices([('-m', '--msg'), ], line, text)
