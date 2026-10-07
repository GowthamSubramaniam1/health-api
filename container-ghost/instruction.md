# Task: Container Ghost – Debugging a Production Docker Deployment

The production application at `/workspace/container-ghost` is deployed using Docker and is experiencing startup, connectivity, configuration, and health-check problems.

During recent deployments, the following issues have been observed:

1. The container may start successfully but the application is inaccessible from outside the container.
2. The application may start before a required dependency is ready.
3. Missing or invalid configuration can cause unpredictable startup behavior.
4. The container does not reliably report whether the application is ready to receive requests.
5. The Docker image may contain unnecessary files or dependencies and may not behave deterministically across clean builds.

Refactor the existing project so that the Docker deployment is deterministic, resilient, and compliant with the requirements below.

## Execution Interface

The application must be buildable and executable using Docker:

docker build -t container-ghost .

docker run --rm -p 8080:8080 container-ghost

## Operational Requirements

### 1. Network Binding

The application must:

- Listen on `0.0.0.0`.
- Use port `8080`.
- Be accessible through the published Docker port.
- Must not bind only to `127.0.0.1`.

### 2. Docker Image

The Docker image must:

- Use an appropriate base image.
- Install only required dependencies.
- Set an explicit working directory.
- Copy required application files.
- Start the correct application process.
- Avoid unnecessary packages.
- Avoid embedding secrets.

### 3. Environment Configuration

Application configuration must be supplied through environment variables where appropriate.

Required configuration must be validated.

Missing or invalid required configuration must produce a clear startup error.

Secrets must not be hard-coded into the Dockerfile or application configuration.

### 4. Health Check

The container must provide a meaningful health check.

The health check must verify that the application is actually responding and must use the correct application port.

A running process alone must not be considered sufficient proof that the application is healthy.

### 5. Dependency Readiness

If the application requires another service:

- Do not assume that the dependency is ready merely because its container has started.
- Use an appropriate readiness or health-check mechanism.
- Handle temporary dependency unavailability predictably.

### 6. Logging

Application logs must be available through Docker:

docker logs <container>

Important startup and runtime failures must be clearly reported.

Secrets must never be written to logs.

### 7. Container Lifecycle

The application must:

- Start successfully.
- Handle termination signals.
- Shut down cleanly.
- Restart without relying on state from a previous container.
- Exit with a non-zero status when an unrecoverable startup configuration error occurs.

### 8. Security

The deployment should:

- Avoid unnecessary privileges.
- Avoid unnecessary exposed ports.
- Avoid copying unnecessary files.
- Avoid storing secrets in the image.
- Use `.dockerignore` where appropriate.
- Run as a non-root user when compatible with the application.

## Validation Requirements

The implementation must be tested for:

1. Clean Docker build.
2. Normal container startup.
3. Application accessibility on port 8080.
4. Correct network binding.
5. Health-check success.
6. Missing configuration.
7. Invalid configuration.
8. Dependency unavailable.
9. Container restart.
10. Graceful shutdown.
11. Application logging.

## Constraints

- Use only technologies already required by the application.
- Do not introduce unnecessary third-party dependencies.
- Do not remove existing application functionality.
- Do not hard-code secrets.
- Do not change the public application interface unnecessarily.
- The deployment must work in an offline environment once required dependencies are available.
- Modify only files necessary to satisfy the requirements.

## Required Deliverable

Inspect the existing project before making changes.

Identify the root causes of the Docker deployment problems and implement the necessary fixes.

After implementing the changes, build and test the Docker deployment against the validation requirements above.

The final deployment must be deterministic, resilient, and suitable for production use.
