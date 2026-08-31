// new-portfolio-ai/Jenkinsfile
pipeline {
    agent any

    environment {
        // 1. 새 프로젝트 경로 및 PM2 프로세스명 설정
        PROJECT_NAME = 'smart-portfolio-mariadb'
        DEPLOY_DIR = "/home/totoro/Pythonproject/${env.PROJECT_NAME}"
        PYTHON_BIN = 'python3'
        APP_PORT = '8502'
        PATH = "/usr/local/bin:/usr/bin:/bin:${env.PATH}"
    }

    stages {
        stage('Sync Files') {
            steps {
                sh '''
                    mkdir -p ${DEPLOY_DIR}
                    # MariaDB 사용으로 SQLite DB 파일 제외 옵션 제거, 개발/배포 환경 격리를 위한 제외 항목 정리
                    rsync -av --exclude='.venv' \
                              --exclude='venv' \
                              --exclude='.env' \
                              --exclude='.git' \
                              --exclude='__pycache__' \
                              --exclude='*.pyc' \
                              ./ ${DEPLOY_DIR}/
                '''
            }
        }

        stage('Setup Virtualenv & Dependencies') {
            steps {
                sh '''
                    cd ${DEPLOY_DIR}
                    if [ ! -d ".venv" ]; then
                        ${PYTHON_BIN} -m venv .venv
                    fi
                    .venv/bin/pip install --upgrade pip
                    # pymysql / DBUtils 등이 포함된 requirements.txt 설치
                    .venv/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Deploy & Start with PM2') {
            steps {
                // Jenkins Credentials(MariaDB 접속정보가 포함된 .env 파이프라인 자격증명) 주입
                withCredentials([file(credentialsId: 'new-portfolio-env', variable: 'SECRET_ENV')]) {
                    sh '''
                        cd ${DEPLOY_DIR}

                        # Credentials에서 가져온 MariaDB 환경변수(.env) 복사 및 보안 권한 설정
                        cp ${SECRET_ENV} .env
                        chmod 600 .env

                        # 기존 프로세스가 있다면 정리 후 재시작
                        if pm2 describe ${PROJECT_NAME} >/dev/null 2>&1; then
                            echo "Cleaning up existing process..."
                            pm2 delete ${PROJECT_NAME}
                        fi

                        echo "Starting Streamlit app with PM2..."
                        pm2 start .venv/bin/streamlit \
                          --name "${PROJECT_NAME}" \
                          --interpreter .venv/bin/python3 \
                          -- run app.py --server.port=${APP_PORT} --server.address=0.0.0.0

                        pm2 save
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "Deployment of ${env.PROJECT_NAME} completed successfully!"
        }
        failure {
            echo "Deployment of ${env.PROJECT_NAME} failed. Check Jenkins logs."
        }
    }
}