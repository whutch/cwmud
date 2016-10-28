# -*- coding: utf-8 -*-
"""Message brokering."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import redis


BROKER = redis.StrictRedis(decode_responses=True)


def get_pubsub():
    """Return a Redis pubsub connection."""
    return BROKER.pubsub(ignore_subscribe_messages=True)
