import streamlit as st
import pandas as pd
import sqlalchemy
import os
import plotly.graph_objects as go
import time

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "crypto")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# Page Config
st.set_page_config(page_title="Crypto Dashboard", layout="wide")

# Helper Functions
@st.cache_data(ttl=60)
def fetch_data(symbol):
    try:
        engine = sqlalchemy.create_engine(DB_URL)
        query = sqlalchemy.text("""
            SELECT time, price AS close, volume
            FROM market_data
            WHERE symbol = :symbol
            ORDER BY time ASC
        """)
        df = pd.read_sql(query, engine, params={"symbol": symbol})
        if not df.empty:
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return pd.DataFrame()

def calculate_mas(df):
    if len(df) > 0:
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
    return df

# Sidebar
st.sidebar.title("Configuration")
symbol = st.sidebar.selectbox("Select Asset", ["BTC/USDT", "ETH/USDT"])
live_mode = st.sidebar.toggle("Live Mode", value=False)

if live_mode:
    st.sidebar.warning("⚠️ LIVE TRADING ACTIVE - Real API calls enabled")

# Main Layout
st.title(f"Crypto Dashboard: {symbol}")

tab1, tab2 = st.tabs(["Market Overview", "Paper Trading"])

with tab1:
    st.subheader("Price vs Moving Averages")
    
    df = fetch_data(symbol)
    
    if not df.empty:
        df = calculate_mas(df)
        
        # Plotly Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['close'], mode='lines', name='Price'))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], mode='lines', name='EMA 20', line=dict(dash='dot', color='orange')))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name='SMA 50', line=dict(color='purple')))
        
        fig.update_layout(height=600, xaxis_title="Time", yaxis_title="Price (USDT)")
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df.tail())
    else:
        st.info("No data available for this symbol. Ensure Ingestion Engine is running.")

with tab2:
    st.subheader("Paper Trading Simulator")
    
    # Initialize Session State
    if 'balance' not in st.session_state:
        st.session_state.balance = 10000.0  # Initial fake balance
    if 'positions' not in st.session_state:
        st.session_state.positions = {} # {symbol: quantity}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Wallet Balance", f"${st.session_state.balance:,.2f}")
    
    with col2:
        current_price = df['close'].iloc[-1] if not df.empty else 0
        st.metric(f"Current {symbol} Price", f"${current_price:,.2f}")
    
    # Buy/Sell Actions
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        buy_qty = st.number_input("Buy Quantity", min_value=0.0, step=0.01, key="buy_qty")
        if st.button("Buy"):
            cost = buy_qty * current_price
            if cost > 0 and st.session_state.balance >= cost:
                st.session_state.balance -= cost
                st.session_state.positions[symbol] = st.session_state.positions.get(symbol, 0) + buy_qty
                st.success(f"Bought {buy_qty} {symbol} for ${cost:.2f}")
                st.rerun()
            elif cost > 0:
                st.error("Insufficient funds")
                
    with action_col2:
        sell_qty = st.number_input("Sell Quantity", min_value=0.0, step=0.01, key="sell_qty")
        if st.button("Sell"):
            if sell_qty > 0 and st.session_state.positions.get(symbol, 0) >= sell_qty:
                revenue = sell_qty * current_price
                st.session_state.balance += revenue
                st.session_state.positions[symbol] -= sell_qty
                st.success(f"Sold {sell_qty} {symbol} for ${revenue:.2f}")
                st.rerun()
            elif sell_qty > 0:
                st.error("Insufficient holdings")

    st.subheader("Active Positions")
    if st.session_state.positions:
        pos_df = pd.DataFrame(list(st.session_state.positions.items()), columns=['Symbol', 'Quantity'])
        pos_df = pos_df[pos_df['Quantity'] > 0] # Filter out zero positions
        st.dataframe(pos_df)
    else:
        st.write("No active positions.")
