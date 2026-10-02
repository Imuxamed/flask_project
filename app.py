from flask import Flask, render_template,request
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    today = datetime.now().strftime("%d.%m.%Y")
    return render_template('index.html', name="Имухамед", date=today)

@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        message = request.form['message']
        return render_template('thanks.html', name=name, message=message)
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
