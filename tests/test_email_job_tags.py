from pathlib import Path


def test_email_tag_helper_includes_job_applications():
    from routes.email_helpers import (
        EMAIL_CATEGORY_TAGS,
        EMAIL_MANAGED_TAGS,
        classify_job_application_stage,
        normalize_email_tag,
    )

    assert "job-applications" in EMAIL_CATEGORY_TAGS
    assert "job-recruiter" in EMAIL_CATEGORY_TAGS
    assert "job-interview" in EMAIL_CATEGORY_TAGS
    assert "job-assessment" in EMAIL_CATEGORY_TAGS
    assert "job-rejection" in EMAIL_CATEGORY_TAGS
    assert "job-offer" in EMAIL_CATEGORY_TAGS
    assert "job-application-update" in EMAIL_CATEGORY_TAGS
    assert "job-applications" in EMAIL_MANAGED_TAGS
    assert normalize_email_tag("job_applications") == "job-applications"
    assert normalize_email_tag("job applications") == "job-applications"
    assert normalize_email_tag("promo") == "marketing"
    assert classify_job_application_stage("Recruiter reaching out about a role") == "job-recruiter"
    assert classify_job_application_stage("Interview invitation for software engineer") == "job-interview"
    assert classify_job_application_stage("Please complete this coding assessment") == "job-assessment"
    assert classify_job_application_stage("We are not moving forward with your application") == "job-rejection"
    assert classify_job_application_stage("Offer letter attached") == "job-offer"
    assert classify_job_application_stage("Thanks for applying to our role") == "job-application-update"
    assert classify_job_application_stage("Talent Acquisition", "Interview invitation") == "job-interview"
    assert classify_job_application_stage("After your interview, offer letter attached") == "job-offer"


def test_email_library_exposes_job_application_filter():
    src = (Path(__file__).resolve().parents[1] / "static" / "js" / "emailLibrary.js").read_text(encoding="utf-8")
    assert 'value="tag:job-applications"' in src
    assert 'value="tag:job-recruiter"' in src
    assert 'value="tag:job-interview"' in src
    assert 'value="tag:job-assessment"' in src
    assert 'value="tag:job-rejection"' in src
    assert 'value="tag:job-offer"' in src
    assert 'value="tag:job-application-update"' in src


def test_email_styles_include_job_application_pill():
    src = (Path(__file__).resolve().parents[1] / "static" / "style.css").read_text(encoding="utf-8")
    assert ".email-tag-job-applications" in src
    assert ".email-tag-job-recruiter" in src
    assert ".email-tag-job-interview" in src
    assert ".email-tag-job-assessment" in src
    assert ".email-tag-job-rejection" in src
    assert ".email-tag-job-offer" in src
    assert ".email-tag-job-application-update" in src
