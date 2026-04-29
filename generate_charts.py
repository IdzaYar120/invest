import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import os

# Створюємо папку для графіків
output_dir = "charts_output"
os.makedirs(output_dir, exist_ok=True)

# Мокові дані для 10 відомих компаній для репрезентативної вибірки
tickers = ['AAPL', 'MSFT', 'NVDA', 'KO', 'PEP', 'JPM', 'V', 'XOM', 'CVX', 'TSLA']
names = ['Apple', 'Microsoft', 'NVIDIA', 'Coca-Cola', 'PepsiCo', 'J.P. Morgan', 'Visa', 'Exxon', 'Chevron', 'Tesla']

# Фінансові метрики
betas = np.array([1.2, 1.1, 1.8, 0.6, 0.65, 1.1, 1.0, 0.8, 0.85, 2.1])
profits = np.array([0.25, 0.35, 0.45, 0.22, 0.15, 0.30, 0.50, 0.10, 0.12, 0.15])
pes = np.array([28, 35, 60, 24, 26, 12, 30, 10, 11, 70])
divs = np.array([0.005, 0.008, 0.001, 0.03, 0.028, 0.025, 0.007, 0.04, 0.042, 0.0])

# NLP оцінки новин (-1 до 1)
sentiments = np.array([0.8, 0.6, 0.9, 0.2, 0.1, 0.4, 0.5, 0.1, 0.0, 0.7])

# Функція розрахунку ваг AHP (адаптовано з utils.py)
def calculate_ahp_scores(weights):
    inv_betas = 1 / (betas + 0.01)
    norm_risk = inv_betas / inv_betas.sum()
    
    clean_profits = np.maximum(profits, 0)
    norm_profit = clean_profits / (clean_profits.sum() + 0.0001)
    
    inv_pes = 1 / (pes + 0.01)
    norm_pe = inv_pes / inv_pes.sum()
    
    norm_div = divs / (divs.sum() + 0.0001)
    
    metrics_matrix = np.column_stack((norm_risk, norm_profit, norm_pe, norm_div))
    scores = np.dot(metrics_matrix, weights)
    return scores

# -------------------------------------------------------------------------
# ГРАФІК 1: Розподіл оцінок (AHP vs Базовий підхід)
# -------------------------------------------------------------------------
# AHP: акцент на високий прибуток і низький ризик
ahp_weights = [0.3, 0.5, 0.1, 0.1] 
ahp_scores = calculate_ahp_scores(ahp_weights) * 100

# Equal Weights (стандартний середній бал)
eq_weights = [0.25, 0.25, 0.25, 0.25]
eq_scores = calculate_ahp_scores(eq_weights) * 100

# Сортуємо за результатами AHP
indices = np.argsort(ahp_scores)[::-1]
sorted_names = [names[i] for i in indices]
sorted_ahp = ahp_scores[indices]
sorted_eq = eq_scores[indices]

plt.figure(figsize=(12, 6))
x = np.arange(len(tickers))
width = 0.35
plt.bar(x - width/2, sorted_ahp, width, label='AHP (Багатокритеріальна оптимізація)', color='#2E86C1')
plt.bar(x + width/2, sorted_eq, width, label='Equal Weights (Просте усереднення)', color='#85C1E9')
plt.xticks(x, sorted_names, rotation=45, ha='right', fontsize=10)
plt.ylabel('Фінальна оцінка (Score)', fontsize=12)
plt.title('Графік 1: Порівняння алгоритму AHP з базовим усередненням', fontsize=14, fontweight='bold')
plt.legend(fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(f'{output_dir}/1_ahp_vs_equal.png', dpi=300)
plt.close()

# -------------------------------------------------------------------------
# ГРАФІК 2: Вплив NLP Аналізу на Рейтинг (Sentiment Effect)
# -------------------------------------------------------------------------
ahp_scores_no_nlp = ahp_scores.copy()
# Моделюємо вплив новин (NLP додає мультиплікатор до оцінки від 0.75 до 1.25)
nlp_multiplier = 1 + (sentiments - 0.5) * 0.5  
ahp_scores_nlp = ahp_scores * nlp_multiplier

# Визначаємо ранги (1 - найкращий)
rank_no_nlp = len(tickers) - np.argsort(np.argsort(ahp_scores_no_nlp))
rank_nlp = len(tickers) - np.argsort(np.argsort(ahp_scores_nlp))

plt.figure(figsize=(10, 7))
for i in range(len(tickers)):
    color = '#27AE60' if rank_nlp[i] < rank_no_nlp[i] else '#E74C3C' if rank_nlp[i] > rank_no_nlp[i] else '#7F8C8D'
    plt.plot([1, 2], [rank_no_nlp[i], rank_nlp[i]], marker='o', color=color, linewidth=2.5, markersize=8)
    
    # Підписи зліва і справа
    plt.text(0.95, rank_no_nlp[i], f"{names[i]} (#{rank_no_nlp[i]})", ha='right', va='center', fontsize=11)
    plt.text(2.05, rank_nlp[i], f"(#{rank_nlp[i]}) {names[i]}", ha='left', va='center', fontsize=11, fontweight='bold' if rank_nlp[i] < rank_no_nlp[i] else 'normal')

plt.xlim(0.5, 2.5)
plt.ylim(0.5, len(tickers) + 0.5)
plt.gca().invert_yaxis()
plt.axis('off')
plt.text(1, 0, 'Тільки фінансові метрики\n(Без NLP)', ha='center', va='top', fontweight='bold', fontsize=12)
plt.text(2, 0, '+ VADER Sentiment Analysis\n(З урахуванням новин)', ha='center', va='top', fontweight='bold', fontsize=12)
plt.title('Графік 2: Зміна рейтингу акцій під впливом аналізу тональності тексту', fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(f'{output_dir}/2_nlp_impact.png', dpi=300)
plt.close()

# -------------------------------------------------------------------------
# ГРАФІК 3: Оптимізація часу виконання (Time Complexity)
# -------------------------------------------------------------------------
n_stocks = np.array([1, 5, 10, 20, 50, 100])
# Без кешування O(N): ~1.2 секунди на кожен API запит yfinance
time_api = n_stocks * 1.2 
# З In-Memory кешуванням O(1): мікросекунди на доступ, плюс сталий час на рендеринг
time_cache = np.array([0.05, 0.06, 0.08, 0.1, 0.15, 0.2])

plt.figure(figsize=(10, 6))
plt.plot(n_stocks, time_api, marker='s', label='Без кешування (O(N) - Послідовні API виклики)', color='#E74C3C', linestyle='--', linewidth=2, markersize=8)
plt.plot(n_stocks, time_cache, marker='o', label='In-Memory Cache Redis/Local (O(1) - Кешування)', color='#27AE60', linewidth=3, markersize=8)
plt.xlabel('Кількість акцій для аналізу (N)', fontsize=12)
plt.ylabel('Час виконання алгоритму (секунди)', fontsize=12)
plt.title('Графік 3: Обчислювальна складність та оптимізація часу відповіді системи', fontsize=14, fontweight='bold')
plt.legend(fontsize=11)
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(f'{output_dir}/3_time_complexity.png', dpi=300)
plt.close()

# -------------------------------------------------------------------------
# ГРАФІК 4: Радар-чарт (Профілі Портфелів)
# -------------------------------------------------------------------------
# Вибір топ-5 за AHP (збалансовано)
top5_ahp_indices = np.argsort(ahp_scores)[::-1][:5]
# Вибір топ-5 просто за найвищою прибутковістю (однофакторний вибір)
top5_profit_indices = np.argsort(profits)[::-1][:5]

# Середні показники портфелів
avg_beta_ahp = np.mean(betas[top5_ahp_indices])
avg_profit_ahp = np.mean(profits[top5_ahp_indices]) * 100
avg_pe_ahp = np.mean(pes[top5_ahp_indices])
avg_div_ahp = np.mean(divs[top5_ahp_indices]) * 100

avg_beta_prof = np.mean(betas[top5_profit_indices])
avg_profit_prof = np.mean(profits[top5_profit_indices]) * 100
avg_pe_prof = np.mean(pes[top5_profit_indices])
avg_div_prof = np.mean(divs[top5_profit_indices]) * 100

categories = ['Ризик (Beta)\n(менше - краще)', 'Прибутковість (%)\n(більше - краще)', 'Вартість (P/E)\n(менше - краще)', 'Дивіденди (%)\n(більше - краще)']
# Нормалізація для графіка від 0 до 100
max_b = 2.0; max_p = 50; max_pe = 60; max_d = 5.0
# Інвертуємо дестимулятори (Beta та P/E) щоб ближче до краю було "краще" (більше балів)
ahp_vals = [ (1 - avg_beta_ahp/max_b)*100, (avg_profit_ahp/max_p)*100, (1 - avg_pe_ahp/max_pe)*100, (avg_div_ahp/max_d)*100 ]
prof_vals = [ (1 - avg_beta_prof/max_b)*100, (avg_profit_prof/max_p)*100, (1 - avg_pe_prof/max_pe)*100, (avg_div_prof/max_d)*100 ]

angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
ahp_vals += ahp_vals[:1]
prof_vals += prof_vals[:1]
angles += angles[:1]

fig, ax = plt.subplots(figsize=(9, 8), subplot_kw=dict(polar=True))
ax.plot(angles, ahp_vals, color='#27AE60', linewidth=2.5, label='Збалансований Портфель (AHP)')
ax.fill(angles, ahp_vals, color='#27AE60', alpha=0.25)

ax.plot(angles, prof_vals, color='#E74C3C', linewidth=2.5, label='Незбалансований Портфель (Лише Прибуток)')
ax.fill(angles, prof_vals, color='#E74C3C', alpha=0.25)

ax.set_yticklabels([])
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=12, fontweight='bold')
plt.title('Графік 4: Радар характеристик сформованих портфелів', size=15, fontweight='bold', y=1.1)
plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
plt.tight_layout()
plt.savefig(f'{output_dir}/4_radar_portfolio.png', dpi=300)
plt.close()

print(f"Графіки успішно згенеровано! Збережено у папці: {os.path.abspath(output_dir)}")
