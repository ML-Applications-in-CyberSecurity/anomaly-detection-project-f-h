import socket
import json
import pandas as pd
import joblib

HOST = 'localhost'
PORT = 9999

model = joblib.load("anomaly_model.joblib")
TOGETHER_API_KEY = "your_api_key_here"
TOGETHER_MODEL = "togethercomputer/llama-2-70b-chat"


def pre_process_data(data):
    # Convert data to DataFrame for model prediction
    df = pd.DataFrame([data])
    df = pd.get_dummies(df, columns=["protocol"], drop_first=True)

    # اطمینان از وجود ستون protocol_UDP حتی اگر داده TCP باشد
    if "protocol_UDP" not in df.columns:
        df["protocol_UDP"] = False
    return df

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    buffer = ""
    print("Client connected to server.\n")

    while True:
        chunk = s.recv(1024).decode()
        if not chunk:
            break
        buffer += chunk

        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            try:
                data = json.loads(line)
                print(f'Data Received:\n{data}\n')

                df_processed = pre_process_data(data)
                prediction = model.predict(df_processed)[0]

                if prediction == -1:
                    print("🚨 Anomaly detected!")

                    # مرحله ارسال به LLM
                    messages = [
                        {"role": "system", "content": "You are an assistant for labeling cybersecurity anomalies."},
                        {"role": "user", "content": f"Sensor reading: {json.dumps(data)}\nDescribe the type of anomaly and suggest a possible cause."}
                    ]

                    response = httpx.post(
                        "https://api.together.xyz/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {TOGETHER_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": TOGETHER_MODEL,
                            "messages": messages,
                            "temperature": 0.7
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        message = result["choices"][0]["message"]["content"]
                        print(f"\n🚨 LLM Response:\n{message}\n")
                    else:
                        print("❌ Error from LLM API:", response.text)
                else:
                    print("✅ Normal data.\n")

            except json.JSONDecodeError:
                print("Error decoding JSON.")
