# telegram_bot.py (시장 컨텍스트 알림 추가 버전)
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
        "target_price": 275.0,
        "stop_loss": 240.0
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

# 시장 지수 모니터링 설정
MARKET_INDICES = {
    "SPY": {"name": "S&P 500", "threshold": 0.015},     # 1.5% 변동시 알림
    "QQQ": {"name": "나스닥", "threshold": 0.02},        # 2% 변동시 알림
    "VIX": {"name": "VIX 공포지수", "threshold": 0.15}   # 15% 변동시 알림
}

class TelegramNewsBot:
    def __init__(self):
        self.sent_news_file = "sent_news.json"
        self.sent_news = self.load_sent_news()
        self.last_prices_file = "last_prices.json" 
        self.last_prices = self.load_last_prices()
        self.market_data_file = "market_data.json"
        self.market_data = self.load_market_data()
        
        # 알림 중복 방지를 위한 메모리 기반 추적
        self.session_alerts = set()
        
    def load_sent_news(self):
        """이전에 보낸 뉴스 목록 로드 (GitHub Actions에서는 메모리 기반)"""
        # GitHub Actions는 매번 새로운 환경이므로 간단한 중복 방지만 사용
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

    def load_market_data(self):
        """이전 시장 데이터 로드"""
        try:
            if os.path.exists(self.market_data_file):
                with open(self.market_data_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_market_data(self):
        """시장 데이터 저장"""
        try:
            with open(self.market_data_file, 'w') as f:
                json.dump(self.market_data, f)
        except Exception as e:
            print(f"시장 데이터 저장 오류: {e}")
        
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

    def check_market_conditions(self):
        """시장 상황 체크 및 알림"""
        print("시장 상황 체크 중...")
        
        for symbol, info in MARKET_INDICES.items():
            try:
                current_price = self.get_stock_price(symbol)
                if not current_price:
                    continue
                    
                last_price = self.market_data.get(symbol, current_price)
                change_pct = ((current_price - last_price) / last_price) * 100
                
                # 임계값 초과 시 알림
                if abs(change_pct) >= info["threshold"] * 100:
                    
                    if symbol == "VIX":
                        # VIX는 특별 처리
                        if change_pct > 0:
                            alert_message = f"""⚠️ **시장 공포지수 급등!**

📊 **VIX 지수**: {current_price:.1f} ({change_pct:+.1f}%)
😰 **시장 심리**: 공포감 증가

🛡️ **포트폴리오 대응방안**:
• 방어 모드 권장
• 추가 매수 신중하게
• 손절 기준 재검토

💡 변동성이 큰 시기입니다. 감정적 판단 금물!"""
                        else:
                            alert_message = f"""😌 **시장 안정화 신호**

📊 **VIX 지수**: {current_price:.1f} ({change_pct:+.1f}%)
😊 **시장 심리**: 안정감 회복

🚀 **포트폴리오 기회**:
• 공격적 투자 고려 가능
• 우량주 매수 타이밍
• 목표가 상향 검토

💡 시장이 안정화되고 있습니다!"""
                    
                    else:
                        # SPY, QQQ 등 일반 지수
                        if change_pct > 0:
                            emoji = "📈🟢"
                            impact = "상승 모멘텀"
                            recommendation = "추가 매수 기회 검토"
                        else:
                            emoji = "📉🔴"
                            impact = "하락 압력"
                            recommendation = "방어적 포지션 고려"
                            
                        alert_message = f"""{emoji} **{info['name']} 급변동!**

📊 **현재 상황**:
• 지수: {current_price:.2f}
• 변동: {change_pct:+.2f}%

💼 **포트폴리오 영향**:
• 예상 영향: {impact}
• 개별 종목도 동조화 가능성

💡 **추천 행동**: {recommendation}

🔍 개별 종목 현황도 함께 확인하세요!"""

                    # 알림 전송
                    result = self.send_telegram_message(alert_message)
                    if result and result.get("ok"):
                        print(f"[{symbol}] 시장 알림 전송 완료: {change_pct:+.1f}%")
                
                # 현재 데이터 저장
                self.market_data[symbol] = current_price
                
            except Exception as e:
                print(f"[{symbol}] 시장 데이터 오류: {e}")
        
        self.save_market_data()

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

💡 **알림**: 급격한 변동이 감지되었습니다. 시장 전체 상황도 확인해보세요!"""

        return alert_message

    def get_alpha_vantage_news(self, symbol):
        """Alpha Vantage 뉴스 조회 (개선된 버전)"""
        if not ALPHA_VANTAGE_KEY:
            print("Alpha Vantage API 키가 없습니다.")
            return None
            
        url = "https://www.alphavantage.co/query"
        
        # 종목별 더 구체적인 검색어 사용
        search_terms = {
            "IBM": "International Business Machines",
            "NOW": "ServiceNow",
            "SOUN": "SoundHound AI"
        }
        
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "topics": "technology,earnings",
            "apikey": ALPHA_VANTAGE_KEY,
            "limit": 5,
            "sort": "LATEST"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            # 응답 데이터 검증 및 필터링
            if data and "feed" in data:
                filtered_feed = []
                search_term = search_terms.get(symbol, symbol)
                
                for item in data["feed"]:
                    title = item.get("title", "").lower()
                    summary = item.get("summary", "").lower()
                    
                    # 해당 회사명이 실제로 언급된 뉴스만 선택
                    company_mentioned = (
                        search_term.lower() in title or 
                        search_term.lower() in summary or
                        symbol.lower() in title
                    )
                    
                    # 다른 회사명이 더 많이 언급된 경우 제외
                    other_companies = ["seagate", "tesla", "apple", "microsoft", "google", "amazon"]
                    other_company_mentioned = any(company in title for company in other_companies)
                    
                    if company_mentioned and not other_company_mentioned:
                        filtered_feed.append(item)
                
                data["feed"] = filtered_feed
                print(f"[{symbol}] 필터링 후 뉴스 {len(filtered_feed)}개")
                
            return data
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

    def comprehensive_market_check(self):
        """종합 시장 체크 (뉴스 + 가격 + 시장상황)"""
        print(f"[{datetime.now()}] 종합 시장 체크 시작...")
        
        # 1. 시장 상황 먼저 체크
        self.check_market_conditions()
        
        # 2. 개별 종목 체크
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
                
                # 뉴스 조회
                news_data = self.get_alpha_vantage_news(symbol)
                
                if news_data and "feed" in news_data:
                    for news_item in news_data["feed"][:2]:
                        news_url = news_item.get("url", "")
                        
                        if news_url in self.sent_news:
                            continue
                        
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
        
        # 데이터 저장
        self.save_last_prices()

    def send_morning_briefing(self):
        """강화된 아침 브리핑"""
        briefing = f"""🌅 **소피아 종합 모닝 브리핑**

📅 {datetime.now().strftime('%Y년 %m월 %d일')}

"""
        
        # 시장 상황 요약
        try:
            spy_price = self.get_stock_price("SPY")
            vix_price = self.get_stock_price("VIX")
            
            if spy_price and vix_price:
                if vix_price > 20:
                    market_mood = "😰 불안정"
                elif vix_price < 15:
                    market_mood = "😊 안정적"
                else:
                    market_mood = "😐 보통"
                
                briefing += f"🌍 **시장 상황**: S&P500 ${spy_price:.2f} | VIX {vix_price:.1f} {market_mood}\n\n"
        except:
            pass
        
        # 포트폴리오 상황
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
                briefing += f"   손익: ${profit_loss:+.2f} | 목표가: {target_distance:.1f}% | 손절선: {stop_distance:.1f}%\n\n"
        
        briefing += f"💰 **총 손익**: ${total_profit:+.2f}\n\n"
        briefing += "🤖 오늘도 소피아가 24시간 시장을 감시합니다!\n"
        briefing += "💡 궁금한 것이 있으면 언제든 물어보세요!"
        
        self.send_telegram_message(briefing)

def main():
    """메인 실행 함수"""
    bot = TelegramNewsBot()
    
    try:
        current_hour = datetime.now().hour
        
        if current_hour == 0:  # UTC 자정 = 한국 오전 9시
            print("아침 브리핑 전송...")
            bot.send_morning_briefing()
        else:
            print("종합 시장 체크 실행...")
            bot.comprehensive_market_check()
            
    except Exception as e:
        print(f"실행 오류: {e}")
        bot.send_telegram_message(f"🚨 시스템 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
