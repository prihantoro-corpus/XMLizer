import streamlit as st
import chardet
import re
from lxml import etree

st.set_page_config(page_title="XMLizer", layout="centered")

st.title("🧩 XMLizer")
st.caption("Convert any document into clean, sentence-based XML")

# --------------------------------------------------
# Utilities
# --------------------------------------------------

def detect_and_decode(file_bytes):
    result = chardet.detect(file_bytes)
    encoding = result.get("encoding", "utf-8")
    try:
        text = file_bytes.decode(encoding, errors="replace")
    except Exception:
        text = file_bytes.decode("utf-8", errors="replace")
        encoding = "utf-8"
    return text, encoding


def clean_illegal_xml_chars(text):
    illegal_xml_re = re.compile(
        r"[\x00-\x08\x0B\x0C\x0E-\x1F\uD800-\uDFFF\uFFFE\uFFFF]"
    )
    return illegal_xml_re.sub("", text)


def escape_xml_entities(text):
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )


def sentence_split(text):
    """
    Rule-based sentence boundary detection.
    Splits on . ! ? followed by whitespace.
    """
    text = re.sub(r"\s+", " ", text.strip())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s for s in sentences if s.strip()]


def wrap_as_xml(sentences, root_tag="document"):
    blocks = []
    for i, sent in enumerate(sentences, start=1):
        blocks.append(
            f"<s n=\"{i}\">\n{sent}\n</s>"
        )

    body = "\n".join(blocks)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<{root_tag}>
{body}
</{root_tag}>
"""


def validate_and_repair_xml(xml_text):
    parser = etree.XMLParser(recover=True)
    try:
        tree = etree.fromstring(xml_text.encode("utf-8"), parser)
        repaired = etree.tostring(
            tree,
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
    "Upload any document (TXT, CSV, XML, etc.)",
    type=None
)

if uploaded_file:
    file_bytes = uploaded_file.read()

    # 1. Detect encoding
    text, detected_encoding = detect_and_decode(file_bytes)
    st.success(f"Detected encoding: **{detected_encoding} → UTF-8**")

    # 2. Clean illegal XML characters
    cleaned_text = clean_illegal_xml_chars(text)

    # 3. Sentence detection
    sentences = sentence_split(cleaned_text)
    st.info(f"Detected **{len(sentences)} sentences**")

    # 4. Escape XML entities
    escaped_sentences = [escape_xml_entities(s) for s in sentences]

    # 5. Wrap into XML
    xml_text = wrap_as_xml(escaped_sentences)

    # 6. Validate & repair
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
