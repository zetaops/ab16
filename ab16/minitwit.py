# -*- coding: utf-8 -*-
"""
    MiniTwit
    ~~~~~~~~

    A microblogging application written with Flask and Pyoko.

    :copyright: (c) 2015 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.

    Pyoko related modifications
    :copyright: (c) 2016 ZetaOps Inc.
"""

from hashlib import md5
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash
from pyoko.exceptions import ObjectDoesNotExist
from ab16.models import User, Message, Follow, Unauthorized
from pyoko.conf import settings

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = settings.BASE_DIR

PER_PAGE = 30




def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = User.objects.filter(username=username)
    return rv[0].key if rv else None


def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.fromtimestamp(int(str(timestamp)[:10])).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.objects.get(session['user_id'])


@app.route('/')
def timeline():
    """Shows a users timeline or if no user is logged in it will
    redirect to the public timeline.  This timeline shows the user's
    messages as well as all the messages of followed users.
    """
    if not g.user:
        return redirect(url_for('public_timeline'))
    return render_template('timeline.html', messages=g.user.MessageCache[:20])


@app.route('/public')
def public_timeline():
    """Displays the latest messages of all users."""
    return render_template('timeline.html',
                           messages=Message.objects.filter()[:PER_PAGE])


@app.route('/<username>')
def user_timeline(username):
    """Display's a users tweets."""
    profile_user = User.get_by_username_or_abort(username)
    followed = g.user.is_follows(profile_user) if g.user else False
    return render_template('timeline.html',
                           messages=Message.objects.filter(author=profile_user)[:PER_PAGE],
                           followed=followed,
                           profile_user=profile_user)


@app.route('/<username>/follow')
def follow_user(username):
    """Adds the current user as follower of the given user."""
    if not g.user:
        abort(401)
    profile_user = User.get_by_username_or_abort(username)
    Follow(who=g.user, whom=profile_user).save()
    flash('You are now following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/<username>/unfollow')
def unfollow_user(username):
    """Removes the current user as follower of the given user."""
    if not g.user:
        abort(401)
    profile_user = User.get_by_username_or_abort(username)
    Follow.objects.get(who=g.user, whom=profile_user).delete()
    flash('You are no longer following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/add_message', methods=['POST'])
def add_message():
    """Registers a new message for the user."""
    if 'user_id' not in session:
        abort(401)
    if request.form['text']:
        Message(text=request.form['text'], author=g.user).save()
        flash('Your message was recorded')
    return redirect(url_for('timeline'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        try:
            user = User.objects.get(username=request.form['username'])
            user.check_password(request.form['password'])
            session['user_id'] = user.key
            g.user = user
            flash('You were logged in')
            return redirect(url_for('timeline'))
        except ObjectDoesNotExist:
            error = 'Invalid username'
        except Unauthorized:
            error = 'Invalid password'
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif len(User.objects.filter(username=request.form['username'])):
            error = 'The username is already taken'
        else:
            user = User(username=request.form['username'],
                          email=request.form['email'],
                          password=request.form['password'])
            user.save()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('public_timeline'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url

if __name__ == '__main__':
    app.run(debug=True)
