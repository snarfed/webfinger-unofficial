#!/usr/bin/env python
"""Renders and serves the front page, host meta, and user LRDD files.
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
DOMAIN = APP_ID_DOMAINS[appengine_config.APP_ID]

# Included in most static HTTP responses.
BASE_HEADERS = {
  'Cache-Control': 'max-age=300',
  'Access-Control-Allow-Origin': '*',
  }
BASE_TEMPLATE_VARS = {
  'domain': DOMAIN,
  'host': appengine_config.HOST,
  }


class TemplateHandler(webapp.RequestHandler):
  """Renders and serves a template based on class attributes.

  Subclasses must override at least template_file.

  Attributes:
    template_vars: dict

  Class attributes:
    content_type: string
    template: path to template file
  """
  content_type = 'text/html'
  template_file = None

  def __init__(self, *args, **kwargs):
    self.template_vars = dict(BASE_TEMPLATE_VARS)
    super(TemplateHandler, self).__init__(*args, **kwargs)

  def get(self):
    self.response.headers['Content-Type'] = self.content_type
    # can't update() because wsgiref.headers.Headers doesn't have it.
    for key, val in BASE_HEADERS.items():
      self.response.headers[key] = val
    self.template_vars.update(self.request.params)
    self.response.out.write(template.render(self.template_file,
                                            self.template_vars))


class FrontPageHandler(TemplateHandler):
  """Renders and serves /, ie the front page.
  """
  template_file = 'templates/index.html'


class HostMetaXrdHandler(TemplateHandler):
  """Renders and serves the /.well-known/host-meta XRD file.
  """
  content_type = 'application/xrd+xml'
  template_file = 'templates/host-meta.xrd'


class UserHandler(TemplateHandler):
  """Renders and serves /user?uri=...
  """
  content_type = 'application/xrd+xml'
  template_file = 'templates/user.xrd'

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

    if host not in (appengine_config.HOST, DOMAIN):
      raise webapp.exc.HTTPBadRequest(
        'User URI %s has unsupported host %s; expected %s or %s.' %
        (uri, host, appengine_config.HOST, DOMAIN))

    # render template
    self.template_vars = {'uri': uri}
    self.template_vars.update(self.get_template_vars(username))
    super(UserHandler, self).get()

  def get_template_vars(self, username):
    if appengine_config.APP_ID == 'facebook-webfinger':
      return {
          'profile_url': 'http://www.facebook.com/%s' % username,
          'picture_url': 'http://graph.facebook.com/%s/picture' % username,
          'openid_url': 'http://facebook-openid.appspot.com/%s' % username,
          'poco_url': 'https://facebook-poco.appspot.com/poco/',
          'activitystreams_url': 'https://facebook-activitystreams.appspot.com/',
          }
    elif appengine_config.APP_ID == 'twitter-webfinger':
      return {
          'profile_url': 'http://twitter.com/%s' % username,
          'picture_url':
            'http://api.twitter.com/1/users/profile_image?screen_name=%s' % username,
          'poco_url': 'https://twitter-poco.appspot.com/poco/',
          'activitystreams_url': 'https://twitter-activitystreams.appspot.com/',
          }
    else:
      raise webapp.exc.HTTPInternalServerError('Unknown app id %s.' %
                                               appengine_config.APP_ID)

    return vars


def main():
  application = webapp.WSGIApplication(
      [('/', FrontPageHandler),
       ('/.well-known/host-meta', HostMetaXrdHandler),
       ('/user', UserHandler),
       ],
      debug=appengine_config.DEBUG)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
