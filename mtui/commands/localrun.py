from argparse import REMAINDER
from logging import getLogger
from subprocess import check_call

from mtui.commands import Command

logger = getLogger("mtui.commands.lrun")

class LocalRun(Command):
    """
    Run command in local shell
    Command run in CWD where is mtui started unless is chroot to template dir enabled.
    """

    command = "lrun"

    @classmethod
    def _add_arguments(cls, parser) -> None:
        parser.add_argument(
            "command", nargs=REMAINDER, help="command to run on local shell"
        )

    def __call__(self):
        if not self.args.command:
            logger.error("Missing argument")
            return

        check_call(" ".join(self.args.command), shell=True)
