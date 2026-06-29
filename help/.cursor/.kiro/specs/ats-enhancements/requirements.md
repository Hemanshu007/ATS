# Requirements Document

## Introduction

This document specifies the requirements for a comprehensive set of enhancements to the Applicant Tracking System (ATS). The enhancements span critical bug fixes and race condition handling, resume storage migration from local filesystem to AWS S3, pagination and filtering on list endpoints, soft delete for job postings, additional API endpoints for companies/recruiters/candidates/documents, and non-blocking email delivery. The implementation targets 36 total API endpoints upon completion.

## Glossary

- **ATS**: The Applicant Tracking System — the FastAPI-based backend application
- **Application_Service**: The service layer responsible for creating and managing job applications
- **Status_Machine**: The component enforcing allowed status transitions on applications
- **S3_Service**: The service layer responsible for uploading, downloading, and deleting files in AWS S3
- **Migration_Script**: A one-time CLI script to move existing local resume files to S3
- **Pagination_Handler**: The component providing limit/offset-based pagination on list endpoints
- **Filter_Handler**: The component applying query parameter filters to list endpoints
- **Job_Service**: The service layer managing job postings including soft delete logic
- **Company_Router**: The router exposing company-related endpoints
- **Recruiter_Dashboard**: The router exposing recruiter pipeline and job summary endpoints
- **Candidate_Dashboard**: The router exposing candidate profile and application summary endpoints
- **Document_Router**: The router exposing document management endpoints
- **Health_Router**: The router exposing health and readiness probe endpoints
- **Email_Service**: The service responsible for sending transactional emails via SMTP or AWS SES
- **Resume**: A PDF document uploaded by a candidate as part of a job application
- **Presigned_URL**: A time-limited URL granting temporary access to an S3 object without authentication
- **Status_Transition**: A change from one application status to another following the allowed state machine
- **Soft_Delete**: Marking a record as deleted without physically removing it from the database
- **Interview_Round**: A scheduled interview stage within an application's hiring pipeline
- **BackgroundTasks**: FastAPI's built-in mechanism for running functions after the response is sent

## Requirements

### Requirement 1: Atomic Transaction on Application Creation

**User Story:** As a candidate, I want my job application to be created atomically, so that partial data is never persisted if any step fails.

#### Acceptance Criteria

1. WHEN a candidate submits an application, THE Application_Service SHALL insert the Document record, Application record, and ApplicationStatusHistory record (with status set to "applied") within a single database transaction
2. IF any insert within the application creation transaction fails, THEN THE Application_Service SHALL roll back all inserts performed in that transaction and return an error response with HTTP 400 containing a message indicating the reason for failure
3. WHEN the transaction commits successfully, THE Application_Service SHALL return the created application resource (including id, job_id, candidate_id, document_id, current_status, and applied_at) with HTTP 201
4. IF a candidate has already applied to the same job, THEN THE Application_Service SHALL reject the submission and return an error response with HTTP 400 indicating a duplicate application

### Requirement 2: Duplicate Application Race Condition Handling

**User Story:** As a candidate, I want to receive a clear error if I apply to the same job twice, so that duplicate applications are never created even under concurrent requests.

#### Acceptance Criteria

1. WHEN a candidate submits an application for a job where an application from the same candidate already exists in the database, THE Application_Service SHALL return HTTP 400 with a response body containing an error message indicating the candidate has already applied to this job
2. IF a database IntegrityError occurs due to the unique constraint on (job_id, candidate_id) during commit, THEN THE Application_Service SHALL roll back the transaction and return HTTP 400 with a response body containing an error message indicating the candidate has already applied to this job
3. THE Application_Service SHALL enforce a database-level unique constraint on the combination of (job_id, candidate_id) as the authoritative duplicate check, ensuring that concurrent requests cannot both succeed
4. IF a duplicate application is detected either by application-level query or by database IntegrityError, THEN THE Application_Service SHALL ensure that no orphan Document record or uploaded resume file persists for the rejected duplicate submission
5. IF a database error other than a unique-constraint IntegrityError occurs during application creation, THEN THE Application_Service SHALL roll back the transaction and return HTTP 400 with a response body containing an error message indicating the application could not be created

### Requirement 3: Pessimistic Locking on Job During Application

**User Story:** As a candidate, I want to be prevented from applying to a job that is being concurrently closed, so that applications are only accepted for genuinely open jobs.

#### Acceptance Criteria

1. WHEN a candidate submits an application, THE Application_Service SHALL acquire a row-level lock (SELECT FOR UPDATE) on the target Job row before validating its status, waiting no longer than 5 seconds for lock acquisition
2. WHILE the Job row is locked by an application transaction, THE Job_Service SHALL queue concurrent status-change requests on that Job until the lock is released, enforced by the database row-level lock
3. IF the locked Job has a status other than "open", THEN THE Application_Service SHALL reject the application with an error response indicating the job is not available, and SHALL NOT persist the application record or associated document
4. IF the row-level lock on the Job cannot be acquired within 5 seconds, THEN THE Application_Service SHALL return an error response indicating a temporary conflict and the candidate may retry the submission

### Requirement 4: Application Status Transition State Machine

**User Story:** As a recruiter, I want status changes to follow a defined workflow, so that applications cannot skip stages or revert to invalid states.

#### Acceptance Criteria

1. THE Status_Machine SHALL enforce the following allowed transitions: "applied" to "screening", "screening" to "interview", "interview" to "offer", "offer" to "hired", "applied" to "rejected", "screening" to "rejected", "interview" to "rejected", "offer" to "rejected"
2. IF a recruiter attempts a status change that violates the allowed transitions, THEN THE Status_Machine SHALL reject the request with HTTP 422 and return an error response containing the current status and the attempted status
3. IF a recruiter attempts to change the status to the same value as the current status, THEN THE Status_Machine SHALL reject the request with HTTP 422 and return an error message indicating no-op transitions are not permitted
4. IF the Status_Machine rejects a transition, THEN THE Status_Machine SHALL NOT create a status history record and SHALL preserve the application's current status unchanged

### Requirement 5: Unique Constraint on Interview Round Number

**User Story:** As a recruiter, I want to be prevented from creating duplicate round numbers for the same application, so that interview scheduling remains consistent.

#### Acceptance Criteria

1. THE ATS SHALL enforce a database-level unique constraint on (application_id, round_number) in the interview_rounds table
2. IF the round_number provided is less than 1 or greater than 100, THEN THE ATS SHALL return HTTP 422 with an error message indicating the round number must be between 1 and 100 inclusive
3. IF a duplicate round number is submitted for the same application, THEN THE ATS SHALL return HTTP 409 with the message "Round {N} already exists for this application"
4. WHEN a new interview round is created with a unique round number for the given application, THE ATS SHALL persist it and return HTTP 201 with the created interview round resource

### Requirement 6: File Validation on Resume Upload

**User Story:** As a system administrator, I want to restrict resume uploads to PDF files under 5MB, so that storage is used efficiently and only valid document types are accepted.

#### Acceptance Criteria

1. WHEN a candidate uploads a resume with content type "application/pdf" and file size between 1 byte and 5,242,880 bytes (5MB), THE Application_Service SHALL accept the file, store it, and associate it with the candidate's application
2. IF the uploaded file's content type is not "application/pdf", THEN THE Application_Service SHALL reject the upload and return an error indicating that only PDF files are allowed
3. IF the uploaded file size exceeds 5,242,880 bytes (5MB), THEN THE Application_Service SHALL reject the upload and return an error indicating the file size limit has been exceeded
4. IF the uploaded file is empty (0 bytes), THEN THE Application_Service SHALL reject the upload and return an error indicating that the file is empty
5. IF no file is attached to the upload request, THEN THE Application_Service SHALL reject the upload and return an error indicating that a resume file is required

### Requirement 7: AWS S3 Service Implementation

**User Story:** As a system administrator, I want resumes stored in AWS S3, so that the system scales beyond a single server and benefits from durable cloud storage.

#### Acceptance Criteria

1. THE S3_Service SHALL upload files to the configured S3 bucket using the boto3 SDK with a key format of "resumes/{candidate_id}/{uuid}/{filename}", accepting only files with content type application/pdf
2. THE S3_Service SHALL generate presigned download URLs with a configurable expiration defaulting to 3600 seconds, accepting expiration values between 60 and 604800 seconds
3. THE S3_Service SHALL delete objects from S3 given a storage key, treating deletion of a non-existent key as a successful operation
4. IF any required environment variable (S3_BUCKET_NAME, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) is missing at service initialization, THEN THE S3_Service SHALL raise a configuration error preventing application startup
5. IF an S3 upload, presigned URL generation, or delete operation fails due to a network or AWS service error, THEN THE S3_Service SHALL log the error at ERROR level and raise an HTTP 502 exception indicating the storage operation failure

### Requirement 8: Migration Script for Local Resumes to S3

**User Story:** As a system administrator, I want to migrate all existing locally stored resumes to S3, so that the system can fully transition to cloud storage without data loss.

#### Acceptance Criteria

1. WHEN the Migration_Script is executed, THE Migration_Script SHALL read all Document records from the database whose file_path does not already contain an S3 key prefix, and upload each corresponding local file to S3 using the key format "resumes/{document_id}/{original_filename}"
2. WHEN a file is successfully uploaded to S3, THE Migration_Script SHALL update the Document record's file_path to the new S3 key within the same transaction
3. IF a local file referenced by a Document record does not exist, THEN THE Migration_Script SHALL log a warning including the Document record ID and missing file path, and continue processing remaining documents
4. IF an S3 upload fails for a Document record, THEN THE Migration_Script SHALL log an error including the Document record ID and failure reason, skip that record, and continue processing remaining documents
5. THE Migration_Script SHALL report a summary upon completion including: total documents evaluated, documents skipped (already migrated), successful migrations, and failures
6. WHEN the Migration_Script is re-executed, THE Migration_Script SHALL skip Document records whose file_path already contains an S3 key prefix, ensuring the script is idempotent and safe to re-run after partial failures

### Requirement 9: Application Endpoint Uses S3 for Resume Storage

**User Story:** As a candidate, I want my uploaded resume to be stored in S3 when I apply, so that it is durably stored in the cloud.

#### Acceptance Criteria

1. WHEN a candidate submits an application with a resume, THE Application_Service SHALL upload the resume to S3 via the S3_Service before creating the Document record
2. WHEN the S3 upload succeeds, THE Application_Service SHALL store the returned S3 key in the Document record's file_path field instead of a local filesystem path
3. IF the S3 upload fails, THEN THE Application_Service SHALL not persist the Document record or Application record to the database and SHALL return HTTP 500 with an error message indicating the upload failed
4. WHEN a candidate submits an application with a resume, THE Application_Service SHALL not write the resume file to the local filesystem

### Requirement 10: Resume Download Endpoint

**User Story:** As a recruiter, I want to download a candidate's resume via a secure presigned URL, so that I can review application materials without direct S3 access.

#### Acceptance Criteria

1. WHEN a recruiter requests a resume download for an application whose job posting they own, THE ATS SHALL return a presigned S3 URL for the associated document that expires after 3600 seconds
2. IF the application does not exist, THEN THE ATS SHALL return HTTP 404
3. IF the recruiter does not own the job posting associated with the application, THEN THE ATS SHALL return HTTP 403
4. IF the application has no associated document in storage, THEN THE ATS SHALL return HTTP 404 with an error message indicating the resume is unavailable

### Requirement 11: Pagination on List Endpoints

**User Story:** As an API consumer, I want paginated responses on all list endpoints, so that large result sets are returned in manageable pages with metadata.

#### Acceptance Criteria

1. THE Pagination_Handler SHALL accept "limit" (integer, minimum 1, default 20, maximum 100) and "offset" (integer, minimum 0, default 0) query parameters on GET /jobs/, GET /applications/job/{id}, GET /applications/me, and GET /companies/
2. THE Pagination_Handler SHALL return a response envelope containing "items" (array of matching resources for the current page), "total" (integer representing the total count of all matching resources regardless of pagination), "limit" (integer applied for the request), and "offset" (integer applied for the request)
3. WHEN a limit value is less than 1, THE Pagination_Handler SHALL clamp it to 1, and WHEN a limit value exceeds 100, THE Pagination_Handler SHALL clamp it to 100, without raising an error
4. WHEN an offset value is less than 0, THE Pagination_Handler SHALL clamp it to 0 without raising an error
5. WHEN the offset value is greater than or equal to the total number of matching resources, THE Pagination_Handler SHALL return an empty "items" array with the accurate "total" count

### Requirement 12: Filter Applications by Status

**User Story:** As a recruiter, I want to filter applications by their current status, so that I can focus on candidates at a specific pipeline stage.

#### Acceptance Criteria

1. WHEN the "status" query parameter is provided on GET /applications/job/{id}, THE Filter_Handler SHALL return only applications whose current_status matches the parameter value using case-sensitive comparison, applying any existing pagination (limit/offset) to the filtered result set
2. IF the "status" query parameter value is not one of the recognized statuses ("applied", "screening", "interview", "offer", "hired", "rejected"), THEN THE Filter_Handler SHALL return HTTP 422 with a response body containing a validation error message indicating the unrecognized status value
3. WHEN no "status" query parameter is provided, THE Filter_Handler SHALL return all applications for the specified job without status filtering
4. WHEN the "status" query parameter matches a recognized status but no applications exist with that status for the given job, THE Filter_Handler SHALL return an empty list with HTTP 200

### Requirement 13: Filter Jobs by Type and Location

**User Story:** As a candidate, I want to filter job listings by type and location, so that I can find relevant positions quickly.

#### Acceptance Criteria

1. WHEN the "job_type" query parameter is provided on GET /jobs/, THE Filter_Handler SHALL return only jobs whose job_type matches the parameter value exactly (case-sensitive)
2. WHEN the "location" query parameter is provided on GET /jobs/, THE Filter_Handler SHALL return only jobs whose location contains the parameter value (case-insensitive partial match)
3. WHEN both "job_type" and "location" parameters are provided, THE Filter_Handler SHALL apply both filters as an AND condition
4. WHEN no filter parameters are provided, THE Filter_Handler SHALL return all open jobs without additional filtering
5. IF the "job_type" query parameter value is not one of the recognized types ("onsite", "remote", "hybrid"), THEN THE Filter_Handler SHALL return HTTP 422 with a validation error

### Requirement 14: Soft Delete on Jobs

**User Story:** As a recruiter, I want to soft-delete a job posting, so that closed jobs are hidden from candidates but data is preserved for reporting.

#### Acceptance Criteria

1. THE Job_Service SHALL add "is_deleted" (boolean, default false) and "deleted_at" (nullable timestamp) columns to the jobs table
2. WHEN a recruiter deletes a job, THE Job_Service SHALL set is_deleted to true and deleted_at to the current UTC timestamp instead of removing the row
3. THE Job_Service SHALL exclude soft-deleted jobs from GET /jobs/ listing results by default
4. WHEN a client requests GET /jobs/{job_id} for a soft-deleted job, THE Job_Service SHALL return HTTP 404
5. IF a recruiter attempts to delete a job that has at least one application with status "applied", "screening", "interview", or "offer", THEN THE Job_Service SHALL return HTTP 409 with a message indicating the job cannot be deleted due to active applications
6. IF the requesting recruiter does not own the job (created_by does not match the recruiter's id), THEN THE Job_Service SHALL return HTTP 403 before performing the soft delete
7. IF a recruiter attempts to delete a job that is already soft-deleted, THEN THE Job_Service SHALL return HTTP 404

### Requirement 15: Company Endpoints

**User Story:** As an API consumer, I want endpoints to list and view company details, so that candidates can browse employers and recruiters can manage their company profile.

#### Acceptance Criteria

1. WHEN a GET request is made to /companies/, THE Company_Router SHALL return a paginated list of all companies using limit (default 20, maximum 100) and offset (default 0, minimum 0) query parameters
2. WHEN a GET request is made to /companies/{id}, THE Company_Router SHALL return the company details including the count of jobs with status "open" associated with that company
3. IF a GET request is made to /companies/{id} and no company exists with the given id, THEN THE Company_Router SHALL return an HTTP 404 response
4. WHEN a GET request is made to /companies/{id}/jobs, THE Company_Router SHALL return a paginated list of jobs with status "open" for that company using limit (default 20, maximum 100) and offset (default 0, minimum 0) query parameters
5. IF a GET request is made to /companies/{id}/jobs and no company exists with the given id, THEN THE Company_Router SHALL return an HTTP 404 response
6. WHEN an authenticated recruiter makes a GET request to /companies/me, THE Company_Router SHALL return the company details associated with the recruiter's company_id
7. WHEN an authenticated recruiter makes a PATCH request to /companies/me with valid fields, THE Company_Router SHALL update only the provided mutable fields (name max 150 characters, industry max 100 characters, location max 100 characters) and return the updated company record
8. IF an authenticated recruiter makes a PATCH request to /companies/me with field values exceeding the maximum allowed length, THEN THE Company_Router SHALL return an HTTP 422 response indicating the validation failure

### Requirement 16: Recruiter Dashboard Endpoints

**User Story:** As a recruiter, I want dashboard endpoints showing my pipeline and job summaries, so that I can quickly assess hiring progress.

#### Acceptance Criteria

1. WHEN an authenticated recruiter makes a GET request to /recruiter/dashboard/pipeline, THE Recruiter_Dashboard SHALL return a JSON object containing an application count for each of the defined status values (applied, screening, interview, offer, hired, rejected) aggregated across all jobs created by that recruiter, including statuses with a count of zero
2. WHEN an authenticated recruiter makes a GET request to /recruiter/dashboard/my-jobs, THE Recruiter_Dashboard SHALL return a paginated list of the recruiter's jobs ordered by creation date descending, where each entry includes the job id, title, job status, and total application count for that job
3. IF the recruiter has no jobs, THEN THE Recruiter_Dashboard SHALL return an empty list for the my-jobs endpoint and all-zero counts for the pipeline endpoint
4. IF a request to /recruiter/dashboard/pipeline or /recruiter/dashboard/my-jobs is made without valid authentication or by a non-recruiter user, THEN THE Recruiter_Dashboard SHALL reject the request with an appropriate HTTP error status and an error message indicating the authorization failure

### Requirement 17: Candidate Dashboard Endpoints

**User Story:** As a candidate, I want dashboard endpoints showing my profile and application summary, so that I can track my job search progress.

#### Acceptance Criteria

1. WHEN an authenticated candidate makes a GET request to /candidate/profile, THE Candidate_Dashboard SHALL return the candidate's profile information including name, phone, location, and the email from the associated user account
2. WHEN an authenticated candidate makes a PATCH request to /candidate/profile with at least one valid field (name, phone, location), THE Candidate_Dashboard SHALL update only the provided mutable fields, enforce maximum lengths (name: 100 characters, phone: 20 characters, location: 100 characters), and return the full updated profile record
3. IF an authenticated candidate makes a PATCH request to /candidate/profile with field values exceeding maximum lengths or with an empty request body containing no recognized fields, THEN THE Candidate_Dashboard SHALL reject the request and return an error response indicating the validation failure
4. WHEN an authenticated candidate makes a GET request to /candidate/dashboard, THE Candidate_Dashboard SHALL return a summary containing the total applications count and a breakdown of applications grouped by current_status (applied, screening, interview, offer, hired, rejected), including groups with zero count
5. IF a non-candidate user (recruiter) makes a request to any /candidate/* endpoint, THEN THE Candidate_Dashboard SHALL reject the request with a 403 Forbidden response indicating that candidate access is required

### Requirement 18: Application Detail Endpoint

**User Story:** As a recruiter, I want to view complete application details including interview rounds and status history, so that I have full context when making hiring decisions.

#### Acceptance Criteria

1. WHEN a recruiter makes a GET request to /applications/{id}, THE ATS SHALL return the application record including candidate name, job title, current status, applied date, interview rounds ordered by round number, and status history ordered chronologically from oldest to newest
2. WHEN a recruiter makes a GET request to /applications/{id}, THE ATS SHALL verify that the requesting recruiter owns the job posting associated with the application before returning the data
3. IF the recruiter does not own the job posting, THEN THE ATS SHALL return HTTP 403
4. IF no application exists with the given id, THEN THE ATS SHALL return HTTP 404 with an error message indicating the application was not found

### Requirement 19: Interview Round Detail and Cancel

**User Story:** As a recruiter, I want to view interview round details and cancel scheduled interviews, so that I can manage interview logistics.

#### Acceptance Criteria

1. WHEN a recruiter makes a GET request to /interviews/{id}, THE ATS SHALL return the interview round record including id, application_id, round_number, scheduled_at, conducted_by, outcome, notes, and created_at
2. WHEN a recruiter makes a PATCH request to /interviews/{id}/cancel, THE ATS SHALL set the interview outcome to "cancelled" and return the updated record
3. IF the interview round has already been conducted (outcome is "pass" or "fail"), THEN THE ATS SHALL return HTTP 409 with the message "Cannot cancel a completed interview" and leave the interview record unchanged
4. IF the interview round outcome is already "cancelled" when a cancel request is received, THEN THE ATS SHALL return HTTP 409 with the message "Cannot cancel a completed interview" and leave the interview record unchanged
5. IF the requesting recruiter does not own the job posting associated with the interview's application, THEN THE ATS SHALL return HTTP 403 and not disclose the interview details
6. IF the interview ID in a GET or PATCH cancel request does not correspond to an existing interview round, THEN THE ATS SHALL return HTTP 404

### Requirement 20: Document Management Endpoints

**User Story:** As a candidate, I want to list and delete my uploaded documents, so that I can manage my application materials.

#### Acceptance Criteria

1. WHEN an authenticated candidate makes a GET request to /documents/me, THE Document_Router SHALL return a paginated list of all documents uploaded by that candidate, supporting limit (default 20, maximum 100) and offset (default 0) query parameters
2. WHEN an authenticated candidate makes a DELETE request to /documents/{id} for a document they own that is not referenced by an active application, THE Document_Router SHALL delete the stored file from S3, remove the Document record from the database, and return HTTP 200
3. IF the document referenced in a DELETE request is linked to an active application (status is not "hired" or "rejected"), THEN THE Document_Router SHALL return HTTP 409 with a message indicating the document cannot be deleted because it is linked to an active application
4. IF the requesting candidate does not own the document specified in a DELETE request, THEN THE Document_Router SHALL return HTTP 403
5. IF the document ID in a DELETE request does not correspond to any existing document, THEN THE Document_Router SHALL return HTTP 404

### Requirement 21: Health and Readiness Endpoints

**User Story:** As a DevOps engineer, I want health and readiness endpoints, so that container orchestrators can properly manage application lifecycle.

#### Acceptance Criteria

1. WHEN a GET request is made to /health, THE Health_Router SHALL return HTTP 200 with a JSON body containing {"status": "ok"} within 2 seconds
2. WHEN a GET request is made to /ready, THE Health_Router SHALL verify database connectivity within a 5-second timeout and return HTTP 200 with {"status": "ready", "database": "connected"} if the database responds within that timeout
3. IF the database does not respond within the 5-second timeout or the connection is refused during a readiness check, THEN THE Health_Router SHALL return HTTP 503 with {"status": "not_ready", "database": "disconnected"}
4. IF an unexpected error occurs while processing a request to /health or /ready, THEN THE Health_Router SHALL return HTTP 503 with a JSON body containing {"status": "error"} and SHALL NOT expose internal error details in the response

### Requirement 22: Non-Blocking Email Delivery

**User Story:** As a candidate, I want status change notifications to be sent without delaying the API response, so that the recruiter's workflow is not blocked by email delivery.

#### Acceptance Criteria

1. WHEN an application status is changed, THE Email_Service SHALL dispatch the notification email asynchronously such that the HTTP response is returned to the caller independently of email delivery duration
2. WHEN the notification email is dispatched, THE Email_Service SHALL send it only after the application status change has been successfully committed to the database
3. IF email delivery fails due to a transport error, THEN THE Email_Service SHALL log the failure at ERROR level including the candidate email (masked), job title, and error reason, without raising an exception to the caller or affecting the HTTP response status
4. IF the email transport environment variable is not set or contains an invalid value, THEN THE Email_Service SHALL fall back to logging the email content at INFO level instead of attempting delivery
5. THE Email_Service SHALL support configuration for either SMTP or AWS SES as the email transport, selected via an environment variable
