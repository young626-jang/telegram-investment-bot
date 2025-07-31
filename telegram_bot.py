# telegram_bot.py (업데이트 버전)
import requests
import os
import json
from datetime import datetime

# 환경변수에서 설정값 가져오기 (보안)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
POLYGON_KEY = os.getenv('POLYGON_KEY')
BENZINGA_KEY = os.getenv('BENZINGA_KEY')

# 모니터링할 종목들 (목표가/손절가 추가)
PORTFOLIO_STOCKS = {
    "IBM": {
        "shares": 16, 
        "avg_price": 261.68,
        "target_price": 275.0,    # 목표가
        "stop_loss": 240.0        # 손절가
    },
    "NOW": {
        "shares": 3, 
        "avg_price": 1017.32,
        "target_price": 1150.0,
        "stop_loss": 900.0
    },
    "SOUN": {
        "shares": 30, 
        "avg_price": 11.05,
        "target_price": 15.0,
        "stop_loss": 8.0
    }
}

class TelegramNewsBot:
    def __init__(self):
        self.sent_news_file = "sent_news.json"
        self.sent_news = self.load_sent_news()
        self.last_prices_file = "last_prices.json"
        self.last_prices = self.load_last_prices()
        
    def load_sent_news(self):
        """이전에 보낸 뉴스 목록 로드"""
        try:
            if os.path.exists(self.sent_news_file):
                with open(self.sent_news_file, 'r') as f:
                    return set(json.load(f))
        except:
            pass
        return set()
    
    def save_sent_news(self):
        """보낸 뉴스 목록 저장"""
        try:
            with open(self.sent_news_file, 'w') as f:
                json.dump(list(self.sent_news), f)
        except Exception as e:
            print(f"뉴스 저장 오류: {e}")

    def load_last_prices(self):
        """이전 가격 데이터 로드"""
        try:
            if os.path.exists(self.last_prices_file):
                with open(self.last_prices_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_last_prices(self):
        """현재 가격 데이터 저장"""
        try:
            with open(self.last_prices_file, 'w') as f:
                json.dump(self.last_prices, f)
        except Exception as e:
            print(f"가격 저장 오류: {e}")
        
    def send_telegram_message(self, message):
        """텔레그램 메시지 전송"""
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
        """실시간 주가 조회"""
        if not POLYGON_KEY:
            print("Polygon API 키가 없습니다.")
            return None
            
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        params = {"apikey": POLYGON_KEY}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("results"):
                return data["results"][0]["c"]
        except Exception as e:
            print(f"주가 조회 오류 ({symbol}): {e}")
        return None

    def check_price_alerts(self, symbol, current_price):
        """가격 알림 체크"""
        if not current_price:
            return None
            
        stock_info = PORTFOLIO_STOCKS.get(symbol, {})
        target_price = stock_info.get("target_price")
        stop_loss = stock_info.get("stop_loss")
        avg_price = stock_info.get("avg_price")
        shares = stock_info.get("shares")
        
        # 이전 가격과 비교
        last_price = self.last_prices.get(symbol, current_price)
        
        alert_message = None
        
        # 목표가 달성 체크
        if target_price and current_price >= target_price and last_price < target_price:
            profit = (current_price - avg_price) * shares
            profit_pct = ((current_price - avg_price) / avg_price) * 100
            
            alert_message = f"""🚀 **{symbol} 목표가 달성!**

💰 **현재가**: ${current_price:.2f}
🎯 **목표가**: ${target_price:.2f} 달성!

📈 **수익 현황**:
• 보유: {shares}주
• 평단가: ${avg_price:.2f}
• 수익금: ${profit:+.2f}
• 수익률: {profit_pct:+.2f}%

💡 **추천**: 부분 또는 전량 수익실현을 고려해보세요!"""

        # 손절가 도달 체크
        elif stop_loss and current_price <= stop_loss and last_price > stop_loss:
            loss = (current_price - avg_price) * shares
            loss_pct = ((current_price - avg_price) / avg_price) * 100
            
            alert_message = f"""🚨 **{symbol} 손절가 도달!**

📉 **현재가**: ${current_price:.2f}
⚠️ **손절가**: ${stop_loss:.2f} 도달!

💸 **손실 현황**:
• 보유: {shares}주
• 평단가: ${avg_price:.2f}
• 손실금: ${loss:.2f}
• 손실률: {loss_pct:.2f}%

⚡ **추천**: 추가 하락 방지를 위한 손절 검토 필요!"""

        # 급등/급락 체크 (1시간 내 ±3% 이상)
        elif abs(current_price - last_price) / last_price >= 0.03:
            change_pct = ((current_price - last_price) / last_price) * 100
            change_amount = (current_price - last_price) * shares
            
            if change_pct > 0:
                emoji = "⚡🟢"
                direction = "급등"
            else:
                emoji = "⚡🔴"
                direction = "급락"
                
            alert_message = f"""{emoji} **{symbol} {direction} 감지!**

📊 **가격 변동**:
• 이전: ${last_price:.2f}
• 현재: ${current_price:.2f}
• 변동: {change_pct:+.2f}%

💰 **포지션 영향**:
• 보유: {shares}주
• 영향금액: ${change_amount:+.2f}

💡 **알림**: 급격한 변동이 감지되었습니다. 시장 상황을 확인해보세요!"""

        return alert_message

    def get_alpha_vantage_news(self, symbol):
        """Alpha Vantage 뉴스 조회 (무료 대안)"""
        if not ALPHA_VANTAGE_KEY:
            print("Alpha Vantage API 키가 없습니다.")
            return None
            
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": ALPHA_VANTAGE_KEY,
            "limit": 3
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            return response.json()
        except Exception as e:
            print(f"뉴스 조회 오류 ({symbol}): {e}")
            return None

    def analyze_news_sentiment(self, title, summary):
        """뉴스 감정 분석"""
        positive_keywords = ["strong", "growth", "beat", "exceed", "positive", "upgrade", "bullish"]
        negative_keywords = ["weak", "decline", "miss", "negative", "downgrade", "bearish", "concern"]
        
        text = (title + " " + summary).lower()
        
        positive_score = sum(1 for word in positive_keywords if word in text)
        negative_score = sum(1 for word in negative_keywords if word in text)
        
        if positive_score > negative_score:
            return "🟢 긍정적", f"+{positive_score}"
        elif negative_score > positive_score:
            return "🔴 부정적", f"-{negative_score}"
        else:
            return "🟡 중립적", "0"

    def format_news_alert(self, symbol, news_item, current_price=None):
        """뉴스 알림 메시지 포맷"""
        title = news_item.get("title", "제목 없음")
        summary = news_item.get("summary", "")
        time_published = news_item.get("time_published", "")
        
        # 감정 분석
        sentiment, score = self.analyze_news_sentiment(title, summary)
        
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
        
        message = f"""🚨 **{symbol} 중요 뉴스**

📰 **{title}**

{sentiment} (영향도: {score})

💰 **포트폴리오 현황**:
• 보유: {shares}주
• 평단가: ${avg_price:.2f}
• 현재가: ${current_price:.2f} {profit_emoji}
• 손익: ${profit_loss:.2f} ({profit_loss_pct:+.2f}%)

⏰ {time_published}

💡 상세분석이 필요하시면 소피아에게 "{symbol} 뉴스 분석해줘"라고 요청하세요!"""

        return message

    def check_news_and_prices(self):
        """뉴스 체크 및 가격 알림"""
        print(f"[{datetime.now()}] 뉴스 및 가격 체크 시작...")
        
        for symbol in PORTFOLIO_STOCKS.keys():
            try:
                # 현재 주가 조회
                current_price = self.get_stock_price(symbol)
                print(f"[{symbol}] 현재가: ${current_price}")
                
                # 가격 알림 체크
                if current_price:
                    price_alert = self.check_price_alerts(symbol, current_price)
                    if price_alert:
                        result = self.send_telegram_message(price_alert)
                        if result and result.get("ok"):
                            print(f"[{symbol}] 가격 알림 전송 완료")
                    
                    # 현재 가격 저장
                    self.last_prices[symbol] = current_price
                
                # 뉴스 조회 (기존 기능)
                news_data = self.get_alpha_vantage_news(symbol)
                
                if news_data and "feed" in news_data:
                    for news_item in news_data["feed"][:2]:  # 최신 2개만
                        news_url = news_item.get("url", "")
                        
                        # 이미 보낸 뉴스는 스킵
                        if news_url in self.sent_news:
                            continue
                        
                        # 중요한 키워드가 포함된 뉴스만 알림
                        title = news_item.get("title", "").lower()
                        important_keywords = ["earnings", "revenue", "quarter", "guidance", "acquisition", "partnership", "deal"]
                        
                        if any(keyword in title for keyword in important_keywords):
                            message = self.format_news_alert(symbol, news_item, current_price)
                            
                            result = self.send_telegram_message(message)
                            if result and result.get("ok"):
                                self.sent_news.add(news_url)
                                self.save_sent_news()
                                print(f"[{symbol}] 뉴스 알림 전송: {title[:50]}...")
                
            except Exception as e:
                print(f"[{symbol}] 오류: {e}")
        
        # 가격 데이터 저장
        self.save_last_prices()

    def send_morning_briefing(self):
        """아침 브리핑"""
        briefing = f"""🌅 **소피아 모닝 브리핑**

📅 {datetime.now().strftime('%Y년 %m월 %d일')}

"""
        
        total_profit = 0
        for symbol, info in PORTFOLIO_STOCKS.items():
            current_price = self.get_stock_price(symbol)
            if current_price:
                profit_loss = (current_price - info["avg_price"]) * info["shares"]
                profit_loss_pct = ((current_price - info["avg_price"]) / info["avg_price"]) * 100
                total_profit += profit_loss
                
                # 목표가/손절가와의 거리 계산
                target_distance = ((info["target_price"] - current_price) / current_price) * 100
                stop_distance = ((current_price - info["stop_loss"]) / current_price) * 100
                
                emoji = "📈" if profit_loss > 0 else "📉" if profit_loss < 0 else "➖"
                briefing += f"📊 **{symbol}**: ${current_price:.2f} ({profit_loss_pct:+.2f}%) {emoji}\n"
                briefing += f"   손익: ${profit_loss:+.2f}\n"
                briefing += f"   목표가까지: {target_distance:.1f}% | 손절선까지: {stop_distance:.1f}%\n\n"
        
        briefing += f"💰 **총 손익**: ${total_profit:+.2f}\n\n"
        briefing += "💡 상세 분석이 필요하시면 '소피아, 모닝 브리핑 해줘'라고 요청해주세요!"
        
        self.send_telegram_message(briefing)

def main():
    """메인 실행 함수"""
    bot = TelegramNewsBot()
    
    # GitHub Actions 환경에서는 한 번만 실행
    try:
        # 환경 확인
        current_hour = datetime.now().hour
        
        if current_hour == 0:  # UTC 자정 = 한국 오전 9시
            print("아침 브리핑 전송...")
            bot.send_morning_briefing()
        else:
            print("뉴스 및 가격 체크 실행...")
            bot.check_news_and_prices()
            
    except Exception as e:
        print(f"실행 오류: {e}")
        # 오류 발생 시 알림
        bot.send_telegram_message(f"🚨 시스템 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
