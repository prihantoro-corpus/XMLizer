import streamlit as st
import chardet
import re
from lxml import etree

st.set_page_config(page_title="XMLizer", layout="centered")

st.title("🧩 XMLizer")
st.caption("Convert text or multiple documents into clean, sentence-based XML")

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
    text = re.sub(r"\s+", " ", text.strip())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s for s in sentences if s.strip()]


def wrap_as_xml(sentences, root_tag="document"):
    blocks = []
    for i, sent in enumerate(sentences, start=1):
        blocks.append(f"<s n=\"{i}\">\n{sent}\n</s>")

    body = "\n".join(blocks)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<{root_tag}>
{body}
</{root_tag}>
"""


def validate_and_repair_xml(xml_text):
    parser = etree.XMLParser(recover=True)
    tree = etree.fromstring(xml_text.encode("utf-8"), parser)
    return etree.tostring(
        tree,
        encoding="utf-8",
        xml_declaration=True
    ).decode("utf-8")


def limited_preview(xml_text, head=5, mid=5, tail=5):
    lines = xml_text.splitlines()
    total = len(lines)

    if total <= head + mid + tail:
        return xml_text

    middle_start = max((total // 2) - (mid // 2), head)
    middle_end = middle_start + mid

    preview_lines = (
        lines[:head]
        + ["..."]
        + lines[middle_start:middle_end]
        + ["..."]
        + lines[-tail:]
    )

    return "\n".join(preview_lines)

# --------------------------------------------------
# UI
# --------------------------------------------------

input_mode = st.radio(
    "Input mode",
    ["Direct text input", "Upload file(s)"],
    horizontal=True
)

all_texts = []

if input_mode == "Direct text input":
    text = st.text_area(
        "Paste your text here",
        height=250,
        placeholder="Paste any text here..."
    )
    if text.strip():
        all_texts.append(text)

else:
    uploaded_files = st.file_uploader(
        "Upload one or more documents",
        type=None,
        accept_multiple_files=True
    )

    if uploaded_files:
        for f in uploaded_files:
            text, enc = detect_and_decode(f.read())
            st.success(f"{f.name}: {enc} → UTF-8")
            all_texts.append(text)

# --------------------------------------------------
# Processing
# --------------------------------------------------

if all_texts:
    combined_text = "\n".join(all_texts)

    # Clean
    cleaned_text = clean_illegal_xml_chars(combined_text)

    # Sentence detection
    sentences = sentence_split(cleaned_text)
    st.info(f"Detected **{len(sentences)} sentences** (combined)")

    # Escape entities
    escaped_sentences = [escape_xml_entities(s) for s in sentences]

    # Wrap XML
    xml_text = wrap_as_xml(escaped_sentences)

    # Validate & repair
    try:
        final_xml = validate_and_repair_xml(xml_text)
        st.success("XML is well-formed (after repair if needed)")
    except Exception as e:
        st.error(f"XML validation failed: {e}")
        final_xml = xml_text

    # Preview
    with st.expander("🔍 XML Preview (limited)"):
        st.code(limited_preview(final_xml), language="xml")

    # Download
    st.download_button(
        label="⬇️ Download XML",
        data=final_xml.encode("utf-8"),
        file_name="output.xml",
        mime="application/xml"
    )
