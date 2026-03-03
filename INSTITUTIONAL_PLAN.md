# 🏦 Plan Stratégique : Sniper Institutionnel Multi-Actifs v4

Ce document définit l'architecture technique et les règles d'exécution pour le déploiement d'un bot de trading de type **Hedge Fund**, spécialisé sur XAUUSD, BTCUSD, US100 et DXY.

---

## 🧠 1️⃣ Optimisation Multi-Timeframe (MTF)

*   **Confluence de Tendance** : Analyse descendante obligatoire de Weekly à M5.
*   **Précision Chirurgicale** : Détection des micro-structures (OB/FVG) sur M5/M1 pour affiner le point d'entrée.
*   **Score MTF** : Chaque trade doit valider une checklist de confluence MTF. Si confluence < seuil → Trade annulé.
*   **SL/TP Dynamique** : Niveaux de sortie basés sur la volatilité des unités de temps supérieures.

## 🔥 2️⃣ Volatilité Adaptative (ATR Dynamic)

*   **ATR Contextuel** : Calcul de l'ATR en temps réel par actif et par session (Londres vs NY).
*   **Filtre de Régime** :
    *   Volatilité trop faible : Marché en range (Risque de fausses cassures).
    *   Volatilité trop élevée : News ou crash (Risque de slippage).
*   **Protection** : Ajustement des stops pour éviter d'être "sorti" par le bruit du marché.

## ⚡ 3️⃣ Analyse Intermarket (Corrélations)
Le bot filtre les entrées en fonction de l'alignement des actifs corrélés :

| Actif principal | Actifs Filtres (Corrélations) |
| :--- | :--- |
| **XAUUSD** | DXY, US100, BTCUSD |
| **BTCUSD** | DXY, US100, XAUUSD |
| **US100** | DXY, BTCUSD |
| **DXY** | XAUUSD, US100, BTCUSD |

*Exemple : Interdiction d'acheter XAUUSD si le DXY montre une force institutionnelle claire.*

## 🧠 4️⃣ News / Macro Filter

*   **Filtre Automatique** : Intégration d'un calendrier économique.
*   **Blackout Zones** : Suspension du trading pendant les news "High Impact" (CPI, NFP, FOMC, Earnings).
*   **Slippage Guard** : Protection contre l'élargissement des spreads.

## 💎 5️⃣ Optimisation Order Block (OB) / FVG

*   **Priorisation HTF** : Les OB/FVG sur Daily et H4 ont priorité absolue sur le micro-SMC.
*   **Scoring Qualité** : Évaluation basée sur le volume de sortie, la liquidité capturée et la confluence HTF.

## 🔥 6️⃣ Scoring Chirurgical Avancé (Seuil 7/10)
| Critère | Poids |
| :--- | :---: |
| HTF Trend aligné (Weekly/Daily) | +2.5 |
| OB aligné HTF (H4/H1) | +2.5 |
| FVG présent | +1.5 |
| Sweep confirmé (BSL/SSL) | +1.5 |
| Fibonacci retracement (OTE) | +1 |
| Session active | +1 |
| News impact imminente | -3 |

**Règle d'or** : Trade validé uniquement si Score ≥ 7/10.

## 🧠 7️⃣ Adaptive Position Sizing

*   **Calcul Dynamique** : Lot size basé on l'ATR, la distance du SL et le score du setup.
*   **Gestion du Risque (Hedge Fund Standard)** :
    *   Setup Parfait (10/10) : **Max 2%** du capital.
    *   Setup Classique (7/10) : **0.5% à 1%** du capital.

## ⚡ 8️⃣ Optimisation de Timing (Sessions)
Le bot ne trade que pendant les fenêtres de liquidité maximale :

| Actif | Session préférée |
| :--- | :--- |
| **XAUUSD** | Londres + New York |
| **BTCUSD** | New York + Londres + Weekend |
| **US100** | New York uniquement |
| **DXY** | Londres + New York |

## 💎 9️⃣ Stop / Take Profit Dynamique

*   **SL Chirurgical** : Placé sous l'OB ou le swing low structurel.
*   **TP Institutionnel** : Basé sur les cibles de liquidité HTF (BSL/SSL) et les zones de déséquilibre.
*   **Management** : Break-even automatique à 1:1 RR et TP partiel sur micro-FVG.

## 🧠 🔟 Machine Learning Adaptatif

*   **Feedback Loop** : Analyse des performances passées pour ajuster les poids du scoring.
*   **Adaptation au Régime** : Détection automatique des changements de phase (Tendance vs Range).

---

## ⚡ Bonus : Psychologie Institutionnelle Intégrée

*   **Max trades / jour** : 5
*   **Max drawdown / jour** : 5%
*   **Max perte / trade** : 2%
*   **Discipline 100%** : Le bot refuse toute entrée ne respectant pas strictement les filtres MTF et intermarket.
