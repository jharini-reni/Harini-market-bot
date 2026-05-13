# India Market Bot - Deployment Guide

## Step 1: Get Free NewsAPI Key
1. Go to https://newsapi.org
2. Click "Get API Key" → Register free
3. Copy your API key

## Step 2: Upload to GitHub
1. Go to https://github.com → Sign up free
2. Create new repository → name it "market-bot"
3. Upload these 3 files: bot.py, requirements.txt, railway.toml

## Step 3: Deploy on Railway (Free)
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your "market-bot" repo
5. Go to "Variables" tab → Add:
   - NEWS_API_KEY = (your newsapi key)
6. Click Deploy ✅

## Done!
Bot runs 24/7 for free. Check your Telegram!

## Schedule:
- 7:00 AM → Morning briefing
- 9:15 AM to 3:30 PM → Every 5 mins live update
- Every 30 mins → Stock specific news
