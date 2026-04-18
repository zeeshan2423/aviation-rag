import re

def split_subsections(section):
    text = section["text"]
    section_title = section["section"]

    pattern = r"(?:^|\s)([a-z]\.\s+[A-Z][^\.]+)"

    splits = re.split(pattern, text)
    matches = re.findall(pattern, text)

    structured = []

    for i in range(1, len(splits), 2):
        subsection_title = splits[i].strip()
        content = splits[i + 1].strip()

        structured.append({
            "section": section_title,
            "subsection": subsection_title,
            "text": content
        })

    return structured