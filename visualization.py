import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import os

def generate_mood_chart(data: list, output_path: str):
    """
    Generates a mood score line chart using matplotlib and saves it to a file.
    
    :param data: List of dictionaries with keys 'timestamp' and 'mood_score'.
    :param output_path: Path to save the generated PNG file.
    """
    # Convert list of dicts to pandas DataFrame
    df = pd.DataFrame(data)
    
    # Convert timestamp string to datetime objects
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort by time
    df = df.sort_values(by='timestamp')
    
    # Prepare data for plotting
    dates = df['timestamp']
    mood_scores = df['mood_score']
    
    # --- Plotting ---
    
    # Set a professional style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot the mood scores
    ax.plot(dates, mood_scores, marker='o', linestyle='-', color='#4CAF50', linewidth=2, markersize=6)
    
    # Set labels and title
    ax.set_title('Трекинг Настроения за Неделю', fontsize=16, fontweight='bold')
    ax.set_xlabel('Дата и Время', fontsize=12)
    ax.set_ylabel('Оценка Настроения (1-10)', fontsize=12)
    
    # Set y-axis limits and ticks
    ax.set_ylim(0.5, 10.5)
    ax.set_yticks(range(1, 11))
    
    # Format x-axis to show dates nicely
    # Use a more compact date format for better readability on the chart
    date_format = plt.matplotlib.dates.DateFormatter('%a, %H:%M')
    ax.xaxis.set_major_formatter(date_format)
    
    # Rotate date labels for better fit
    plt.xticks(rotation=45, ha='right')
    
    # Add grid lines
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Highlight the average mood
    avg_mood = mood_scores.mean()
    ax.axhline(avg_mood, color='r', linestyle='--', linewidth=1, label=f'Среднее: {avg_mood:.1f}')
    ax.legend()
    
    # Ensure tight layout
    plt.tight_layout()
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # Save the figure
    plt.savefig(output_path)
    plt.close(fig)

if __name__ == '__main__':
    # Example usage for testing the visualization
    # Create a dummy data set
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
    
    # To view the chart, you would typically need to send it to the user or open it.
    # For this environment, we just confirm it was created.
    if os.path.exists(test_path):
        print("Test chart creation successful.")
    else:
        print("Test chart creation failed.")
