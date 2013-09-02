webfinger-unofficial ![Webfinger](https://raw.github.com/snarfed/webfinger-unofficial/master/static/pointing_finger.png)
===

  * [About](#about)
  * [Using](#using)
  * [Future work](#future-work)
  * [Development](#development)


About
---

This is a [WebFinger](http://code.google.com/p/webfinger/) server for Facebook
and Twitter. It's deployed at these endpoints:

http://facebook-webfinger.appspot.com/  
http://twitter-webfinger.appspot.com/

It's part of a suite of projects that implement the
[OStatus](http://ostatus.org/) federation protocols for the major social
networks. The other projects include
[activitystreams-](https://github.com/snarfed/activitystreams-unofficial),
[portablecontacts-](https://github.com/snarfed/portablecontacts-unofficial),
[salmon-](https://github.com/snarfed/salmon-unofficial), and
[ostatus-unofficial](https://github.com/snarfed/ostatus-unofficial).

License: This project is placed in the public domain.


Using
---

This simply implements the
[WebFinger protocol](http://code.google.com/p/webfinger/wiki/WebFingerProtocol)
using Facebook's and Twitter's OAuth authentication and APIs. To use it, just
point your WebFinger client code at the [endpoints above](#about).

If your client consumes arbitrary email addresses, you'll need to hard-code
exceptions for `facebook.com` and `twitter.com` and redirect HTTP requests to
these endpoints. (The user URI may use either domain, e.g.
`snarfed.org@facebook.com` or `snarfed.org@facebook-webfinger.appspot.com`.)


Future work
---

This should be refactored so it can be used as a library, like
[activitystreams-unofficial](https://github.com/snarfed/activitystreams-unofficial).

We'd also love to add more sites! Off the top of my head,
[Yahoo](http://yahoo.com/),
[Microsoft](https://login.live.com/),
[Amazon](http://login.amazon.com/),
[Apple's iCloud](https://www.icloud.com/),
[Instagram](http://instagram.com/developer/),
[WordPress.com](http://wordpress.com/), and
[Sina Weibo](http://en.wikipedia.org/wiki/Sina_Weibo) would be good candidates. If
you're looking to get started, implementing a new site is a good place to start.
It's pretty self contained and the existing sites are good examples to follow,
but it's a decent amount of work, so you'll be familiar with the whole project
by the end.


Development
---

Pull requests are welcome! Feel free to [ping me](http://snarfed.org/about) with
any questions.

Most dependencies are included as git submodules. Be sure to run `git submodule
init` after cloning this repo.

You can run the unit tests with `./alltests.py`. They depend on the
[App Engine SDK](https://developers.google.com/appengine/downloads) and
[mox](http://code.google.com/p/pymox/), both of which you'll need to install
yourself.

Note the `app.yaml.*` files, one for each App Engine app id. To work on or deploy
a specific app id, `symlink app.yaml` to its `app.yaml.xxx` file. Likewise, if you
add a new site, you'll need to add a corresponding `app.yaml.xxx` file.

To deploy:

```shell
rm -f app.yaml && ln -s app.yaml.twitter app.yaml && \
  ~/google_appengine/appcfg.py --oauth2 update . && \
rm -f app.yaml && ln -s app.yaml.facebook app.yaml && \
  ~/google_appengine/appcfg.py --oauth2 update .
```
