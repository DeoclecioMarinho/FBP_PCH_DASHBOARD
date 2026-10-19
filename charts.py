"""Gráficos Plotly testáveis, com códigos P01-P15 e enunciados no hover."""
import html
from textwrap import wrap
import pandas as pd
import plotly.graph_objects as go

NAVY='#172E43'; BLUE='#1E617E'; ORANGE='#B67937'; RED='#B94D50'


def bar_figure(df, label_key, value_key, max_rows=5, palette=BLUE):
    data=df.head(max_rows).iloc[::-1]
    values=pd.to_numeric(data[value_key], errors='coerce').fillna(0)
    colors=[RED if n<50 else ORANGE if n<70 else palette for n in values]
    if 'Enunciado' in data.columns:
        hoverdata=[['<br>'.join(html.escape(line) for line in wrap(str(q),width=64,break_long_words=False))]
                   for q in data['Enunciado'].fillna('')]
        hover='<b>%{y}</b><br>%{customdata[0]}<br><b>Taxa de acerto: %{x:.1f}%</b><extra></extra>'
    else:
        hoverdata=None
        hover='%{y}: %{x:.1f}%<extra></extra>'
    fig=go.Figure(go.Bar(x=values,y=data[label_key],orientation='h',marker_color=colors,
            text=[f'{v:.0f}%' for v in values],textposition='outside',cliponaxis=False,
            customdata=hoverdata,hovertemplate=hover))
    fig.update_layout(height=max(240,58*len(data)+35),margin=dict(t=10,b=18,l=5,r=35),
                      xaxis=dict(range=[0,111],dtick=25,gridcolor='#E7EDF2',title=None,zeroline=False),
                      yaxis=dict(title=None,automargin=True),font=dict(color=NAVY,size=12),
                      showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    return fig
