pipeline {
    agent any

    environment {
        PROJECT_NAME = 'smart-portfolio-mariadb'
        DEPLOY_DIR = "/home/totoro/Pythonproject/${env.PROJECT_NAME}"
        PYTHON_BIN = 'python3'
        APP_PORT = '8502'
        PATH = "/usr/local/bin:/usr/bin:/bin:${env.PATH}"
    }

    stages {

        // ============================================================
        // 1. Sync Files
        // ============================================================
        stage('1. Sync Files') {
            steps {
                sh '''
                    set -e

                    echo "=============================================="
                    echo "Syncing project files"
                    echo "=============================================="

                    mkdir -p "${DEPLOY_DIR}"

                    rsync -rv --delete \
                        --exclude='.venv' \
                        --exclude='venv' \
                        --exclude='.env' \
                        --exclude='.git' \
                        --exclude='__pycache__' \
                        --exclude='*.pyc' \
                        ./ "${DEPLOY_DIR}/"

                    echo "File sync completed."
                '''
            }
        }

        // ============================================================
        // 2. Setup Virtualenv & Dependencies
        // ============================================================
        stage('2. Setup Virtualenv & Dependencies') {
            steps {
                sh '''
                    set -e

                    cd "${DEPLOY_DIR}"

                    echo "=============================================="
                    echo "Python version"
                    echo "=============================================="

                    ${PYTHON_BIN} --version

                    if [ ! -d ".venv" ]; then
                        echo "Creating virtual environment..."
                        ${PYTHON_BIN} -m venv .venv
                    fi

                    echo "Upgrading pip..."
                    .venv/bin/python -m pip install --upgrade pip

                    echo "Installing dependencies..."
                    .venv/bin/python -m pip install -r requirements.txt

                    echo "Dependencies installed."
                '''
            }
        }

        // ============================================================
        // 3. Deploy Environment
        // ============================================================
        stage('3. Deploy Environment') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'new-portfolio-env',
                        variable: 'SECRET_ENV'
                    )
                ]) {
                    sh '''
                        set -e

                        echo "=============================================="
                        echo "Deploying .env"
                        echo "=============================================="

                        sudo install \
                            -o totoro \
                            -g totoro \
                            -m 600 \
                            "${SECRET_ENV}" \
                            "${DEPLOY_DIR}/.env"

                        echo ".env deployed successfully."

                        echo "Checking .env permission..."
                        ls -l "${DEPLOY_DIR}/.env"
                    '''
                }
            }
        }

        // ============================================================
        // 4. Restart Streamlit
        // ============================================================
        stage('4. Restart Streamlit with systemd') {
            steps {
                sh '''
                    set -e

                    SERVICE_NAME="smart-portfolio-mariadb"

                    echo "=============================================="
                    echo "Service: ${SERVICE_NAME}"
                    echo "Port: ${APP_PORT}"
                    echo "=============================================="

                    echo "Reloading systemd..."
                    sudo systemctl daemon-reload

                    echo "Restarting Streamlit..."
                    sudo systemctl restart "${SERVICE_NAME}"

                    echo "Waiting for service..."
                    sleep 3

                    echo "Checking service status..."

                    if ! sudo systemctl is-active --quiet "${SERVICE_NAME}"; then

                        echo "ERROR: Streamlit service failed to start."

                        echo ""
                        echo "===== SYSTEMD STATUS ====="

                        sudo systemctl \
                            --no-pager \
                            -l \
                            status "${SERVICE_NAME}" || true

                        echo ""
                        echo "===== JOURNAL ====="

                        sudo journalctl \
                            -u "${SERVICE_NAME}" \
                            -n 100 \
                            --no-pager || true

                        echo ""
                        echo "===== APPLICATION ERROR LOG ====="

                        if [ -f "${DEPLOY_DIR}/logs/app-error.log" ]; then
                            tail -100 \
                                "${DEPLOY_DIR}/logs/app-error.log" || true
                        fi

                        exit 1
                    fi

                    echo "Streamlit service is running."

                    echo "Checking port ${APP_PORT}..."

                    for i in $(seq 1 30); do

                        if curl -fsS \
                            --connect-timeout 1 \
                            "http://127.0.0.1:${APP_PORT}" \
                            >/dev/null 2>&1; then

                            echo "Streamlit is available on port ${APP_PORT}"
                            break
                        fi

                        if [ "$i" -eq 30 ]; then

                            echo "ERROR: Streamlit did not respond."

                            echo ""
                            echo "===== SYSTEMD STATUS ====="

                            sudo systemctl \
                                --no-pager \
                                -l \
                                status "${SERVICE_NAME}" || true

                            echo ""
                            echo "===== JOURNAL ====="

                            sudo journalctl \
                                -u "${SERVICE_NAME}" \
                                -n 100 \
                                --no-pager || true

                            exit 1
                        fi

                        sleep 1
                    done

                    echo "=============================================="
                    echo "Deployment completed"
                    echo "=============================================="
                '''
            }
        }
    }

    post {

        success {
            echo """
==============================================
Deployment SUCCESS
==============================================

Application : ${env.PROJECT_NAME}
Port        : ${env.APP_PORT}
Service     : smart-portfolio-mariadb
Manager     : systemd
"""
        }

        failure {
            echo """
==============================================
Deployment FAILED
==============================================

Application : ${env.PROJECT_NAME}
Port        : ${env.APP_PORT}
Service     : smart-portfolio-mariadb
"""
        }

        always {
            echo "Jenkins Pipeline Finished"
        }
    }
}