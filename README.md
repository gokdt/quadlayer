# Quad Layer

Quad Layer is a Slack bot that integrates GPT-4 API into Slack. It is written from scratch in Python using [Bolt for Python](https://slack.dev/bolt-python/concepts).

## Features

- Recognize voice messages using OpenAI's Whisper API
- Store messages in Redis for specified amount of time
- Generate responses using GPT-4 API (both OpenAI and Azure OpenAI is supported)
- Use in channels, DMs, and threads
  - Quad Layer replies in threads by default, meaning each thread can have its own conversation
- Use slash commands to interact with Quad Layer and change settings

## Installation

We include a Dockerfile for easy deployment. You can also run the bot locally. You will need to create a Slack app and a Redis instance.

### Bot Token Scopes

You need to add the following scopes to your bot token:

- `app_mentions:read` - to listen for mentions
- `channels:history` - to listen for messages within channels
- `im:history` - to listen for messages within DMs
- `groups:history` - to listen for messages within private channels
- `mpim:history` - to listen for messages within group DMs
- `chat:write` - to send messages
- `commands` - to listen for slash commands

### Environment Variables

You will need to set the following environment variables. Please refer to the [.env.example](.env.example) file for an example.

- `SLACK_BOT_TOKEN` - your bot token (stated as `Bot User OAuth Token` in your app and starts with `xoxb-`)
- `SLACK_APP_TOKEN` - your app token (stated as `App-Level Tokens` in your app and starts with `xapp-`)
- `REDIS_URL` - your Redis URL (e.g. `redis://localhost:6379`)

## Usage

Although Quad Layer is designed for deployment within a single Slack workspace, it should be easy to modify it to work with multiple workspaces. (PRs are welcome!)

### Deployment

We recommend using [Render](https://render.com/) to deploy Quad Layer due to its simplicity and free tier. You can also deploy it to Heroku or any other platform that supports Docker. You can also run it locally, with or without Docker.

You need to setup a Redis instance to store messages. You can use [Render](https://render.com/) to deploy a Redis instance as well. You can also use a free tier of [Redis Labs](https://redislabs.com/). You can also run Redis locally.

In addition to these, you will need to have access to GPT-4 API, either through OpenAI or Azure OpenAI.
