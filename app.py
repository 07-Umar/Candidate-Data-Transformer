import os
import json
import logging
import typer
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("eightfold_pipeline")

# Streamlit detection and routing
try:
    from streamlit.runtime import exists
    if exists():
        from ui.streamlit_app import run_streamlit_app
        run_streamlit_app()
        # Exit early to prevent CLI execution
        import sys
        sys.exit(0)
except ImportError:
    pass

app = typer.Typer(help="Eightfold Multi-Source Candidate Data Transformer Pipeline CLI")


@app.command()
def process_candidate(
    csv: Optional[str] = typer.Option(
        None, "--csv", "-c", help="Path to recruiter CSV candidate profile"
    ),
    resume: Optional[str] = typer.Option(
        None, "--resume", "-r", help="Path to candidate resume PDF"
    ),
    config_path: str = typer.Option(
        ..., "--config", "-cfg", help="Path to runtime projection config JSON"
    ),
    output_path: str = typer.Option(
        ..., "--output", "-o", help="Path to write the final projected candidate JSON"
    )
):
    """
    Runs the multi-source candidate ingestion pipeline:
    1. Parse CSV and/or PDF.
    2. Normalize all data points.
    3. Merge sources and resolve conflicts.
    4. Compute field-level and overall confidence scores.
    5. Track data provenance (origin source and method).
    6. Project output structure using runtime config.
    7. Validate projected output against schema.
    8. Write result to output path.
    """
    logger.info("Initializing Candidate Data Transformer Pipeline...")

    # Validate config file existence
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found at: {config_path}")
        raise typer.Exit(code=1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config JSON: {e}")
        raise typer.Exit(code=1)

    # 1. Parsing Phase
    csv_profile = None
    if csv:
        if os.path.exists(csv):
            logger.info(f"Parsing Recruiter CSV: {csv}...")
            from parsers.csv_parser import parse_recruiter_csv
            csv_profile = parse_recruiter_csv(csv)
        else:
            logger.warning(f"CSV file specified but not found at: {csv}. Proceeding without it.")
            
    resume_profile = None
    if resume:
        if os.path.exists(resume):
            logger.info(f"Parsing Resume PDF: {resume}...")
            from parsers.resume_parser import parse_resume_pdf
            resume_profile = parse_resume_pdf(resume)
        else:
            logger.warning(f"Resume PDF specified but not found at: {resume}. Proceeding without it.")

    if not csv_profile and not resume_profile:
        logger.error("No valid candidate sources were parsed. Execution aborted.")
        raise typer.Exit(code=1)

    # 2. Merging, Normalization, Confidence, & Provenance
    logger.info("Merging sources and applying conflict resolution policies...")
    from merge.merge_engine import merge_profiles
    canonical_profile = merge_profiles(
        csv_profile=csv_profile,
        resume_profile=resume_profile,
        csv_source_name=os.path.basename(csv) if csv else "recruiter.csv",
        resume_source_name=os.path.basename(resume) if resume else "resume.pdf"
    )

    # 3. Projection Phase
    logger.info("Projecting canonical profile using runtime configuration...")
    from projection.projector import project_candidate
    try:
        projected_candidate = project_candidate(canonical_profile, config)
    except Exception as e:
        logger.error(f"Error during projection layer: {e}")
        raise typer.Exit(code=1)

    # 4. Validation Phase
    logger.info("Validating projected candidate schema...")
    from validator.schema_validator import validate_projected_output, SchemaValidationError
    try:
        validate_projected_output(projected_candidate, config)
    except SchemaValidationError as e:
        logger.error(f"Schema validation failed: {e}")
        raise typer.Exit(code=1)

    # 5. Save Output
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(projected_candidate, f, indent=2)
        logger.info(f"Candidate profile successfully processed and saved to: {output_path}")
    except Exception as e:
        logger.error(f"Failed to write output candidate JSON to '{output_path}': {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
