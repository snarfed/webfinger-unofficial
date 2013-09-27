#!/usr/bin/python
"""Unit tests for user.py.
"""

__author__ = ['Ryan Barrett <webfinger@ryanb.org>']

try:
  import json
except ImportError:
  import simplejson as json
import mox
import urllib2
from webob import exc

import appengine_config
import user
from webutil import testutil
from webutil import webapp2


class UserHandlerTest(testutil.HandlerTest):

  def setUp(self):
    super(UserHandlerTest, self).setUp()
    appengine_config.APP_ID = 'facebook-webfinger'
    appengine_config.DOMAIN = 'facebook.com'
    appengine_config.USER_KEY_HANDLER_SECRET = 'secret'
    self.response = webapp2.Response()

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
    resp = user.application.get_response('/user?uri=acct:ryan@xyz.com')
    self.assertEquals(400, resp.status_int)

  def test_facebook(self):
    req = webapp2.Request.blank('/user.json?uri=acct:ryan@facebook.com')
    handler = user.UserHandler(req, self.response)

    vars = handler.template_vars()
    ryan = user.User.get_by_key_name('acct:ryan@facebook.com')
    self.assert_equals(
      {'username': 'ryan',
       'domain': 'facebook.com',
       'profile_url': 'http://www.facebook.com/ryan',
       'picture_url': 'http://graph.facebook.com/ryan/picture',
       'openid_url': 'http://facebook-openid.appspot.com/ryan',
       'poco_url': 'https://facebook-poco.appspot.com/poco/',
       'activitystreams_url': 'https://facebook-activitystreams.appspot.com/',
       'uri': 'acct:ryan@facebook.com',
       'magic_public_key': 'RSA.%s.%s' % (ryan.mod, ryan.public_exponent),
       },
      vars)


  def test_twitter(self):
    self.expect_urlopen('https://api.twitter.com/1.1/users/show.json?screen_name=ryan',
                        json.dumps({'profile_image_url': 'http://pic/ture'}))
    self.mox.ReplayAll()

    appengine_config.APP_ID = 'twitter-webfinger'
    appengine_config.DOMAIN = 'twitter.com'

    req = webapp2.Request.blank('/user.json?uri=acct:ryan@twitter.com')
    handler = user.UserHandler(req, self.response)
    vars = handler.template_vars()
    ryan = user.User.get_by_key_name('acct:ryan@twitter.com')
    self.assert_equals(
      {'username': 'ryan',
       'domain': 'twitter.com',
       'profile_url': 'http://twitter.com/ryan',
       'hcard_url': 'http://twitter.com/ryan',
       'xfn_url': 'http://twitter.com/ryan',
       'poco_url': 'https://twitter-poco.appspot.com/poco/',
       'activitystreams_url': 'https://twitter-activitystreams.appspot.com/',
       'uri': 'acct:ryan@twitter.com',
       'picture_url': 'http://pic/ture',
       'magic_public_key': 'RSA.%s.%s' % (ryan.mod, ryan.public_exponent),
       },
      vars)

  def test_twitter_profile_image_urlopen_fails(self):
    url = 'https://api.twitter.com/1.1/users/show.json?screen_name=ryan'
    urllib2.urlopen(mox.Func(lambda req: req.get_full_url() == url),
                    timeout=999).AndRaise(urllib2.URLError(''))
    self.mox.ReplayAll()

    appengine_config.APP_ID = 'twitter-webfinger'
    appengine_config.DOMAIN = 'twitter.com'

    req = webapp2.Request.blank('/user.json?uri=acct:ryan@twitter.com')
    handler = user.UserHandler(req, self.response)
    self.assertEquals(None, handler.template_vars().get('picture_url'))

  def test_keypair_is_persistent(self):
    req = webapp2.Request.blank('/user.json?uri=acct:ryan@facebook.com')
    handler = user.UserHandler(req, self.response)

    first = handler.template_vars()
    second = handler.template_vars()
    self.assertEqual(first['magic_public_key'], second['magic_public_key'])

  def test_user_key_handler(self):
    resp = user.application.get_response('/user_key?uri=acct:ryan&secret=secret')
    ryan = user.User.get_by_key_name('acct:ryan')
    self.assertEqual(200, resp.status_int)
    self.assertEqual({
        'public_exponent': ryan.public_exponent,
        'private_exponent': ryan.private_exponent,
        'mod': ryan.mod
       }, json.loads(resp.body))

  def test_user_key_handler_bad_secret(self):
    user.User(key_name='acct:ryan@facebook.com',
              public_exponent='123', private_exponent='456', mod='789').save()
    resp = user.application.get_response(
      '/user_key?uri=acct:ryan@facebook.com&secret=bad')
    self.assertEqual(403, resp.status_int)
