Task: Health API – Production Service Reliability and Configuration

The production HTTP service at /workspace/health-api is deployed in containerized environments and is experiencing configuration, networking, health-check, logging, and lifecycle problems.

During recent deployments, the following issues have been observed:

The service may start with missing or invalid configuration and fail later instead of rejecting the configuration during startup.

The application may bind to a local-only interface, making it inaccessible from outside the container.

The service does not reliably distinguish between a running process and an application that is ready to receive requests.

Health monitoring may report an incorrect status when the HTTP service is unavailable.

Malformed configuration values may cause unclear or unhandled startup failures.

The container does not consistently shut down and restart cleanly.

Important startup and runtime failures are not reliably visible through container logs.

Refactor the existing project so that the service is deterministic, resilient, and compliant with the operational contract below.

Execution Interface

The service must be buildable and executable using Docker:

docker build -t health-api .
docker run --rm -p 8080:8080 -e APP_HOST=0.0.0.0 -e APP_PORT=8080 health-api


The application must provide an HTTP service accessible through port 8080.

Operational Requirements
1. Network Binding

The application must:

Listen on 0.0.0.0.

Use port 8080.

Be accessible through the published Docker port.

Must not bind exclusively to 127.0.0.1.

2. Environment Configuration

The application must obtain its host and port configuration from environment variables.

Required configuration:

APP_HOST

APP_PORT

APP_HOST must be configured as 0.0.0.0.

APP_PORT must represent a valid TCP port between 1 and 65535.

The application must reject:

Missing APP_HOST.

Empty APP_HOST.

An APP_HOST value other than 0.0.0.0.

Missing APP_PORT.

Empty APP_PORT.

Non-numeric APP_PORT.

A port value below 1.

A port value above 65535.

Invalid configuration must produce a clear startup error and terminate with a non-zero exit status.

Configuration must be validated before the application begins serving requests.

3. HTTP Service

The application must provide a health endpoint at /health.

A successful health request must return:

HTTP status 200.

Response body healthy.

The service must continue to provide its existing root HTTP functionality.

A request to / must return a successful HTTP response.

4. Health Check

The container must provide a meaningful Docker health check.

The health check must verify that the HTTP application is actually responding on port 8080.

A running application process alone must not be considered sufficient proof that the service is healthy.

The container must report an unhealthy state when the application cannot successfully respond to the health endpoint.

5. Docker Image

The Docker image must:

Use an appropriate Python base image.

Define an explicit working directory.

Include only files required for runtime operation.

Install only dependencies required by the application.

Expose port 8080.

Start the correct application process.

Avoid unnecessary operating-system packages.

Avoid copying development and evaluation artifacts unnecessarily.

The runtime image must not unnecessarily contain evaluator scripts, task instructions, reference solution files, source-control metadata, or other development-only files.

6. Security

The application must run without requiring root privileges.

The container must use a dedicated non-root application user.

The deployment must not embed passwords, tokens, API keys, private keys, or other credentials into the image.

Secrets must not be hard-coded into application configuration.

The runtime environment should contain only the privileges and files required by the application.

7. Logging

Application startup and runtime failures must be visible through Docker container logs.

Successful startup must produce a recognizable message indicating that the server is listening.

Configuration failures must produce clear diagnostic information.

Unexpected runtime failures must not be silently ignored.

Secrets must never be written to application logs.

8. Container Lifecycle

The application must:

Start successfully with valid configuration.

Reject invalid startup configuration.

Exit with a non-zero status for unrecoverable startup errors.

Handle normal container termination.

Shut down the HTTP service cleanly.

Release resources during shutdown.

Restart successfully using valid configuration.

Remain functional after restart.

Avoid relying on state from a previous container instance.

9. Dependency Requirements

The service must not require an external database, cache, message broker, or other network service for normal operation.

Do not introduce an unnecessary external dependency merely to satisfy this task.

The application must remain capable of operating in an offline environment once the required runtime is available.

10. Build Determinism

A clean Docker build must succeed after the previous image has been removed.

The deployment must not depend on files generated by a previous container or build.

Fresh containers created from the image must behave consistently.

The image construction must not rely on unnecessary external services.

11. Application Availability

After successful startup:

The application must be reachable through port 8080.

The root endpoint must respond successfully.

The health endpoint must return the expected healthy response.

Docker health status must eventually become healthy.

The service must remain functional after a container restart.

Validation Requirements

The implementation must be tested for:

Clean Docker build.

Normal container startup.

Application accessibility on port 8080.

Correct network binding.

Missing host configuration.

Missing port configuration.

Invalid host configuration.

Non-numeric port configuration.

Port values outside the valid range.

Successful root endpoint response.

Successful health endpoint response.

Correct health response body.

Docker health-check configuration.

Docker health status.

Non-root container execution.

Minimal runtime image contents.

Absence of hard-coded secrets.

Deterministic clean rebuild.

Startup logging.

Secret-free logging.

Graceful container shutdown.

Successful container restart.

Application availability after restart.

Exit Behavior

The application must exit with a non-zero status when mandatory startup configuration is missing or invalid.

Normal termination must allow the application to shut down cleanly.

The application must not continue serving requests after an unrecoverable startup configuration error.

Constraints

Use only technologies already required by the application.

Use the Python standard library where sufficient.

Do not introduce unnecessary third-party dependencies.

Do not remove existing application functionality.

Do not unnecessarily change the public HTTP interface.

Do not hard-code secrets.

Do not require an external service for normal operation.

The deployment must operate offline once required dependencies are available.

Modify only files necessary to satisfy the requirements.

Inspect the existing project before making changes.

Required Deliverable

Inspect the existing /workspace/health-api project and identify the root causes of the configuration, networking, health-check, logging, and lifecycle problems.

Implement the necessary changes while preserving existing application functionality.

After implementing the changes, build and test the Docker deployment against the validation requirements above.

The final deployment must be deterministic, resilient, secure, and suitable for production use.
Git diff practice