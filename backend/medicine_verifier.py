import streamlit as st
from PIL import Image
import os
from shutil import which
try:
    from pyzbar.pyzbar import decode
    BARCODE_SUPPORTED = True
except Exception:
    decode = None
    BARCODE_SUPPORTED = False
import pytesseract
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
import re

# Configure Tesseract path in a flexible way.
TESSERACT_PATHS = [
    os.getenv("TESSERACT_CMD", "").strip(),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    which("tesseract") or "",
]
for candidate in TESSERACT_PATHS:
    if candidate and os.path.exists(candidate):
        pytesseract.pytesseract.tesseract_cmd = candidate
        break

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Medicine Verifier",
    page_icon="💊",
    layout="centered"
)

st.title("💊 Medicine Verifier")
st.caption("Scan or upload your medicine / pharmacy bill to verify safety, recalls, interactions and price.")
st.markdown("Looking for hospital recommendations? Open **Hospital Finder** at [http://localhost:5173](http://localhost:5173).")

# ─────────────────────────────────────────
# STEP 1 — INPUT
# ─────────────────────────────────────────
st.markdown("### Step 1: Provide your medicine or bill")

option = st.radio(
    "Choose input method:",
    ["📷 Take Photo (camera)", "📁 Upload Image or PDF"]
)

image_input = None
pdf_input   = None

if option == "📷 Take Photo (camera)":
    image_input = st.camera_input("Point camera at medicine strip, box, or bill")

elif option == "📁 Upload Image or PDF":
    uploaded = st.file_uploader(
        "Upload medicine image or pharmacy bill (JPG, PNG, PDF)",
        type=["jpg", "jpeg", "png", "pdf"]
    )
    if uploaded:
        if uploaded.type == "application/pdf":
            pdf_input = uploaded
        else:
            image_input = uploaded


# ─────────────────────────────────────────
# HELPER: Extract text from PDF
# ─────────────────────────────────────────
def extract_text_from_pdf(pdf_file) -> str:
    pdf_bytes = pdf_file.getvalue()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text


# ─────────────────────────────────────────
# HELPER: Extract text from image (barcode → OCR)
# ─────────────────────────────────────────
def extract_from_image(image_file):
    img = Image.open(image_file)
    barcode_data = None
    ocr_text     = ""

    # Try barcode first
    if BARCODE_SUPPORTED:
        barcodes = decode(img)
        if barcodes:
            barcode_data = barcodes[0].data.decode("utf-8")

    # Always run OCR too (for name, MRP, batch etc.)
    try:
        ocr_text = pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError:
        st.error(
            "Tesseract OCR engine is not installed or not in your system PATH. \n\n"
            "**How to fix:**\n"
            "1. Download and install Tesseract-OCR for Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Restart your terminal & the application.\n"
            "3. If it still doesn't work, set environment variable `TESSERACT_CMD` to your `tesseract.exe` path."
        )

    return barcode_data, ocr_text


# ─────────────────────────────────────────
# HELPER: Medicine Name Cleaning & FDA mapping
# ─────────────────────────────────────────
BRAND_TO_GENERIC = {
    "rantac":       "ranitidine",
    "crocin":       "paracetamol",
    "dolo":         "paracetamol",
    "combiflam":    "ibuprofen",
    "augmentin":    "amoxicillin",
    "azithral":     "azithromycin",
    "pan":          "pantoprazole",
    "omez":         "omeprazole",
    "metpure":      "metoprolol",
    "glycomet":     "metformin",
}

def clean_medicine_name(name: str) -> str:
    # Remove Tab/Cap/Syp/Inj prefixes
    name = re.sub(r'^(Tab|Cap|Syp|Inj|Syr|Oint)\.?\s+', '', name, flags=re.IGNORECASE)
    # Remove trailing numbers (quantities)
    name = re.sub(r'\s+\d+$', '', name.strip())
    return name.strip()

def get_generic_name(brand_name: str) -> str:
    key = brand_name.lower().split()[0]
    return BRAND_TO_GENERIC.get(key, key)

def is_valid_medicine(name: str) -> bool:
    # Too short
    if len(name) < 3:  # Changed to 3 to allow short names
        return False
    # Mostly numbers
    if sum(c.isdigit() for c in name) > len(name) * 0.4:
        return False
    # Known noise patterns - removed 'fibro' and 'sm' because SM Fibro is a real prescription
    noise = ["big", "pre"]
    if any(n in name.lower() for n in noise):
        return False
    return True

# ─────────────────────────────────────────
# HELPER: Parse medicine names from raw text
# ─────────────────────────────────────────
def parse_medicine_names(text: str) -> list:
    """
    Looks for capitalized words + dose patterns like:
    Paracetamol 500mg, Metformin 850mg, Atorvastatin 10mg
    Also grabs common prescription prefixes like Tab, Cap, Syr.
    """
    names = []
    
    # 1. Match Name + mg/ml/mcg (e.g. Paracetamol 500mg)
    pattern1 = r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(\d+\s?(?:mg|mcg|ml|g|IU))\b'
    for m in re.findall(pattern1, text):
        names.append(f"{m[0]} {m[1]}")

    # 2. Match Tab/Cap/Syr prefixes (e.g. CAP SM FIBRO)
    # Extracts the prefix and up to 3 following words, stopping at symbols like '-'
    pattern2 = r'\b(?:TAB|CAP|SYR|INJ|OINT|DROPS?|Tab|Cap|Syr|Inj|Oint|Drop|tab|cap)\.?\s+([A-Z0-9a-z]+(?:\s+[A-Z0-9a-z]+){0,2})'
    for m in re.findall(pattern2, text):
        clean_name = m.strip()
        names.append(clean_name)

    # Deduplicate and Clean
    seen = set()
    unique = []
    for n in names:
        n_clean = clean_medicine_name(n)
        if not is_valid_medicine(n_clean):
            continue
            
        dedup_key = n_clean.lower().replace(" ", "")
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique.append(n_clean.title()) # Title case for nicer display

    return unique if unique else []


# ─────────────────────────────────────────
# HELPER: Extract MRP from text
# ─────────────────────────────────────────
def extract_mrp(text: str) -> dict:
    results = {}
    # Pattern: MRP ₹ 45.00 or MRP: 45 or M.R.P 120
    pattern = r'(?:M\.?R\.?P\.?|mrp)[:\s₹Rs\.]*(\d+(?:\.\d{1,2})?)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        results["mrp_values_found"] = [float(m) for m in matches]
    return results


# ─────────────────────────────────────────
# HELPER: CDSCO Recall Check
# ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def check_cdsco_recall(medicine_name: str) -> dict:
    urls = [
        "https://cdsco.gov.in/opencms/opencms/en/Drugs/Recall-and-rapid-alerts/",
        "https://cdsco.gov.in/opencms/opencms/en/Drugs/Recall-of-Drugs/",
    ]
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        page_text = ""
        source_url = None
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    page_text = BeautifulSoup(resp.text, "html.parser").get_text().lower()
                    source_url = url
                    break
            except requests.RequestException:
                continue

        if not page_text:
            return {
                "status": "unavailable",
                "message": "CDSCO recall service is currently unavailable. Please verify manually.",
                "url": urls[0]
            }

        name_lower = medicine_name.lower().split()[0]  # use first word only
        if name_lower in page_text:
            return {
                "status": "warning",
                "message": f"⚠️ '{medicine_name}' found in CDSCO recall page. Verify the batch number manually.",
                "url": source_url
            }
        else:
            return {
                "status": "ok",
                "message": f"✅ No recall found for '{medicine_name}' on CDSCO."
            }
    except Exception:
        return {
            "status": "unavailable",
            "message": "Could not verify CDSCO recall status right now. Please recheck later."
        }


# ─────────────────────────────────────────
# HELPER: OpenFDA Drug Info + Interactions
# ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def check_openfda(medicine_name: str) -> dict:
    try:
        clean   = clean_medicine_name(medicine_name)
        generic = get_generic_name(clean)
        
        url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{generic}&limit=1"
        resp = requests.get(url, timeout=8)

        if resp.status_code == 404:
            return {"status": "not_found", "message": f"No FDA data found for '{medicine_name}'"}
        if resp.status_code >= 500:
            return {"status": "unavailable", "message": "FDA service is temporarily unavailable."}
        resp.raise_for_status()

        data = resp.json()

        if "results" not in data:
            return {"status": "not_found", "message": f"No FDA data found for '{medicine_name}'"}

        result = data["results"][0]

        warnings       = result.get("warnings", ["No specific warnings listed"])
        interactions   = result.get("drug_interactions", ["No interaction data listed"])
        indications    = result.get("indications_and_usage", ["No indication data"])
        dosage         = result.get("dosage_and_administration", ["No dosage data"])

        return {
            "status": "found",
            "warnings":      warnings[0][:300] if warnings else "None",
            "interactions":  interactions[0][:300] if interactions else "None",
            "indications":   indications[0][:200] if indications else "None",
            "dosage":        dosage[0][:200] if dosage else "None",
        }
    except requests.RequestException:
        return {"status": "unavailable", "message": "Could not reach FDA service. Please try again later."}
    except Exception:
        return {"status": "unavailable", "message": "Unable to process FDA response for this medicine."}


# ─────────────────────────────────────────
# STEP 2 — PROCESS
# ─────────────────────────────────────────
raw_text     = ""
barcode_data = None

if image_input or pdf_input:

    st.markdown("---")
    st.markdown("### Step 2: Extracted Information")

    if pdf_input:
        with st.spinner("Reading PDF bill..."):
            raw_text = extract_text_from_pdf(pdf_input)
        st.success("PDF text extracted successfully")

    elif image_input:
        with st.spinner("Scanning image..."):
            barcode_data, raw_text = extract_from_image(image_input)

        if barcode_data:
            st.info(f"🔲 Barcode detected: `{barcode_data}`")
        else:
            st.info("No barcode found — using OCR text instead")

        if not BARCODE_SUPPORTED:
            st.warning("Barcode scanner library is unavailable on this system. OCR is still active.")

    # Show raw extracted text in expander
    with st.expander("📄 Raw extracted text (click to view)"):
        st.text(raw_text if raw_text.strip() else "No text could be extracted")

    # Parse medicine names
    medicines = parse_medicine_names(raw_text)

    if medicines:
        st.success(f"Found **{len(medicines)}** medicine(s): {', '.join(medicines)}")
    else:
        st.warning("Could not auto-detect medicine names. Try entering manually below.")
        manual = st.text_input("Enter medicine name manually (e.g. Paracetamol 500mg)")
        if manual:
            medicines = [manual]

    # MRP check
    mrp_data = extract_mrp(raw_text)
    if mrp_data.get("mrp_values_found"):
        st.info(f"💰 MRP values found on bill/packaging: ₹{mrp_data['mrp_values_found']}")

    # ─────────────────────────────────────────
    # STEP 3 — VERIFY
    # ─────────────────────────────────────────
    if medicines:
        st.markdown("---")
        st.markdown("### Step 3: Verification Report")

        # Optional: user adds other medicines they are taking
        other_meds = st.text_input(
            "💊 Are you currently taking other medicines? (optional — for interaction check)",
            placeholder="e.g. Metformin, Atorvastatin"
        )

        if st.button("🔍 Run Full Verification", type="primary"):

            for med in medicines:
                st.markdown(f"---\n#### 💊 {med}")

                col1, col2 = st.columns(2)

                # CDSCO Recall
                with col1:
                    with st.spinner(f"Checking CDSCO recall for {med}..."):
                        recall = check_cdsco_recall(med)
                    if recall["status"] == "ok":
                        st.success(recall["message"])
                    elif recall["status"] == "warning":
                        st.warning(recall["message"])
                        st.markdown(f"[🔗 Check manually]({recall['url']})")
                    else:
                        st.info(recall["message"])
                        if recall.get("url"):
                            st.markdown(f"[🔗 Open CDSCO recall page]({recall['url']})")

                # OpenFDA Info
                with col2:
                    with st.spinner(f"Fetching drug info for {med}..."):
                        fda = check_openfda(med)
                    if fda["status"] == "found":
                        st.success("✅ Drug found in FDA database")
                    elif fda["status"] == "not_found":
                        st.info(fda["message"])
                    else:
                        st.warning(fda.get("message", "Unable to verify with FDA right now."))

                # Detailed FDA info
                if fda.get("status") == "found":
                    with st.expander("📋 Drug Details"):
                        st.markdown(f"**Indicated for:** {fda['indications']}")
                        st.markdown(f"**Dosage note:** {fda['dosage']}")
                        st.markdown(f"**Warnings:** {fda['warnings']}")
                        st.markdown(f"**Known interactions:** {fda['interactions']}")

                # Cross-check with other medicines user is taking
                if other_meds.strip():
                    for other in other_meds.split(","):
                        other = other.strip()
                        if other:
                            with st.spinner(f"Checking interaction: {med} + {other}..."):
                                inter = check_openfda(other)
                            if inter.get("status") == "found" and "interactions" in inter:
                                if med.lower().split()[0] in inter["interactions"].lower():
                                    st.error(f"⚠️ Possible interaction between **{med}** and **{other}** — consult your doctor")
                                else:
                                    st.success(f"✅ No direct interaction found between {med} and {other}")

            # MRP Summary
            if mrp_data.get("mrp_values_found"):
                st.markdown("---")
                st.markdown("### 💰 Price Check")
                st.info(
                    f"MRP printed on packaging/bill: ₹{mrp_data['mrp_values_found']}\n\n"
                    "If the chemist charged more than the highest MRP listed, "
                    "that is illegal under Indian drug pricing rules. "
                    "You can report overcharging to your State Drug Control Authority."
                )

# ─────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────
st.markdown("---")
st.caption(
    "⚠️ This tool is for informational purposes only and does not replace "
    "professional medical advice. Always consult a licensed pharmacist or doctor."
)
