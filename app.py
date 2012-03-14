#!/usr/bin/env python
"""Renders and serves the /.well-known/host-meta and /user?uri=... URLs.
"""

__author__ = 'Ryan Barrett <webfinger-unofficial@ryanb.org>'

import appengine_config

import logging
import os
import urlparse

from google.appengine.api import app_identity
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

# maps app id to expected host in user URIs
APP_ID_DOMAINS = {
  'facebook-webfinger': 'facebook.com',
  'twitter-webfinger': 'twitter.com',
  }
APP_ID = app_identity.get_application_id()
DOMAIN = APP_ID_DOMAINS[APP_ID]
# app_identity.get_default_version_hostname() would be better here, but
# it doesn't work in dev_appserver since that doesn't set
# os.environ['DEFAULT_VERSION_HOSTNAME'].
HOST = os.getenv('HTTP_HOST')


class FrontPageHandler(webapp.RequestHandler):
  """Renders and serves /, ie the front page.
  """
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    self.response.headers['Cache-Control'] = 'max-age=300'
    self.response.headers['Access-Control-Allow-Origin'] = '*'
    self.response.out.write(template.render('templates/index.html',
                                            {'domain': DOMAIN, 'host': HOST}))


class HostMetaHandler(webapp.RequestHandler):
  """Renders and serves /.well-known/host-meta.
  """
  def get(self):
    self.response.headers['Content-Type'] = 'application/xrd+xml'
    self.response.headers['Cache-Control'] = 'max-age=300'
    self.response.headers['Access-Control-Allow-Origin'] = '*'
    self.response.out.write(template.render('templates/host-meta.xrd',
                                            {'domain': DOMAIN, 'host': HOST}))


class UserHandler(webapp.RequestHandler):
  """Renders and serves /user?uri=...
  """
  def get(self):
    # parse and validate user uri
    uri = self.request.get('uri')
    if not uri:
      raise webapp.exc.HTTPBadRequest('Missing uri query parameter.')

    parsed = urlparse.urlparse(uri)
    if parsed.scheme and parsed.scheme != 'acct':
      raise webapp.exc.HTTPBadRequest('Unsupported URI scheme: %s' % parsed.scheme)

    try:
      username, host = parsed.path.split('@')
      assert username, host
    except ValueError, AssertionError:
      raise webapp.exc.HTTPBadRequest('Bad user URI: %s' % uri)

    if host not in (HOST, DOMAIN):
      raise webapp.exc.HTTPBadRequest(
        'User URI %s has unsupported host %s; expected %s or %s.' %
        (uri, host, HOST, DOMAIN))

    # render template
    vars = {'uri': uri}
    vars.update(self.get_template_vars(username))

    self.response.headers['Content-Type'] = 'application/xrd+xml'
    self.response.headers['Cache-Control'] = 'max-age=300'
    self.response.headers['Access-Control-Allow-Origin'] = '*'
    self.response.out.write(template.render('templates/user.xrd', vars))

  def get_template_vars(self, username):
    if APP_ID == 'facebook-webfinger':
      return {
          'profile_url': 'http://www.facebook.com/%s' % username,
          'picture_url': 'http://graph.facebook.com/%s/picture' % username,
          'openid_url': 'http://facebook-openid.appspot.com/%s' % username,
          'poco_url': 'https://facebook-poco.appspot.com/poco/',
          'activitystreams_url': 'https://facebook-activitystreams.appspot.com/',
          }
    elif APP_ID == 'twitter-webfinger':
      return {
          'profile_url': 'http://twitter.com/%s' % username,
          'picture_url':
            'http://api.twitter.com/1/users/profile_image?screen_name=%s' % username,
          'poco_url': 'https://twitter-poco.appspot.com/poco/',
          'activitystreams_url': 'https://twitter-activitystreams.appspot.com/',
          }
    else:
      raise webapp.exc.HTTPInternalServerError('Unknown app id %s.' % APP_ID)

    return vars


def main():
  application = webapp.WSGIApplication(
      [('/', FrontPageHandler),
       ('/.well-known/host-meta', HostMetaHandler),
       ('/user', UserHandler),
       ],
      debug=appengine_config.DEBUG)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
