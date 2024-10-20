import os
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from olx_scraper import OLXScraper
import threading

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = '/tmp/scraped_data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

scraper = None
scrape_thread = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global scraper, scrape_thread
    if request.method == 'POST':
        location = request.form['location']
        num_pages = int(request.form['num_pages'])

        scraper = OLXScraper("https://www.olx.co.id/mobil-bekas_c198")
        scrape_thread = threading.Thread(target=run_scraper, args=(location, num_pages))
        scrape_thread.start()

        return "Scraping started. Check progress at /progress"

    return render_template('index.html')

def run_scraper(location, num_pages):
    global scraper
    filename = scraper.run(location, num_pages)
    if filename:
        # Move the file to the upload folder
        safe_filename = secure_filename(filename)
        os.rename(filename, os.path.join(app.config['UPLOAD_FOLDER'], safe_filename))
        scraper.progress['filename'] = safe_filename

@app.route('/progress')
def progress():
    global scraper
    if scraper:
        return jsonify(scraper.progress)
    return jsonify({"status": "No scraping in progress"})

@app.route('/result')
def result():
    global scraper, scrape_thread
    if scraper and not scrape_thread.is_alive():
        if scraper.progress["status"] == "Completed":
            return send_file(os.path.join(app.config['UPLOAD_FOLDER'], scraper.progress["filename"]), as_attachment=True)
        else:
            return "Scraping failed. Please try again."
    return "Scraping still in progress or hasn't started."

@app.route('/_ah/health')
def health_check():
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)