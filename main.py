#!/usr/bin/env python3
"""
fetch_and_visualize.py
Fetches VT ETF data and generates Plotly charts for multiple currencies
"""

import json
import os
from datetime import datetime

import pandas as pd
import yfinance as yf


def fetch_historical_forex_rates(period="5y"):
    """Fetch historical exchange rates aligned with VT data"""
    print("Fetching historical forex data...")

    # We'll store forex data as dataframes
    forex_data = {}

    try:
        # Fetch EUR/USD historical data
        eurusd = yf.Ticker("EURUSD=X")
        eurusd_hist = eurusd.history(period=period)
        forex_data["EUR"] = eurusd_hist["Close"]  # EUR/USD rate

        # Fetch GBP/USD historical data
        gbpusd = yf.Ticker("GBPUSD=X")
        gbpusd_hist = gbpusd.history(period=period)
        forex_data["GBP"] = gbpusd_hist["Close"]  # GBP/USD rate

        # Fetch CHF/USD historical data
        chfusd = yf.Ticker("CHFUSD=X")
        chfusd_hist = chfusd.history(period=period)
        forex_data["CHF"] = chfusd_hist["Close"]  # CHF/USD rate

        # USD is always 1
        forex_data["USD"] = 1.0

        print(f"Fetched forex data for {len(forex_data)} currencies")

    except Exception as e:
        print(f"Error fetching historical forex rates: {e}")
        # Return current rates as fallback
        forex_data = {
            "EUR": 0.85,  # EUR/USD
            "GBP": 1.25,  # GBP/USD
            "CHF": 1.10,  # CHF/USD
            "USD": 1.0,
        }

    return forex_data


def fetch_vt_data(period="5y"):
    """Fetch VT ETF historical data"""
    vt = yf.Ticker("VT")
    hist = vt.history(period=period)

    # Get additional info
    info = vt.info

    return hist, info


def create_chart_data(hist, forex_data):
    """Create chart data in a format optimized for JavaScript charting"""

    chart_data = {"labels": hist.index.strftime("%Y-%m-%d").tolist(), "datasets": []}

    # Modern color palette
    colors = {
        "USD": {"line": "#0066CC", "background": "rgba(0, 102, 204, 0.1)"},
        "EUR": {"line": "#FF6B35", "background": "rgba(255, 107, 53, 0.1)"},
        "GBP": {"line": "#00A878", "background": "rgba(0, 168, 120, 0.1)"},
        "CHF": {"line": "#C73E1D", "background": "rgba(199, 62, 29, 0.1)"},
    }

    # Create dataset for each currency
    for currency in ["USD", "EUR", "GBP", "CHF"]:
        if currency == "USD":
            y_values = hist["Close"].tolist()
        else:
            if isinstance(forex_data[currency], pd.Series):
                aligned_forex = forex_data[currency].reindex(hist.index, method="ffill")
                y_values = (hist["Close"] / aligned_forex).tolist()
            else:
                y_values = (hist["Close"] / forex_data[currency]).tolist()

        dataset = {
            "label": currency,
            "data": y_values,
            "borderColor": colors[currency]["line"],
            "backgroundColor": colors[currency]["background"],
            "borderWidth": 3,
            "tension": 0.4,  # Smooth curves
            "pointRadius": 0,  # Hide points for cleaner look
            "pointHoverRadius": 0,  # Hide points even on hover
            "pointBackgroundColor": colors[currency]["line"],
            "pointBorderColor": "#fff",
            "pointBorderWidth": 0,
            "pointHitRadius": 10,  # Still allow hover detection
            "fill": currency == "USD",  # Only fill USD
        }

        chart_data["datasets"].append(dataset)

    return chart_data


def create_summary_data(hist, info, forex_data):
    """Create summary statistics for display"""
    latest_close = hist["Close"].iloc[-1]

    # Get latest forex rates
    latest_rates = {}
    for currency, data in forex_data.items():
        if isinstance(data, pd.Series):
            # Get the most recent rate
            latest_rates[currency] = data.iloc[-1]
        else:
            # It's already a single value
            latest_rates[currency] = data

    summary = {
        "last_updated": datetime.now().isoformat(),
        "etf_info": {
            "symbol": "VT",
            "name": info.get("longName", "Vanguard Total World Stock ETF"),
            "expense_ratio": info.get("annualReportExpenseRatio", 0.0007),
            "total_assets": info.get("totalAssets", 0),
        },
        "latest_prices": {},
        "exchange_rates": latest_rates,
    }

    # Calculate prices and statistics for each currency
    for currency in ["USD", "EUR", "GBP", "CHF"]:
        if currency == "USD":
            currency_hist = hist["Close"]
        else:
            if isinstance(forex_data[currency], pd.Series):
                # Align forex data with VT data
                aligned_forex = forex_data[currency].reindex(hist.index, method="ffill")
                # Divide VT price by exchange rate to get price in foreign currency
                currency_hist = hist["Close"] / aligned_forex
            else:
                currency_hist = hist["Close"] / forex_data[currency]

        # Calculate statistics
        latest_price = currency_hist.iloc[-1]
        prev_price = currency_hist.iloc[-2] if len(currency_hist) > 1 else latest_price

        summary["latest_prices"][currency] = {
            "price": float(latest_price),
            "currency": currency,
            "change_1d": float(latest_price - prev_price),
            "change_1d_pct": float((latest_price / prev_price - 1) * 100)
            if prev_price != 0
            else 0,
            "high_52w": float(currency_hist.tail(252).max())
            if len(currency_hist) >= 252
            else float(currency_hist.max()),
            "low_52w": float(currency_hist.tail(252).min())
            if len(currency_hist) >= 252
            else float(currency_hist.min()),
        }

    return summary


def main():
    """Main function to orchestrate data fetching and visualization"""

    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)

    print("Fetching VT data...")
    hist, info = fetch_vt_data()

    print("Fetching historical exchange rates...")
    forex_data = fetch_historical_forex_rates()

    print("Creating chart data...")
    chart_data = create_chart_data(hist, forex_data)

    # Save chart data for JavaScript
    with open("data/chartData.json", "w") as f:
        json.dump(chart_data, f)

    # Create and save summary data
    summary = create_summary_data(hist, info, forex_data)
    with open("data/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("✅ Data fetch complete!")
    print(f"Latest VT price: ${hist['Close'].iloc[-1]:.2f} USD")

    # Display latest prices in all currencies
    for currency, data in summary["latest_prices"].items():
        print(f"  {currency}: {data['price']:.2f}")


if __name__ == "__main__":
    main()
