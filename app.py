#!/usr/bin/env python
"""Renders and serves the /.well-known/host-meta and /user?uri=... URLs.
"""

__author__ = 'Ryan Barrett <webfinger-unofficial@ryanb.org>'

import appengine_config

import logging
import os
import urlparse

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template


class HostMetaHandler(webapp.RequestHandler):
  """Renders and serves /.well-known/host-meta.

  TODO: add caching headers
  """

  def get(self):
    self.response.headers['Content-Type'] = 'application/xrd+xml'
    self.response.out.write(template.render(
        'templates/host-meta.xrd',
        # app_identity.get_default_version_hostname() would be better here, but
        # it doesn't work in dev_appserver since that doesn't set
        {'lrdd_url': 'https://%s/user?uri={uri}' % os.getenv('HTTP_HOST')}))


class UserHandler(webapp.RequestHandler):
  """Renders and serves /user?uri=...

  TODO: add caching headers
  """

  def get(self):
    # parse and validate user uri
    uri = self.request.get('uri')
    if not uri:
      raise webapp.exc.HTTPBadRequest('Missing uri query parameter.')

    scheme, user = urlparse.urlparse(uri)
    if scheme != 'acct':
      raise webapp.exc.HTTPBadRequest('URI must start with acct:.')

    try:
      username, host = user.split('@')
      assert username, host
    except ValueError, AssertionError:
      raise webapp.exc.HTTPBadRequest('Bad user URI: %s' % uri)

    # render template
    vars = {'uri': uri}
    vars.update(self.get_template_vars(username, host))

    self.response.headers['Content-Type'] = 'application/xrd+xml'
    self.response.out.write(template.render('templates/user.xrd', vars))

  def get_template_vars(self, username, host):
    if host == 'facebook.com':
      return {
          'profile_url': 'http://www.facebook.com/%s' % username,
          'picture_url': 'http://graph.facebook.com/%s/picture' % username,
          'openid_url': 'http://facebook-openid.appspot.com/%s' % username,
          }
    else:
      raise webapp.exc.HTTPInternalServerError('%s is not yet supported.' % host)

    return vars


def main():
  application = webapp.WSGIApplication(
      [('/.well-known/host-meta', HostMetaHandler),
       ('/user', UserHandler),
       ],
      debug=appengine_config.DEBUG)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
