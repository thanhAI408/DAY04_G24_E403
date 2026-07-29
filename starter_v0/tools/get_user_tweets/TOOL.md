---
name: get_user_tweets
track: core
kind: live_api
provider: RapidAPI Twitter API45
requires_env: [RAPIDAPI_KEY, RAPIDAPI_TWITTER_HOST]
inputs: [screenname, limit]
outputs: [items]
side_effect: false
---
# get_user_tweets

Fetches recent posts from a single account. `screenname` is an account handle
without `@`.

