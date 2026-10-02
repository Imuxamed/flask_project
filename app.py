from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    today = datetime.now().strftime("%d.%m.%Y")
    return render_template('index.html', name="Имухамед", date=today)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
