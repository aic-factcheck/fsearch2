from io import BytesIO
import tempfile
from markdownify import markdownify as md
# import pdfplumber
# from pdf2markdown4llm import PDF2Markdown4LLM
from readability import Document

def html_to_markdown(html: str) -> str:
    """
    Convert HTML content to Markdown using readability + markdownify.
    """
    doc = Document(html)
    clean_html = doc.summary()
    return md(clean_html, heading_style="ATX")

# The PDF conversion does not work well

# def pdf_to_text_plain_text(pdf_bytes: bytes) -> str:
#     """
#     Convert PDF content to plain text using pdfplumber.
#     """
#     text = ""
#     pdf_file = BytesIO(pdf_bytes)
#     with pdfplumber.open(pdf_file) as pdf:
#         for page in pdf.pages:
#             page_text = page.extract_text()
#             if page_text:
#                 text += page_text + "\n\n"
#     return text.strip()


# def pdf_to_text(pdf_bytes: bytes) -> str:
#     converter = PDF2Markdown4LLM(remove_headers=False, skip_empty_tables=True, table_header="### Table")
#     with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
#         tmp.write(pdf_bytes)
#         tmp.flush()
#         markdown_content = converter.convert(tmp.name)
#     return markdown_content
   