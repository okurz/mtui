from itertools import count
from mtui.utils import zip_longest
from mtui.utils import check_eq
from argparse import ArgumentTypeError

class RequestReviewIDParseError(ValueError, ArgumentTypeError):
    # Note: need to inherit ArgumentTypeError so the custom exception
    # messages get shown to the users properly
    # by L{argparse.ArgumentParser._get_value}
    def __init__(self, message):
        super(RequestReviewIDParseError, self).__init__(
            "OBS Request Review ID: " + message
        )

class TooManyComponentsError(RequestReviewIDParseError):
    limit = 4
    def __init__(self):
        super(TooManyComponentsError, self).__init__(
            "Too many components (> {0})".format(self.limit)
        )

    @classmethod
    def raise_if(cls, xs):
        if len(xs) > cls.limit:
            raise cls()

class InternalParseError(RequestReviewIDParseError):
    def __init__(self, f, cnt):
        super(InternalParseError, self).__init__(
            "Internal error: f: {0!r} cnt: {1!r}".format(f, cnt)
        )

class MissingComponent(RequestReviewIDParseError):
    def __init__(self, index, expected):
        super(MissingComponent, self).__init__(
            "Missing {0}. component. Expected: {1!r}".format(
                index, expected
        ))

class ComponentParseError(RequestReviewIDParseError):
    def __init__(self, index, expected, got):
        super(ComponentParseError, self).__init__(
            "Failed to parse {0}. component. Expected {1!r}. Got: {2!r}"
                .format(index, expected, got)
        )

class RequestReviewID(object):
    def __init__(self, maintenance_id, review_id):
        for x in ["maintenance_id", "review_id"]:
            if not isinstance(locals()[x], int):
                raise TypeError("{0} expected int, got:{1!}".format(
                    x,
                    locals()[x]
                ))

        self.maintenance_id = maintenance_id
        self.review_id = review_id

    def __str__(self):
        return "SUSE:Maintenance:{0}:{1}".format(
            self.maintenance_id,
            self.review_id
        )

    @classmethod
    def from_str(cls, rrid):
        parsers =  [
              check_eq("SUSE")
            , check_eq("Maintenance")
            , int
            , int
            ]

        # filter empty entries
        xs  = [x for x in rrid.split(":") if x]
        TooManyComponentsError.raise_if(xs)

        # construct [(parser, input, index), ...]
        xs = zip_longest(parsers, xs, range(1,5))

        # apply parsers to inputs, getting parsed values or raise
        xs = [_apply_parser(*ys) for ys in xs]

        mid, rid = xs[-2:]

        return cls(mid, rid)

def _apply_parser(f, x, cnt):
    if not f or not cnt:
        raise InternalParseError(f, cnt)

    if not x:
        raise MissingComponent(cnt, f)

    try:
        return f(x)
    except Exception as e:
        new = ComponentParseError(cnt, f, x)
        new.__cause__ = e
        raise new