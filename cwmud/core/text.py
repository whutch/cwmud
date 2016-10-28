# -*- coding: utf-8 -*-
"""Text manipulation and processing."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)


# TODO: should every character after a caret be considered a code?
CARET_CODES = [
    "^k", "^K", "^r", "^R", "^g", "^G", "^y", "^Y", "^b", "^B",
    "^m", "^M", "^c", "^C", "^w", "^W", "^0", "^1", "^2", "^3",
    "^4", "^5", "^6", "^d", "^I", "^i", "^~", "^U", "^u", "^!",
    "^.", "^s", "^l"]


def strip_caret_codes(text):
    """Strip out any caret codes from a string.

    :param str text: The text to strip the codes from
    :returns str: The clean text

    """
    text = text.replace("^^", "\0")
    for code in CARET_CODES:
        text = text.replace(code, "")
    return text.replace("\0", "^")
