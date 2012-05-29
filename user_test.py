#!/usr/bin/python
"""Unit tests for user.py.
"""

__author__ = ['Ryan Barrett <webfinger@ryanb.org>']

try:
  import json
except ImportError:
  import simplejson as json
from webob import exc

import appengine_config
import user
from webutil import testutil
from webutil import webapp2

from google.appengine.api import urlfetch


class UserHandlerTest(testutil.HandlerTest):

  def setUp(self):
    super(UserHandlerTest, self).setUp()
    appengine_config.APP_ID = 'facebook-webfinger'
    appengine_config.DOMAIN = 'facebook.com'
    self.response = webapp2.Response()

  def get_public_exponent(self, uri):
    entity = user.User.get_by_key_name(uri)
    assert entity.mod and entity.public_exponent and entity.private_exponent
    return entity.public_exponent

  def test_no_uri_error(self):
    resp = user.application.get_response('/user')
    self.assertEquals(400, resp.status_int)

  def test_uri_scheme_not_acct_error(self):
    resp = user.application.get_response('/user?uri=mailto:ryan@facebook.com')
    self.assertEquals(400, resp.status_int)

  def test_bad_uri_format_error(self):
    resp = user.application.get_response('/user?uri=acct:foo')
    self.assertEquals(400, resp.status_int)

  def test_uri_wrong_domain_error(self):
    resp = user.application.get_response('/user?uri=acct:ryan@twitter.com')
    self.assertEquals(400, resp.status_int)

  def test_facebook(self):
    req = webapp2.Request.blank('/user.json?uri=acct:ryan@facebook.com')
    handler = user.UserHandler(req, self.response)

    vars = handler.template_vars()
    self.assert_equals(
      {'profile_url': 'http://www.facebook.com/ryan',
       'picture_url': 'http://graph.facebook.com/ryan/picture',
       'openid_url': 'http://facebook-openid.appspot.com/ryan',
       'poco_url': 'https://facebook-poco.appspot.com/poco/',
       'activitystreams_url': 'https://facebook-activitystreams.appspot.com/',
       'uri': 'acct:ryan@facebook.com',
       'magic_key_public_exponent': self.get_public_exponent('acct:ryan@facebook.com'),
       },
      vars)


  def test_twitter(self):
    redirect = self.UrlfetchResult(302, '', headers={'Location': 'http://my/image'})
    urlfetch.fetch('http://api.twitter.com/1/users/profile_image?screen_name=ryan',
                   deadline=30, follow_redirects=False)\
                   .AndReturn(redirect)
    self.mox.ReplayAll()

    appengine_config.APP_ID = 'twitter-webfinger'
    appengine_config.DOMAIN = 'twitter.com'

    req = webapp2.Request.blank('/user.json?uri=acct:ryan@twitter.com')
    handler = user.UserHandler(req, self.response)
    vars = handler.template_vars()
    self.assert_equals(
      {'profile_url': 'http://twitter.com/ryan',
       'hcard_url': 'http://twitter.com/ryan',
       'xfn_url': 'http://twitter.com/ryan',
       'poco_url': 'https://twitter-poco.appspot.com/poco/',
       'activitystreams_url': 'https://twitter-activitystreams.appspot.com/',
       'uri': 'acct:ryan@twitter.com',
       'picture_url': 'http://my/image',
       'magic_key_public_exponent': self.get_public_exponent('acct:ryan@twitter.com'),
       },
      vars)

  def test_keypair_is_persistent(self):
    req = webapp2.Request.blank('/user.json?uri=acct:ryan@facebook.com')
    handler = user.UserHandler(req, self.response)

    first_pubexp = handler.template_vars()['magic_key_public_exponent']
    second_pubexp = handler.template_vars()['magic_key_public_exponent']
    self.assertEqual(first_pubexp, second_pubexp)


  def test_twitter_profile_image_urlfetch_fails(self):
    urlfetch.fetch('http://api.twitter.com/1/users/profile_image?screen_name=ryan',
                   deadline=30, follow_redirects=False)\
                   .AndRaise(urlfetch.Error())
    self.mox.ReplayAll()

    appengine_config.APP_ID = 'twitter-webfinger'
    appengine_config.DOMAIN = 'twitter.com'

    req = webapp2.Request.blank('/user.json?uri=acct:ryan@twitter.com')
    handler = user.UserHandler(req, self.response)
    self.assertEquals(None, handler.template_vars().get('picture_url'))
