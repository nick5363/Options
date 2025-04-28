# app.py
import websocket
import json
import pandas as pd
import threading
import gradio as gr
from datetime import datetime
import os

columns = ["Time", "Symbol", "Buy/Sell", "Strike", "Call/Put", "Expiry", "Premium ($)", "Type"]
df = pd.DataFrame(columns=columns)

csv_path = "/tmp/optionstrat_flow.csv"
if not os.path.exists(csv_path):
    df.to_csv(csv_path, index=False)

def on_message(ws, message):
    global df
    try:
        data = json.loads(message)
        if isinstance(data, dict) and "symbol" in data:
            symbol = data.get("symbol", "")
            strike = data.get("strikePrice", "")
            expiry_raw = data.get("expiration", "")
            expiry = datetime.strptime(expiry_raw, "%Y-%m-%d").strftime("%b %d") if expiry_raw else ""
            opt_type = data.get("optionType", "")
            price = data.get("price", 0)
            quantity = data.get("quantity", 0)
            premium = round(price * quantity * 100)
            side = data.get("side", "").capitalize()
            action_type = data.get("actionType", "")
            time_now = datetime.utcnow().strftime('%H:%M:%S')

            new_row = {
                "Time": time_now,
                "Symbol": symbol,
                "Buy/Sell": side,
                "Strike": strike,
                "Call/Put": opt_type,
                "Expiry": expiry,
                "Premium ($)": f"${premium:,}",
                "Type": action_type.upper()
            }
            df.loc[len(df)] = new_row
            df.to_csv(csv_path, index=False)
    except Exception as e:
        print("Error parsing message:", e)

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Connection closed.")

def on_open(ws):
    print("Connected to OptionStrat WebSocket.")

def run_websocket():
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        "wss://stream.optionstrat.com/flow/live",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()

def update_table():
    global df
    return df.tail(50)

def download_file():
    return gr.File.update(value=csv_path)

threading.Thread(target=run_websocket, daemon=True).start()

with gr.Blocks() as app:
    gr.Markdown("# OptionStrat Unusual Options Flow (Real-time Style)")
    filter_symbol = gr.Textbox(label="Filter Symbol (leave blank to show all)", placeholder="e.g., AAPL, TSLA...")

    table = gr.Dataframe(update_table, every=10, label="Latest Flow", wrap=True, interactive=True)
    selected_detail = gr.Markdown("**Select a flow to view details.**")

    gr.Markdown("## Download Flow Data")
    download_btn = gr.Button("Download Latest CSV")
    file_output = gr.File()

    download_btn.click(fn=download_file, inputs=[], outputs=file_output)

app.launch(server_name="0.0.0.0", server_port=7860)