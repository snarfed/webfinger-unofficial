#!/usr/bin/env python
"""Serves user LRDD files at the /user endpoint.
"""

__author__ = 'Ryan Barrett <webfinger-unofficial@ryanb.org>'

import appengine_config

import logging
import os
import urlparse
from webob import exc
from webutil import handlers
from webutil import webapp2

from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app


class UserHandler(handlers.XrdOrJrdHandler):
  """Renders and serves /user?uri=... requests.
  """

  def template_prefix(self):
    return 'templates/user'

  def template_vars(self):
    # parse and validate user uri
    uri = self.request.get('uri')
    if not uri:
      raise exc.HTTPBadRequest('Missing uri query parameter.')
    self.template_vars = {'uri': uri}

    parsed = urlparse.urlparse(uri)
    if parsed.scheme and parsed.scheme != 'acct':
      raise exc.HTTPBadRequest('Unsupported URI scheme: %s' % parsed.scheme)

    try:
      username, host = parsed.path.split('@')
      assert username, host
    except ValueError, AssertionError:
      raise exc.HTTPBadRequest('Bad user URI: %s' % uri)

    if host not in (appengine_config.HOST, appengine_config.DOMAIN):
      raise exc.HTTPBadRequest(
        'User URI %s has unsupported host %s; expected %s or %s.' %
        (uri, host, appengine_config.HOST, appengine_config.DOMAIN))

    if appengine_config.APP_ID == 'facebook-webfinger':
      return {
          'profile_url': 'http://www.facebook.com/%s' % username,
          'picture_url': 'http://graph.facebook.com/%s/picture' % username,
          'openid_url': 'http://facebook-openid.appspot.com/%s' % username,
          'poco_url': 'https://facebook-poco.appspot.com/poco/',
          'activitystreams_url': 'https://facebook-activitystreams.appspot.com/',
          'uri': uri,
          }
    elif appengine_config.APP_ID == 'twitter-webfinger':
      profile_url = 'http://twitter.com/%s' % username
      vars = {
          'profile_url': profile_url,
          'hcard_url': profile_url,
          'xfn_url': profile_url,
          'poco_url': 'https://twitter-poco.appspot.com/poco/',
          'activitystreams_url': 'https://twitter-activitystreams.appspot.com/',
          'uri': uri,
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
      raise exc.HTTPInternalServerError('Unknown app id %s.' %
                                        appengine_config.APP_ID)


application = webapp2.WSGIApplication(
  [('/user(?:\.json)?', UserHandler)],
  debug=appengine_config.DEBUG)


def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
