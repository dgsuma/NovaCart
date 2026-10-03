pipeline {
    agent {
        label 'jenkins-agent-01'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    environment {
        REGISTRY           = 'ghcr.io'
        IMAGE_ORG          = 'dgsuma'
        FRONTEND_IMAGE     = 'novacart-frontend'
        PAYMENT_IMAGE      = 'novacart-payment'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm

                script {
                    env.GIT_SHA = sh(
                        returnStdout: true,
                        script: 'git rev-parse HEAD'
                    ).trim()

                    env.GIT_SHORT = env.GIT_SHA.take(8)
                    env.IMAGE_TAG = env.GIT_SHA

                    env.FRONTEND_REF =
                        "${env.REGISTRY}/${env.IMAGE_ORG}/${env.FRONTEND_IMAGE}:${env.IMAGE_TAG}"

                    env.PAYMENT_REF =
                        "${env.REGISTRY}/${env.IMAGE_ORG}/${env.PAYMENT_IMAGE}:${env.IMAGE_TAG}"

                    echo "Commit: ${env.GIT_SHORT}"
                    echo "Frontend: ${env.FRONTEND_REF}"
                    echo "Payment:  ${env.PAYMENT_REF}"
                }
            }
        }

        stage('Payment: syntax') {
            steps {
                sh '''
                    set -eu

                    docker run --rm \
                        -v "$PWD:/workspace:ro" \
                        -w /workspace \
                        node:22-slim \
                        node --check src/payment/charge.js

                    docker run --rm \
                        -v "$PWD:/workspace:ro" \
                        -w /workspace \
                        node:22-slim \
                        node --check src/payment/index.js
                '''
            }
        }

        stage('Docker: build frontend') {
            steps {
                sh '''
                    set -eu

                    docker build --pull \
                        -f src/frontend/Dockerfile \
                        -t "${FRONTEND_REF}" \
                        .
                '''
            }
        }

        stage('Docker: build payment') {
            steps {
                sh '''
                    set -eu

                    docker build --pull \
                        -f src/payment/Dockerfile \
                        -t "${PAYMENT_REF}" \
                        .
                '''
            }
        }

        stage('Trivy: frontend') {
            steps {
                sh '''
                    trivy image \
                        --scanners vuln \
                        --severity CRITICAL \
                        --exit-code 1 \
                        "${FRONTEND_REF}"
                '''
            }
        }

        stage('Trivy: payment') {
            steps {
                sh '''
                    trivy image \
                        --scanners vuln \
                        --severity CRITICAL \
                        --exit-code 1 \
                        "${PAYMENT_REF}"
                '''
            }
        }

        stage('GHCR: push images') {
            when {
                branch 'main'
            }

            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'oci-registry-credentials',
                        usernameVariable: 'GHCR_USER',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    sh '''
                        set -eu

                        trap 'docker logout "$REGISTRY" >/dev/null 2>&1 || true' EXIT

                        echo "$GHCR_TOKEN" | docker login "$REGISTRY" \
                            -u "$GHCR_USER" \
                            --password-stdin

                        docker push "${FRONTEND_REF}"
                        docker push "${PAYMENT_REF}"
                    '''
                }
            }
        }

        stage('GHCR: verify public pull') {
            when {
                branch 'main'
            }

            steps {
                sh '''
                    set -eu

                    docker logout "$REGISTRY" >/dev/null 2>&1 || true

                    echo "Checking anonymous access to frontend image..."
                    docker manifest inspect "${FRONTEND_REF}" >/dev/null

                    echo "Checking anonymous access to payment image..."
                    docker manifest inspect "${PAYMENT_REF}" >/dev/null

                    echo "Both NovaCart images are anonymously pullable."
                '''
            }
        }

        stage('GitOps: update NovaCart images') {
            when {
                branch 'main'
            }

            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'gitops-repo-credentials',
                        usernameVariable: 'GITOPS_USER',
                        passwordVariable: 'GITOPS_TOKEN'
                    )
                ]) {
                    sh '''
                        set -eu

                        rm -rf gitops-repo
                        rm -f .git-askpass.sh

                        printf '%s\\n' \
                            '#!/bin/sh' \
                            'case "$1" in' \
                            '    *Username*) echo "$GITOPS_USER" ;;' \
                            '    *Password*) echo "$GITOPS_TOKEN" ;;' \
                            'esac' \
                            > .git-askpass.sh

                        chmod 700 .git-askpass.sh

                        export GIT_ASKPASS="$PWD/.git-askpass.sh"
                        export GIT_TERMINAL_PROMPT=0

                        trap 'rm -f "$WORKSPACE/.git-askpass.sh"' EXIT

                        git clone \
                            https://github.com/dgsuma/dgs-private-cloud.git \
                            gitops-repo

                        cd gitops-repo

                        git config user.name "Jenkins CI"
                        git config user.email "jenkins@dgs-private-cloud"

                        python3 - <<'PY'
import os
import re
from pathlib import Path

tag = os.environ["IMAGE_TAG"]

frontend_file = Path(
    "clusters/beelink-talos/novacart/frontend-layer.yaml"
)
payment_file = Path(
    "clusters/beelink-talos/novacart/leaf-services.yaml"
)

frontend_ref = f"ghcr.io/dgsuma/novacart-frontend:{tag}"
payment_ref = f"ghcr.io/dgsuma/novacart-payment:{tag}"

def replace_one(path, pattern, replacement):
    text = path.read_text()
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)

    if count != 1:
        raise SystemExit(
            f"Expected exactly one image replacement in {path}, found {count}"
        )

    path.write_text(updated)

replace_one(
    frontend_file,
    r'^(\\s*image:\\s+)(?:ghcr\\.io/open-telemetry/demo:2\\.1\\.3-frontend|ghcr\\.io/dgsuma/novacart-frontend:\\S+)\\s*$',
    rf'\\1{frontend_ref}',
)

replace_one(
    payment_file,
    r'^(\\s*image:\\s+)(?:ghcr\\.io/open-telemetry/demo:2\\.1\\.3-payment|ghcr\\.io/dgsuma/novacart-payment:\\S+)\\s*$',
    rf'\\1{payment_ref}',
)
PY

                        echo "Updated frontend image:"
                        grep -n "novacart-frontend:" \
                            clusters/beelink-talos/novacart/frontend-layer.yaml

                        echo "Updated payment image:"
                        grep -n "novacart-payment:" \
                            clusters/beelink-talos/novacart/leaf-services.yaml

                        git diff --check

                        git diff -- \
                            clusters/beelink-talos/novacart/frontend-layer.yaml \
                            clusters/beelink-talos/novacart/leaf-services.yaml

                        git add \
                            clusters/beelink-talos/novacart/frontend-layer.yaml \
                            clusters/beelink-talos/novacart/leaf-services.yaml

                        if git diff --cached --quiet; then
                            echo "GitOps already points to ${IMAGE_TAG}; nothing to commit."
                        else
                            git commit \
                                -m "deploy(novacart): frontend and payment ${IMAGE_TAG}"

                            git pull --rebase origin main
                            git push origin main
                        fi
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "NovaCart Phase-1 CI succeeded: ${IMAGE_TAG}"
        }

        failure {
            echo 'NovaCart Phase-1 CI failed — inspect the failed stage.'
        }

        always {
            sh '''
                if [ -n "${FRONTEND_REF:-}" ]; then
                    docker image rm -f "${FRONTEND_REF}" || true
                fi

                if [ -n "${PAYMENT_REF:-}" ]; then
                    docker image rm -f "${PAYMENT_REF}" || true
                fi

                rm -f .git-askpass.sh
                rm -rf gitops-repo
            '''

            cleanWs()
        }
    }
}
