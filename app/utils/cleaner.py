import re

def clean_text(text: str) -> str:
    text = re.sub(r"AC\s*\d+-\d+[A-Z]?\s*\d+/\d+/\d+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^\.\s*", "", text)

    return text.strip()
