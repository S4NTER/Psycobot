import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import os


def generate_mood_chart(data: list, output_path: str):
    filtered_data = []
    for entry in data:
        if 'timestamp' in entry and 'mood_score' in entry:
            try:
                dt = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                score = int(entry['mood_score'])
                if 1 <= score <= 10:
                    filtered_data.append({
                        'timestamp': dt,
                        'mood_score': score
                    })
            except:
                continue

    filtered_data.sort(key=lambda x: x['timestamp'])
    timestamps = [x['timestamp'] for x in filtered_data]
    scores = [x['mood_score'] for x in filtered_data]
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, scores, marker='o', linestyle='-', color='#4CAF50', linewidth=2, markersize=6)
    plt.title('Настроение за Неделю', fontsize=16, fontweight='bold')
    plt.xlabel('Дата и Время', fontsize=12)
    plt.ylabel('Оценка Настроения (1-10)', fontsize=12)
    plt.ylim(0.5, 10.5)
    plt.yticks(range(1, 11))
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d.%m %H:%M'))
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.7)
    avg_score = sum(scores) / len(scores)
    plt.axhline(avg_score, color='r', linestyle='--', linewidth=1, label=f'Среднее: {avg_score:.1f}')
    plt.legend()
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    plt.savefig(output_path, dpi=100)
    plt.close()
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0
