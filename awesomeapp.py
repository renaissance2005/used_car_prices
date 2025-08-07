import os
import streamlit as st
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime, timezone
from urllib.parse import quote_plus
import pandas as pd
import sqlite3

# Suppress TensorFlow and absl logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Selenium for pagination detection
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()
app = FirecrawlApp()

# --- SQLite Setup ---
conn = sqlite3.connect("car_cache.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS cache (
    brand TEXT,
    model TEXT,
    max_mileage INTEGER,
    timestamp TEXT,
    filename TEXT
)
""")
conn.commit()

# --- Data Models ---
class IndividualCar(BaseModel):
    brand: str = Field(description="The brand of the car")
    model: str = Field(description="The model of the car")
    year: int = Field(description="Year manufactured")
    mileage: int = Field(description="Mileage in km")
    price: float = Field(description="Price in RM")

class CarListing(BaseModel):
    listings: list[IndividualCar] = Field(description="List of car listings")

# --- Helper: detect max pages via Selenium ---
def get_max_pages(url: str) -> int:
    driver = webdriver.Chrome()
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav[aria-label='Pagination Navigation']")))
    pagination_elements = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.v-pagination.theme--light li"))
    )
    page_numbers = [int(el.text) for el in pagination_elements if el.text.isdigit()]
    max_page = max(page_numbers) if page_numbers else 1
    driver.quit()
    return max_page

# --- Streamlit UI ---
st.set_page_config(page_title="Awesome Car Listings", page_icon="🚗")
st.title("Awesome Car Listings")

# Inputs
brand = st.text_input("Brand", value="Perodua")
model = st.text_input("Model", value="Myvi")
max_mileage = st.number_input("Max Mileage (km)", min_value=0, value=50000, step=1000)
base_url = f"https://www.carsome.my/buy-car/{brand.lower()}/{model.lower()}?mileage=0,{int(max_mileage)}"

# Cache lookup
cur.execute(
    "SELECT timestamp, filename FROM cache WHERE brand=? AND model=? AND max_mileage=? "
    "ORDER BY timestamp DESC LIMIT 1",
    (brand, model, max_mileage)
)
cache_row = cur.fetchone()

def display_cached():
    prev_time, prev_file = cache_row
    st.markdown(f"""
    <div style="border:1px solid #7abaff;background-color:#e6f4ff;padding:16px;border-radius:8px;margin-bottom:1em">
      <b>Previous extraction for:</b> {brand} {model}<br>
      <b>Max mileage:</b> {max_mileage:,} km<br>
      <b>Last extracted:</b> {prev_time}<br>
      <b>Results saved in:</b> <code>{prev_file}</code><br>
      <i>The data below is loaded from cache. Press <b>Search</b> to fetch new results.</i>
    </div>
    """, unsafe_allow_html=True)
    try:
        df_cached = pd.read_csv(prev_file)
        st.success(f"Displaying {len(df_cached)} cached listings")
        st.dataframe(df_cached)
        # Download button for cache
        with open(prev_file, 'rb') as f:
            st.download_button("📥 Download Cached CSV", data=f, file_name=prev_file, mime="text/csv")
    except Exception as e:
        st.error(f"Failed to load cached file {prev_file}: {e}")

# Show cache immediately if exists
if cache_row:
    display_cached()

# Pagination detection
if 'max_pages' not in st.session_state:
    st.session_state.max_pages = None
if st.button('Detect Pages'):
    with st.spinner('Detecting max pages...'):
        try:
            st.session_state.max_pages = get_max_pages(base_url)
        except Exception as e:
            st.error(f"Failed to detect pages: {e}")

if st.session_state.max_pages:
    st.info(f"Max pages available: {st.session_state.max_pages}")
    pages_to_scrape = st.number_input(
        "Pages to scrape", min_value=1,
        max_value=st.session_state.max_pages,
        value=st.session_state.max_pages
    )
else:
    pages_to_scrape = 1

# Search action
if st.button('Search'):
    all_listings = []
    st.write(f"🔍 Scraping {pages_to_scrape} page(s) for: {brand} {model} under {max_mileage:,} km")
    with st.spinner("Running Firecrawl across pages..."):
        try:
            for page in range(1, pages_to_scrape + 1):
                page_url = f"{base_url}&pageNo={page}"
                result = app.scrape_url(
                    url=page_url,
                    formats=["extract"],
                    extract={
                        "schema": CarListing.model_json_schema(),
                        "prompt": "Extract used car listings (brand, model, year, mileage, price)",
                        "systemPrompt": "You are a helpful assistant extracting used car data"
                    }
                )
                all_listings.extend(result.extract.get('listings', []))
            # Process
            timestamp = datetime.now(timezone.utc)
            df = pd.DataFrame(all_listings)
            df['timestamp'] = timestamp
            if df.empty:
                st.warning("No results found matching your criteria.")
            else:
                df.insert(0, 'No.', range(1, len(df) + 1))
                st.success(f"Found {len(df)} total listings")
                st.dataframe(df.rename_axis(None, axis=1))
                # Export CSV
                ts = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
                csv_fn = f"car_price_updated_{ts}.csv"
                csv_data = df.to_csv(index=False).encode('utf-8')
                # Persist CSV to disk for caching and future loads
                df.to_csv(csv_fn, index=False)
                st.download_button("📥 Download CSV", data=csv_data, file_name=csv_fn, mime='text/csv')
                # Cache
                cur.execute(
                    "INSERT INTO cache (brand, model, max_mileage, timestamp, filename) VALUES (?, ?, ?, ?, ?)",
                    (brand, model, max_mileage, ts, csv_fn)
                )
                conn.commit()
        except Exception as e:
            st.error(f"❌ Scraping failed. {e}")
            st.info(
                "This error may be due to a missing or changed selector on the website. "
                "Try inspecting the element with your browser and update the selector if needed."
            )
