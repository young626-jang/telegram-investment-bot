# telegram_bot.py - 소피아 투자 봇 (8시 30분 브리핑)
import requests
import os
import json
from datetime import datetime, timezone, timedelta
import time

# 환경변수에서 설정값 가져오기
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
POLYGON_KEY = os.getenv('POLYGON_KEY')
BENZINGA_KEY = os.getenv('BENZINGA_KEY')
ACTION_TYPE = os.getenv('ACTION_TYPE', 'auto')

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# 모니터링할 종목들
PORTFOLIO_STOCKS = {
    "IBM": {"shares": 16, "avg_price": 261.68, "name": "IBM"},
    "NOW": {"shares": 3, "avg_price": 1017.32, "name": "ServiceNow"},
    "SOUN": {"shares": 30, "avg_price": 11.05, "name": "SoundHound AI"}
}

class SofiaInvestmentBot:
    def __init__(self):
        self.sent_news_file = "sent_news.json"
        self.sent_news = self.load_sent_news()
        
    def load_sent_news(self):
        """이전에 보낸 뉴스 목록 로드"""
        try:
            if os.path.exists(self.sent_news_file):
                with open(self.sent_news_file, 'r') as f:
                    return set(json.load(f))
        except Exception as e:
            print(f"뉴스 로드 오류: {e}")
        return set()
    
    def save_sent_news(self):
        """보낸 뉴스 목록 저장"""
        try:
            with open(self.sent_news_file, 'w') as f:
                json.dump(list(self.sent_news), f)
        except Exception as e:
            print(f"뉴스 저장 오류: {e}")
        
    def send_telegram_message(self, message, parse_mode="Markdown"):
        """텔레그램 메시지 전송"""
        if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
            print("❌ 텔레그램 설정 오류: 토큰 또는 채팅 ID가 없습니다.")
            return None
            
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            if result.get("ok"):
                print("✅ 텔레그램 메시지 전송 성공")
                return result
            else:
                print(f"❌ 텔레그램 전송 실패: {result}")
                return None
        except Exception as e:
            print(f"❌ 텔레그램 전송 오류: {e}")
            return None

    def get_stock_price_polygon(self, symbol):
        """Polygon API로 실시간 주가 조회"""
        if not POLYGON_KEY:
            print(f"❌ Polygon API 키가 없습니다.")
            return None
            
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        params = {"apikey": POLYGON_KEY}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("results"):
                price = data["results"][0]["c"]
                print(f"✅ {symbol} 주가 조회 성공: ${price}")
                return price
        except Exception as e:
            print(f"❌ {symbol} 주가 조회 오류: {e}")
        return None

    def get_stock_price_alpha_vantage(self, symbol):
        """Alpha Vantage API로 주가 조회 (백업)"""
        if not ALPHA_VANTAGE_KEY:
            return None
            
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            quote = data.get("Global Quote", {})
            if quote:
                price = float(quote.get("05. price", 0))
                if price > 0:
                    print(f"✅ {symbol} Alpha Vantage 주가: ${price}")
                    return price
        except Exception as e:
            print(f"❌ {symbol} Alpha Vantage 오류: {e}")
        return None

    def get_stock_price(self, symbol):
        """주가 조회 (Polygon 우선, Alpha Vantage 백업)"""
        price = self.get_stock_price_polygon(symbol)
        if price is None:
            print(f"🔄 {symbol} Polygon 실패, Alpha Vantage 시도...")
            time.sleep(1)  # API 레이트 리밋 방지
            price = self.get_stock_price_alpha_vantage(symbol)
        return price

    def get_news_alpha_vantage(self, symbol):
        """Alpha Vantage 뉴스 조회"""
        if not ALPHA_VANTAGE_KEY:
            print("❌ Alpha Vantage API 키가 없습니다.")
            return None
            
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": ALPHA_VANTAGE_KEY,
            "limit": 10,
            "time_from": "20250801T0000"  # 8월 1일 이후 뉴스만
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if "feed" in data:
                print(f"✅ {symbol} 뉴스 {len(data['feed'])}건 조회")
                return data
        except Exception as e:
            print(f"❌ {symbol} 뉴스 조회 오류: {e}")
        return None

    def analyze_news_importance(self, title, summary):
        """뉴스 중요도 분석"""
        text = (title + " " + summary).lower()
        
        # 매우 중요한 키워드 (즉시 알림)
        critical_keywords = [
            "earnings", "revenue", "quarter", "guidance", "beat", "miss",
            "acquisition", "merger", "partnership", "deal", "contract",
            "upgrade", "downgrade", "target", "rating"
        ]
        
        # 긍정/부정 키워드
        positive_keywords = ["strong", "growth", "exceed", "positive", "bullish", "buy", "outperform"]
        negative_keywords = ["weak", "decline", "concern", "bearish", "sell", "underperform"]
        
        critical_score = sum(1 for word in critical_keywords if word in text)
        positive_score = sum(1 for word in positive_keywords if word in text)
        negative_score = sum(1 for word in negative_keywords if word in text)
        
        # 중요도 판정
        if critical_score >= 2:
            importance = "🚨 매우 중요"
        elif critical_score >= 1:
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
            
        return importance, sentiment, critical_score

    def calculate_portfolio_impact(self, symbol, current_price):
        """포트폴리오 영향 계산"""
        if symbol not in PORTFOLIO_STOCKS or not current_price:
            return None
            
        stock_info = PORTFOLIO_STOCKS[symbol]
        shares = stock_info["shares"]
        avg_price = stock_info["avg_price"]
        
        profit_loss = (current_price - avg_price) * shares
        profit_loss_pct = ((current_price - avg_price) / avg_price) * 100
        
        if profit_loss > 0:
            emoji = "📈"
            status = "수익"
        elif profit_loss < 0:
            emoji = "📉"
            status = "손실"
        else:
            emoji = "➖"
            status = "동일"
            
        return {
            "profit_loss": profit_loss,
            "profit_loss_pct": profit_loss_pct,
            "emoji": emoji,
            "status": status,
            "shares": shares,
            "avg_price": avg_price
        }

    def format_news_alert(self, symbol, news_item, current_price=None):
        """뉴스 알림 메시지 포맷"""
        title = news_item.get("title", "제목 없음")
        summary = news_item.get("summary", "")[:200] + "..." if len(news_item.get("summary", "")) > 200 else news_item.get("summary", "")
        time_published = news_item.get("time_published", "")
        
        # 뉴스 분석
        importance, sentiment, critical_score = self.analyze_news_importance(title, summary)
        
        # 포트폴리오 영향
        impact = self.calculate_portfolio_impact(symbol, current_price)
        
        stock_name = PORTFOLIO_STOCKS.get(symbol, {}).get("name", symbol)
        
        message = f"""🎯 **{stock_name} ({symbol}) 뉴스 알림**

{importance} | {sentiment}

📰 **{title}**

📝 {summary}"""

        if impact:
            message += f"""

💰 **포트폴리오 현황**:
- 보유: {impact['shares']}주 @ ${impact['avg_price']:.2f}
- 현재가: ${current_price:.2f} {impact['emoji']}
- 손익: ${impact['profit_loss']:+.2f} ({impact['profit_loss_pct']:+.2f}%)"""

        message += f"""

⏰ {time_published[:16]}

💡 상세분석이 필요하시면 "소피아, {symbol} 분석해줘"라고 요청하세요!"""

        return message

    def check_news(self):
        """뉴스 체크 및 알림"""
        now_kst = datetime.now(KST)
        print(f"🔍 [{now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}] 뉴스 체크 시작...")
        
        for symbol in PORTFOLIO_STOCKS.keys():
            try:
                print(f"📊 {symbol} 분석 중...")
                
                # 현재 주가 조회
                current_price = self.get_stock_price(symbol)
                
                # 뉴스 조회
                news_data = self.get_news_alpha_vantage(symbol)
                
                if news_data and "feed" in news_data:
                    for news_item in news_data["feed"][:5]:  # 최신 5개
                        news_url = news_item.get("url", "")
                        
                        # 이미 보낸 뉴스는 스킵
                        if news_url in self.sent_news:
                            continue
                        
                        title = news_item.get("title", "")
                        summary = news_item.get("summary", "")
                        
                        # 중요도 분석
                        importance, sentiment, critical_score = self.analyze_news_importance(title, summary)
                        
                        # 중요한 뉴스만 알림 (critical_score >= 1)
                        if critical_score >= 1:
                            message = self.format_news_alert(symbol, news_item, current_price)
                            
                            result = self.send_telegram_message(message)
                            if result and result.get("ok"):
                                self.sent_news.add(news_url)
                                self.save_sent_news()
                                print(f"✅ {symbol} 뉴스 알림 전송: {title[:50]}...")
                            
                            time.sleep(2)  # 메시지 간 간격
                
                time.sleep(3)  # API 간 간격
                
            except Exception as e:
                print(f"❌ {symbol} 처리 오류: {e}")

    def send_morning_briefing(self):
        """8시 30분 모닝 브리핑"""
        now_kst = datetime.now(KST)
        
        briefing = f"""🌅 **소피아 8:30 모닝 브리핑**

📅 {now_kst.strftime('%Y년 %m월 %d일 (%A)')}
⏰ {now_kst.strftime('%H:%M')} 업데이트

"""
        
        total_investment = 0
        total_current_value = 0
        total_profit = 0
        
        portfolio_details = []
        
        for symbol, info in PORTFOLIO_STOCKS.items():
            current_price = self.get_stock_price(symbol)
            
            if current_price:
                investment = info["avg_price"] * info["shares"]
                current_value = current_price * info["shares"]
                profit_loss = current_value - investment
                profit_loss_pct = (profit_loss / investment) * 100
                
                total_investment += investment
                total_current_value += current_value
                total_profit += profit_loss
                
                emoji = "📈" if profit_loss > 0 else "📉" if profit_loss < 0 else "➖"
                
                portfolio_details.append(f"""📊 **{info['name']} ({symbol})**
   현재가: ${current_price:.2f} | 평단가: ${info['avg_price']:.2f}
   손익: ${profit_loss:+.2f} ({profit_loss_pct:+.2f}%) {emoji}""")
            
            time.sleep(2)  # API 레이트 리밋 방지
        
        # 포트폴리오 상세 정보 추가
        for detail in portfolio_details:
            briefing += detail + "\n\n"
        
        # 전체 요약
        total_profit_pct = (total_profit / total_investment) * 100 if total_investment > 0 else 0
        total_emoji = "📈" if total_profit > 0 else "📉" if total_profit < 0 else "➖"
        
        briefing += f"""💰 **전체 포트폴리오 요약**
- 총 투자금: ${total_investment:,.2f}
- 현재 평가액: ${total_current_value:,.2f}
- 총 손익: ${total_profit:+.2f} ({total_profit_pct:+.2f}%) {total_emoji}

"""
        
        # 오늘의 주요 일정
        briefing += f"""📅 **오늘의 주요 일정**
"""
        
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
        
        briefing += f"""
💡 포트폴리오 문의사항이 있으시면 "소피아, 포트폴리오 분석해줘"라고 요청해주세요!

🤖 소피아가 8:30에 정확히 브리핑해드렸습니다! 📈"""
        
        result = self.send_telegram_message(briefing)
        if result:
            print(f"✅ 8:30 모닝 브리핑 전송 완료")
        else:
            print(f"❌ 모닝 브리핑 전송 실패")

def main():
    """메인 실행 함수"""
    print("🤖 소피아 투자 봇 시작...")
    
    bot = SofiaInvestmentBot()
    
    try:
        now_kst = datetime.now(KST)
        current_hour = now_kst.hour
        current_minute = now_kst.minute
        
        print(f"⏰ 현재 시간: {now_kst.strftime('%H:%M')} KST")
        print(f"🎯 실행 모드: {ACTION_TYPE}")
        
        # 액션 타입별 실행
        if ACTION_TYPE == "morning_briefing":
            print("🌅 수동 모닝 브리핑 실행...")
            bot.send_morning_briefing()
        elif ACTION_TYPE == "news_check":
            print("📰 수동 뉴스 체크 실행...")
            bot.check_news()
        elif ACTION_TYPE == "portfolio_update":
            print("📊 포트폴리오 업데이트 실행...")
            bot.send_morning_briefing()
        else:
            # 자동 모드: 시간에 따라 결정
            if current_hour == 8 and 25 <= current_minute <= 35:
                print("🌅 8:30 모닝 브리핑 시간입니다!")
                bot.send_morning_briefing()
            else:
                print("📰 뉴스 체크 실행...")
                bot.check_news()
                
    except Exception as e:
        error_msg = f"🚨 소피아 봇 오류 발생: {str(e)}"
        print(error_msg)
        bot.send_telegram_message(error_msg)

if __name__ == "__main__":
    main()
