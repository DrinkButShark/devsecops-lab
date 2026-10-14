from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "DevSecOps Lab"

@app.route("/cmd")
def cmd():
    user_input = "ls"
    subprocess.run(user_input, shell=True)
    return "executed"

app.run(host="0.0.0.0", port=5000)
