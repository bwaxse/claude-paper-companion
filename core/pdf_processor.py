"""
PDF processing functionality for Paper Companion
"""

import base64
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from rich.console import Console

console = Console()


class PDFProcessor:
    """Handles PDF text and image extraction"""

    @staticmethod
    def compute_pdf_hash(pdf_path: Path) -> str:
        """
        Compute SHA256 hash of PDF for unique identification.

        Args:
            pdf_path: Path to PDF file

        Returns:
            First 16 characters of SHA256 hash
        """
        with open(pdf_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]

    @staticmethod
    def extract_from_pdf(pdf_path: Path, label: str = "PDF") -> Tuple[str, List[Dict]]:
        """
        Extract text and images from a single PDF.

        Args:
            pdf_path: Path to PDF file
            label: Label for console output

        Returns:
            Tuple of (text_content, images)
            - text_content: String of all extracted text
            - images: List of image dicts with base64 data
        """
        console.print(f"[cyan]Loading {label}: {pdf_path.name}[/cyan]")
        doc = fitz.open(pdf_path)

        text_content = []
        images = []

        for page_num, page in enumerate(doc, 1):
            # Text extraction
            text = page.get_text()
            if text.strip():
                text_content.append(f"[Page {page_num}]\n{text}")

            # Image extraction
            for img_index, img in enumerate(page.get_images(full=True)):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)

                    # Only include substantial images (likely figures)
                    if pix.width > 200 and pix.height > 200:
                        if pix.n - pix.alpha < 4:  # RGB or grayscale
                            img_data = pix.tobytes("png")
                            img_base64 = base64.b64encode(img_data).decode()
                            images.append({
                                "source": pdf_path.name,
                                "page": page_num,
                                "index": img_index,
                                "data": img_base64,
                                "type": "image/png"
                            })
                    pix = None
                except Exception:
                    continue

        doc.close()
        console.print(f"[green]✓ Loaded {len(text_content)} pages, {len(images)} figures from {label}[/green]")
        return "\n\n".join(text_content), images

    @classmethod
    def load_pdf_with_supplements(
        cls,
        main_pdf_path: Path,
        supplement_paths: List[Path] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Load main PDF and optional supplements.

        Args:
            main_pdf_path: Path to main PDF
            supplement_paths: Optional list of supplement PDF paths

        Returns:
            Tuple of (combined_text, combined_images)
        """
        # Extract main PDF
        main_text, main_images = cls.extract_from_pdf(main_pdf_path, "main PDF")

        # Start with main content
        combined_text = main_text
        combined_images = main_images

        # Add supplements if any
        if supplement_paths:
            for supp_path in supplement_paths:
                supp_text, supp_images = cls.extract_from_pdf(supp_path, "supplemental PDF")
                combined_text += f"\n\n=== SUPPLEMENTAL MATERIAL: {supp_path.name} ===\n\n" + supp_text
                combined_images.extend(supp_images)

        # Show summary
        console.print(f"[bold green]✓ Total: {len(combined_images)} figures across all PDFs[/bold green]")

        return combined_text, combined_images
