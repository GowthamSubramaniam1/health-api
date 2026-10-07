import subprocess
import sys
import time
import urllib.request
from pathlib import Path


IMAGE = "health-api"
CONTAINER = "health-api-eval"
PORT = 8080


def run(command, timeout=10):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            command,
            124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\nTIMEOUT"
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


def main():
    results = []

    cleanup()

    dockerfile_path = Path("Dockerfile")

    results.append(
        check(
            dockerfile_path.exists(),
            "Dockerfile exists"
        )
    )

    if not dockerfile_path.exists():
        return 1

    dockerfile = dockerfile_path.read_text(
        encoding="utf-8"
    )

    # Dockerfile checks

    results.append(
        check(
            "FROM " in dockerfile,
            "Dockerfile specifies a base image"
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
            "EXPOSE 8080" in dockerfile,
            "Dockerfile exposes port 8080"
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
            "USER " in dockerfile,
            "Dockerfile configures a runtime user"
        )
    )

    results.append(
        check(
            "0.0.0.0" in dockerfile
            or "APP_HOST" in dockerfile,
            "Dockerfile supports 0.0.0.0 binding"
        )
    )

    # Build

    print()
    print("Building Docker image...")

    build = run([
        "docker",
        "build",
        "--pull=false",
        "-t",
        IMAGE,
        "."
    ])

    results.append(
        check(
            build.returncode == 0,
            "Docker image builds successfully"
        )
    )

    if build.returncode != 0:
        print(build.stdout)
        print(build.stderr)
        return 1

    # Missing configuration

    print()
    print("Testing missing configuration...")

    missing = run([
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "python",
        IMAGE,
        "/app/server.py"
    ])

    missing_output = (
        missing.stdout + missing.stderr
    )

    results.append(
        check(
            missing.returncode != 0,
            "Missing configuration is rejected"
        )
    )

    results.append(
        check(
            "APP_HOST" in missing_output
            or "APP_PORT" in missing_output,
            "Missing configuration produces a clear error"
        )
    )

    # Invalid configuration

    print()
    print("Testing invalid configuration...")

    invalid_cases = [
        ("APP_HOST", "127.0.0.1", "invalid host"),
        ("APP_PORT", "abc", "non-numeric port"),
        ("APP_PORT", "0", "port below valid range"),
        ("APP_PORT", "99999", "port above valid range"),
    ]

    for variable, value, description in invalid_cases:

        environment = [
            "--entrypoint",
            "python",
            "-e",
            "APP_HOST=0.0.0.0",
            "-e",
            "APP_PORT=8080",
        ]

        if variable == "APP_HOST":
            environment[3] = f"APP_HOST={value}"
        else:
            environment[5] = f"APP_PORT={value}"

        result = run([
            "docker",
            "run",
            "--rm",
            *environment,
            IMAGE,
            "/app/server.py"
        ])

        output = result.stdout + result.stderr

        results.append(
            check(
                result.returncode != 0,
                f"Invalid configuration rejected ({description})"
            )
        )

        results.append(
            check(
                "ERROR" in output
                or "error" in output
                or "invalid" in output.lower(),
                f"Clear error reported ({description})"
            )
        )

    # Normal startup

    print()
    print("Starting container...")

    start = run([
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
            start.returncode == 0,
            "Container starts successfully"
        )
    )

    if start.returncode != 0:
        print(start.stderr)
        cleanup()
        return 1

    time.sleep(3)

    # Runtime user

    user = run([
        "docker",
        "exec",
        CONTAINER,
        "id",
        "-u"
    ])

    results.append(
        check(
            user.returncode == 0
            and user.stdout.strip() != "0",
            "Container runs as non-root"
        )
    )

    # Health endpoint

    print()
    print("Testing health endpoint...")

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
                "Health endpoint returns healthy"
            )
        )

    except Exception as exc:
        print(f"FAIL: Health endpoint unavailable: {exc}")
        results.append(False)
        results.append(False)

    # Docker health

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

    # Logs

    print()
    print("Testing logs...")

    logs = run([
        "docker",
        "logs",
        CONTAINER
    ])

    log_text = logs.stdout + logs.stderr

    results.append(
        check(
            "Server listening" in log_text,
            "Startup message appears in Docker logs"
        )
    )

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
            "Logs do not expose obvious secrets"
        )
    )

    # Root endpoint

    print()
    print("Testing root endpoint...")

    try:
        response = urllib.request.urlopen(
            "http://localhost:8080/",
            timeout=5
        )

        results.append(
            check(
                response.status == 200,
                "Root endpoint returns HTTP 200"
            )
        )

    except Exception as exc:
        print(f"FAIL: Root endpoint unavailable: {exc}")
        results.append(False)

    # Graceful shutdown

    print()
    print("Testing shutdown...")

    stop = run([
        "docker",
        "stop",
        "-t",
        "5",
        CONTAINER
    ])

    results.append(
        check(
            stop.returncode == 0,
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

    # Restart

    print()
    print("Testing restart...")

    restart = run([
        "docker",
        "start",
        CONTAINER
    ])

    results.append(
        check(
            restart.returncode == 0,
            "Container restarts successfully"
        )
    )

    if restart.returncode == 0:

        time.sleep(2)

        try:
            response = urllib.request.urlopen(
                "http://localhost:8080/health",
                timeout=5
            )

            results.append(
                check(
                    response.status == 200,
                    "Health endpoint works after restart"
                )
            )

        except Exception as exc:
            print(
                f"FAIL: Health endpoint failed after restart: {exc}"
            )
            results.append(False)

    cleanup()

    print()
    print("================================")
    print("Health API Evaluation")
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
