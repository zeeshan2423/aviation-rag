import re

def split_sections(text):
    """Split text into sections"""
    pattern = r"\n?\d+\.\s+[A-Z][A-Z\s]+\."

    sections = re.split(pattern, text)
    titles = re.findall(pattern, text)

    structured = []

    for i, content in enumerate(sections[1:]):
        structured.append({
            "section": titles[i].strip(),
            "text": content.strip()
        })

    return structured