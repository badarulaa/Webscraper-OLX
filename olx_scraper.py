from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import pandas as pd
from datetime import datetime
import os

class OLXScraper:
    def __init__(self, url):
        self.url = url
        self.setup_driver()
        self.data = []
        self.progress = {
            "status": "Not started",
            "current_page": 0,
            "total_pages": 0,
            "scraped_links": 0,
            "total_links": 0,
            "filename": None
        }

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument('--ignore-certificate-errors')  # Ignore SSL certificate errors
        chrome_options.add_argument('--allow-running-insecure-content')  # Allow insecure content
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        service = Service('chromedriver.exe')  # Update this path
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })

    def insert_location_and_search(self, location):
        try:
            print(f"Inserting location: {location}")
            # Wait for the location input box to be visible and clickable
            location_box = WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input._1dasd"))
            )

            location_box.clear()
            location_box.send_keys(location)

            # Select from the dropdown after entering location
            dropdown_item = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-aut-id='locationItem']"))
            )
            dropdown_item.click()

            # Click the search button
            search_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-aut-id='btnSearch']"))
            )
            search_button.click()
            print("Location selected and search triggered.")

        except TimeoutException:
            print("Timed out waiting for the location input, dropdown, or search button.")
        except Exception as e:
            print(f"Error inserting the location or triggering the search: {e}")

    def scrape_all_links_on_page(self):
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-aut-id='itemBox']"))
            )
            item_links = self.driver.find_elements(By.CSS_SELECTOR, "li[data-aut-id='itemBox'] a")
            return [link.get_attribute('href') for link in item_links]
        except TimeoutException:
            print("Timed out waiting for the search results.")
            return []
        except Exception as e:
            print(f"An error occurred while scraping links: {e}")
            return []

    def scrape_data_from_link(self, href):
        try:
            self.driver.get(href)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-aut-id='itemTitle']"))
            )

            title = self.driver.find_element(By.CSS_SELECTOR, "[data-aut-id='itemTitle']").text
            price = self.driver.find_element(By.CSS_SELECTOR, "[data-aut-id='itemPrice']").text

            # These fields might not always be present, so we'll use a try-except block
            try:
                fuel = self.driver.find_element(By.CSS_SELECTOR, "[data-aut-id='itemAttribute_fuel']").text
            except NoSuchElementException:
                fuel = "N/A"

            try:
                km = self.driver.find_element(By.CSS_SELECTOR, "[data-aut-id='itemAttribute_mileage']").text
            except NoSuchElementException:
                km = "N/A"

            try:
                transmission = self.driver.find_element(By.CSS_SELECTOR, "[data-aut-id='itemAttribute_transmission']").text
            except NoSuchElementException:
                transmission = "N/A"

            try:
                subtitle = self.driver.find_element(By.CLASS_NAME, "BxCeR").text
            except NoSuchElementException:
                subtitle = "N/A"

            try:
                lokasi_elements = self.driver.find_elements(By.CLASS_NAME, "_3VRXh")
                lokasi = lokasi_elements[1].text if len(lokasi_elements) > 1 else "N/A"
            except IndexError:
                lokasi = "N/A"

            self.data.append({
                "Title": title,
                "SubBrand": subtitle,
                "Lokasi": lokasi,
                "Price": price,
                "Fuel": fuel,
                "KM": km,
                "Transmission": transmission,
                "URL": href
            })

            print(f"Scraped: {title}")

        except Exception as e:
            print(f"Error scraping {href}: {e}")

    #load more pages
    def load_more_pages(self):
        try:
            load_more_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-aut-id='btnLoadMore']"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
            time.sleep(1)  # Give some time for any overlays to disappear
            load_more_button.click()
            time.sleep(2)  # Wait for the new content to load
            return True
        except TimeoutException:
            print("No more pages to load or timed out.")
            return False
        except Exception as e:
            print(f"Error loading more pages: {e}")
            return False

    def export_to_excel(self):
        if self.data:
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"olx_data_{timestamp}.xlsx"

            df = pd.DataFrame(self.data)
            df.to_excel(filename, index=False)
            print(f"Data successfully exported to {filename}")
            return filename
        else:
            print("No data to export.")
            return None

    def run(self, location, num_pages):
        try:
            self.progress["status"] = "Initializing"
            self.progress["total_pages"] = num_pages

            print(f"Navigating to {self.url}")
            self.driver.get(self.url)

            print("Page loaded. Now inserting location and triggering search.")
            self.insert_location_and_search(location)

            total_links = set()  # Use a set to store unique links
            for page in range(num_pages):
                self.progress["status"] = f"Scraping page {page + 1}"
                self.progress["current_page"] = page + 1

                print(f"Scraping links from page {page + 1}...")
                links = self.scrape_all_links_on_page()
                new_links = set(links) - total_links  # Only add new, unique links
                total_links.update(new_links)

                self.progress["scraped_links"] = len(total_links)
                print(f"Found {len(new_links)} new links on page {page + 1}. Total unique links so far: {len(total_links)}")

                if page < num_pages - 1:
                    if not self.load_more_pages():
                        print("No more pages to load. Stopping scraping.")
                        break

            self.progress["status"] = "Scraping individual listings"
            self.progress["total_links"] = len(total_links)
            print(f"Scraping data from {len(total_links)} unique links...")

            for index, href in enumerate(total_links):
                self.scrape_data_from_link(href)
                self.progress["scraped_links"] = index + 1

            self.progress["status"] = "Exporting data"
            filename = self.export_to_excel()
            if filename:
                self.progress["filename"] = os.path.basename(filename)

            self.progress["status"] = "Completed"
            return filename
        except Exception as e:
            self.progress["status"] = f"Error: {str(e)}"
            print(f"An error occurred: {str(e)}")
            return None
        finally:
            self.driver.quit()

if __name__ == "__main__":
    url = "https://www.olx.co.id/mobil-bekas_c198"
    location = input("Enter the location you want to search: ")
    num_pages = int(input("Enter the number of pages to scrape: "))
    scraper = OLXScraper(url)
    scraper.run(location, num_pages)