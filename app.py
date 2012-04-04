#!/usr/bin/env python
"""Serves the HTML front page and discovery files.
"""

__author__ = 'Ryan Barrett <webfinger-unofficial@ryanb.org>'

import appengine_config
from webutil import handlers

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app


class FrontPageHandler(handlers.TemplateHandler):
  """Renders and serves /, ie the front page.
  """
  def template_file(self):
    return 'templates/index.html'

  def template_vars(self):
    return {'domain': appengine_config.DOMAIN}


def main():
  application = webapp.WSGIApplication(
      [('/', FrontPageHandler)] + handlers.HOST_META_ROUTES,
      debug=appengine_config.DEBUG)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
