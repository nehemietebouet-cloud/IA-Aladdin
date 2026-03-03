# analyzer/sentiment.py

from textblob import TextBlob
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    from vaderSentiment import SentimentIntensityAnalyzer
import requests
import json
from config import CONFIG

class SentimentNLP:
    """
    Market Sentiment Analysis using NLP (News & Twitter)
    """
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.ollama_url = CONFIG["ollama_url"]
        self.model = "llama3.2" # Using a faster text model if possible, or same vision model

    def analyze_with_llm(self, headlines):
        """
        Uses LLM to get deep semantic sentiment from headlines
        """
        text = "\n".join(headlines)
        prompt = f"""
        Analyze the overall market sentiment from these headlines:
        {text}
        
        Rules:
        1. Classify as Bullish, Bearish, or Neutral.
        2. Give a Score from -1.0 (Panic) to 1.0 (Euphoria).
        3. Provide a 2-sentence summary of the news bias.
        
        Output format: JSON only
        {{
            "bias": "...",
            "score": 0.0,
            "summary": "..."
        }}
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            result = response.json()
            return json.loads(result.get("response", "{}"))
        except:
            return None

    def analyze_text(self, text):
        """
        Combines TextBlob and VADER for robust sentiment score
        """
        # VADER (Better for social media/financial short text)
        vader_score = self.vader.polarity_scores(text)['compound']
        
        # TextBlob
        blob = TextBlob(text)
        blob_score = blob.sentiment.polarity
        
        # Combined Score (-1 to 1)
        combined = (vader_score + blob_score) / 2
        
        sentiment = "Neutral"
        if combined > 0.05: sentiment = "Bullish"
        elif combined < -0.05: sentiment = "Bearish"
            
        return {
            "score": round(combined, 3),
            "sentiment": sentiment,
            "subjectivity": round(blob.sentiment.subjectivity, 2)
        }

    def analyze_news_list(self, headlines):
        """
        Aggregate sentiment from a list of headlines
        """
        scores = [self.analyze_text(h)['score'] for h in headlines]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        bias = "Neutral"
        if avg_score > 0.1: bias = "Bullish (News Driven)"
        elif avg_score < -0.1: bias = "Bearish (Panic/Negative News)"
            
        return {"avg_score": round(avg_score, 3), "bias": bias}
