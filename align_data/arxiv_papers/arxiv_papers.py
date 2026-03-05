import arxiv
import requests
import logging
import time
import jsonlines

import pandas as pd

from dataclasses import dataclass
from markdownify import markdownify
from tqdm import tqdm
from align_data.common.alignment_dataset import AlignmentDataset, DataEntry

logger = logging.getLogger(__name__)


@dataclass
class ArxivPapers(AlignmentDataset):
    COOLDOWN: int = 1
    done_key = "url"

    def setup(self) -> None:
        """
        Load arxiv ids
        """
        self._setup()
        self.papers_csv_path = self.write_jsonl_path.parent / "raw" / "ai-alignment-papers.csv" 

        self.df = pd.read_csv(self.papers_csv_path)
        self.df_arxiv = self.df[self.df["Url"].str.contains(
            "arxiv.org/abs") == True].drop_duplicates(subset="Url", keep="first")
        self.arxiv_ids = [xx.split('/abs/')[1] for xx in self.df_arxiv.Url]

    def _get_arxiv_metadata(self, paper_id) -> arxiv.Result:
        """
        Get metadata from arxiv
        """
        try:
            search = arxiv.Search(id_list=[paper_id], max_results=1)
        except Exception as e:
            logger.error(e)
            return None
        return next(search.results())

    def fetch_entries(self) -> None:
        """
        Fetch entries
            - Check if entry is already done
            - Get metadata from arxiv
            - Download PDF and process with grobid
            - Extract text from grobid response
            - Write to jsonl
        output:
            - jsonl file with entries
        """
        self.setup()
        for ii, ids in enumerate(tqdm(self.arxiv_ids)):
            logger.info(f"Processing {ids}")
            if self._entry_done(self._get_arxiv_link(ids)):
                # logger.info(f"Already done {self._get_arxiv_link(ids)}")
                continue

            markdown = self.process_id(ids)

            paper = self._get_arxiv_metadata(ids)
            if markdown is None or paper is None:
                logger.info(f"Skipping {ids}")
                new_entry = DataEntry({
                    "url": self._get_arxiv_link(ids),
                    "title": "n/a",
                    "authors": "n/a",
                    "date_published": "n/a",
                    "source": "arxiv",
                    "text": "n/a",
                })
            else:
                new_entry = DataEntry({"url": self._get_arxiv_link(ids),
                                   "source": "arxiv",
                                   "source_type": "html",
                                   "converted_with": "markdownify",
                                   "title": paper.title,
                                   "authors": [str(x) for x in paper.authors],
                                   "date_published": str(paper.published),
                                   "data_last_modified": str(paper.updated),
                                   "abstract": paper.summary.replace("\n", " "),
                                   "author_comment": paper.comment,
                                   "journal_ref": paper.journal_ref,
                                   "doi": paper.doi,
                                   "primary_category": paper.primary_category,
                                   "categories": paper.categories,
                                   "text": markdown,
                                   })
            new_entry.add_id()
            yield new_entry
            time.sleep(self.COOLDOWN)

    def _get_pdf_link(self, paper_id) -> str:
        """
        Get arxiv PDF link
        """
        return f"https://arxiv.org/pdf/{paper_id}.pdf"

    def _get_arxiv_link(self, paper_id) -> str:
        """
        Get arxiv link
        """
        return f"https://arxiv.org/abs/{paper_id}"

    def _strip_markdown(self, markdown) -> str:
        """
        Strip markdown - updated for arXiv HTML (not arxiv-vanity)
        """
        # For arXiv HTML, try to extract main content
        # Look for common section markers
        if "Abstract" in markdown:
            # Split after abstract and before references/acknowledgments
            parts = markdown.split("Abstract", 1)
            if len(parts) > 1:
                content = parts[1]
                # Remove references section if it exists
                ref_splits = content.split("\nReferences\n")
                content = ref_splits[0]
                # Remove acknowledgments if they exist
                ack_splits = content.split("\nAcknowledgments\n")
                content = ack_splits[0]
                return content.replace("\n\n", "\n").strip()
        # Fallback: return most of the content, removing obvious non-paper parts
        return markdown.replace("\n\n", "\n").strip()

    def _is_dud(self, markdown) -> bool:
        """
        Check if markdown is a dud - updated for arXiv HTML
        """
        # Check if it's too short (likely not a full paper)
        if len(markdown.strip()) < 500:
            return True
        # Check for error messages
        if "404" in markdown or "not found" in markdown.lower():
            return True
        # Check if it looks like an abstract-only page
        if "Abstract" in markdown and len(markdown.split()) < 100:
            return True
        return False

    def process_id(self, paper_id) -> str:
        """
        Process arxiv id using PDF and grobid
        """
        pdf_link = self._get_pdf_link(paper_id)
        logger.info(f"Fetching PDF: {pdf_link}")

        try:
            # Download PDF
            pdf_response = requests.get(pdf_link, timeout=10 * self.COOLDOWN)
            if pdf_response.status_code == 404:
                logger.info(f"PDF not available for {paper_id}, skipping")
                return None
            pdf_response.raise_for_status()

            # Send to grobid for processing
            grobid_url = "http://localhost:8070/api/processFulltextDocument"
            files = {'input': ('paper.pdf', pdf_response.content, 'application/pdf')}
            # Try without Accept header, or try 'application/xml'
            headers = {'Accept': 'application/xml'}

            grobid_response = requests.post(grobid_url, files=files, headers=headers, timeout=60)

            if grobid_response.status_code != 200:
                logger.error(f"Grobid processing failed for {paper_id}: {grobid_response.status_code} - {grobid_response.text[:200]}")
                return None

            # Parse XML response instead of JSON
            try:
                from xml.etree import ElementTree as ET
                root = ET.fromstring(grobid_response.text)

                # Extract text from grobid TEI XML format
                # Look for body text in the XML structure
                body = root.find('.//{http://www.tei-c.org/ns/1.0}body')
                if body is not None:
                    text_parts = []
                    for p in body.findall('.//{http://www.tei-c.org/ns/1.0}p'):
                        if p.text:
                            text_parts.append(p.text)
                    text = ' '.join(text_parts)
                else:
                    text = grobid_response.text  # fallback

                if not text or len(text.strip()) < 500:
                    logger.info(f"Insufficient text extracted for {paper_id}")
                    return None

                return text.strip()

            except Exception as e:
                logger.error(f"XML parsing failed for {paper_id}: {e}")
                return None

        except Exception as e:
            logger.error(f"Failed to process {paper_id}: {e}")
            return None
