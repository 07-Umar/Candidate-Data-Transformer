import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def build_pdf(filename="UmarMohmed_umarmd0507@gmail.com_Eightfold.pdf"):
    # Target letter size (8.5 x 11 inches) -> 612 x 792 points
    # 0.5-inch margins -> 36 points margin all around
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles to fit on a single page
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'), # Slate 900
        alignment=1, # Center
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#475569'), # Slate 600
        alignment=1, # Center
        spaceAfter=10
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#1E3A8A'), # Navy 900
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1E293B'), # Slate 800
        spaceAfter=3
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=2
    )
    
    code_style = ParagraphStyle(
        'CodeLayout',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A'),
        backColor=colors.HexColor('#F8FAFC'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=0.5,
        borderPadding=4,
        spaceBefore=4,
        spaceAfter=4
    )

    story = []
    
    # Title Block
    story.append(Paragraph("TECHNICAL DESIGN: MULTI-SOURCE CANDIDATE TRANSFORMATION PIPELINE", title_style))
    story.append(Paragraph("Candidate: Umar Mohmed  |  Email: umarmd0507@gmail.com  |  Eightfold Engineering Intern Assignment", subtitle_style))
    
    # Section 1
    story.append(Paragraph("1. PIPELINE ARCHITECTURE", heading_style))
    p1_text = (
        "The candidate ingestion pipeline runs sequentially across decoupled phases to guarantee correctness, modularity, and determinism. "
        "Each stage executes separate business logic that protects the integrity of the data stream:"
    )
    story.append(Paragraph(p1_text, body_style))
    
    pipeline_flow = (
        "<b>Pipeline Flow:</b> [Inputs] &rarr; (CSV / PDF Parsers) &rarr; [Raw Profiles] &rarr; (Normalizers) &rarr; [Normalized Profiles]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        "&rarr; (Merge Engine + Confidence Engine) &rarr; [Canonical Profile] &rarr; (Projector Layer) &rarr; [Projected Candidate JSON] &rarr; (Validator) &rarr; [Valid Output]"
    )
    story.append(Paragraph(pipeline_flow, code_style))
    
    story.append(Paragraph("&bull; <b>Source Parsing:</b> Extracts structured data from CSV (Pandas) and unstructured text from PDF (pdfplumber) using heuristic-based layout parsing.", bullet_style))
    story.append(Paragraph("&bull; <b>Normalization:</b> Sanitizes values (emails, phones, dates, skills, location components) to canonical standards prior to merging.", bullet_style))
    story.append(Paragraph("&bull; <b>Merge & Confidence Engine:</b> Resolves field-level source conflicts and scores data confidence based on overlap and source trust.", bullet_style))
    story.append(Paragraph("&bull; <b>Projection & Validation:</b> Filters, renames, and formats the output schema via a runtime JSON config, executing jsonschema validation before saving.", bullet_style))
    
    # Section 2
    story.append(Paragraph("2. CANONICAL SCHEMA & NORMALIZATION RULES", heading_style))
    story.append(Paragraph("&bull; <b>candidate_id / full_name / headline:</b> Cleaned, whitespace-trimmed strings; name defaults to the first line of the resume.", bullet_style))
    story.append(Paragraph("&bull; <b>emails / phones:</b> Emails are lowercased and deduplicated. Phones are normalized to the <b>E164</b> international format using the <i>phonenumbers</i> library.", bullet_style))
    story.append(Paragraph("&bull; <b>location:</b> Parsed into city, state, and country. Country is standardized to <b>ISO-3166-1 alpha-2</b> format (e.g., 'IN' or 'US').", bullet_style))
    story.append(Paragraph("&bull; <b>links:</b> Standardized list of URLs (LinkedIn, GitHub, LeetCode) prefixed with <i>https://</i>.", bullet_style))
    story.append(Paragraph("&bull; <b>skills:</b> Match names against a canonical software engineering taxonomy using <i>rapidfuzz</i> similarity (threshold &ge; 80), keeping custom skills.", bullet_style))
    story.append(Paragraph("&bull; <b>experience & education:</b> Nested lists. Dates normalized to <b>YYYY-MM</b> or 'Present'. Experience sorted newest-to-oldest by end date.", bullet_style))
    story.append(Paragraph("&bull; <b>provenance:</b> Map of field paths to their source files (e.g., <i>recruiter.csv</i>, <i>resume.pdf</i>) and extraction methods (e.g., <i>pdf_extraction</i>, <i>csv_parsing</i>).", bullet_style))

    # Section 3
    story.append(Paragraph("3. MERGE & CONFLICT RESOLUTION POLICY", heading_style))
    story.append(Paragraph("If values overlap or conflict between sources, the engine applies deterministic priority and confidence adjustment rules:", body_style))
    story.append(Paragraph("&bull; <b>Source Preference:</b> Recruiter CSV is preferred for contact details (emails, phones, location). Resume PDF is preferred for skill names, headline, experience, and education.", bullet_style))
    story.append(Paragraph("&bull; <b>Confidence Base:</b> Resume PDF default confidence = <b>0.9</b>; Recruiter CSV default confidence = <b>0.8</b>.", bullet_style))
    story.append(Paragraph("&bull; <b>Agreement Rule:</b> If sources agree on a field, confidence is boosted: C_merged = min(1.0, max(C_resume, C_csv) + 0.05) &rarr; e.g. 0.95 for name.", bullet_style))
    story.append(Paragraph("&bull; <b>Conflict Rule:</b> If sources disagree, the preferred source's value is taken, but confidence is reduced: C_merged = C_preferred * 0.75 &rarr; e.g., 0.9 * 0.75 = 0.675.", bullet_style))
    story.append(Paragraph("&bull; <b>Overall Confidence:</b> Computed as the simple average of all populated field confidences, providing a single quality metric for the profile.", bullet_style))

    # Section 4
    story.append(Paragraph("4. RUNTIME PROJECTION & DYNAMIC VALIDATION", heading_style))
    p4_text = (
        "The <b>Projector Layer</b> reads a runtime configuration file to reshape the internal canonical record into the final candidate JSON structure. "
        "It supports subset selection, remapping paths (e.g., mapping index <i>emails[0]</i> to a flat key <i>primary_email</i>), executing field-level normalizations, "
        "toggling confidence/provenance blocks, and executing missing-value behaviors (<i>null</i>, <i>omit</i>, or raising a hard <i>error</i>). "
        "The <b>Validator Layer</b> translates the config's fields and types into a strict JSON Schema at runtime. It runs jsonschema validation and "
        "throws human-readable errors with precise violation paths if fields mismatch."
    )
    story.append(Paragraph(p4_text, body_style))

    # Section 5
    story.append(Paragraph("5. EDGE CASES & SCOPE DESCISION", heading_style))
    story.append(Paragraph("&bull; <b>Malformed CSV:</b> The parser handles empty files, missing columns, or parsing failures gracefully by logging errors and proceeding with remaining sources.", bullet_style))
    story.append(Paragraph("&bull; <b>Missing Resume:</b> The pipeline runs end-to-end utilizing recruiter data only, mapping confidence to 0.8 and adjusting overall metrics.", bullet_style))
    story.append(Paragraph("&bull; <b>Malformed Dates/Phones:</b> If standard parsing fails, fallback values (cleaned digits or raw text) are retained to prevent data loss, preserving original strings.", bullet_style))
    story.append(Paragraph("&bull; <b>Out of Scope (Time/Resource Constraints):</b> OCR for scanned PDF documents (requires a readable text layer); deep NLP semantic analysis (replaced with robust regex and rapidfuzz matching); live external API calls for location lookup (replaced with mapping lists).", bullet_style))

    # Build the document
    try:
        doc.build(story)
        print("PDF successfully generated.")
    except Exception as e:
        print(f"Error building PDF: {e}", file=sys.stderr)

if __name__ == "__main__":
    build_pdf()
