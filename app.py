import streamlit as st
import chardet
import re
from lxml import etree
from io import BytesIO

st.set_page_config(page_title="XMLizer", layout="centered")

st.title("🧩 XMLizer")
st.caption("Convert any document into clean, well-formed XML")

# --------------------------------------------------
# Utilities
# --------------------------------------------------

def detect_and_decode(file_bytes):
    """Detect encoding and decode to UTF-8"""
    result = chardet.detect(file_bytes)
    encoding = result.get("encoding", "utf-8")
    try:
        text = file_bytes.decode(encoding, errors="replace")
    except Exception:
        text = file_bytes.decode("utf-8", errors="replace")
        encoding = "utf-8"
    return text, encoding


def clean_illegal_xml_chars(text):
    """Remove characters illegal in XML 1.0"""
    illegal_xml_re = re.compile(
        r"[\x00-\x08\x0B\x0C\x0E-\x1F\uD800-\uDFFF\uFFFE\uFFFF]"
    )
    return illegal_xml_re.sub("", text)


def escape_xml_entities(text):
    """Convert special characters to XML entities"""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )


def wrap_as_xml(text, root_tag="document"):
    """Wrap plain text inside an XML structure"""
    lines = text.splitlines()
    xml_lines = ["  <line>{}</line>".format(line) for line in lines if line.strip()]
    xml_body = "\n".join(xml_lines)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<{root_tag}>
{xml_body}
</{root_tag}>
"""


def validate_and_repair_xml(xml_text):
    """Check XML well-formedness and attempt repair"""
    parser = etree.XMLParser(recover=True)
    try:
        tree = etree.fromstring(xml_text.encode("utf-8"), parser)
        repaired = etree.tostring(
            tree,
            pretty_print=True,
            encoding="utf-8",
            xml_declaration=True
        ).decode("utf-8")
        return True, repaired
    except Exception as e:
        return False, str(e)


# --------------------------------------------------
# UI
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload any document (TXT, XML, CSV, etc.)",
    type=None
)

if uploaded_file:
    file_bytes = uploaded_file.read()

    # Step 1: Detect encoding
    text, detected_encoding = detect_and_decode(file_bytes)
    st.success(f"Detected encoding: **{detected_encoding} → UTF-8**")

    # Step 2: Clean illegal characters
    cleaned_text = clean_illegal_xml_chars(text)

    # Step 3: Escape XML entities
    escaped_text = escape_xml_entities(cleaned_text)

    # Step 4: Wrap into XML
    xml_text = wrap_as_xml(escaped_text)

    # Step 5: Validate & repair
    is_valid, final_xml = validate_and_repair_xml(xml_text)

    if is_valid:
        st.success("XML is well-formed (after repair if needed)")
    else:
        st.error("XML validation failed")

    # Preview
    with st.expander("🔍 XML Preview"):
        st.code(final_xml, language="xml")

    # Download
    st.download_button(
        label="⬇️ Download XML",
        data=final_xml.encode("utf-8"),
        file_name="output.xml",
        mime="application/xml"
    )
