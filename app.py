import os
import time
import logging
import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify

# Configure logging to see errors in the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def gplinks_bypass(url: str):
    """
    Attempts to bypass GPLinks using cloudscraper.
    Returns the bypassed URL or raises an Exception.
    """
    # 1. Setup the client with browser-like headers
    client = cloudscraper.create_scraper(allow_brotli=False)
    
    # Standard headers to mimic a real browser visit
    client.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'Referer': 'https://gplinks.co/' 
    })

    domain = "https://gplinks.co/"
    
    # 2. Initial Handshake (Get Video ID)
    logger.info(f"Processing: {url}")
    try:
        # We disable redirects to catch the 'Location' header
        init_resp = client.get(url, allow_redirects=False)
        
        if 'Location' not in init_resp.headers:
            raise ValueError("Invalid GPLink or no redirect found. Link might be dead.")
            
        vid = init_resp.headers["Location"].split("=")[-1]
        final_url = f"{url}/?{vid}"
        logger.info(f"Video ID extracted: {vid}")

    except Exception as e:
        logger.error(f"Handshake Failed: {e}")
        return f"Error: Could not verify link. {str(e)}"

    # 3. Fetch the Page & Form Data
    try:
        response = client.get(final_url, allow_redirects=False)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find the form with ID 'go-link'
        form = soup.find(id="go-link")
        if not form:
            raise ValueError("Could not find the bypass form. Cloudflare might have blocked the bot.")
            
        inputs = form.find_all(name="input")
        data = {inp.get('name'): inp.get('value') for inp in inputs}
        logger.info("Form data extracted successfully.")

    except Exception as e:
        logger.error(f"Scraping Failed: {e}")
        return f"Error: Failed to parse page. {str(e)}"

    # 4. The Mandatory Wait (Server-side sleep)
    # The user waits on the loading screen while this happens
    time.sleep(10)

    # 5. Final POST Request
    try:
        headers = {"x-requested-with": "XMLHttpRequest"}
        # Some GPLinks versions require the Referer to be set to the previous page
        client.headers.update({'Referer': final_url})
        
        post_resp = client.post(domain + "links/go", data=data, headers=headers)
        json_data = post_resp.json()

        if "url" in json_data:
            return json_data["url"]
        else:
            return f"Error: Server returned unexpected data: {json_data}"

    except Exception as e:
        logger.error(f"Final Request Failed: {e}")
        return f"Error: Failed final step. {str(e)}"


@app.route('/', methods=['GET', 'POST'])
def home():
    result = None
    error = None
    
    if request.method == 'POST':
        url = request.form.get('url')
        if url and "gplinks" in url:
            try:
                result_url = gplinks_bypass(url)
                if result_url.startswith("Error"):
                    error = result_url
                else:
                    result = result_url
            except Exception as e:
                error = f"System Error: {str(e)}"
        else:
            error = "Please enter a valid GPLinks URL."

    return render_template('index.html', result=result, error=error)

if __name__ == '__main__':
    # Use the PORT environment variable for cloud hosting
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
