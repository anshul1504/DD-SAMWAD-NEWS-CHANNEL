import argparse
import json
from pathlib import Path

import pymupdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(args.pdf.resolve())
    audit = {"page_count": document.page_count, "pages": []}

    for number, page in enumerate(document, start=1):
        preview = page.get_pixmap(matrix=pymupdf.Matrix(0.8, 0.8), alpha=False)
        preview.save(output / f"page-{number}.jpg")
        blocks = []
        for block in page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue
            lines = []
            for line in block["lines"]:
                text = " ".join(
                    span["text"].strip()
                    for span in line["spans"]
                    if span["text"].strip()
                )
                if text:
                    lines.append(
                        {
                            "text": text,
                            "size": max(span["size"] for span in line["spans"]),
                        }
                    )
            if lines:
                blocks.append({"bbox": block["bbox"], "lines": lines})

        images = []
        for image in page.get_image_info(xrefs=True):
            if image.get("xref"):
                images.append(
                    {
                        "bbox": image["bbox"],
                        "width": image["width"],
                        "height": image["height"],
                        "xref": image["xref"],
                    }
                )
        audit["pages"].append(
            {
                "number": number,
                "width": page.rect.width,
                "height": page.rect.height,
                "blocks": blocks,
                "images": images,
            }
        )

    (output / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"pages={document.page_count} output={output}")


if __name__ == "__main__":
    main()
