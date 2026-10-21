import requests
import pandas as pd
import json
import os


def create_twitter_url():
    handle = "bitcoin"
    max_results = 100
    mrf = "max_results={}".format(max_results)
    q = "query=from:{}".format(handle)
    url = "https://api.twitter.com/2/tweets/search/recent?{}&{}".format(
        mrf, q
    )
    return url


def create_bearer_token():
    return os.environ["TWITTER_BEARER_TOKEN"]


def twitter_auth_and_connect(bearer_token, url):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    response = requests.request("GET", url, headers=headers)
    return response.json()


def main():
    url = create_twitter_url()
    bearer_token = create_bearer_token()
    res_json = twitter_auth_and_connect(bearer_token, url)
    print(res_json)

if __name__ == "__main__":
    main()