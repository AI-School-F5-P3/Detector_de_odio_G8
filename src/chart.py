# src/chart.py
import plotly.graph_objects as go

def create_gauge_chart(probability: float, threshold: float) -> go.Figure:
    """Crea un gráfico de gauge para visualizar la probabilidad."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = probability * 100,
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, threshold * 100], 'color': "lightgray"},
                {'range': [threshold * 100, 100], 'color': "rgb(250, 200, 200)"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': threshold * 100
            }
        },
        title = {'text': "Probabilidad de Odio (%)"}
    ))
    
    fig.update_layout(height=250)
    return fig
