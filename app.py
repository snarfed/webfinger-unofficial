#!/usr/bin/env python
"""Renders and serves the front page, host meta, and user LRDD files.
"""

__author__ = 'Ryan Barrett <webfinger-unofficial@ryanb.org>'

import appengine_config

import logging
import os
import urlparse

from google.appengine.api import urlfetch
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

  Subclasses must override template_file() and may also override content_type().

  Attributes:
    template_vars: dict
  """
  def __init__(self, *args, **kwargs):
    super(TemplateHandler, self).__init__(*args, **kwargs)
    self.template_vars = dict(BASE_TEMPLATE_VARS)

  def template_file(self):
    """Returns the string template file path."""
    raise NotImplementedError()

  def content_type(self):
    """Returns the string content type."""
    return 'text/html'

  def get(self):
    self.response.headers['Content-Type'] = self.content_type()
    # can't update() because wsgiref.headers.Headers doesn't have it.
    for key, val in BASE_HEADERS.items():
      self.response.headers[key] = val
    self.template_vars.update(self.request.params)
    self.response.out.write(template.render(self.template_file(),
                                            self.template_vars))


class FrontPageHandler(TemplateHandler):
  """Renders and serves /, ie the front page.
  """
  def template_file(self):
    return 'templates/index.html'


class XrdOrJrdHandler(TemplateHandler):
  """Renders and serves an XRD or JRD file.

  JRD is served if the request path ends in .json, or the query parameters
  include 'format=json', or the request headers include
  'Accept: application/json'.

  Subclasses must override template_prefix().
  """
  def content_type(self):
    return 'application/json' if self.is_jrd() else 'application/xrd+xml'

  def template_file(self):
    return self.template_prefix() + ('.jrd' if self.is_jrd() else '.xrd')

  def is_jrd(self):
    """Returns True if JRD should be served, False if XRD."""
    return (os.path.splitext(self.request.path)[1] == '.json' or
            self.request.get('format') == 'json' or
            self.request.headers.get('Accept') == 'application/json')


class HostMetaHandler(XrdOrJrdHandler):
  """Renders and serves the /.well-known/host-meta file.
  """
  def template_prefix(self):
    return 'templates/host-meta'


class UserHandler(XrdOrJrdHandler):
  """Renders and serves /user?uri=... requests.
  """
  def template_prefix(self):
    return 'templates/user'

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
      profile_url = 'http://twitter.com/%s' % username
      vars = {
          'profile_url': profile_url,
          'hcard_url': profile_url,
          'xfn_url': profile_url,
          'poco_url': 'https://twitter-poco.appspot.com/poco/',
          'activitystreams_url': 'https://twitter-activitystreams.appspot.com/',
          }

      # fetch the image URL. it'd be way easier to pass back the api.twitter.com
      # URL itself, since it 302 redirects, but twitter explicitly says we
      # shouldn't do that. :/ ah well.
      # https://dev.twitter.com/docs/api/1/get/users/profile_image/%3Ascreen_name
      try:
        url = ('http://api.twitter.com/1/users/profile_image?screen_name=%s' %
               username)
        resp = urlfetch.fetch(url, follow_redirects=False, deadline=30)
        location = resp.headers.get('Location')
        if resp.status_code == 302 and location:
            vars['picture_url'] = location
      except urlfetch.Error, e:
        logging.exception('Error while fetching %s' % url)

      return vars

    else:
      raise webapp.exc.HTTPInternalServerError('Unknown app id %s.' %
                                               appengine_config.APP_ID)

    return vars


def main():
  application = webapp.WSGIApplication(
      [('/', FrontPageHandler),
       ('/\.well-known/host-meta(?:\.json)?', HostMetaHandler),
       ('/user(?:\.json)?', UserHandler),
       ],
      debug=appengine_config.DEBUG)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
