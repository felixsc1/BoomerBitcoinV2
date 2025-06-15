import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
import yfinance as yf

st.set_page_config(layout="wide")

# MongoDB connection setup
connection_string = st.secrets["mongodb"]["connection_string"]
client = MongoClient(connection_string)
db = client.bitcoin_db
purchases = db.purchases

@st.cache_data(ttl=3600)
def get_sp500_prices(start_date=None):
    if start_date:
        start_date_str = start_date.strftime('%Y-%m-%d')
    else:
        start_date_str = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    try:
        # Get S&P 500 data
        sp500 = yf.download('^GSPC', start=start_date_str)
        if 'Close' in sp500.columns:
            sp500 = sp500[['Close']].reset_index()
        elif 'Adj Close' in sp500.columns:
            sp500 = sp500[['Adj Close']].reset_index()
        else:
            raise ValueError("Neither 'Close' nor 'Adj Close' column found in S&P 500 data")
        
        sp500.columns = ['date', 'price']
        
        # Get current USD/CHF exchange rate
        try:
            usd_chf = yf.download('USDCHF=X', period='1d')['Close'][-1]
        except:
            # Fallback to a direct API call if the forex data fails
            usd_chf = yf.Ticker('USDCHF=X').fast_info['last_price']
        
        sp500['price'] = sp500['price'] * usd_chf
        return sp500
    except Exception as e:
        st.error(f"Error fetching S&P 500 data: {str(e)}")
        # Return empty DataFrame with correct structure
        return pd.DataFrame(columns=['date', 'price'])

@st.cache_data(ttl=3600)
def get_bitcoin_prices(start_date=None):
    # Calculate days from start_date to today
    if start_date:
        days = (datetime.today().date() - start_date).days + 30  # Add 30 days before earliest purchase
    else:
        days = 365  # Default to 1 year if no start_date provided
        
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=chf&days={days}"
    response = requests.get(url)
    data = response.json()
    prices = data["prices"]
    df_prices = pd.DataFrame(prices, columns=["timestamp", "price"])
    df_prices["date"] = pd.to_datetime(df_prices["timestamp"], unit="ms").dt.date
    df_prices = df_prices.drop(columns=["timestamp"])
    # Resample to weekly averages (Note: CoinGecko returns daily data, so we resample)
    df_prices["date"] = pd.to_datetime(df_prices["date"])
    df_prices = df_prices.set_index("date").resample("W").mean().reset_index()
    return df_prices

@st.cache_data(ttl=60)  # Cache for just 1 minute to keep it fresh
def get_current_bitcoin_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=chf"
    response = requests.get(url)
    data = response.json()
    return data["bitcoin"]["chf"]

st.title("Gewinn")
st.write("Hoi Werner! Die blaue Kurve ist der Bitcoin Preis über die Zeit. Bei den roten Punkten hast du Bitcoin gekauft.")

# Load purchases from MongoDB
df_purchases = pd.DataFrame(list(purchases.find({}, {'_id': 0})))

# Get earliest purchase date if there are any purchases
earliest_purchase_date = None
if not df_purchases.empty:
    df_purchases["date"] = pd.to_datetime(df_purchases["date"]).dt.date
    earliest_purchase_date = df_purchases["date"].min()

# Get price data using the earliest purchase date
df_prices = get_bitcoin_prices(earliest_purchase_date)

# Get real-time current price
current_price = get_current_bitcoin_price()

# No need to filter purchases anymore since we're getting the correct date range
df_purchases_recent = df_purchases.copy()

# Create Plotly figure
fig = go.Figure()

# Add price curve
fig.add_trace(go.Scatter(x=df_prices["date"], y=df_prices["price"], mode="lines", name="BTC Preis"))

# Add purchase points if there are any
if not df_purchases_recent.empty:
    fig.add_trace(go.Scatter(x=df_purchases_recent["date"], y=df_purchases_recent["price_chf"], mode="markers", name="Käufe", marker=dict(color="red", size=10)))

# Set layout
fig.update_layout(title="Bitcoin Preisverlauf (CHF)", xaxis_title="Datum", yaxis_title="Preis (CHF)")

# Display the figure
st.plotly_chart(fig)

# Calculate profit/loss using all purchases and real-time price
if not df_purchases.empty:
    df_purchases["profit_loss"] = (current_price - df_purchases["price_chf"]) * df_purchases["amount"]
    total_profit_loss = df_purchases["profit_loss"].sum()
    
    # Calculate total investment and percentage change
    total_investment = (df_purchases["price_chf"] * df_purchases["amount"]).sum()
    percentage_change = (total_profit_loss / total_investment) * 100 if total_investment != 0 else 0
    
    # Display metric with absolute value and percentage change
    st.metric(
        label="Gesamtgewinn/-verlust (CHF)", 
        value=f"{total_profit_loss:,.2f}", 
        delta=f"{percentage_change:+.1f}%"
    )
else:
    st.metric(
        label="Gesamtgewinn/-verlust (CHF)", 
        value="0.00", 
        delta="0.0%"
    )

# Display current price
year_ago_price = df_prices.iloc[0]["price"]  # First price in our dataset (1 year ago)
price_change_pct = ((current_price - year_ago_price) / year_ago_price) * 100

st.metric(
    label="Aktueller Bitcoin Preis (CHF)",
    value=f"{current_price:,.2f}",
    delta=f"{price_change_pct:+.1f}% (verglichen zum Vorjahr)"
)

# Add S&P 500 comparison
st.write("---")
st.write("### Vergleich mit Aktien")
st.write("Hier siehst du, wie viel Gewinn/Verlust du gemacht hättest, wenn du die gleichen CHF-Beträge zum gleichen Zeitpunkt in den S&P 500 Index investiert hättest.")

if not df_purchases.empty:
    # Get S&P 500 data
    sp500_data = get_sp500_prices(earliest_purchase_date)
    current_sp500_price = sp500_data.iloc[-1]["price"]
    
    # Calculate equivalent shares of S&P 500 for each purchase
    sp500_investments = []
    for _, purchase in df_purchases.iterrows():
        purchase_date = purchase["date"]
        chf_amount = purchase["amount"] * purchase["price_chf"]  # Amount in CHF
        
        # Find closest S&P 500 price to purchase date
        sp500_price_at_purchase = sp500_data[sp500_data["date"].dt.date <= purchase_date]["price"].iloc[-1]
        sp500_shares = chf_amount / sp500_price_at_purchase
        
        sp500_profit = sp500_shares * (current_sp500_price - sp500_price_at_purchase)
        sp500_investments.append({
            "shares": sp500_shares,
            "profit_loss": sp500_profit
        })
    
    # Calculate total S&P 500 profit/loss
    total_sp500_profit = sum(inv["profit_loss"] for inv in sp500_investments)
    total_investment = (df_purchases["price_chf"] * df_purchases["amount"]).sum()
    sp500_percentage_change = (total_sp500_profit / total_investment) * 100 if total_investment != 0 else 0
    
    st.metric(
        label="S&P 500 Gewinn/-verlust mit gleichen Investitionen (CHF)", 
        value=f"{total_sp500_profit:,.2f}", 
        delta=f"{sp500_percentage_change:+.1f}%"
    )
else:
    st.metric(
        label="S&P 500 Gewinn/-verlust mit gleichen Investitionen (CHF)", 
        value="0.00", 
        delta="0.0%"
    )