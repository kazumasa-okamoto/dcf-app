import requests
import streamlit as st

FMP_API_KEY = st.secrets["FMP_API_KEY"] 
BASE_URL = "https://financialmodelingprep.com/api/v3"

def search_ticker_by_name(company_name):
    url = f"https://financialmodelingprep.com/api/v3/search"
    params = {
        "query": company_name,
        "limit": 5,
        "apikey": FMP_API_KEY
    }
    response = requests.get(url, params=params)
    return response.json()


def fetch_income_statement(ticker, limit=10):
    url = f"{BASE_URL}/income-statement/{ticker}?limit={limit}&apikey={FMP_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_balance_sheet(ticker, limit=10):
    url = f"{BASE_URL}/balance-sheet-statement/{ticker}?limit={limit}&apikey={FMP_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_cash_flow(ticker, limit=10):
    url = f"{BASE_URL}/cash-flow-statement/{ticker}?limit={limit}&apikey={FMP_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_market_data(ticker: str):
    url = f"{BASE_URL}/profile/{ticker}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

