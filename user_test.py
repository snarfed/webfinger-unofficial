#!/usr/bin/python
"""Unit tests for user.py.
"""

__author__ = ['Ryan Barrett <webfinger@ryanb.org>']

try:
  import json
except ImportError:
  import simplejson as json
import mox
from webob import exc

import user
from webutil import testutil


class UserHandlerTest(testutil.HandlerTest):
  pass
