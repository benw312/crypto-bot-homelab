import os
import tweepy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from influxdb import InfluxDBClient
import json

# Twitter API credentials
bearer_token = os.environ["TWITTER_BEARER_TOKEN"]

# InfluxDB credentials
host = os.getenv("INFLUXDB_HOST", "localhost")
port = int(os.getenv("INFLUXDB_PORT", "8086"))
user = os.environ["INFLUXDB_USERNAME"]
password = os.environ["INFLUXDB_PASSWORD"]
dbname = os.getenv("INFLUXDB_DB", "crypto")

# Set up sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Set up InfluxDB client
influx_client = InfluxDBClient(host, port, user, password, dbname)

class SentimentStreamer(tweepy.StreamingClient):
    def __init__(self, *args, coin_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.coin_ids = coin_ids

    def on_tweet(self, tweet):
        for coin_id in self.coin_ids:
            if coin_id in tweet.data['text']:
                process_tweet(tweet.data, coin_id)

def process_tweet(tweet_data, coin_id):
    # Filter out retweets
    if 'RT @' not in tweet_data['text']:
        # Get sentiment scores
        scores = analyzer.polarity_scores(tweet_data['text'])
        json_body = [
            {
                "measurement": "crypto_sentiment",
                "tags": {
                    "user": tweet_data['author']['username'],
                    "coin": coin_id
                },
                "fields": {
                    "positive": scores['pos'],
                    "neutral": scores['neu'],
                    "negative": scores['neg'],
                    "compound": scores['compound']
                }
            }
        ]
        # Write points to InfluxDB
        influx_client.write_points(json_body)

def start_sentiment_trackers(coins):
    streamer = SentimentStreamer(bearer_token)
    
    # Get current rules
    current_rules = streamer.get_rules()
    if 'data' in current_rules:
        ids = [rule['id'] for rule in current_rules['data']]

        if not ids:
            print("No rules to delete")
        else:
            streamer.delete_rules(ids)
    
    # Define the rules for filtering the tweets
    rules = [
        {
            'value': coin + " -is:retweet -is:reply",
            'tag': coin
        }
        for coin in coins
    ]
    
    streamer.add_rules(rules)
    
    # Start streaming
    streamer.filter()


if __name__ == "__main__":
    # Test sentiment tracker with Bitcoin
    start_sentiment_trackers(["bitcoin"])