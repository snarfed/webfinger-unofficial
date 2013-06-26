#!/usr/bin/env python
"""Serves user LRDD files at the /user endpoint.

Includes Magic Signatures public keys. Details:
http://salmon-protocol.googlecode.com/svn/trunk/draft-panzer-magicsig-01.html
"""

__author__ = 'Ryan Barrett <webfinger-unofficial@ryanb.org>'

try:
  import json
except ImportError:
  import simplejson as json

import appengine_config

import logging
import os
import urlparse
from webob import exc
from webutil import handlers
from webutil import util
from webutil import webapp2

from django_salmon import magicsigs
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app


class User(db.Model):
  """Stores a user's public/private key pair used for Magic Signatures.

  The key name is the user URI, including the acct: prefix.

  The modulus and exponent properties are all encoded as base64url (ie URL-safe
  base64) strings as described in RFC 4648 and section 5.1 of the Magic
  Signatures spec.

  Magic Signatures are used to sign Salmon slaps. Details:
  http://salmon-protocol.googlecode.com/svn/trunk/draft-panzer-magicsig-01.html
  http://salmon-protocol.googlecode.com/svn/trunk/draft-panzer-salmon-00.html
  """
  mod = db.StringProperty(required=True)
  public_exponent = db.StringProperty(required=True)
  private_exponent = db.StringProperty(required=True)

  @staticmethod
  @db.transactional
  def get_or_create(uri):
    """Loads and returns a User from the datastore. Creates it if necessary."""
    user = User.get_by_key_name(uri)

    if not user:
      # this uses urandom(), and does some nontrivial math, so it can take a
      # while depending on the amount of randomness available on the system.
      pubexp, mod, privexp = magicsigs.generate()
      user = User(key_name=uri, mod=mod, public_exponent=pubexp,
                  private_exponent=privexp)
      user.put()

    return user


class UserHandler(handlers.XrdOrJrdHandler):
  """Renders and serves /user?uri=... requests.
  """

  def template_prefix(self):
    return 'templates/user'

  def template_vars(self):
    # parse and validate user uri
    uri = self.request.get('uri') or self.request.get('resource')
    if not uri:
      raise exc.HTTPBadRequest('Missing uri query parameter.')

    try:
      allowed_domains = (appengine_config.HOST, appengine_config.DOMAIN)
      username, host = util.parse_acct_uri(uri, allowed_domains)
    except ValueError, e:
      raise exc.HTTPBadRequest(e.message)

    user = User.get_or_create(uri)

    # construct the response
    vars = {
      'uri': uri,
      'magic_public_key': 'RSA.%s.%s' % (user.mod, user.public_exponent),
      }

    if appengine_config.APP_ID == 'facebook-webfinger':
      vars.update({
          'profile_url': 'http://www.facebook.com/%s' % username,
          'picture_url': 'http://graph.facebook.com/%s/picture' % username,
          'openid_url': 'http://facebook-openid.appspot.com/%s' % username,
          'poco_url': 'https://facebook-poco.appspot.com/poco/',
          'activitystreams_url': 'https://facebook-activitystreams.appspot.com/',
          })
      return vars
    elif appengine_config.APP_ID == 'twitter-webfinger':
      profile_url = 'http://twitter.com/%s' % username
      vars.update({
          'profile_url': profile_url,
          'hcard_url': profile_url,
          'xfn_url': profile_url,
          'poco_url': 'https://twitter-poco.appspot.com/poco/',
          'activitystreams_url': 'https://twitter-activitystreams.appspot.com/',
          })

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


class UserKeyHandler(webapp2.RequestHandler):
  """Serves users' Magic Signature private keys.

  The response is a JSON object with public_exponent, private_exponent, and mod.
  """

  def get(self):
    if self.request.get('secret') != appengine_config.USER_KEY_HANDLER_SECRET:
      raise exc.HTTPForbidden()

    user = User.get_or_create(self.request.get('uri'))
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json.dumps(db.to_dict(user), indent=2))


application = webapp2.WSGIApplication(
  [('/(?:.well-known/webfinger|user)(?:\.json)?', UserHandler),
   ('/user(?:\.json)?', UserHandler),
   ('/user_key', UserKeyHandler),
   ],
  debug=appengine_config.DEBUG)


def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
