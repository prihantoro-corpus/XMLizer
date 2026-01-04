import streamlit as st
import chardet
import re
from lxml import etree
from io import BytesIO
import zipfile
import os

st.set_page_config(page_title="XMLizer", layout="centered")

st.title("🧩 XMLizer")
st.caption("Convert text or documents into clean, sentence-based XML")

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


def wrap_as_xml(sentences):
    blocks = []
    for i, sent in enumerate(sentences, start=1):
        blocks.append(f"<s n=\"{i}\">\n{sent}\n</s>")

    body = "\n".join(blocks)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<document>
{body}
</document>
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


def process_single_text(text):
    cleaned = clean_illegal_xml_chars(text)
    sentences = sentence_split(cleaned)
    escaped = [escape_xml_entities(s) for s in sentences]
    xml_raw = wrap_as_xml(escaped)
    return validate_and_repair_xml(xml_raw), len(sentences)

# --------------------------------------------------
# UI
# --------------------------------------------------

input_mode = st.radio(
    "Input mode",
    ["Direct text input", "Upload file(s)"],
    horizontal=True
)

outputs = []

if input_mode == "Direct text input":
    text = st.text_area(
        "Paste your text here",
        height=250,
        placeholder="Paste any text here..."
    )

    if text.strip():
        xml, count = process_single_text(text)
        outputs.append(("input_text.xml", xml, count))

else:
    uploaded_files = st.file_uploader(
        "Upload one or more documents",
        type=None,
        accept_multiple_files=True
    )

    if uploaded_files:
        for f in uploaded_files:
            raw_text, enc = detect_and_decode(f.read())
            st.success(f"{f.name}: {enc} → UTF-8")

            xml, count = process_single_text(raw_text)

            xml_name = os.path.splitext(f.name)[0] + ".xml"
            outputs.append((xml_name, xml, count))

# --------------------------------------------------
# Output
# --------------------------------------------------

if outputs:
    total_sentences = sum(o[2] for o in outputs)
    st.info(f"Processed **{len(outputs)} document(s)** · **{total_sentences} sentences**")

    # Preview FIRST file only (never merged)
    with st.expander("🔍 XML Preview (limited)"):
        st.code(limited_preview(outputs[0][1]), language="xml")

    # One document → one XML
    if len(outputs) == 1:
        name, xml, _ = outputs[0]
        st.download_button(
            label="⬇️ Download XML",
            data=xml.encode("utf-8"),
            file_name=name,
            mime="application/xml"
        )

    # Multiple documents → ZIP (flat, separated)
    else:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for name, xml, _ in outputs:
                z.writestr(name, xml)

        zip_buffer.seek(0)

        st.download_button(
            label="⬇️ Download ZIP (separate XMLs)",
            data=zip_buffer,
            file_name="xmlizer_output.zip",
            mime="application/zip"
        )



