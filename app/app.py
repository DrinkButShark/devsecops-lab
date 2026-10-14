from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "DevSecOps Lab"

@app.route("/cmd")
def cmd():
    subprocess.run(["ls"])
    return "executed"

if __name__ == "__main__":
    app.run()
