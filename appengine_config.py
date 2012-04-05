"""App Engine settings.
"""

from webutil.appengine_config import *

# maps app id to domain
DOMAINS = {
  'facebook-webfinger': 'facebook.com',
  'twitter-webfinger': 'twitter.com',
  }

DOMAIN = DOMAINS.get(APP_ID)
