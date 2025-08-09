import os
import streamlit as st
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime, timezone
import pandas as pd
import sqlite3

# Suppress TensorFlow and absl logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Selenium for pagination detection
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, ElementNotInteractableException, JavascriptException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Load environment variables
load_dotenv()
app = FirecrawlApp()

# --- SQLite Setup ---
conn = sqlite3.connect("car_cache.db")
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS cache (
        brand TEXT,
        model TEXT,
        min_mileage INTEGER,            -- NEW: store minimum mileage
        max_mileage INTEGER,
        timestamp TEXT,
        filename TEXT
    )
    """
)
# If an older DB exists without min_mileage, add it (simple migration)
cur.execute("PRAGMA table_info(cache)")
cols = [r[1] for r in cur.fetchall()]
if "min_mileage" not in cols:
    cur.execute("ALTER TABLE cache ADD COLUMN min_mileage INTEGER DEFAULT 0")
    conn.commit()

conn.commit()

# --- Data Models ---
class IndividualCar(BaseModel):
    brand: str
    model: str
    year: int
    mileage: int
    price: float

class CarListing(BaseModel):
    listings: list[IndividualCar]

# --- Helper: detect max pages via Selenium with filter applied ---
def get_max_pages(url: str, max_mileage: int) -> int:
    driver = webdriver.Chrome()
    driver.set_window_size(1920, 1080)  # ensure desktop layout
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    # Try to dismiss any blocking overlays (location prompt, scrims, etc.)
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        driver.execute_script(
            "document.querySelectorAll('.location-model__mask, .location-model, .v-overlay, .v-overlay__scrim, .v-dialog__scrim, .modal-backdrop, .backdrop').forEach(el=>el.remove());"
        )
    except Exception:
        pass

    # Open mileage filter panel (retry + JS fallback)
    toggle_sel = "div.filter__btn-list__item--Mileage > button.filter__btn"
    toggle = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, toggle_sel)))
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, toggle_sel)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
        toggle.click()
    except (ElementClickInterceptedException, ElementNotInteractableException):
        driver.execute_script("arguments[0].click();", toggle)

    # Set only the MAX mileage value (leave MIN at default 0 via URL)
    inputs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input.mod-car-mileage__input-box__input")))
    inputs = [el for el in inputs if el.is_displayed() and el.is_enabled()]

    # Choose the rightmost input on screen as MAX (handles DOM order flips)
    max_el = None
    if inputs:
        with_positions = []
        for el in inputs:
            try:
                left = driver.execute_script("return arguments[0].getBoundingClientRect().left;", el)
            except JavascriptException:
                left = 0
            with_positions.append((left, el))
        with_positions.sort(key=lambda t: t[0])
        max_el = with_positions[-1][1]
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", max_el)
            max_el.clear()
            max_el.send_keys(str(max_mileage))
        except (ElementNotInteractableException, JavascriptException):
            driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles:true}));",
                max_el, str(max_mileage)
            )

    # Click Apply (with JS fallback)
    apply_sel = "button.mod-car-filter__apply-btn"
    apply_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, apply_sel)))
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, apply_sel)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", apply_btn)
        apply_btn.click()
    except (ElementClickInterceptedException, ElementNotInteractableException):
        driver.execute_script("arguments[0].click();", apply_btn)

    # Read pagination (after modal closes/results reload)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav[aria-label='Pagination Navigation']")))
    items = driver.find_elements(By.CSS_SELECTOR, "ul.v-pagination.theme--light li")
    items = [li for li in items if li.is_displayed()]  # visible only
    pages = [int(li.text) for li in items if li.text.isdigit()]
    driver.quit()
    return max(pages) if pages else 1

# --- Streamlit UI ---
st.set_page_config(page_title="Awesome Car Listings", page_icon="🚗")
st.title("Awesome Car Listings")

# Inputs — make them empty by default (NEW)
brand = st.text_input("Brand", value="", placeholder="e.g., Perodua")
model = st.text_input("Model", value="", placeholder="e.g., Myvi")
max_mileage_str = st.text_input("Max Mileage (km)", value="", placeholder="e.g., 50000")

# Parse mileage input safely
def parse_int(s: str):
    s = (s or "").replace(",", "").strip()
    if s == "":
        return None
    try:
        return max(0, int(s))
    except ValueError:
        return None

max_mileage = parse_int(max_mileage_str)

# Validate required inputs (short-circuit to avoid None comparisons)
brand_ok = bool(brand.strip())
model_ok = bool(model.strip())
miles_ok = (max_mileage is not None)
ready = brand_ok and model_ok and miles_ok

# Build URL only when inputs are valid
base_url = None
if ready:
    base_url = (
        f"https://www.carsome.my/buy-car/{brand.lower()}/{model.lower()}?mileage=0,{max_mileage}"
    )
else:
    # Show helpful hints about what is missing/invalid
    if not brand_ok or not model_ok:
        st.info("Enter both Brand and Model to proceed.")
    if max_mileage is None:
        st.info("Enter numeric Max mileage.")

# Pagination detection
if 'max_pages' not in st.session_state:
    st.session_state.max_pages = None
if 'cache_checked' not in st.session_state:  # ensure cache check runs after detection
    st.session_state.cache_checked = False

if 'max_pages' not in st.session_state:
    st.session_state.max_pages = None
if 'cache_checked' not in st.session_state:  # NEW: ensure cache check runs after detection
    st.session_state.cache_checked = False

# Disable until inputs are valid
detect_clicked = st.button('Detect Pages', disabled=not ready, key='btn_detect')
if detect_clicked:
    # Extra safety: guard even if somehow triggered
    if not ready:
        st.warning("Please fill in Brand, Model, and valid Max Mileage first.")
    else:
        with st.spinner("Detecting max pages..."):
            try:
                st.session_state.max_pages = get_max_pages(base_url, max_mileage)
                st.success(f"Max pages: {st.session_state.max_pages}")
            except Exception as e:
                st.error(f"Failed to detect pages: {e}")
                st.session_state.max_pages = None

        # After detection, check cache for this exact query (incl. min mileage)
        cur.execute(
            "SELECT timestamp, filename FROM cache WHERE brand=? AND model=? AND max_mileage=? ORDER BY timestamp DESC LIMIT 1",
            (brand, model, max_mileage)
        )
        cache_row = cur.fetchone()
        st.session_state.cache_checked = True
        if cache_row:
            prev_time, prev_file = cache_row
            st.info(f"Previous run found: {prev_time} — file: {prev_file}")
            if st.button("Load cached results", key="btn_load_cache"):
                try:
                    df_cache = pd.read_csv(prev_file)
                    st.success(f"Loaded {len(df_cache)} cached rows")
                    st.dataframe(df_cache)
                    with open(prev_file, 'rb') as f:
                        st.download_button("📥 Download Cached CSV", data=f, file_name=prev_file, key="btn_dl_cached")
                except Exception as e:
                    st.error(f"Failed to load cached file {prev_file}: {e}")
        else:
            st.info("No previous results found for this exact Brand/Model/Max combination.")

# Pages to scrape control
if st.session_state.max_pages:
    pages_to_scrape = st.number_input(
        "Pages to scrape", min_value=1,
        max_value=st.session_state.max_pages,
        value=st.session_state.max_pages
    )
else:
    pages_to_scrape = 1

# Main Search
# Disable until inputs are valid AND pages detected
search_clicked = st.button('Srape Now', disabled=not (ready and st.session_state.max_pages), key='btn_search')
if search_clicked:
    if not ready:
        st.warning("Please fill in Brand, Model, and valid Max Mileage first.")
        st.stop()
    if not st.session_state.max_pages:
        st.warning("Please click 'Detect Pages' first.")
        st.stop()

    all_listings = []
    st.write(f"Scraping {pages_to_scrape} page(s) for {brand} {model} — up to {max_mileage:,} km")
    for page in range(1, pages_to_scrape+1):
        page_url = f"{base_url}&pageNo={page}"
        try:
            result = app.scrape_url(
                url=page_url,
                formats=["extract"],
                extract={
                    "schema": CarListing.model_json_schema(),
                    "prompt": "Extract car listings",
                    "systemPrompt": "You are a helpful assistant"
                }
            )
        except Exception as e:
            st.error(f"❌ Firecrawl request failed: {e}")
            st.stop()
        listings = result.extract.get('listings', [])
        all_listings.extend(listings)

    # Post-process
    timestamp = datetime.now(timezone.utc)
    df = pd.DataFrame(all_listings)
    df['timestamp'] = timestamp
    if df.empty:
        st.warning("No listings found.")
    else:
        df.insert(0, 'No.', range(1, len(df)+1))
        st.dataframe(df)
        ts = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        fn = f"listings_{brand}_{model}_upto{max_mileage}_{ts}.csv"
        df.to_csv(fn, index=False)
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv_data, file_name=fn, key='btn_dl_new')
        cur.execute(
            "INSERT INTO cache (brand, model, max_mileage, timestamp, filename) VALUES (?,?,?,?,?)",
            (brand, model, max_mileage, ts, fn)
        )
        conn.commit()
