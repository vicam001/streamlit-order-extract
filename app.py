import streamlit as st
import json
import re
import tempfile
from docling.document_converter import DocumentConverter
from streamlit_ace import st_ace

def extract_text_from_pdf(pdf_path):
    """Extracts structured data from a PDF using Docling's DocumentConverter."""
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    
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

def remove_substring_if_found(substring: str, main_string: str) -> str:
    """
    Converts both input strings to uppercase, and if the first string is found
    in the second one, removes it.

    :param substring: The string to check and remove.
    :param main_string: The string from which the substring should be removed.
    :return: The modified main string with the substring removed if found.
    """
    if not substring or not main_string:
        return main_string.strip()

    substring_upper = substring.upper()
    main_string_upper = main_string.upper()

    if main_string_upper.startswith(substring_upper):
        return main_string[len(substring) :].strip()

    return main_string.strip()


def concatenate_text_from_index(objects_list, start_index=11):
    """
    Concatenates the 'text' values from a list of objects starting from a given index.

    :param objects_list: List of dictionaries containing a "text" key.
    :param start_index: Index from which to start concatenation.
    :return: Concatenated string of 'text' values.
    """
    return "\n".join(obj["text"] for obj in objects_list[start_index:] if "text" in obj and obj["text"].strip())

def main():
    st.title("SEMAT PDF Data Extraction")
    st.write("Upload a PDF file to extract key information from the Order.")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_pdf_path = temp_file.name
        
        st.write("Extracting information...")
        extracted_data = extract_text_from_pdf(temp_pdf_path)
        
        if extracted_data:
            st.success("Extraction Complete!")

            
            #st.subheader("Extracted Markdown Data")
            #st.markdown(extracted_data["text"])  # Display extracted text in a markdown visualizer

            st.subheader("Extracted JSON Data")
            
            data = extracted_data["dict"]

            external_id = next((item["text"] for item in data["texts"] if item.get("self_ref") == "#/texts/5"), None)
            st.write("External ID: ", external_id)

            delivery_requested_at = next((item["text"] for item in data["texts"] if item.get("self_ref") == "#/texts/6"), None)
            st.write("Delivery Requested at: ", delivery_requested_at)


            ## Table 0
            table_0_grid = data["tables"][0]["data"]["grid"]           
            carplate = get_first_non_matching_value(table_0_grid[0], exclude_value="Matrícula / Bastidor:")
            st.write("Carplate: ", carplate)
            make = get_first_non_matching_value(table_0_grid[1], exclude_value="Marca:")
            st.write("Make: ", make)
            model = get_first_non_matching_value(table_0_grid[2], exclude_value="Modelo:")
            model = remove_substring_if_found(make, model)
            st.write("Model: ", model)

            ## Table 1
            st.subheader("Origin")
            table_1_grid = data["tables"][1]["data"]["grid"]
            origin_name = get_first_non_matching_value(table_1_grid[0], exclude_value="Punto de Recogida:")
            st.write("Origin Name: ", origin_name)
            origin_contact = get_first_non_matching_value(table_1_grid[1], exclude_value="Persona de Contacto:")
            st.write("Origin Contact: ", origin_contact)
            origin_address = get_first_non_matching_value(table_1_grid[2], exclude_value="Dirección:")
            st.write("Origin Address: ", origin_address)
            origin_zip = get_first_non_matching_value(table_1_grid[3], exclude_value="Código Postal:")
            origin_zip = get_first_word(origin_zip)
            st.write("Origin ZIP: ", origin_zip)
            origin_province = get_first_non_matching_value(table_1_grid[4], exclude_value="Provincia:")
            st.write("Origin Province: ", origin_province)
            origin_telephone = get_first_non_matching_value(table_1_grid[5], exclude_value="Teléfono de Contacto:")
            st.write("Origin Telephone: ", origin_telephone)
            origin_comments = get_first_non_matching_value(table_1_grid[6], exclude_value="Observaciones:")
            st.write("Origin Comments: ", origin_comments)

            ## Table 2
            st.subheader("Destination")          
            table_2_grid = data["tables"][2]["data"]["grid"]
            destination_name = get_first_non_matching_value(table_2_grid[0], exclude_value="Punto de Entrega:")
            st.write("Name: ", destination_name)
            destination_contact = get_first_non_matching_value(table_2_grid[1], exclude_value="Persona de Contacto:")
            st.write("Contact: ", destination_contact)
            destination_address = get_first_non_matching_value(table_2_grid[2], exclude_value="Dirección:")
            st.write("Address: ", destination_address)
            destination_zip = get_first_non_matching_value(table_2_grid[3], exclude_value="Código Postal:")
            destination_zip = get_first_word(destination_zip)
            st.write("ZIP: ", destination_zip)
            destination_province = get_first_non_matching_value(table_2_grid[4], exclude_value="Provincia:")
            st.write("Province: ", destination_province)
            destination_telephone = get_first_non_matching_value(table_2_grid[5], exclude_value="Teléfono de Contacto:")
            st.write("Telephone: ", destination_telephone)
            destination_comments = get_first_non_matching_value(table_2_grid[6], exclude_value="Observaciones:")
            st.write("Comments: ", destination_comments)

            ## Comments

            comments = concatenate_text_from_index(data["texts"], start_index=11)
            st.text_area("Comments:", comments, height=300)
            
            json_data = json.dumps(data, indent=4)
            st_ace(json_data, language="json", theme="monokai", key="json_viewer")
        else:
            st.error("No data extracted from the PDF.")

if __name__ == "__main__":
    main()
