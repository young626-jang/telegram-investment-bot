# telegram_bot.py (기존 봇 수정 - 8시 30분 브리핑)
import requests
import os
import json
from datetime import datetime, timezone, timedelta
import time

# 환경변수에서 설정값 가져오기 (기존 동일)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
POLYGON_KEY = os.getenv('POLYGON_KEY')
BENZINGA_KEY = os.getenv('BENZINGA_KEY')

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# 모니터링할 종목들 (기존 동일)
PORTFOLIO_STOCKS = {
    "IBM": {"shares": 16, "avg_price": 261.68},
    "NOW": {"shares": 3, "avg_price": 1017.32},  # ServiceNow
    "SOUN": {"shares": 30, "avg_price": 11.05}   # SoundHound AI
}

class TelegramNewsBot:  # 기존 클래스명 유지
    def __init__(self):
        self.sent_news_file = "sent_news.json"
        self.sent_news = self.load_sent_news()
        
    def load_sent_news(self):
        """이전에 보낸 뉴스 목록 로드 (기존 동일)"""
        try:
            if os.path.exists(self.sent_news_file):
                with open(self.sent_news_file, 'r') as f:
                    return set(json.load(f))
        except:
            pass
        return set()
    
    def save_sent_news(self):
        """보낸 뉴스 목록 저장 (기존 동일)"""
        try:
            with open(self.sent_news_file, 'w') as f:
                json.dump(list(self.sent_news), f)
        except Exception as e:
            print(f"뉴스 저장 오류: {e}")
        
    def send_telegram_message(self, message):
        """텔레그램 메시지 전송 (기존 동일)"""
        if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
            print("텔레그램 설정 오류: 토큰 또는 채팅 ID가 없습니다.")
            return None
            
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            return response.json()
        except Exception as e:
            print(f"텔레그램 전송 오류: {e}")
            return None

    def get_stock_price(self, symbol):
        """실시간 주가 조회 (Polygon 우선, Alpha Vantage 백업)"""
        # 먼저 Polygon 시도
        if POLYGON_KEY:
            try:
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
                params = {"apikey": POLYGON_KEY}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get("results"):
                    price = data["results"][0]["c"]
                    print(f"✅ {symbol} Polygon 주가: ${price}")
                    return price
            except Exception as e:
                print(f"Polygon 오류 ({symbol}): {e}")
        
        # Polygon 실패 시 Alpha Vantage 백업
        if ALPHA_VANTAGE_KEY:
            try:
                url = "https://www.alphavantage.co/query"
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": ALPHA_VANTAGE_KEY
                }
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                quote = data.get("Global Quote", {})
                if quote:
                    price = float(quote.get("05. price", 0))
                    if price > 0:
                        print(f"✅ {symbol} Alpha Vantage 주가: ${price}")
                        return price
            except Exception as e:
                print(f"Alpha Vantage 주가 오류 ({symbol}): {e}")
        
        print(f"❌ {symbol} 주가 조회 실패")
        return None

    def get_alpha_vantage_news(self, symbol):
        """Alpha Vantage 뉴스 조회 (기존 함수명 유지)"""
        if not ALPHA_VANTAGE_KEY:
            print("Alpha Vantage API 키가 없습니다.")
            return None
            
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": ALPHA_VANTAGE_KEY,
            "limit": 5
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            return response.json()
        except Exception as e:
            print(f"뉴스 조회 오류 ({symbol}): {e}")
            return None

    def analyze_news_sentiment(self, title, summary):
        """뉴스 감정 분석 (기존 함수 개선)"""
        text = (title + " " + summary).lower()
        
        # 중요 키워드
        important_keywords = ["earnings", "revenue", "quarter", "guidance", "beat", "miss", 
                            "acquisition", "partnership", "deal", "upgrade", "downgrade"]
        
        positive_keywords = ["strong", "growth", "beat", "exceed", "positive", "upgrade", "bullish"]
        negative_keywords = ["weak", "decline", "miss", "negative", "downgrade", "bearish", "concern"]
        
        important_score = sum(1 for word in important_keywords if word in text)
        positive_score = sum(1 for word in positive_keywords if word in text)
        negative_score = sum(1 for word in negative_keywords if word in text)
        
        # 중요도 판정
        if important_score >= 2:
            importance = "🚨 매우 중요"
        elif important_score >= 1:
            importance = "⚠️ 중요"
        else:
            importance = "ℹ️ 일반"
        
        # 감정 분석
        if positive_score > negative_score:
            sentiment = "🟢 긍정적"
        elif negative_score > positive_score:
            sentiment = "🔴 부정적"
        else:
            sentiment = "🟡 중립적"
            
        return sentiment, str(important_score), important_score

    def format_news_alert(self, symbol, news_item, current_price=None):
        """뉴스 알림 메시지 포맷 (기존 함수 개선)"""
        title = news_item.get("title", "제목 없음")
        summary = news_item.get("summary", "")
        time_published = news_item.get("time_published", "")
        
        # 감정 분석 (기존 함수 사용)
        sentiment, score, important_score = self.analyze_news_sentiment(title, summary)
        
        # 포트폴리오 정보
        portfolio_info = PORTFOLIO_STOCKS.get(symbol, {})
        shares = portfolio_info.get("shares", 0)
        avg_price = portfolio_info.get("avg_price", 0)
        
        # 손익 계산
        if current_price and avg_price:
            profit_loss = (current_price - avg_price) * shares
            profit_loss_pct = ((current_price - avg_price) / avg_price) * 100
            profit_emoji = "📈" if profit_loss > 0 else "📉"
        else:
            profit_loss = 0
            profit_loss_pct = 0
            profit_emoji = "➖"
        
        # 중요도 표시
        if important_score >= 2:
            importance = "🚨 매우 중요"
        elif important_score >= 1:
            importance = "⚠️ 중요"
        else:
            importance = "ℹ️ 일반"
        
        message = f"""🚨 **{symbol} 중요 뉴스**

{importance} | {sentiment}

📰 **{title}**

💰 **포트폴리오 현황**:
- 보유: {shares}주
- 평단가: ${avg_price:.2f}
- 현재가: ${current_price:.2f} {profit_emoji}
- 손익: ${profit_loss:.2f} ({profit_loss_pct:+.2f}%)

⏰ {time_published}

💡 상세분석이 필요하시면 소피아에게 "{symbol} 뉴스 분석해줘"라고 요청하세요!"""

        return message

    def check_news(self):
        """뉴스 체크 및 알림 (기존 함수 개선)"""
        now_kst = datetime.now(KST)
        print(f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}] 뉴스 체크 시작...")
        
        for symbol in PORTFOLIO_STOCKS.keys():
            try:
                # 현재 주가 조회
                current_price = self.get_stock_price(symbol)
                if current_price:
                    print(f"[{symbol}] 현재가: ${current_price}")
                
                # 뉴스 조회
                news_data = self.get_alpha_vantage_news(symbol)
                
                if news_data and "feed" in news_data:
                    for news_item in news_data["feed"][:3]:  # 최신 3개
                        news_url = news_item.get("url", "")
                        
                        # 이미 보낸 뉴스는 스킵
                        if news_url in self.sent_news:
                            continue
                        
                        # 중요한 키워드가 포함된 뉴스만 알림
                        title = news_item.get("title", "").lower()
                        important_keywords = ["earnings", "revenue", "quarter", "guidance", 
                                            "acquisition", "partnership", "deal", "upgrade", "downgrade"]
                        
                        if any(keyword in title for keyword in important_keywords):
                            message = self.format_news_alert(symbol, news_item, current_price)
                            
                            result = self.send_telegram_message(message)
                            if result and result.get("ok"):
                                self.sent_news.add(news_url)
                                self.save_sent_news()
                                print(f"[{symbol}] 뉴스 알림 전송: {title[:50]}...")
                            
                            time.sleep(2)  # 메시지 간 간격
                
                time.sleep(3)  # API 간 간격
                
            except Exception as e:
                print(f"[{symbol}] 오류: {e}")

    def send_morning_briefing(self):
        """8시 30분 모닝 브리핑 (기존 함수 수정)"""
        now_kst = datetime.now(KST)
        
        briefing = f"""🌅 **소피아 8:30 모닝 브리핑**

📅 {now_kst.strftime('%Y년 %m월 %d일')}
⏰ 08:30 업데이트

"""
        
        total_profit = 0
        all_prices_available = True
        
        for symbol, info in PORTFOLIO_STOCKS.items():
            current_price = self.get_stock_price(symbol)
            
            if current_price:
                profit_loss = (current_price - info["avg_price"]) * info["shares"]
                profit_loss_pct = ((current_price - info["avg_price"]) / info["avg_price"]) * 100
                total_profit += profit_loss
                
                emoji = "📈" if profit_loss > 0 else "📉" if profit_loss < 0 else "➖"
                
                # 종목별 이름 표시
                if symbol == "IBM":
                    name = "IBM"
                elif symbol == "NOW":
                    name = "ServiceNow"
                elif symbol == "SOUN":
                    name = "SoundHound AI"
                else:
                    name = symbol
                    
                briefing += f"📊 **{name} ({symbol})**: ${current_price:.2f} ({profit_loss_pct:+.2f}%) {emoji}\n"
                briefing += f"   손익: ${profit_loss:+.2f}\n\n"
                
                time.sleep(2)  # API 레이트 리밋 방지
            else:
                all_prices_available = False
                briefing += f"📊 **{symbol}**: 가격 조회 실패 ❌\n\n"
        
        if all_prices_available:
            briefing += f"💰 **총 손익**: ${total_profit:+.2f}\n\n"
        
        # 8월 7일 SoundHound 실적 특별 알림
        if now_kst.month == 8 and now_kst.day == 7:
            briefing += f"""🚨 **오늘 SoundHound AI (SOUN) Q2 실적 발표!**
- 예상 EPS: -$0.06 (vs 전년 -$0.11)
- 예상 매출: $33.03M (+145% YoY)
- 발표 시간: 미국 장 마감 후

"""
        elif now_kst.month == 8 and now_kst.day == 6:
            briefing += f"""⚠️ **내일 SoundHound AI 실적 발표 예정!**

"""
        
        briefing += f"""💡 상세 분석이 필요하시면 '소피아, 모닝 브리핑 해줘'라고 요청해주세요!

🤖 소피아가 8:30에 정확히 브리핑해드렸습니다! 📈"""
        
        result = self.send_telegram_message(briefing)
        if result:
            print(f"✅ 8:30 모닝 브리핑 전송 완료")
        else:
            print(f"❌ 모닝 브리핑 전송 실패")

def main():
    """메인 실행 함수 (기존 구조 유지하되 8:30 브리핑으로 수정)"""
    bot = TelegramNewsBot()  # 기존 클래스명 유지
    
    # GitHub Actions 환경에서는 한 번만 실행
    try:
        # 한국시간으로 현재 시간 확인
        now_kst = datetime.now(KST)
        current_hour = now_kst.hour
        current_minute = now_kst.minute
        
        print(f"⏰ 현재 시간: {now_kst.strftime('%H:%M')} KST")
        
        # 8시 30분 브리핑 시간 체크 (8:25 ~ 8:35 사이)
        if current_hour == 8 and 25 <= current_minute <= 35:
            print("🌅 8:30 모닝 브리핑 시간입니다!")
            bot.send_morning_briefing()
        else:
            print("📰 뉴스 체크 실행...")
            bot.check_news()
            
    except Exception as e:
        print(f"실행 오류: {e}")
        # 오류 발생 시 알림
        error_msg = f"🚨 소피아 봇 시스템 오류 발생: {str(e)}"
        bot.send_telegram_message(error_msg)

if __name__ == "__main__":
    main()
