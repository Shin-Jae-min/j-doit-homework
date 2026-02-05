
import subprocess
import os
import sys

# Define target directory and script
target_dir = r"C:\Users\sjmem\Downloads\DOITproject\J_Doit_Homework_Bot"
script = "J_Doit_homework_bot.py"

# Path to python executable (current env)
python_exe = sys.executable

print(f"🚀 Launching Bot from: {target_dir}")

try:
    # Run the bot with the correct working directory
    subprocess.run([python_exe, script], cwd=target_dir)
except KeyboardInterrupt:
    print("Bot stopped.")
except Exception as e:
    print(f"Error launching bot: {e}")
