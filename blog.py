import os
import webapp2
import jinja2
import hashlib
import hmac
import random
import re
import string
from jinja2 import filters, environment
#from string import letters
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

# create a flter to get user name from ID
def getusername(uid):
    return Users.get_by_id(uid).username


# create a flter to get comments for a post
def getcomments(post_id):
    coms = db.GqlQuery("select * from Comments where post_id=" + post_id +
                       " order by created desc")
    return coms;

#Register the filter with Environment
jinja_env.filters['getusername'] = getusername
jinja_env.filters['getcomments'] = getcomments

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
    created_by = db.IntegerProperty(required = True)
    count_like = db.IntegerProperty(default=0)
    count_comment = db.IntegerProperty(default=0)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self, user):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self, u=user)

# User registration table
# Every entity in the AppEngine has a unique key and id
#Users().key().id()
class Users(db.Model):
    username = db.StringProperty(required = True)
    password = db.TextProperty(required = True)
    email = db.TextProperty()#(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

#Comment on blog posts by user
# One user can post multiple comments
# Comments are arranged by time created.
class Comments(db.Model):
    post_id = db.IntegerProperty(required = True)
    user_id = db.IntegerProperty(required = True)
    comment = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

# One Like per user. Up/Dn vote
class Likes(db.Model):
    post_id = db.IntegerProperty(required = True)
    user_id = db.IntegerProperty(required = True)
    like = db.IntegerProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    
# /blog/?        
class BlogFront(webapp2.RequestHandler):
    def get(self):
        # if user logged in render blog else
        # redirect to login 
        #Get user name from cookie
        uid = 0
        username =""
        user = None
        uid_cookie_str = self.request.cookies.get('uid')
        if uid_cookie_str :
            uid = check_secure_val(uid_cookie_str);        
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;

        if not valid_username(username):
            self.redirect('/blog/login')
            #self.render('welcome.html', username = username)
        else:
            posts = db.GqlQuery("select * from Post order by created desc limit 10")
            #Enhance to take comments
            #self.render('front.html', posts = posts, u=user)
            t = jinja_env.get_template('front.html')
            self.response.out.write(t.render(posts=posts, u=user))
            

#Posting a page leads to a perma link.
class PostPage(webapp2.RequestHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        username =""
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        if valid_username(username):
            #self.render("permalink.html", post = post, u=user)
            t = jinja_env.get_template('permalink.html')
            self.response.out.write(t.render(p=post, u=user))
        else:
            self.redirect('/blog/login')
# type of self is webapp.RequestHandler
# refresh the same page.
class LikePost(webapp2.RequestHandler):
    def get(self, post_id):
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        username =""
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
            
        if valid_username(username):
            # User already liked - than no processing
            likes = db.GqlQuery("select * from Likes where " +
                                " user_id=" + str(uid) + 
                                " and post_id=" + str(post_id));
            for like in likes:
                if (like.user_id == uid and
                    like.post_id == int(post_id)) :
                    self.redirect('/blog/'+post_id)
                    return
                
            #Update post like count
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)            
            if post:
                post.count_like = post.count_like+1;
                post.put()                
                # Create Likes - to restrict multiple likes 
                like = Likes(post_id=int(post_id),
                             user_id=uid, like=1)
                like.put()
                self.redirect('/blog/'+post_id)                
            else:
                self.redirect('/blog/')


# Check if user is logged in, if not redirect to login.
# Modify to user both new post and edit existing post
class NewPost(webapp2.RequestHandler):
    def get(self, post_id):
        #Get user name from cookie
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        user=None
        post=None
        # Can't handle zero - throws excption
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        if valid_username(username):
            #self.render('newpost.html', u = user)
            t = jinja_env.get_template('newpost.html')
            self.response.out.write(t.render(p=post, u=user))
        else:
            self.redirect('/blog/login')        

    def post(self, p_id):
        # Validate user
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        user =None
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        if user:
            #post_id = self.request.get('post_id')
            subject = self.request.get('subject')
            content = self.request.get('content')
            post = None
            # if post_id is valid - this is an edit
            if int(p_id) > 0:
                # Handle failure- in case if a invalid key is provided.
                key = db.Key.from_path('Post', int(p_id), parent=blog_key())
                if key:
                    post = db.get(key)                        

            if subject and content:
                if post:
                    post.subject = subject
                    post.content = content
                    post.put()
                else:
                    post = Post(parent = blog_key(), subject = subject, 
                         content = content, created_by=uid)
                    post.put()
                self.redirect('/blog/%s' % str(post.key().id()))
            else: # if updated with blank subject
                error = "subject and content, please!"
                #self.render("newpost.html", post_id=post_id, subject=subject, 
                #            content=content, error=error, u = user)
                t = jinja_env.get_template('newpost.html')
                self.response.out.write(t.render(p=post, u=user))
                
        else:
            self.redirect('/blog/login')
# Global function - all comments and likes with post.
def deletePost(post_id):
    if int(post_id) > 0 :
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        if post:
            coms = db.GqlQuery(
             "SELECT * FROM Comments WHERE post_id=" + str(post.key().id()))
            for c in coms:
                c.delete()
            likes = db.GqlQuery(
             "SELECT * FROM Likes WHERE post_id=" + str(post.key().id()))
            for l in likes:
                l.delete()
            post.delete()
            
            
# Check if user is logged in, if not redirect to login.
# Delete post, comments and likes
class DelPost(webapp2.RequestHandler):
    def get(self, post_id):
        #Get user name from cookie
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        user=None
        post=None
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        if valid_username(username) and post:
            # user is owner of the post
            if int(uid) == post.created_by:
                # delete blog and dependent
                deletePost(post.key().id())
        
        self.redirect('/blog')        

# Check if user is logged in, if not redirect to login.
class CommentPost(webapp2.RequestHandler):
    def get(self, post_id):
        #Get user name from cookie
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        user = None
        if uid != 0:
            user = Users.get_by_id(uid)
        if user:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)                        
            if post:
                coms = getcomments(post_id)
                t = jinja_env.get_template('comment.html')
                #self.render('comment.html', post=post, coms=coms, u = user)
                self.response.out.write(t.render(post=post, coms=coms, u=user))
        else:
            self.redirect('/blog/login')        

    def post(self, post_id):
        # Validate user
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        #post_id = self.get('post_id');
        #Update post like count
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        user = None
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        if user :
            comment = self.request.get('comment')
            # User can't comment his own blog            
            if comment and post.created_by != uid :
                com = Comments(parent = blog_key(), 
                         post_id = int(post_id), 
                         user_id=uid, comment = comment)
                com.put()
                if post: 
                    post.count_comment += 1;
                    post.put()
                # Find and update post id as well
                self.redirect('/blog/%s' % str(post.key().id()))
            else:
                error = "comment, please!"
                coms = getcomments(post_id)
                t = jinja_env.get_template('comment.html')
                self.response.out.write(t.render(posts=posts, coms=coms, u=user))
                #self.render("comment.html", posts=posts,coms=coms,u = user)
        else:
            self.redirect('/blog/login')


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

# Login takes to front page
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
                        self.redirect('/blog/')
                        have_error = False
        if (have_error):
            self.render('login-form.html', **params)

# logout - take to login
class Logout(BlogHandler):
    def get(self):
        # clear cookie.
        self.response.headers.add_header(
                'Set-Cookie', 'uid=;Path=/;')
        self.redirect('/blog/login')

#Sign up  take to blog home
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
                user = Users(username = username,
                    password = pass_digest,
                    email = email);
                user.put();
                uid = user.key().id();
                # Set uid|hash - cookie.
                uid_cookie = make_secure_val(str(uid))
                self.response.headers.add_header('Set-Cookie',
                    'uid=%s;Path=/' %uid_cookie)
                #self.redirect('/blog/welcome')
                self.redirect('/blog/')

class Welcome(BlogHandler):
    def get(self):
        #Get user name from cookie
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        user =""
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;

        if user:
            self.render('welcome.html', u = user)
        else:
            self.redirect('/blog/signup')

# Debug only
# Clean all database and start with sign up            
class FlushDb(BlogHandler):
    def get(self):
        # Delete all Post
        posts = Post.all()
        for p in posts:
            p.delete()

        # Delete all users
        users = Users.all()
        for u in users:
            u.delete()
            
        # Delete all comments
        comments = Comments.all()
        for c in comments:
            c.delete()
        
        # Delete all likes
        likes = Likes.all()
        for l in likes:
            l.delete()
        self.redirect('/blog/signup');

# Debug only
# Raw dump database
class DumpDb(BlogHandler):
    def get(self):
        # dump all Post
        posts = Post.all()
        self.response.out.write("<table>")
        self.response.out.write("<tr><th>Blog Posts</th></tr>")
        save_id=0
        for p in posts:
            self.response.out.write("<tr><td>" + str(p.key().id()) +"</td></tr>")
            save_id = p.key().id()
        # see if get by id works
        post = Post.get_by_id(save_id)
        if post == None:
            self.response.out.write("<tr><td>Post.get_by_id(" + str(save_id) + ")=" + str(post) +"</td></tr>")        
        else :
            self.response.out.write("<tr><td>Post.get_by_id()=" + str(post.key().id()) +"</td></tr>")
        
        # Dump all comments
        self.response.out.write("<tr><th>Comments</th></tr>")
        comments = Comments.all()
        for c in comments:
            self.response.out.write("<tr><td>" + str(c.post_id) +"</td></tr>")
        # Dump all likes
        self.response.out.write("<tr><th>Likes</th></tr>")
        likes = Likes.all()
        for l in likes:
            self.response.out.write("<tr><td>" + str(l.post_id) + "</td></tr>")

        # try invalid key
        key = db.Key.from_path('Post', 101, parent=blog_key())
        post = db.get(key)
        if post:
            self.response.out.write("<tr><td>id=101 returns post</td></tr>")
        else :
            self.response.out.write("<tr><td>id=101 return None</td></tr>")
            

app = webapp2.WSGIApplication([
       ('/', MainPage),
       ('/blog/logout', Logout),
       ('/blog/login', Login),
       ('/blog/signup', Signup),
       ('/blog/welcome', Welcome),
       ('/blog/?', BlogFront),
       ('/blog/([0-9]+)', PostPage),
       ('/blog/newpost/([0-9]+)', NewPost),
       ('/blog/delpost/([0-9]+)', DelPost),
       ('/blog/likepost/([0-9]+)', LikePost),
       ('/blog/comment/([0-9]+)', CommentPost), # post_id as a param
       ('/blog/flushdb', FlushDb),
       ('/blog/dumpdb', DumpDb),       
       ],
      debug=True)
