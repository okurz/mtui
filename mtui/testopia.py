# -*- coding: utf-8 -*-
#
# manage connection to Testopia
#

import re
import collections
from logging import getLogger
from xml.sax import saxutils

from mtui.connector.bugzilla import Bugzilla

from mtui.utils import nottest


logger = getLogger("mtui.testopia")


@nottest
class Testopia(object):

    """Managing Testopia testcases

    Interface to the Testopia XMLRPC API documented at
    https://wiki.mozilla.org/Testopia:Documentation:XMLRPC

    """

    # product to testplan maps
    plans = {"9": "251", "10": "263,351", "11": "2672", "12": "4809", "15": "6151"}
    status = {3: "disabled", 2: "confirmed", 1: "proposed"}
    automated = {1: "yes", 0: "no"}

    def __init__(self, config, product=None, packages=None):
        """create xmlrpclib.ServerProxy object for communication

        creates a ServerProxy XMLRPC instance with Testopie credentials

        Keyword arguments:
        None

        """

        self.testcases = {}
        self.product = product
        self.packages = packages
        self.casebuffer = collections.deque(maxlen=10)

        interface = config.testopia_interface
        username = config.testopia_user
        password = config.testopia_pass

        logger.debug("creating Testopia Interface at {!s}".format(interface))
        self.bugzilla = Bugzilla(interface, username, password)

        # cache testcases since Testopia is slow
        self.update_testcase_list()

    @staticmethod
    def _unescape_html(text):
        text = re.sub("<br>", "\n", text)
        text = re.sub("</span>", "\n", text)
        text = re.sub("</div>", "\n", text)
        text = re.sub("&nbsp;", " ", text)
        text = re.sub("<[^>]*>", "", text)

        try:
            return saxutils.unescape(text)
        except Exception:
            return text

    @staticmethod
    def _escape_html(text):
        entities = {"|br|": "<br>"}
        try:
            return saxutils.escape(text, entities)
        except Exception:
            return text

    def convert_datafield(self, datafield):
        for key in list(datafield.keys()):
            if key == "automated":
                automated = {}
                for k, v in list(self.automated.items()):
                    automated[v] = k
                try:
                    datafield["isautomated"] = automated[datafield.pop("automated")]
                except KeyError as error:
                    logger.critical(
                        "unknown value for automated: {!s}. using default.".format(
                            error
                        )
                    )
            elif key == "status":
                status = {}
                for k, v in list(self.status.items()):
                    status[v] = k
                try:
                    datafield["case_status_id"] = status[datafield.pop("status")]
                except KeyError as error:
                    logger.critical(
                        "unknown value for status: {!s}. using default.".format(error)
                    )

        return datafield

    def update_testcase_list(self):
        logger.debug("updating Testopia testcase list")
        self.testcases = self.get_testcase_list()

    def append_testcase_cache(self, case_id, testcase):
        logger.debug("writing testcase {!s} to cache".format(case_id))
        self.casebuffer.append({"case_id": case_id, "testcase": testcase})

    def remove_testcase_cache(self, case_id):
        element = None
        for case in self.casebuffer:
            if case["case_id"] == case_id:
                element = case

        if element:
            logger.debug("removing testcase {!s} from cache".format(element["case_id"]))
            self.casebuffer.remove(element)

    def get_testcase_list(self):
        """queries package testcases

        search for package testcases for the update product

        Keyword arguments:
        packages -- list of package names to search for
        product  -- SUSE product to query for (11, 12, 15)

        """

        cases = {}

        if not self.product and not self.packages:
            return {}

        logger.debug(
            "getting testcase list for packages {!s} in testplan {!s}".format(
                self.packages, self.plans[self.product]
            )
        )
        tags = ",".join(
            ["packagename_{name},testcase_{name}".format(name=i) for i in self.packages]
        )

        try:
            response = self.bugzilla.query_interface(
                "TestCase.list",
                {
                    "tags": tags,
                    "tags_type": "anyexact",
                    "plan_id": self.plans[self.product],
                },
            )
        except Exception:
            logger.critical("failed to query TestCase.list")
            return {}

        # since we're too lazy to copy testcases over to our latest products,
        # fall back to the old ones if none were found
        if not response:
            response = self.bugzilla.query_interface(
                "TestCase.list",
                {"tags": tags, "tags_type": "anyexact", "plan_id": self.plans["11"]},
            )
            if response:
                logger.warning(
                    "found testcases for product 11 while {!s} was empty".format(
                        self.product
                    )
                )
                logger.warning(
                    "please consider migrating the testcases to product {!s}".format(
                        self.product
                    )
                )

        for case in response:
            cases[case["case_id"]] = {
                "summary": case["summary"],
                "status": self.status[case["case_status_id"]],
                "automated": self.automated[case["isautomated"]],
            }

        return cases

    def get_testcase(self, case_id):
        """queries testopia testcase actions

        show testcase actions

        Keyword arguments:
        case_id  -- Testopia testcase ID

        """

        if not case_id:
            return {}

        for case in self.casebuffer:
            if case["case_id"] == case_id:
                logger.debug("found testcase {!s} in cache".format(case_id))
                return case["testcase"]

        try:
            response = self.bugzilla.query_interface("TestCase.get", case_id)
        except Exception:
            logger.critical("failed to query TestCase.get")
            return {}

        # first, import mandatory fields
        try:
            testcase = {
                "action": self._unescape_html(response["text"]["action"]),
                "summary": self._unescape_html(response["summary"]),
                "status": self.status[response["case_status_id"]],
                "automated": self.automated[response["isautomated"]],
            }
        except KeyError:
            logger.error("testcase {!s} not found".format(case_id))
            return {}

        # import optional fields
        try:
            testcase["requirement"] = self._unescape_html(response["requirement"])
        except KeyError:
            testcase["requirement"] = ""
        try:
            testcase["breakdown"] = self._unescape_html(response["text"]["breakdown"])
        except KeyError:
            testcase["breakdown"] = ""
        try:
            testcase["setup"] = self._unescape_html(response["text"]["setup"])
        except KeyError:
            testcase["setup"] = ""
        try:
            testcase["effect"] = self._unescape_html(response["text"]["effect"])
        except KeyError:
            testcase["effect"] = ""

        self.append_testcase_cache(case_id, testcase)

        return testcase

    def create_testcase(self, values):
        """ create new testopia testcase

        creates new testopia testcase in current update testrun

        Keyword arguments:
        values  -- Testopia testcase values

        """
        try:
            plan = self.plans[self.product]
        except KeyError:
            logger.error("no testplan found for product {!s}".format(self.product))
            raise

        logger.debug("creating testcase for product {!s}".format(self.product))

        testcase = {"status": 2, "category": 2919, "priority": 6, "plans": plan}

        for k, v in list(values.items()):
            values[k] = self._escape_html(v)

        testcase.update(values)

        testcase = self.convert_datafield(testcase)

        try:
            response = self.bugzilla.query_interface("TestCase.create", testcase)
        except Exception:
            logger.critical("failed to query TestCase.create")
            raise

        self.testcases.update(
            {
                response["case_id"]: {
                    "summary": response["summary"],
                    "status": self.status[response["case_status_id"]],
                    "automated": self.automated[response["isautomated"]],
                }
            }
        )

        return response["case_id"]

    def modify_testcase(self, case_id, values):
        """ modify existing Testopia testcase

        updates fields of already existing Testopia testcase

        Keyword arguments:
        case_id -- Testopia testcase ID
        values  -- Testopia testcase values
        """

        for k, v in list(values.items()):
            values[k] = self._escape_html(v)

        summary = values["summary"]
        requirement = values["requirement"]
        action = values["action"]
        setup = values["setup"]
        effect = values["effect"]
        breakdown = values["breakdown"]

        update = {
            "summary": summary,
            "requirement": requirement,
            "automated": values["automated"],
            "status": values["status"],
        }

        update = self.convert_datafield(update)

        try:
            self.bugzilla.query_interface("TestCase.update", case_id, update)
        except Exception:
            logger.critical("failed to query TestCase.update")
            raise

        try:
            self.bugzilla.query_interface(
                "TestCase.store_text", case_id, action, effect, setup, breakdown
            )
        except Exception:
            logger.critical("failed to query TestCase.store_text")
            raise

        try:
            tags = self.bugzilla.query_interface("TestCase.get_tags", case_id)
        except Exception:
            logger.critical("failed to query TestCase.get_tags")
            raise

        new_tags = set(
            [
                tag.replace("packagename_", "testcase_")
                for tag in tags
                if tag.startswith("packagename")
            ]
        ) - set(tags)
        if new_tags:
            try:
                tags = self.bugzilla.query_interface(
                    "TestCase.add_tag", case_id, list(new_tags)
                )
            except Exception:
                logger.critical("failed to query TestCase.add_tag")
                raise

        logger.debug("values for testcase {!s} stored".format(case_id))
        # remove testcase from cache to get the updated version on
        # the next query
        self.remove_testcase_cache(case_id)
        self.update_testcase_list()
