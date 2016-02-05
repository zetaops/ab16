# -*-  coding: utf-8 -*-
"""
"""
from pyoko import Model, LinkProxy, ListNode
from pyoko import field
from pyoko.exceptions import ObjectDoesNotExist
from werkzeug.exceptions import abort
from werkzeug.security import check_password_hash, generate_password_hash


class Unauthorized(Exception):
    pass


class User(Model):
    username = field.String("Username", index=True)
    email = field.String("Email", index=True)
    password = field.String("Password", index=True)

    class MessageCache(ListNode):
        author_key = field.String()
        username = field.String()
        mail = field.String()
        timestamp = field.TimeStamp()
        text = field.String("Message Text")

    def add_to_stream(self, msg):
        self.MessageCache(author_key=msg.author.key,
                          username=msg.author.username,
                          mail=msg.author.email,
                          timestamp=msg.timestamp,
                          text=msg.text)
        self.save()

    def pre_save(self):
        # this is pre-save hook
        # encrypt password if not already encrypted
        if not self.password.startswith('pbkdf2'):
            self.password = generate_password_hash(self.password)

    def check_password(self, clean_password):
        # check password hash against given clean password input
        if not check_password_hash(self.password, clean_password):
            raise Unauthorized()

    def is_follows(self, user):
        # is current user follows the given one
        return Follow.objects.filter(whom=user, who=self).count()

    @classmethod
    def get_by_username_or_abort(cls, username):
        # get user by username or raise 404 exception
        try:
            return cls.objects.get(username=username)
        except ObjectDoesNotExist:
            abort(404)


class Follow(Model):
    who = User(reverse_name='following', cache_level=0)
    whom = User(reverse_name='followers', cache_level=0)


class Message(Model):
    author = User()
    text = field.String("Message Text", index=True)

    @property
    def mail(self):
        return self.author.email

    @property
    def username(self):
        return self.author.username

    def post_save(self):
        # this is post-save hook
        # fan-out to all followers of the author
        # TODO: Make this a background (celery) job
        #  for better concurrency
        for follow in Follow.objects.filter(whom=self.author):
            follow.who.add_to_stream(self)
