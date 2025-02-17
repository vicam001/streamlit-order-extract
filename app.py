import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from streamlit_ace import st_ace
import re
import tempfile
import json
from docling.document_converter import DocumentConverter
from pydantic import ValidationError
from datetime import datetime
from dateutil.parser import parse
from bs4 import BeautifulSoup

# Import the Pydantic models
from models import OrderList, Order, Header, StopInfo, Address, Contact, Vehicle, ActivityEnum, ColorEnum

# Constants
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Set page to wide mode
st.set_page_config(page_title="Orders Data", layout="wide")

# Ensure session state is initialized
if "extracted_orders" not in st.session_state:
    st.session_state.extracted_orders = []
if "json_viewer_key" not in st.session_state:
    st.session_state.json_viewer_key = "json_viewer_1"  # Unique key for the st_ace widget


def extract_text_from_file(file_path):
    """Extracts structured data from a PDF/HTML file using Docling's DocumentConverter."""
    converter = DocumentConverter()
    result = converter.convert(file_path)
    
    extracted_data = {
        "text": result.document.export_to_markdown(),
        "dict": result.document.export_to_dict(),
    }
    return extracted_data

def extract_value_by_self_ref(json_data, self_ref):
    """Extracts value dynamically based on self_ref."""
    for table in json_data.get("tables", []):
        if table.get("self_ref") == self_ref:
            return [cell["text"] for cell in table["data"]["table_cells"]]
    return None

def get_first_non_matching_value(columns, exclude_value):
    """
    Returns the first value from a given key in an array of objects that does NOT match the exclude_value.

    :param columns: List of dictionaries.
    :param exclude_value: String value to be excluded.
    :return: The first non-matching string or None if all match/exclude.
    """
    for col in columns:
        if isinstance(col, dict) and "text" in col:  # Ensure col is a dict and contains the key "text"
            value = col["text"]
            if isinstance(value, str) and value.strip() and value != exclude_value:
                return value  # Return the first non-matching value
    return None  # Return None if all values match exclude_value

def get_first_word(text):
    """
    Extracts the first word from a given text safely and ensures it has a valid postal code format.

    :param text: The input string.
    :return: The first word if it looks like a postal code; otherwise, the original text.
    """
    if not isinstance(text, str) or not text.strip():
        return ""  # Return empty string if text is None, empty, or not a string

    first_word = text.split()[0]

    # Postal Code Format: Typically 5-digit numbers (can be extended for other formats)
    if re.fullmatch(r"\d{4,5}", first_word):  
        return first_word

    return text  # Return original input if first word is not a postal code

def remove_substring_if_found(substring: str | None, main_string: str | None) -> str:
    """
    Removes the given substring from the start of the main string, case-insensitively.

    :param substring: The string to check and remove (can be None).
    :param main_string: The string from which the substring should be removed (can be None).
    :return: The modified main string with the substring removed if found.
    """
    # Handle None values by converting them to empty strings
    if substring is None:
        substring = ""
    if main_string is None:
        return ""

    main_string = main_string.strip()
    substring = substring.strip()

    if main_string.upper().startswith(substring.upper()):
        return main_string[len(substring) :].lstrip()  # Use lstrip() to remove leftover leading spaces

    return main_string

def concatenate_text_from_index(objects_list, start_index=11):
    """
    Concatenates the 'text' values from a list of objects starting from a given index.

    :param objects_list: List of dictionaries containing a "text" key.
    :param start_index: Index from which to start concatenation.
    :return: Concatenated string of 'text' values.
    """
    return "\n".join(obj["text"] for obj in objects_list[start_index:] if "text" in obj and obj["text"].strip())

def format_date(value):
    """Formats dates into 'DD/MM/YYYY' format."""
    if value:
        try:
            return parse(value).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return value
    return value

def build_order_model(data):
    """Builds a structured OrderList object from extracted PDF data."""
    
    # Extract header fields
    external_id = next((item["text"] for item in data["texts"] if item.get("self_ref") == "#/texts/5"), None)
    delivery_requested_at = next((item["text"] for item in data["texts"] if item.get("self_ref") == "#/texts/6"), None)
    
    ## Table 0
    table_0_grid = data["tables"][0]["data"]["grid"]           
    carplate = get_first_non_matching_value(table_0_grid[0], exclude_value="Matrícula / Bastidor:")
    make = remove_substring_if_found("Marca:",get_first_non_matching_value(table_0_grid[1], exclude_value="Marca:"))
    model = remove_substring_if_found("Modelo:",get_first_non_matching_value(table_0_grid[2], exclude_value="Modelo:"))
    model = remove_substring_if_found(make, model)

    # Table 1 (Origin)
    table_1_grid = data["tables"][1]["data"]["grid"]
    origin_address = Address(
        address_name=get_first_non_matching_value(table_1_grid[0], "Punto de Recogida:"),
        street=get_first_non_matching_value(table_1_grid[2], "Dirección:"),
        city=None,  # Extract city if available
        province=get_first_non_matching_value(table_1_grid[4], "Provincia:"),
        postal_code=get_first_word(get_first_non_matching_value(table_1_grid[3], "Código Postal:")),
    )
    origin_contact = Contact(
        contact_person=get_first_non_matching_value(table_1_grid[1], "Persona de Contacto:"),
        phone=get_first_non_matching_value(table_1_grid[5], "Teléfono de Contacto:")
    )
    origin_comments=remove_substring_if_found("Observaciones:",get_first_non_matching_value(table_1_grid[6], "Observaciones:"))
    
    # Table 2 (Destination)
    table_2_grid = data["tables"][2]["data"]["grid"]
    destination_address = Address(
        address_name=get_first_non_matching_value(table_2_grid[0], "Punto de Entrega:"),
        street=get_first_non_matching_value(table_2_grid[2], "Dirección:"),
        city=None,  
        province=get_first_non_matching_value(table_2_grid[4], "Provincia:"),
        postal_code=get_first_word(get_first_non_matching_value(table_2_grid[3], "Código Postal:")),
    )
    destination_contact = Contact(
        contact_person=get_first_non_matching_value(table_2_grid[1], "Persona de Contacto:"),
        phone=get_first_non_matching_value(table_2_grid[5], "Teléfono de Contacto:")
    )
    destination_comments=remove_substring_if_found("Observaciones:",get_first_non_matching_value(table_2_grid[6], "Observaciones:"))


    # Vehicles
    vehicles_origin = [Vehicle(
        license_plate=carplate or "UNKNOWN",
        make=make or "UNKNOWN",
        model=model,
        activity=ActivityEnum.Collection,  # Collection for first stop
    )]

    vehicles_destination = [Vehicle(
        license_plate=carplate or "UNKNOWN",
        make=make or "UNKNOWN",
        model=model,
        activity=ActivityEnum.Delivery,  # Delivery for second stop
    )]

    # Stops
    stops = [
        StopInfo(stop_number=1, address=origin_address, contact=origin_contact, vehicles=vehicles_origin, comments=origin_comments),
        StopInfo(stop_number=2, address=destination_address, contact=destination_contact, vehicles=vehicles_destination, comments=destination_comments),
    ]

    # Header
    header = Header(
        company_name="SEMAT",
        customer_code=None,
        shipment_id=external_id or "UNKNOWN",
        available_at=format_date(datetime.now().isoformat()),
        delivery_requested_at=format_date(delivery_requested_at),
        sender_email=None,
        number_of_stops=len(stops),
        number_of_vehicles=len(vehicles_origin),
    )

    return Order(header=header, stops=stops)

def process_uploaded_pdfs(uploaded_files):
    """Processes and extracts data from uploaded PDF files."""
    new_orders = []
    progress_bar = st.progress(0)

    for idx, uploaded_file in enumerate(uploaded_files):
        file_size = uploaded_file.size
        if file_size > MAX_FILE_SIZE_BYTES:
            st.error(f"File '{uploaded_file.name}' exceeds {MAX_FILE_SIZE_MB}MB and was skipped.")
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_pdf_path = temp_file.name

        st.write(f"🔍 Extracting data from **{uploaded_file.name}**...")

        try:
            extracted_data = extract_text_from_file(temp_pdf_path)  # Assume function exists
            if extracted_data:
                new_order = build_order_model(extracted_data["dict"])  # Assume function exists
                new_orders.append(new_order)
        except ValidationError as e:
            st.error(f"❌ Validation error in {uploaded_file.name}: {e}")
        except Exception as e:
            st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")

        progress_bar.progress((idx + 1) / len(uploaded_files))  # Update progress bar

    progress_bar.empty()  # Remove progress bar when done
    return new_orders

def extract_nested_tables(html_content):
    """Extracts data from multiple nested tables and returns a structured dictionary."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    def parse_table(table):
        """Recursively extracts table data into a structured dictionary."""
        data = []
        headers = [th.get_text(strip=True) for th in table.find_all("th")]

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if cells:
                row_data = {}
                for idx, cell in enumerate(cells):
                    if headers and idx < len(headers):
                        key = headers[idx]
                    else:
                        key = f"Column_{idx + 1}"
                    
                    # Check if this cell contains another table
                    nested_table = cell.find("table")
                    if nested_table:
                        row_data[key] = parse_table(nested_table)  # Recursively process
                    else:
                        row_data[key] = cell.get_text(strip=True)

                data.append(row_data)

        return data

    # Extract top-level tables
    extracted_data = []
    for table in soup.find_all("table"):
        extracted_data.append(parse_table(table))

    return extracted_data

def process_uploaded_htmls(uploaded_files):
    """Processes and extracts data from uploaded HTML files."""
    new_orders = []
    progress_bar = st.progress(0)

    for idx, uploaded_file in enumerate(uploaded_files):
        file_size = uploaded_file.size
        if file_size > MAX_FILE_SIZE_BYTES:
            st.error(f"File '{uploaded_file.name}' exceeds {MAX_FILE_SIZE_MB}MB and was skipped.")
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_html_path = temp_file.name

        st.write(f"🔍 Extracting data from **{uploaded_file.name}**...")

        try:
            # extracted_data = extract_text_from_file(temp_html_path)
            converter = DocumentConverter()
            result = converter.convert(temp_html_path)
            
            # Extract structured table data
            tables_data = extract_nested_tables(uploaded_file.getvalue())

            extracted_data = {
                "text": result.document.export_to_markdown(),
                "dict": result.document.export_to_dict(),
                "tables": tables_data
            }
            if extracted_data:
               # new_order = build_order_model(extracted_data["dict"])
               # new_orders.append(new_order)
               new_orders = extracted_data

        except ValidationError as e:
            st.error(f"❌ Validation error in {uploaded_file.name}: {e}")
        except Exception as e:
            st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")

        progress_bar.progress((idx + 1) / len(uploaded_files))  # Update progress bar

    progress_bar.empty()  # Remove progress bar when done
    return new_orders

def display_extracted_orders():
    """Displays extracted orders with a PDF viewer on the left and JSON on the right."""
    if st.session_state.extracted_orders:
        st.subheader("📋 Extracted Order Data")

        # Create a side-by-side layout
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📄 Uploaded PDFs")
            if "uploaded_files" in st.session_state:
                for uploaded_file in st.session_state.uploaded_files:
                    binary_data = uploaded_file.getvalue()
                    pdf_viewer(input=binary_data, width=700)

        with col2:
            st.subheader("📂 JSON Viewer")
            order_list = OrderList(orders=st.session_state.extracted_orders)
            formatted_json = order_list.model_dump_json(indent=4)
            st_ace(formatted_json, language="json", theme="monokai", key=st.session_state.json_viewer_key)

        # Clear orders button
        if st.button("🗑️ Clear Extracted Orders"):
            st.session_state.extracted_orders = []
            st.session_state.json_viewer_key = f"json_viewer_{st.session_state.json_viewer_key[-1:]}"  # Update widget key
            st.rerun()  # Refresh UI

def display_extracted_html_orders():
    """Displays extracted orders with an HTML viewer on the left and JSON on the right."""
    if st.session_state.extracted_orders:
        st.subheader("📋 Extracted Order Data")

        # Create a side-by-side layout
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📄 Uploaded HTMLs")
            if "uploaded_files" in st.session_state:
                for uploaded_file in st.session_state.uploaded_files:
                    binary_data = uploaded_file.getvalue()                    

        with col2:
            st.subheader("📂 JSON Viewer")
            order_list = OrderList(orders=st.session_state.extracted_orders)
            formatted_json = order_list.model_dump_json(indent=4)
            st_ace(formatted_json, language="json", theme="monokai", key=st.session_state.json_viewer_key)

        # Clear orders button
        if st.button("🗑️ Clear Extracted Orders"):
            st.session_state.extracted_orders = []
            st.session_state.json_viewer_key = f"json_viewer_{st.session_state.json_viewer_key[-1:]}"  # Update widget key
            st.rerun()  # Refresh UI            


def main():

    # Sidebar navigation
    page = st.sidebar.radio("Navigation", ["PDF Orders", "HTML Orders"])

    if page == "PDF Orders":
        st.title("📄 PDF Data Extraction")
        st.write("Upload multiple PDF files to extract key information from Orders.")

        uploaded_files = st.file_uploader(
            "📂 Choose PDF files (Max: 25MB each)",
            type=["pdf"],
            accept_multiple_files=True,
            key="uploaded_files"
        )

        if uploaded_files:
            new_orders = process_uploaded_pdfs(uploaded_files)
            
            if new_orders:
                st.session_state.extracted_orders.extend(new_orders)
                st.success(f"✅ Successfully extracted {len(new_orders)} new orders!")

        display_extracted_orders()

    elif page == "HTML Orders":
        st.title("📄 HTML Data Extraction")
        st.write("Upload multiple HTML files to extract key information from Orders.")

        uploaded_files = st.file_uploader(
            "📂 Choose HTML files (Max: 25MB each)",
            type=["html"],
            accept_multiple_files=True,
            key="uploaded_files"
        )

        if uploaded_files:
            extracted_data = process_uploaded_htmls(uploaded_files)

            # Display extracted data
            st.success("Extraction Complete!")
            st.subheader("Extracted JSON Data")
            json_data = json.dumps(extracted_data, indent=4)
            st_ace(json_data, language="json", theme="monokai", key="json_viewer")

if __name__ == "__main__":
    main()