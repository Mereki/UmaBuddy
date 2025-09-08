import sqlite3
# import requests
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException


def scrape_event_data():
    """
    Scrapes a wiki page for event data using Selenium by mapping hidden tooltip
    data to visible event triggers based on matching text content.
    """
    # --- CONFIGURATION ---
    URL = "https://gametora.com/umamusume/characters/100101-special-week"
    CHARACTER_NAME = "Special Week"

    # --- SELENIUM SETUP ---
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    print(f"Scraping data for {CHARACTER_NAME} from {URL} using Selenium...")

    driver = None
    try:
        driver_path = ChromeDriverManager().install()
        print(f"Using ChromeDriver at path: {driver_path}")
        service = ChromeService(driver_path)

        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(URL)

        print("Waiting for the basic page structure (body) to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("Basic page structure loaded.")

        print("Finding all event triggers to click them...")
        event_trigger_elements = driver.find_elements(By.CSS_SELECTOR, 'div[class*="compatibility_viewer_item__"]')
        print(f"Found {len(event_trigger_elements)} triggers. Clicking each one to load its tooltip...")

        for element in event_trigger_elements:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.1)
            driver.execute_script("arguments[0].click();", element)
            time.sleep(0.2)

        print("Finished clicking. Grabbing final page source.")
        page_source = driver.page_source

        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("Saved page content to debug_page.html for inspection.")

    except TimeoutException:
        print("\n--- A SELENIUM TIMEOUT ERROR OCCURRED ---")
        return []
    except WebDriverException as e:
        print(f"\n--- A SELENIUM WEBDRIVER ERROR OCCURRED ---\n{e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during Selenium operation: {e}")
        return []
    finally:
        if driver:
            driver.quit()

    soup = BeautifulSoup(page_source, "html.parser")
    scraped_data = []

    tooltips_map = {}
    all_tooltips = soup.select('div.tippy-box')

    for tooltip in all_tooltips:
        content_area = tooltip.find('div', class_='tippy-content')
        if not content_area:
            continue

        temp_content = BeautifulSoup(str(content_area), 'html.parser')
        table_in_temp = temp_content.find('table')
        if table_in_temp:
            table_in_temp.decompose()

        title_text = temp_content.get_text(strip=True)
        cleaned_title = re.sub(r'[^a-zA-Z0-9\s]', '', title_text).strip()

        if cleaned_title:
            tooltips_map[cleaned_title] = tooltip

    print(f"Found and mapped {len(tooltips_map)} hidden tooltip data blocks.")
    if not tooltips_map:
        print("CRITICAL FAILURE: Could not find any tooltips to build the data map.")
        return []

    event_triggers = soup.select('div[class*="compatibility_viewer_item__"]')
    if not event_triggers:
        print("Could not find any event trigger items. The class name 'compatibility_viewer_item__' may have changed.")
        return []

    print(f"Found {len(event_triggers)} potential event triggers to process.")

    for trigger in event_triggers:
        trigger_title = trigger.get_text(strip=True)
        cleaned_trigger_title = re.sub(r'[^a-zA-Z0-9\s]', '', trigger_title).strip()

        matched_tooltip = tooltips_map.get(cleaned_trigger_title)

        if matched_tooltip:
            table = matched_tooltip.find("table")
            if not table:
                continue

            # THE FIX: Process all <tr> rows, not skipping the first one.
            option_rows = table.find_all("tr")

            for i, row in enumerate(option_rows):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                choice_text = cells[0].get_text(strip=True)
                outcome_text = cells[1].get_text(strip=True).replace('\n', ' ')
                full_outcome = f"{choice_text} -> {outcome_text}"
                option_number = i + 1

                scraped_data.append(
                    (CHARACTER_NAME, cleaned_trigger_title, option_number, full_outcome)
                )
        else:
            pass

    print(f"\nSuccessfully scraped {len(scraped_data)} event outcomes.")
    return scraped_data

# --- DATABASE CREATION ---

event_data = scrape_event_data()

if event_data:
    con = None
    try:
        con = sqlite3.connect("umamusume_events.db")
        cur = con.cursor()
        print("Successfully connected to database.")
        cur.execute("DROP TABLE IF EXISTS events")
        # THE FIX: Wrap all column names in double quotes to prevent syntax errors.
        cur.execute('''
            CREATE TABLE events (
                "character_name" TEXT NOT NULL,
                "event_title" TEXT NOT NULL,
                "option_number" INTEGER NOT NULL,
                "outcome_description" TEXT NOT NULL
            )
        ''')
        cur.executemany("INSERT INTO events VALUES (?, ?, ?, ?)", event_data)
        con.commit()
        print(f"Inserted {len(event_data)} records into the database.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if con:
            con.close()
            print("Database connection closed.")
else:
    print("No data was scraped, database was not created.")

