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

#from dbmodel import Users
from dbmodel import Comments
from dbmodel import Likes

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)
def getcomments(post_id):
    coms = db.GqlQuery("select * from Comments where post_id=" + post_id +
                       " order by created desc")
    return coms;

jinja_env.filters['getcomments'] = getcomments

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

# Module contains all storage tables
class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    count_comment = db.IntegerProperty(default=0)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
#        return render_str("post.html", p = self, u=user)
        t = jinja_env.get_template("post.html")
        return t.render(p = self)        

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
      self.redirect('/blog')

##### blog stuff

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

    
# /blog/?        
class BlogFront(webapp2.RequestHandler):
    def get(self):
        posts = db.GqlQuery("select * from Post order by created desc limit 10")
        #Enhance to take comments
        t = jinja_env.get_template('front.html')
        self.response.out.write(t.render(posts=posts))
            

#Posting a page leads to a perma link.
class PostPage(webapp2.RequestHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return
        #self.render("permalink.html", post = post, u=user)
        t = jinja_env.get_template('permalink.html')
        self.response.out.write(t.render(p=post))
# type of self is webapp.RequestHandler
# refresh the same page.

class NewPost(webapp2.RequestHandler):
    def get(self, post_id):
        post=None
        # Can't handle zero - throws excption
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
        #self.render('newpost.html', u = user)
        t = jinja_env.get_template('newpost.html')
        self.response.out.write(t.render(p=post)) 

    def post(self, p_id):
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
            post.delete()
            
            
# Check if user is logged in, if not redirect to login.
# Delete post, comments and likes
class DelPost(webapp2.RequestHandler):
    def get(self, post_id):
        post=None
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            
        if post:
                deletePost(post.key().id())
        
        self.redirect('/blog')        
# Check if user is logged in, if not redirect to login.
# Delete a single comment
class DelComment(webapp2.RequestHandler):
    def get(self, comment_id):
        comment=None
        post_id = None
        if int(comment_id) > 0 :
            #comment = Comments.get_by_id(int(comment_id))
            #coms = db.GqlQuery(
            #        "SELECT * FROM Comments WHERE id=" + str(comment_id))
            #for c in coms:
            #    comment = c            
            key = db.Key.from_path('Comments', int(comment_id), parent=blog_key())
            comment = db.get(key)
            
        if comment:
            post_id=comment.post_id
            comment.delete()
            pkey = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(pkey)
            post.count_comment -= 1
            post.put()
                
        if post_id :
            self.redirect('/blog/comment/' + str(post_id))
        else :
            self.redirect('/blog')
        
# Check if user is logged in, if not redirect to login.
class CommentPost(webapp2.RequestHandler):
    def get(self, post_id):
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)                        
            if post:
                coms = getcomments(post_id)
                t = jinja_env.get_template('comment.html')
                #self.render('comment.html', post=post, coms=coms, u = user)
                self.response.out.write(t.render(post=post, coms=coms))

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        comment = self.request.get('comment')
        com = Comments(parent = blog_key(), 
                         post_id = int(post_id), 
                         comment = comment)
        com.put()
        if post: 
          post.count_comment += 1;
          post.put()
                # Find and update post id as well
        self.redirect('/blog/%s' % str(post.key().id()))
        coms = getcomments(post_id)
        t = jinja_env.get_template('comment.html')
        self.response.out.write(t.render(posts=posts, coms=coms))
class EditComment(webapp2.RequestHandler):
    def get(self, comment_id):
            
        if int(comment_id) > 0:
            ckey = db.Key.from_path('Comments', int(comment_id), parent=blog_key())
            com = db.get(ckey)        
            if com:
                pkey = db.Key.from_path('Post', int(com.post_id), parent=blog_key())
                post = db.get(pkey)
                t = jinja_env.get_template('comment-edit.html')
                #self.render('comment.html', post=post, coms=coms, u = user)
                self.response.out.write(t.render(post=post, com=com))       

    def post(self, com_id):
        ckey = db.Key.from_path('Comments', int(com_id), parent=blog_key())
        com = db.get(ckey)
        updated_comment = self.request.get('comment')
        com.comment = updated_comment
        com.put()
        self.redirect('/blog/comment/%s' % str(com.post_id))  
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
        self.response.out.write("<tr><th>PostID</th><th>Subject</th></tr>")
        for p in posts:
            self.response.out.write("<tr><td>" + str(p.key().id()) + "</td>")
            self.response.out.write("<td>p.subject</td></tr>")
            save_id = p.key().id()
        # see if get by id works
        post = Post.get_by_id(save_id)
        if post == None:
            self.response.out.write("<tr><td>Post.get_by_id(" + str(save_id) + ")=" + str(post) +"</td></tr>")        
        else :
            self.response.out.write("<tr><td>Post.get_by_id()=" + str(post.key().id()) +"</td></tr>")
        
        # Dump all comments
        self.response.out.write("<tr><th>PostID</th><th>CommentID</th></tr>")
        comments = Comments.all()
        comment_id = 0
        for c in comments:
            self.response.out.write("<tr><td>" + str(c.post_id) +"</td>")
            self.response.out.write("<td>" + str(c.key().id()) + "</td></tr>")
            comment_id = c.key().id()
        
        # Dump all likes
        self.response.out.write("<tr><th>PostID</th><th>LikeID</th></tr>")        
        likes = Likes.all()
        for l in likes:
            self.response.out.write("<tr><td>" + str(l.post_id) + "</td>")
            self.response.out.write("<td>" + str(l.key().id()) + "</td></tr>")

        # test Comments get_by_id
        if comment_id > 0:
            c = Comments.get_by_id(comment_id)
            if c:
                self.response.out.write("<tr><td> Comments.get_by_id("+ str(comment_id) + ")")
                selt.response.out.write("=" + c.key().id() + "</td></tr>")
            else : 
                self.response.out.write("<tr><td>Comments.get_by_id(id) return None</td></tr>")
            coms = db.GqlQuery(
                "SELECT * FROM Comments WHERE id=" + str(comment_id))
            c = coms.fetch(1)
            if c:
                self.response.out.write("<tr><td>Select on Comments return a record.</td></tr>")
        else:
            self.response.out.write("<tr><td>Zero Comments in db</td></tr>")
            
        
        # try invalid key
        key = db.Key.from_path('Post', 101, parent=blog_key())
        post = db.get(key)
        if post:
            self.response.out.write("<tr><td>id=101 returns post</td></tr>")
        else :
            self.response.out.write("<tr><td>id=101 return None</td></tr>")
            

app = webapp2.WSGIApplication([
       ('/', MainPage),
       ('/blog/?', BlogFront),
       ('/blog/([0-9]+)', PostPage),
       ('/blog/newpost/([0-9]+)', NewPost),
       ('/blog/delpost/([0-9]+)', DelPost),
       ('/blog/delcom/([0-9]+)', DelComment),
       ('/blog/editcom/([0-9]+)', EditComment),
       ('/blog/comment/([0-9]+)', CommentPost),
       ('/blog/flushdb', FlushDb),
       ('/blog/dumpdb', DumpDb),       
       ],
      debug=True)
