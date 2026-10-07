import subprocess
import sys
import time
import urllib.request
from pathlib import Path


IMAGE = "container-ghost"
CONTAINER = "container-ghost-eval"
PORT = 8080


def run(command):
    return subprocess.run(
        command,
        capture_output=True,
        text=True
    )


def cleanup():
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER],
        capture_output=True,
        text=True
    )


def check(condition, message):
    if condition:
        print(f"PASS: {message}")
        return True

    print(f"FAIL: {message}")
    return False


def image_id():
    result = run([
        "docker",
        "image",
        "inspect",
        IMAGE,
        "--format",
        "{{.Id}}"
    ])

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def main():
    results = []

    cleanup()

    # =================================================
    # Dockerfile static checks
    # =================================================

    dockerfile_path = Path("Dockerfile")

    if not dockerfile_path.exists():
        print("FAIL: Dockerfile exists")
        return 1

    dockerfile = dockerfile_path.read_text(
        encoding="utf-8"
    )

    results.append(
        check(
            "EXPOSE 8080" in dockerfile,
            "Dockerfile exposes port 8080"
        )
    )

    results.append(
        check(
            "0.0.0.0" in dockerfile
            or "APP_HOST" in dockerfile,
            "Dockerfile supports binding the application to 0.0.0.0"
        )
    )

    results.append(
        check(
            "HEALTHCHECK" in dockerfile,
            "Dockerfile defines a health check"
        )
    )

    results.append(
        check(
            "WORKDIR" in dockerfile,
            "Dockerfile defines a working directory"
        )
    )

    results.append(
        check(
            "FROM " in dockerfile,
            "Dockerfile specifies a base image"
        )
    )

    results.append(
        check(
            "CMD " in dockerfile,
            "Dockerfile specifies a startup command"
        )
    )

    results.append(
        check(
            "USER appuser" in dockerfile,
            "Dockerfile configures a non-root application user"
        )
    )

    # =================================================
    # Build
    # =================================================

    print()
    print("Building Docker image...")

    result = run([
        "docker",
        "build",
        "--pull=false",
        "-t",
        IMAGE,
        "."
    ])

    results.append(
        check(
            result.returncode == 0,
            "Docker image builds successfully"
        )
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        cleanup()
        return 1

    # =================================================
    # Invalid configuration
    # =================================================

    print()
    print("Testing invalid configuration...")

    invalid_cases = [
        ("APP_PORT", "abc", "non-numeric port"),
        ("APP_PORT", "0", "port below valid range"),
        ("APP_PORT", "99999", "port above valid range"),
    ]

    for variable, value, description in invalid_cases:
        result = run([
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python",
            "-e",
            f"{variable}={value}",
            "-e",
            "APP_HOST=0.0.0.0",
            IMAGE,
            "/app/server.py"
        ])

        output = result.stdout + result.stderr

        results.append(
            check(
                result.returncode != 0,
                f"Invalid configuration is rejected ({description})"
            )
        )

        results.append(
            check(
                "ERROR:" in output,
                f"Invalid configuration produces a clear error ({description})"
            )
        )

    # =================================================
    # Dependency readiness
    # =================================================

    print()
    print("Testing dependency configuration...")

    dependency_terms = [
        "depends_on",
        "redis",
        "postgres",
        "mysql",
        "mongodb",
        "rabbitmq",
        "kafka",
        "DATABASE_URL",
        "REDIS_URL"
    ]

    dependency_detected = any(
        term.lower() in dockerfile.lower()
        for term in dependency_terms
    )

    if dependency_detected:
        results.append(
            check(
                "HEALTHCHECK" in dockerfile,
                "Dependency configuration includes health handling"
            )
        )
    else:
        results.append(
            check(
                True,
                "Application does not require an external dependency"
            )
        )

    # =================================================
    # Secret handling
    # =================================================

    print()
    print("Testing secret handling...")

    secret_patterns = [
        "PASSWORD=",
        "PASSWORD ",
        "SECRET=",
        "SECRET ",
        "TOKEN=",
        "TOKEN ",
        "API_KEY=",
        "API_KEY ",
        "PRIVATE_KEY=",
        "PRIVATE_KEY ",
        "AWS_SECRET",
        "DATABASE_PASSWORD"
    ]

    dockerfile_lower = dockerfile.lower()

    hardcoded_secret = any(
        pattern.lower() in dockerfile_lower
        for pattern in secret_patterns
    )

    results.append(
        check(
            not hardcoded_secret,
            "Dockerfile does not contain obvious hard-coded secrets"
        )
    )

    env_result = run([
        "docker",
        "inspect",
        IMAGE,
        "--format",
        "{{range .Config.Env}}{{println .}}{{end}}"
    ])

    env_text = env_result.stdout.lower()

    suspicious_env = any(
        key in env_text
        for key in [
            "password=",
            "secret=",
            "token=",
            "api_key=",
            "private_key="
        ]
    )

    results.append(
        check(
            not suspicious_env,
            "Docker image environment does not contain obvious secrets"
        )
    )

    # =================================================
    # Docker image contents
    # =================================================

    print()
    print("Testing Docker image contents...")

    results.append(
        check(
            "COPY . /app" not in dockerfile,
            "Dockerfile avoids copying the entire project into the image"
        )
    )

    image_files = run([
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "sh",
        IMAGE,
        "-c",
        "find /app -maxdepth 1 -type f -printf '%f\\n'"
    ])

    image_file_list = set(
        line.strip()
        for line in image_files.stdout.splitlines()
        if line.strip()
    )

    unnecessary_files = {
        ".git",
        ".gitignore",
        "__pycache__",
        "eval.py",
        "instruction.md",
        "solve.sh"
    }

    found_unnecessary = sorted(
        image_file_list.intersection(unnecessary_files)
    )

    results.append(
        check(
            len(found_unnecessary) == 0,
            "Image does not contain unnecessary project files"
        )
    )

    # =================================================
    # Deterministic clean build
    # =================================================

    print()
    print("Testing deterministic clean build...")

    first_id = image_id()

    remove_result = run([
        "docker",
        "image",
        "rm",
        "-f",
        IMAGE
    ])

    results.append(
        check(
            remove_result.returncode == 0,
            "Docker image can be removed cleanly"
        )
    )

    rebuild_result = run([
        "docker",
        "build",
        "--pull=false",
        "-t",
        IMAGE,
        "."
    ])

    results.append(
        check(
            rebuild_result.returncode == 0,
            "Clean Docker rebuild succeeds"
        )
    )

    second_id = image_id()

    results.append(
        check(
            bool(first_id) and bool(second_id),
            "Docker image has a valid identity after clean rebuild"
        )
    )

    # =================================================
    # Missing configuration
    # =================================================

    print()
    print("Testing missing configuration...")

    missing_config = run([
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "python",
        IMAGE,
        "/app/server.py"
    ])

    missing_output = (
        missing_config.stdout
        + missing_config.stderr
    )

    results.append(
        check(
            missing_config.returncode != 0,
            "Container fails when required configuration is missing"
        )
    )

    results.append(
        check(
            "APP_HOST" in missing_output
            or "APP_PORT" in missing_output,
            "Missing configuration produces a clear error"
        )
    )

    # =================================================
    # Normal startup
    # =================================================

    print()
    print("Starting container...")

    result = run([
        "docker",
        "run",
        "-d",
        "--name",
        CONTAINER,
        "-p",
        f"{PORT}:{PORT}",
        "-e",
        "APP_HOST=0.0.0.0",
        "-e",
        "APP_PORT=8080",
        IMAGE
    ])

    results.append(
        check(
            result.returncode == 0,
            "Container starts successfully"
        )
    )

    if result.returncode != 0:
        print(result.stderr)
        cleanup()
        return 1

    time.sleep(3)

    # =================================================
    # Container inspection
    # =================================================

    inspect = run([
        "docker",
        "inspect",
        CONTAINER
    ])

    results.append(
        check(
            inspect.returncode == 0,
            "Container can be inspected"
        )
    )

    # =================================================
    # Runtime user
    # =================================================

    user = run([
        "docker",
        "exec",
        CONTAINER,
        "id",
        "-u"
    ])

    results.append(
        check(
            user.stdout.strip() != "0",
            "Container runs as a non-root user"
        )
    )

    # =================================================
    # Health endpoint
    # =================================================

    try:
        response = urllib.request.urlopen(
            "http://localhost:8080/health",
            timeout=5
        )

        body = response.read().decode()

        results.append(
            check(
                response.status == 200,
                "Health endpoint returns HTTP 200"
            )
        )

        results.append(
            check(
                body == "healthy",
                "Health endpoint returns healthy response"
            )
        )

    except Exception as exc:
        print(f"FAIL: Application is reachable: {exc}")
        results.append(False)
        results.append(False)

    # =================================================
    # Docker health
    # =================================================

    health = run([
        "docker",
        "inspect",
        "--format",
        "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        CONTAINER
    ])

    results.append(
        check(
            health.stdout.strip() == "healthy",
            "Docker health status is healthy"
        )
    )

    # =================================================
    # Logging
    # =================================================

    logs = run([
        "docker",
        "logs",
        CONTAINER
    ])

    results.append(
        check(
            "Server listening" in logs.stdout,
            "Application produces startup logs"
        )
    )

    log_text = logs.stdout + logs.stderr

    results.append(
        check(
            not any(
                value in log_text.lower()
                for value in [
                    "password=",
                    "secret=",
                    "token=",
                    "api_key="
                ]
            ),
            "Application logs do not expose obvious secrets"
        )
    )

    # =================================================
    # Graceful shutdown
    # =================================================

    print()
    print("Testing graceful shutdown...")

    stop_result = run([
        "docker",
        "stop",
        "-t",
        "5",
        CONTAINER
    ])

    results.append(
        check(
            stop_result.returncode == 0,
            "Container stops successfully"
        )
    )

    status = run([
        "docker",
        "inspect",
        "--format",
        "{{.State.Status}}",
        CONTAINER
    ])

    results.append(
        check(
            status.stdout.strip() == "exited",
            "Container exits cleanly"
        )
    )

    # =================================================
    # Restart behavior
    # =================================================

    print()
    print("Testing container restart...")

    start_again = run([
        "docker",
        "start",
        CONTAINER
    ])

    results.append(
        check(
            start_again.returncode == 0,
            "Container can restart successfully"
        )
    )

    if start_again.returncode == 0:
        time.sleep(2)

        try:
            response = urllib.request.urlopen(
                "http://localhost:8080/health",
                timeout=5
            )

            results.append(
                check(
                    response.status == 200,
                    "Application remains healthy after restart"
                )
            )

        except Exception as exc:
            print(
                f"FAIL: Application is not healthy after restart: {exc}"
            )
            results.append(False)

    # =================================================
    # Cleanup
    # =================================================

    cleanup()

    # =================================================
    # Final result
    # =================================================

    print()
    print("================================")
    print("Container Ghost Evaluation")
    print("================================")

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if all(results):
        print("RESULT: PASS")
        return 0

    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
