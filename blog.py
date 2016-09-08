import os
import webapp2
import jinja2
import hashlib
import hmac
import random
import re
import string
#from string import letters
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

class MainPage(BlogHandler):
  def get(self):
      self.write('Hello, Udacity!')

##### blog stuff

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

# User registration table
# Every entity in the AppEngine has a unique key and id
#Users().key().id()
class Users(db.Model):
    username = db.StringProperty(required = True)
    password = db.TextProperty(required = True)
    email = db.TextProperty()#(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

# Register a new user in users table

class BlogFront(BlogHandler):
    def get(self):
        posts = db.GqlQuery("select * from Post order by created desc limit 10")
        self.render('front.html', posts = posts)

class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        self.render("permalink.html", post = post)

class NewPost(BlogHandler):
    def get(self):
        self.render("newpost.html")

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:
            p = Post(parent = blog_key(), subject = subject, content = content)
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject, content=content, error=error)



###### Unit 2 HW's
class Rot13(BlogHandler):
    def get(self):
        self.render('rot13-form.html')

    def post(self):
        rot13 = ''
        text = self.request.get('text')
        if text:
            rot13 = text.encode('rot13')

        self.render('rot13-form.html', text = rot13)


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

## Cookie related functions
SECRET='t0p5ecret'
def hash_str(s):
    #return hashlib.md5(s).hexdigest();
    return hmac.new(SECRET, s).hexdigest();

# Function takes a string 
# and returns a string of the format: s|HASH
def make_secure_val(s):
    #return s+"|"+hash_str(s);
    return '%s|%s' %(s, hash_str(s))

# -----------------
# User Instructions
# 
# Implement the function check_secure_val, which takes a string of the format 
# s,HASH
# and returns s if hash_str(s) == HASH, otherwise None 
def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val(val) :
        return int(val)
    else :
        return 0

# Password related functions
def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    dig = hashlib.sha256(name+pw+salt).hexdigest()
    return '%s,%s' %(dig, salt)    
#    return hashlib.sha256(name+pw+salt).hexdigest() + ',' + salt

def valid_pw(user, pw, h):
    salt = h.split(',')[1]
    return h==make_pw_hash(user, pw, salt)
    
def check_user_exist(username):
    query = datamodel.User().all()
    for result in query:
        print result.key().id()

class Login(BlogHandler):

    def get(self):
        self.render("login-form.html")

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        params = dict(username = username)
        have_error = True
        params['error_username'] = "Invalid user or passowrd."
        cursor = db.GqlQuery(
             "SELECT * FROM Users WHERE username='" + username +"' LIMIT 1")

        if cursor:
            for user in cursor:
                if username == user.username:
                   if valid_pw(username, password, user.password):
                        # Set uid|hash - cookie.
                        uid = user.key().id()
                        uid_cookie = make_secure_val(str(uid))
                        self.response.headers.add_header('Set-Cookie',
                                        'uid=%s;Path=/' %uid_cookie)
                        self.redirect('/blog/welcome')
                        have_error = False
        if (have_error):
            self.render('login-form.html', **params)
        
class Signup(BlogHandler):

    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        params = dict(username = username,
                      email = email)

        if not valid_username(username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif password != verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True
        # ptional
        if email :
            if not valid_email(email):
                params['error_email'] = "That's not a valid email."
                have_error = True
        else:
            email = ""
            
        if have_error:
            self.render('signup-form.html', **params)
        else:
            #check if user already exist
            cursor = db.GqlQuery(
                "SELECT * FROM Users WHERE username='" + username +"'")
            if cursor:
                for user in cursor:
                    if username == user.username:
                        params['error_username'] = "User already exist."
                        have_error = True

            if have_error:
                params['error_username'] = "User already exist."
                self.render('signup-form.html', **params)
            else :
                # Save user in table
                # No plain text password:
                pass_digest = make_pw_hash(username, password)
                u = Users(username = username,
                    password = pass_digest,
                    email = email);
                u.put();
                uid = u.key().id();
                # Set uid|hash - cookie.
                uid_cookie = make_secure_val(str(uid))
                self.response.headers.add_header('Set-Cookie',
                    'uid=%s;Path=/' %uid_cookie)
                #self.redirect('/blog/welcome?username=' + username)
                self.redirect('/blog/welcome')            

class Welcome(BlogHandler):
    def get(self):
        #Get user name from cookie
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        username =""
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        else: # try to get from URL
            username = self.request.get('username')
        if valid_username(username):
            self.render('welcome.html', username = username)
        else:
            self.redirect('/blog/signup')

app = webapp2.WSGIApplication([
       ('/', MainPage),
       ('/unit2/rot13', Rot13),
       ('/blog/login', Login),
       ('/blog/signup', Signup),
       ('/blog/welcome', Welcome),
       ('/blog/?', BlogFront),
       ('/blog/([0-9]+)', PostPage),
       ('/blog/newpost', NewPost),
       ],
      debug=True)
