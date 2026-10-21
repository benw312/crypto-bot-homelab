#reddit.py
import os
import praw
from praw.models import MoreComments
from textblob import TextBlob
import time

# Reddit API credentials are read from the environment (see .env.example)
client_id = os.environ["REDDIT_CLIENT_ID"]
client_secret = os.environ["REDDIT_CLIENT_SECRET"]
user_agent = os.getenv("REDDIT_USER_AGENT", "python:Sentiment Tracker:v1.0")

# Create a Reddit instance
reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)

# Define the subreddits you want to monitor
subreddits_to_monitor = ["cryptomarkets", "bitcoin", "ethereum", "altcoin"]

# Define search keywords
keywords = ["bitcoin", "ethereum", "ripple"]

# Define a global variable to keep track of seen posts
seen_posts_ids = []

def get_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

def analyze_posts(limit):
    global seen_posts_ids

    post_counts = {keyword: 0 for keyword in keywords}
    post_sentiments = {keyword: [] for keyword in keywords}

    for subreddit_name in subreddits_to_monitor:
        subreddit = reddit.subreddit(subreddit_name)

        for submission in subreddit.new(limit=limit):
            if submission.id not in seen_posts_ids:
                seen_posts_ids.append(submission.id)
                for keyword in keywords:
                    if keyword in submission.title.lower() or keyword in submission.selftext.lower():
                        post_counts[keyword] += 1

                        post_sentiment = get_sentiment(submission.selftext)
                        post_sentiments[keyword].append(post_sentiment)

            time.sleep(2)  # To ensure we don't exceed Reddit's rate limit of 2 requests per second

    data_to_return = {}
    for keyword in keywords:
        if post_sentiments[keyword]:
            avg_sentiment = sum(post_sentiments[keyword]) / len(post_sentiments[keyword])
        else:
            avg_sentiment = 0

        data_to_return[keyword] = {
            'post_count': post_counts[keyword],
            'average_sentiment': avg_sentiment,
        }

    return data_to_return

if __name__ == "__main__":
    while True:
        data = analyze_posts(limit=30)  # Adjusting the limit to stay within Reddit's rate limit of 30 requests per minute
        print(data)
        time.sleep(60)  # Sleep for a minute before checking again
