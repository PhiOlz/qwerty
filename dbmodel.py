from google.appengine.ext import db



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
