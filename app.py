from flask import Flask, render_template, redirect
import os

app = Flask(__name__)

@app.route('/')
def index():
    files = [f for f in os.listdir('files') if f.endswith('.txt')]
    # Remove the .txt extension for display
    files_display = [os.path.splitext(f)[0] for f in files]
    return render_template('index.html', files=files_display)

@app.route('/file/<filename>')
def show_file(filename):
    filepath = os.path.join('files', filename + '.txt')
    with open(filepath, 'r') as file:
        links = file.readlines()
    return render_template('file.html', links=links)

@app.route('/redirect/<path:url>')
def redirect_url(url):
    return redirect(url, code=302)

if __name__ == '__main__':
    app.run(debug=True)
