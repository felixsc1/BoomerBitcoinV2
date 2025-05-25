import streamlit as st
import pandas as pd
from datetime import date
from pymongo import MongoClient
import os

# MongoDB connection setup
connection_string = st.secrets["mongodb"]["connection_string"]
client = MongoClient(connection_string)
db = client.bitcoin_db  # database name
purchases = db.purchases  # collection name

# Load purchases
@st.cache_data(ttl=1)  # Cache for 1 second to allow updates to show
def load_purchases():
    items = list(purchases.find({}, {'_id': 0}))  # Exclude MongoDB's _id field
    if not items:
        return pd.DataFrame(columns=["date", "amount", "price_chf"])
    return pd.DataFrame(items)

st.title("Meine Bitcoin-Käufe")
st.write("Hier können Sie Ihre Bitcoin-Käufe eingeben. Geben Sie das Datum, die Menge in BTC und den Preis pro BTC in CHF ein, und klicken Sie auf 'Kauf hinzufügen'.")

# Display existing purchases
st.write("Bisherige Käufe:")
df = load_purchases()
st.dataframe(df)

# Form to add new purchase
with st.form("add_purchase"):
    date_input = st.date_input("Datum", value=date.today())
    amount = st.number_input("Menge (BTC)", min_value=0.0, step=0.0001)
    price_chf = st.number_input("Preis pro BTC in CHF", min_value=0.0, step=0.01)
    submitted = st.form_submit_button("Kauf hinzufügen")

    if submitted:
        # Store in MongoDB
        new_purchase = {
            "date": date_input.isoformat(),
            "amount": amount,
            "price_chf": price_chf
        }
        purchases.insert_one(new_purchase)
        st.success("Kauf hinzugefügt!")
        st.rerun()

# Reset button
if st.button("⚠️ Reset", type="primary"):
    # Delete all documents in the collection
    purchases.delete_many({})
    st.success("Alle Käufe wurden gelöscht!")
    st.rerun()