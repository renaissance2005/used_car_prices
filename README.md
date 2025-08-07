# 🚗 Awesome Car Listings Scraper

> **Automate used car data extraction from [Carsome.my](https://www.carsome.my) with an intuitive, interactive dashboard!**  
> Built for rapid car market analysis, data collection, and research.

---

## 🌟 Project Overview

This project is a one-stop solution for scraping used car listings from Carsome.my, Malaysia’s largest car marketplace.  
It combines Streamlit’s visual power, Firecrawl’s structured web scraping, and Playwright’s browser automation to extract car data **accurately and efficiently**, even across multiple paginated result pages.

---

## 🎯 Objectives

- **Automate** extraction of car listings for any given brand/model, including custom filters (like max mileage).
- Provide an **interactive GUI** for users to choose their criteria, preview results, and download as CSV.
- **Accurately determine the number of pages** of results before scraping, preventing missed data.
- Enable **data-driven decisions** for car buyers, sellers, analysts, and researchers.

---

## 💡 Benefits

- **No manual copy-paste:** Automatically gather hundreds of listings in seconds.
- **Filter by criteria:** Choose your preferred brand, model, and mileage limit.
- **Accurate page handling:** Scrape as many pages as you want, without duplicates or missing listings.
- **Downloadable CSV:** Instantly export data for further analysis in Excel or any BI tool.
- **User-friendly:** No coding required – just fill in your search and click.

---

## 🖥️ Application Features

- **🔎 Smart Car Search:** Enter Brand, Model, and Max Mileage – see available listings in real time.
- **🧠 Pagination Awareness:** The app uses Playwright to interact with Carsome’s filters and extract the exact number of result pages.
- **🎛️ Page Selection:** Choose how many pages to scrape (e.g., just top results or the whole set).
- **📋 Data Preview:** Browse results in a neat, numbered table within Streamlit.
- **📥 CSV Download:** Download your results with a single click, timestamped for easy record-keeping.
- **⚠️ Robust Error Handling:** Handles missing selectors, network hiccups, and site changes gracefully.
- **📈 Designed for Analytics:** Results are structured for use in Excel, Power BI, or Python.

---
## 🛠️ Program Flow  

1. 🛠️ **Environment & Setup:** Load environment variables, suppress logs, initialize Firecrawl, and set up SQLite cache.  
2. 🔌 **Initialization:** Instantiate Streamlit page configuration and title.  
3. 🏷️ **User Inputs & URL Construction:** Collect Brand, Model, and Max Mileage; build Carsome search URL.  
4. 💾 **Cache Lookup:** Query SQLite cache for previous results; if found, display cached CSV with download button.  
5. 🌐 **Pagination Detection:** Optional Selenium step to detect `max_pages` by inspecting pagination controls.  
6. 🔄 **Page Selection:** Allow users to choose how many pages to scrape (1..max_pages).  
7. 🕸️ **Scraping Loop:** Iterate over selected pages, call Firecrawl’s `scrape_url` with Pydantic schema, and accumulate listings.  
8. 🔍 **Post-Processing & Display:** Attach timestamps, create DataFrame, add row numbers, and show results in Streamlit.  
9. 💾 **Export & Cache:** Save new CSV locally, provide download button, and insert record into SQLite cache.  
10. 🚨 **Error Handling:** Wrap interactions in try/except to surface meaningful UI errors for selector changes or network issues.

## ⚙️ Technology Stack

| Tool/Library       | Purpose                              |
|--------------------|--------------------------------------|
| **Python 3.9+**    | Main programming language            |
| **Streamlit**      | User interface & dashboard           |
| **Selenium**     | Browser automation for pagination    |
| **Firecrawl**      | Headless web scraping (API or SDK)   |
| **Pandas**         | Data structuring & CSV export        |
| **Pydantic**       | Data model validation                |
| **dotenv**         | Manage environment variables         |

---

## 🛠️ Challenges

- **Dynamic Website Structure:** Carsome’s filters and pagination are built with modern JavaScript, making static scraping unreliable.
- **Hidden Page Counts:** The number of pages is only visible after filter criteria are applied and "Apply" is pressed.
- **Selector Fragility:** CSS selectors may change, potentially breaking scraping scripts.
- **Performance:** Large result sets need to be processed efficiently and displayed to the user.

---

## 🚀 Solutions

- **Playwright for Page Detection:** Uses Playwright to interact with the site like a real user, ensuring accurate page count extraction before scraping.
- **Firecrawl for Scraping:** Keeps scraping decoupled from page navigation for maximum flexibility and error recovery.
- **Interactive UI:** Streamlit’s sidebar and widgets make it easy for users to try different search settings.
- **Robust Error Handling:** All critical actions are wrapped with clear messages for troubleshooting.

---

## ⚠️ Limitations and Future Improvements

- **Selector Stability:** If Carsome changes their HTML structure, selectors may need updates (especially for buttons and input fields).
- **Rate Limits:** High-volume scraping may trigger website anti-bot mechanisms – always respect [Carsome's Terms](https://www.carsome.my/terms).
- **No True Modal in Streamlit:** User interaction for cache/csv data selection uses alerts instead of modal popups.
- **Multi-threaded Scraping:** Currently, scraping is sequential (one page at a time). Future updates may add concurrency for faster results.
- **Scheduled/Automated Runs:** Adding scheduler integration (e.g., cron) would enable regular, automatic data updates.

---

## 💬 Contact / Contribution

- Pull requests and suggestions are welcome!  
- For bug reports, open an issue on [GitHub](https://github.com/your-repo-url).

---

**Enjoy fast, flexible car data scraping for research, pricing, or buying decisions!**  
*Built with ❤️ for the Malaysian car market.*

