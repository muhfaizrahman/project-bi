# File: modules/ml_model.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go

def run_revenue_prediction(df):
    """Menerima DataFrame bersih dari database dan mengembalikan grafik prediksi."""
    
    # 1. GROUPING/AGREGASI
    monthly_sales = df.groupby('order_month')['sales'].sum().reset_index()
    
    # 2. PERSIAPAN VARIABEL
    monthly_sales['time_index'] = np.arange(1, len(monthly_sales) + 1)
    X = monthly_sales[['time_index']]
    y = monthly_sales['sales']
    
    # 3. TRAINING MODEL
    model = LinearRegression()
    model.fit(X, y)
    
    # 4. PREDIKSI 1 KUARTAL (3 BULAN)
    future_steps = 3
    last_index = monthly_sales['time_index'].max()
    
    future_X = pd.DataFrame({'time_index': np.arange(last_index + 1, last_index + 1 + future_steps)})
    future_predictions = model.predict(future_X)
    
    # Bikin label bulan untuk masa depan
    last_month = pd.to_datetime(monthly_sales['order_month'].max())
    future_months = [(last_month + pd.DateOffset(months=i)).strftime('%Y-%m') for i in range(1, future_steps + 1)]
    
    future_df = pd.DataFrame({'order_month': future_months, 'sales': future_predictions, 'status': 'Prediksi'})
    monthly_sales['status'] = 'Historis'
    combined_df = pd.concat([monthly_sales[['order_month', 'sales', 'status']], future_df], ignore_index=True)
    
    # 5. VISUALISASI PLOTLY
    fig = go.Figure()
    historis = combined_df[combined_df['status'] == 'Historis']
    prediksi = combined_df[combined_df['status'] == 'Prediksi']
    nyambung = pd.concat([historis.iloc[-1:], prediksi])
    
    fig.add_trace(go.Scatter(x=historis['order_month'], y=historis['sales'], mode='lines+markers', name='Historis', line=dict(color='#1f77b4', width=2)))
    fig.add_trace(go.Scatter(x=nyambung['order_month'], y=nyambung['sales'], mode='lines+markers', name='Prediksi (1 Kuartal)', line=dict(color='#d62728', width=2, dash='dash')))
                             
    fig.update_layout(title='Forecast Pendapatan 1 Kuartal Mendatang', xaxis_title='Periode', yaxis_title='Total Revenue ($)', hovermode='x unified')
    
    return fig