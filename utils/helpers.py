import os
import uuid
from datetime import datetime
import plotly.graph_objects as go

def save_plot_as_image(fig, folder="history"):
    """
    Saves a Plotly figure as a PNG image in the specified folder.
    Returns the path to the saved image.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
        
    filename = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.png"
    filepath = os.path.join(folder, filename)
    
    try:
        # Requires 'kaleido' package for static image export
        fig.write_image(filepath)
        return filepath
    except Exception as e:
        # Fallback for headless environments or missing kaleido
        print(f"Error saving image: {e}")
        return None

def format_currency(value):
    return f"${value:,.2f}"

def format_percentage(value):
    return f"{value:.2f}%"

def get_session_name(time_val):
    """
    Returns the session name based on UTC hour
    """
    hour = time_val.hour
    if 0 <= hour < 9:
        return "Asie"
    elif 8 <= hour < 17:
        return "Londres"
    elif 13 <= hour < 22:
        return "New York"
    return "Hors Session"
