from peewee import *
from config import app_config as cfg
from collections import defaultdict
import numpy as np
from pandas import DataFrame
from dateutil import parser
from itertools import product

db = SqliteDatabase(cfg.database["name"])


def create_database():
    db.connect()
    db.drop_tables([User, Tweet], True)
    db.create_tables([User, Tweet], True)

class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    screen_name = CharField()
    is_bot = BooleanField()
    followers = IntegerField()
    following = IntegerField()

    def ratio_followers_following(self):
        if self.following == 0:
            return 0

        return self.followers / float(self.following)

    @classmethod
    def ratio_followers_following_per_users(self, is_bot=False):
        users = User.select().where(User.is_bot == is_bot)

        return [user.ratio_followers_following() for user in users]


class Tweet(BaseModel):
    user = ForeignKeyField(User, related_name='tweets')
    text = CharField()
    date = CharField()
    mentions = CharField()

    @classmethod
    def avg_mentions_per_user(cls, is_bot=False):
        tweets = Tweet.select(Tweet).join(User).where(User.is_bot == is_bot)

        mentions_per_user = defaultdict(lambda: [])
        for tweet in tweets:
            count = 0
            if len(tweet.mentions) > 0:
                count = len(tweet.mentions.split(","))
            mentions_per_user[tweet.user_id].append(count)

        avg_per_user = {user: np.mean(mentions) for (user, mentions) in mentions_per_user.iteritems()}

        return avg_per_user

    @classmethod
    def vocabulary_size(cls, is_bot=False, min_tweets=200):
        selected_users = Tweet.select(Tweet.user) \
            .group_by(Tweet.user) \
            .having(fn.Count() >= min_tweets)

        tweets = (Tweet.select(Tweet).join(User)
            .where(
            (User.is_bot == is_bot) &
            (User.id << selected_users)
        ))

        words_per_user = defaultdict(lambda: set())
        for tweet in tweets:
            for word in tweet.text.split(" "):
                words_per_user[tweet.user_id].add(word)

        return {name: len(words) for (name, words) in words_per_user.iteritems()}

    @classmethod
    def tweet_density(cls, is_bot=False, min_tweets=200):
        selected_users = Tweet.select(Tweet.user) \
            .group_by(Tweet.user) \
            .having(fn.Count() >= min_tweets)

        tweets = (Tweet.select(Tweet).join(User)
            .where(
            (User.is_bot == is_bot) &
            (User.id << selected_users)
        ))

        tweets_df = DataFrame(columns=["user_id", "date"], index=range(len(tweets)))
        for i, tweet in enumerate(tweets):
            date = parser.parse(tweet.date)

            tweets_df["date"][i] = str(date.year)+str(date.month)+str(date.day)
            tweets_df["user_id"][i] = tweet.user_id

        grouped = tweets_df.groupby(['user_id', 'date']).size().reset_index()

        count_list_by_user = grouped[0].apply(lambda x: x if (x < 6) else 6).tolist()
        mean_count = np.mean(count_list_by_user)
        median_count = np.median(count_list_by_user)

        return count_list_by_user, mean_count, median_count

    @classmethod
    def tweet_weekday(cls, is_bot=False, min_tweets=200):
        selected_users = Tweet.select(Tweet.user) \
            .group_by(Tweet.user) \
            .having(fn.Count() >= min_tweets)

        tweets = (Tweet.select(Tweet).join(User)
            .where(
            (User.is_bot == is_bot) &
            (User.id << selected_users)
        ))

        tweets_df = DataFrame(columns=["user_id", "weekday"], index=range(len(tweets)))
        for i, tweet in enumerate(tweets):

            tweets_df["weekday"][i] = str(tweet.date.split(' ')[0])
            tweets_df["user_id"][i] = tweet.user_id

        grouped = tweets_df.groupby(['user_id', 'weekday']).size().reset_index()

        list_days = set(grouped["weekday"])
        stats_weekdays = DataFrame(columns=["weekday", "mean","std"], index=range(len(list_days)))
        stats_weekdays["weekday"] = list_days
        stats_weekdays["mean"] = [np.mean(grouped[0][grouped["weekday"] == day]) for day in list_days]
        stats_weekdays["std"] = [np.std(grouped[0][grouped["weekday"] == day]) for day in list_days]

        prop_weekdays = DataFrame(columns=["weekday", "prop","std"], index=range(len(list_days)))
        prop_weekdays["weekday"] = list_days
        prop_weekdays['prop'] = stats_weekdays['mean'] / sum(stats_weekdays['mean'])
        prop_weekdays['std'] = stats_weekdays['std'] / sum(stats_weekdays['mean'])
        sorted_weekdays = prop_weekdays.reindex([4,3,0,2,5,6,1])
        return sorted_weekdays




