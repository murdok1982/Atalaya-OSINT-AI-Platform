from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ReportSection:
    title: str
    content: str
    subsections: list["ReportSection"] = field(default_factory=list)


@dataclass
class IntelligenceReport:
    report_id: str
    title: str
    classification: str = "UNCLASSIFIED"
    author: str = ""
    date: str = ""
    sections: list[ReportSection] = field(default_factory=list)
    executive_summary: str = ""
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    annexes: list[dict[str, str]] = field(default_factory=list)


class PDFReportGenerator:
    """Generates professional PDF intelligence reports."""

    def __init__(self) -> None:
        self._output_dir = settings.REPORTS_STORAGE_PATH
        os.makedirs(self._output_dir, exist_ok=True)

    def generate_pdf(self, report: IntelligenceReport) -> str:
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=25)

            pdf.add_page()
            self._add_cover_page(pdf, report)

            pdf.add_page()
            self._add_classification_header(pdf, report.classification)
            self._add_executive_summary(pdf, report)

            for section in report.sections:
                pdf.add_page()
                self._add_classification_header(pdf, report.classification)
                self._add_section(pdf, section)

            if report.findings:
                pdf.add_page()
                self._add_classification_header(pdf, report.classification)
                self._add_findings(pdf, report.findings)

            if report.recommendations:
                pdf.add_page()
                self._add_classification_header(pdf, report.classification)
                self._add_recommendations(pdf, report.recommendations)

            filepath = os.path.join(self._output_dir, f"{report.report_id}.pdf")
            pdf.output(filepath)
            logger.info("pdf_report_generated", filepath=filepath, report_id=report.report_id)
            return filepath
        except Exception as exc:
            logger.error("pdf_generation_failed", error=str(exc))
            return ""

    def _add_cover_page(self, pdf: Any, report: IntelligenceReport) -> None:
        pdf.set_font("Helvetica", "B", 28)
        pdf.ln(40)
        pdf.cell(0, 20, report.title, align="C")
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 14)
        pdf.cell(0, 10, f"Classification: {report.classification}", align="C")
        pdf.ln(15)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, f"Author: {report.author}", align="C")
        pdf.ln(10)
        pdf.cell(0, 10, f"Date: {report.date or time.strftime('%Y-%m-%d')}", align="C")
        pdf.ln(10)
        pdf.cell(0, 10, f"Report ID: {report.report_id}", align="C")
        pdf.ln(20)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, f"// {report.classification} //", align="C")

    def _add_classification_header(self, pdf: Any, classification: str) -> None:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 8, f"// {classification} //", align="C")
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    def _add_executive_summary(self, pdf: Any, report: IntelligenceReport) -> None:
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "EXECUTIVE SUMMARY")
        pdf.ln(12)
        pdf.set_font("Helvetica", "", 11)
        summary = report.executive_summary or "No executive summary provided."
        pdf.multi_cell(0, 6, summary)

    def _add_section(self, pdf: Any, section: ReportSection) -> None:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, section.title)
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, section.content)
        pdf.ln(5)
        for subsection in section.subsections:
            self._add_section(pdf, subsection)

    def _add_findings(self, pdf: Any, findings: list[str]) -> None:
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "KEY FINDINGS")
        pdf.ln(12)
        pdf.set_font("Helvetica", "", 11)
        for i, finding in enumerate(findings, 1):
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(10, 8, f"{i}.")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, finding)
            pdf.ln(3)

    def _add_recommendations(self, pdf: Any, recommendations: list[str]) -> None:
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "RECOMMENDATIONS")
        pdf.ln(12)
        pdf.set_font("Helvetica", "", 11)
        for i, rec in enumerate(recommendations, 1):
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(10, 8, f"{i}.")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, rec)
            pdf.ln(3)


pdf_generator = PDFReportGenerator()
