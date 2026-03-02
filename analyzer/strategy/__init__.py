# analyzer/strategy.py

import base64
import requests
import json
from config import CONFIG

class TradingAI:
    """
    Main AI Engine for analyzing images using local Ollama model
    """
    def __init__(self, api_key=None):
        self.ollama_url = CONFIG["ollama_url"]
        self.model = CONFIG["ai_model"]

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_chart(self, image_path, technical_data):
        """
        Sends image to local Ollama (Llama-3.2-Vision or LLaVA)
        """
        base64_image = self.encode_image(image_path)
        
        prompt = f"""
        [SYSTÈME : Trader Institutionnel Professionnel SMC/ICT]
        Analysez le graphique ci-joint pour identifier une configuration de trading à haute probabilité.
        
        DONNÉES DE CONTEXTE :
        - Régime du Marché : {technical_data.get('regime')}
        - Structure du Marché : {technical_data.get('structure')}
        - FVG Clé : {technical_data.get('fvg')}
        - Prix Consensus IA : {technical_data.get('prediction')}
        - Biais de Tendance ML : {technical_data.get('trend')}
        
        TÂCHES :
        1. Identifier la narration actuelle (Bullish/Bearish/Neutre).
        2. Localiser les empreintes institutionnelles (Order Blocks, Liquidity Sweeps).
        3. Vérifier l'alignement Premium/Discount avec le biais.
        4. Détecter si nous sommes en phase d'Accumulation, Manipulation ou Distribution (AMD).
        
        PLAN D'EXÉCUTION :
        - Biais : [Bullish/Bearish/Neutre]
        - Zone d'Entrée : [Plage de prix spécifique]
        - Stop Loss : [Protection stricte]
        - Take Profit : [Cibles basées sur la liquidité]
        - Ratio R/R : [Doit être > 2.0]
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [base64_image],
            "stream": False
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
