import json
import os
from dotenv import dotenv_values

toml_lines = []

# 1. AZURE
# Read env vars safely
env = dotenv_values(".env")
for k, v in env.items():
    # Only include the specific keys we need for the app
    if k in ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]: 
        if v:
            toml_lines.append(f'{k} = {json.dumps(v)}')

toml_lines.append("")
toml_lines.append("[gcp_service_account]")

# 2. GCP
if os.path.exists("service_account.json"):
    with open("service_account.json", encoding='utf-8') as f:
        try:
            d = json.load(f)
            for k, v in d.items():
                toml_lines.append(f'{k} = {json.dumps(v)}')
        except Exception as e:
            print(f"Error parsing json: {e}")

with open("streamlit_secrets.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(toml_lines))
    
print("Generated streamlit_secrets.txt successfully.")
