// Pipeline de CI/CD de MediSur (vive en el repositorio, no se configura a clics).
// Credenciales requeridas en Jenkins (Manage Jenkins > Credentials):
//   - ghcr-credentials   : usuario + token (write:packages) del registro
//   - kubeconfig-k8s     : "Secret file" con el kubeconfig de VM-K8S (IP privada)
//   - k8s-node-ip        : "Secret text" con la IP PRIVADA de VM-K8S (para la prueba de humo)   // CAMBIO
//   - sonar-token        : configurado dentro del servidor "sonarqube" (Manage Jenkins > System)
pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        REGISTRY   = 'ghcr.io'
        IMAGE_REPO = 'ghcr.io/sammmcm/medisur-pilot'
        BASE_VERSION = '1.0.0'
        NAMESPACE  = 'medisur'
        DEPLOYMENT = 'medisur-api'
        CONTAINER  = 'api'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHA_SHORT = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD').trim()
                    env.IMAGE_TAG     = "${BASE_VERSION}-${env.GIT_SHA_SHORT}"
                    env.BUILD_DATE    = sh(returnStdout: true, script: 'date -u +%Y-%m-%dT%H:%M:%SZ').trim()
                }
                echo "Commit: ${env.GIT_SHA_SHORT} | Etiqueta de imagen: ${env.IMAGE_TAG}"
            }
        }

        stage('Dependencias y pruebas') {
            agent {
                docker { image 'python:3.12-slim'; args '-u root' }
            }
            steps {
                sh '''
                    pip install --no-cache-dir -r app/requirements-dev.txt
                    cd app
                    python -m pytest tests --cov=app --cov-report=xml:../coverage.xml --cov-fail-under=60 -q
                '''
                stash name: 'coverage', includes: 'coverage.xml'
            }
        }

        stage('Analisis SonarQube') {
            when { anyOf { branch 'main'; branch 'demo/quality-gate' } }
            steps {
                unstash 'coverage'
                script {
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('sonarqube') {
                        sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectVersion=${env.IMAGE_TAG}"
                    }
                }
            }
        }

        stage('Quality Gate') {
            when { anyOf { branch 'main'; branch 'demo/quality-gate' } }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Construir imagen') {
            when { anyOf { branch 'main'; branch 'demo/rollback' } }
            steps {
                sh """
                    docker build \
                      --build-arg APP_VERSION=${IMAGE_TAG} \
                      --build-arg GIT_SHA=${GIT_SHA_SHORT} \
                      --build-arg BUILD_DATE=${BUILD_DATE} \
                      -t ${IMAGE_REPO}:${IMAGE_TAG} .
                """
            }
        }

        stage('Publicar imagen') {
            when { anyOf { branch 'main'; branch 'demo/rollback' } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'ghcr-credentials',
                                                  usernameVariable: 'REG_USER',
                                                  passwordVariable: 'REG_PASS')]) {
                    sh '''
                        echo "$REG_PASS" | docker login ghcr.io -u "$REG_USER" --password-stdin
                        docker push ${IMAGE_REPO}:${IMAGE_TAG}
                        docker logout ghcr.io
                    '''
                }
            }
        }

        stage('Desplegar') {
            when { branch 'main' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig-k8s', variable: 'KUBECONFIG')]) {
                    script { env.DEPLOY_TOUCHED = 'true' }
                    sh '''
                        kubectl apply -f k8s/namespace.yaml
                        kubectl apply -f k8s/configmap.yaml -f k8s/service.yaml
                        # CAMBIO: se aplica el Deployment con la imagen nueva en una sola revision
                        sed "s|image: .*medisur-pilot.*|image: ${IMAGE_REPO}:${IMAGE_TAG}|" k8s/deployment.yaml | kubectl apply -f -
                        kubectl -n ${NAMESPACE} annotate deployment/${DEPLOYMENT} \
                            kubernetes.io/change-cause="${IMAGE_TAG}" --overwrite
                    '''
                }
            }
        }

        stage('Verificar rollout') {
            when { branch 'main' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig-k8s', variable: 'KUBECONFIG')]) {
                    sh 'kubectl -n ${NAMESPACE} rollout status deployment/${DEPLOYMENT} --timeout=120s'
                }
            }
        }

        stage('Prueba de humo') {
            when { branch 'main' }
            steps {
                withCredentials([string(credentialsId: 'k8s-node-ip', variable: 'NODE_IP')]) {
                    sh '''
                        sleep 5
                        curl -fsS http://${NODE_IP}:30080/health
                        curl -fsS http://${NODE_IP}:30080/version | grep "${GIT_SHA_SHORT}"
                    '''
                }
            }
        }
    }

    post {
        failure {
            script {
                if (env.BRANCH_NAME == 'main' && env.DEPLOY_TOUCHED == 'true') {
                    withCredentials([file(credentialsId: 'kubeconfig-k8s', variable: 'KUBECONFIG')]) {
                        sh '''
                            kubectl -n ${NAMESPACE} rollout undo deployment/${DEPLOYMENT}
                            kubectl -n ${NAMESPACE} rollout status deployment/${DEPLOYMENT} --timeout=120s
                        '''
                    }
                    echo 'Reversion automatica ejecutada'
                }
            }
            echo 'Pipeline en ROJO'
        }
        success {
            echo "Pipeline en VERDE. Version desplegada: ${env.IMAGE_TAG}"
        }
        always {
            sh 'docker image prune -af --filter "until=24h" || true'
        }
    }
}
