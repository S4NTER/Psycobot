import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import os

def generate_mood_chart(data: list, output_path: str):
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')
    dates = df['timestamp']
    mood_scores = df['mood_score']
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(dates, mood_scores, marker='o', linestyle='-', color='#4CAF50', linewidth=2, markersize=6)
    ax.set_title('Настроение за Неделю', fontsize=16, fontweight='bold')
    ax.set_xlabel('Дата и Время', fontsize=12)
    ax.set_ylabel('Оценка Настроения (1-10)', fontsize=12)
    ax.set_ylim(0.5, 10.5)
    ax.set_yticks(range(1, 11))
    date_format = plt.matplotlib.dates.DateFormatter('%a, %H:%M')
    ax.xaxis.set_major_formatter(date_format)
    plt.xticks(rotation=45, ha='right')
    ax.grid(True, linestyle='--', alpha=0.7)
    avg_mood = mood_scores.mean()
    ax.axhline(avg_mood, color='r', linestyle='--', linewidth=1, label=f'Среднее: {avg_mood:.1f}')
    ax.legend()
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    plt.savefig(output_path)
    plt.close(fig)

if __name__ == '__main__':
    now = datetime.now()
    example_data = [
        {'timestamp': (now - pd.Timedelta(days=6)).isoformat(), 'mood_score': 5},
        {'timestamp': (now - pd.Timedelta(days=5, hours=3)).isoformat(), 'mood_score': 7},
        {'timestamp': (now - pd.Timedelta(days=4, hours=12)).isoformat(), 'mood_score': 4},
        {'timestamp': (now - pd.Timedelta(days=3, hours=20)).isoformat(), 'mood_score': 8},
        {'timestamp': (now - pd.Timedelta(days=2, hours=5)).isoformat(), 'mood_score': 6},
        {'timestamp': (now - pd.Timedelta(days=1, hours=15)).isoformat(), 'mood_score': 9},
        {'timestamp': now.isoformat(), 'mood_score': 7},
    ]
    test_path = "/tmp/test_mood_chart.png"
    generate_mood_chart(example_data, test_path)
    print(f"Test chart saved to {test_path}")
    if os.path.exists(test_path):
        print("Test chart creation successful.")
    else:
        print("Test chart creation failed.")