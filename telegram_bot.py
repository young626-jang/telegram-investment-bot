# .github/workflows/telegram-bot.yml (기존 파일 수정)
name: Sofia Investment Bot

on:
  schedule:
    # 매일 한국시간 오전 8시 30분 (UTC 23:30) - 모닝 브리핑
    - cron: '30 23 * * *'
    # 기존 뉴스 체크 스케줄 유지 (매 30분마다)
    - cron: '0,30 0-8 * * 1-5'  # 한국시간 9-17시 (장중)
    - cron: '0,30 20-23 * * 0-4'  # 한국시간 05-08시 (미국 장중)
  
  # 수동 실행 가능
  workflow_dispatch:

jobs:
  run-telegram-bot:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests
        
    - name: Load sent news history
      uses: actions/cache@v3
      with:
        path: sent_news.json
        key: sent-news-${{ github.sha }}
        restore-keys: |
          sent-news-
          
    - name: Run Sofia Bot
      env:
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        CHAT_ID: ${{ secrets.CHAT_ID }}
        ALPHA_VANTAGE_KEY: ${{ secrets.ALPHA_VANTAGE_KEY }}
        POLYGON_KEY: ${{ secrets.POLYGON_KEY }}
        BENZINGA_KEY: ${{ secrets.BENZINGA_KEY }}
      run: python telegram_bot.py
      
    - name: Save sent news history
      uses: actions/cache/save@v3
      with:
        path: sent_news.json
        key: sent-news-${{ github.sha }}
        
    - name: Notify on failure (기존 유지)
      if: failure()
      run: |
        curl -X POST "https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage" \
        -d "chat_id=${{ secrets.CHAT_ID }}" \
        -d "text=🚨 소피아 봇 오류 발생! GitHub Actions 실행 실패. 로그를 확인해주세요."
