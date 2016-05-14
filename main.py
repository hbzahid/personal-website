import os, jinja2, webapp2, json, time
from google.appengine.api import memcache
from google.appengine.ext import ndb

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class MainPage(Handler):
	def get(self):
		self.render('front.html')

def blog_key(name = 'default'):
	return ndb.Key('blogs', name)

class Post(ndb.Model):
	subject = ndb.StringProperty(required=True)
	content = ndb.TextProperty(required=True)
	created = ndb.DateTimeProperty(auto_now_add=True)

	def replace(self):
		return self.content.replace('\n', '<br>')

class NewPost(Handler):
	def get(self):
		self.render("newpost.html")

	def post(self):
		subject = self.request.get('subject')
		content = self.request.get('content')

		if subject and content:
			key = '-'.join(subject.split(' ')).lower()
			entry = Post(id=key, subject=subject, content=content, parent=blog_key())
			entry.put()
			entry_id = str(entry.key.id())
			top_posts(True)
			self.redirect('/blog/%s' % (entry_id))
		else:
			error = "Oops! Seems like you left either the title or the content field empty."
			self.render("newpost.html", subject = subject, content = content, error = error)

def top_posts(update=False):
	key = 'POSTS'
	posts = memcache.get(key)
	if posts is None or update:
		posts = list(ndb.gql("SELECT * FROM Post where ancestor is :1 ORDER BY created DESC LIMIT 10", blog_key()))
		memcache.set(key, posts)
	return posts

class BlogFront(Handler):
	def get(self):
		posts = top_posts()
		self.render("blog-front.html", posts=posts)

def get_post(post_id):
	post_key = 'POST_' + post_id
	post = memcache.get(post_key)
	if post is None:
		post = Post.get_by_id(post_id, parent=blog_key())
		memcache.set(post_key, post)
	return post

class PostPage(Handler):
	def get(self, post_id):
		post = get_post(post_id)
		if post:
			self.render("post.html", post=post)
		else:
			self.error(404)

class FlushCache(Handler):
	def get(self):
		memcache.flush_all()
		next_url = self.get_referer()
		self.redirect(next_url)

class Portfolio(Handler):
	def get(self):
		self.render('portfolio.html')

app = webapp2.WSGIApplication([webapp2.Route('/', handler=MainPage),
							   webapp2.Route('/blog', handler=BlogFront),
							   webapp2.Route('/newpost', handler=NewPost),
							   webapp2.Route(r'/blog/<post_id:[A-Za-z0-9_-]+>', handler=PostPage),
							   webapp2.Route('/flush', handler=FlushCache),
							   webapp2.Route('/portfolio', handler=Portfolio),
                               ],
                              debug=True)