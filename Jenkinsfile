// Pipeline de CI/CD de MediSur (vive en el repositorio, no se configura a clics).
// Multibranch Pipeline: Jenkins ejecuta este archivo en cada rama detectada.
//
// Credenciales requeridas en Jenkins (Manage Jenkins > Credentials):
//   - ghcr-credentials : usuario + token (write:packages) del registro
//   - kubeconfig-k8s   : "Secret file" con el kubeconfig de VM-K8S (IP privada)
//   - k8s-node-ip      : "Secret text" con la IP privada de VM-K8S (prueba de humo)
//   - sonar-token      : configurado en el servidor "sonarqube" (Manage Jenkins > System)

pipeline {

    // Ejecuta el pipeline en cualquier agente disponible (VM-TOOLS).
    agent any

    options {
        // Evita que un build colgado ocupe el servidor indefinidamente.
        timeout(time: 30, unit: 'MINUTES')
        // Un solo build a la vez: dos despliegues simultaneos podrian pisarse.
        disableConcurrentBuilds()
        // Marca de tiempo en cada linea de la consola, util para depurar.
        timestamps()
    }

    environment {
        REGISTRY     = 'ghcr.io'
        IMAGE_REPO   = 'ghcr.io/sammmcm/medisur-pilot'
        BASE_VERSION = '1.0.0'          // parte fija de la etiqueta; el SHA la hace unica
        NAMESPACE    = 'medisur'
        DEPLOYMENT   = 'medisur-api'
        CONTAINER    = 'api'
    }

    stages {

        // Etapa 2: descarga el commit exacto y calcula la etiqueta de la imagen.
        // La etiqueta versión-SHA (ej. 1.0.0-a9a6773) permite saber que commit corre en produccion.
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

        // Etapa 3: pruebas unitarias dentro de un contenedor limpio (entorno reproducible).
        // --cov-fail-under=60 aborta el pipeline si la cobertura baja del minimo exigido.
        // Genera coverage.xml, que SonarQube consume en la siguiente etapa.
        stage('Dependencias y pruebas') {
            agent {
                docker { image 'python:3.12-slim'; args '-u root' }
            }
            steps {
                sh '''
                    pip install --no-cache-dir -r app/requirements-dev.txt
                    python -m pytest app/tests --cov=app.app --cov-report=xml:coverage.xml --cov-fail-under=60 -q
                '''
                // stash: el reporte pasa al agente de la siguiente etapa (esta corrio en otro contenedor).
                stash name: 'coverage', includes: 'coverage.xml'
            }
        }

        // Etapa 4: analisis estatico del codigo y de la cobertura con SonarQube.
        // Solo envia resultados; la decision de aprobar o rechazar se toma en la etapa siguiente.
        stage('Analisis SonarQube') {
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

        // Etapa 5: puerta de calidad. Si SonarQube devuelve ERROR, abortPipeline detiene
        // todo antes de construir o publicar la imagen. El limite de 5 minutos evita esperas infinitas.
        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // Etapa 6: construye la imagen Docker. Los build-args quedan registrados en la imagen
        // para que el endpoint /version pueda reportar version, SHA y fecha de compilacion.
        stage('Construir imagen') {
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

        // Etapa 7: publica la imagen en GHCR. Las credenciales se inyectan solo durante
        // la ejecucion (nunca en el codigo) y la contrasena se pasa por stdin para que no
        // aparezca en el historial ni en la consola.
        stage('Publicar imagen') {
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

        // Etapa 8: despliega en k3s, solo desde main (las ramas demo no tocan el cluster).
        // DEPLOY_TOUCHED indica al bloque post que el cluster ya cambio y que, si algo falla
        // despues, hay una revision anterior a la cual regresar.
        stage('Desplegar') {
            when { branch 'main' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig-k8s', variable: 'KUBECONFIG')]) {
                    script { env.DEPLOY_TOUCHED = 'true' }
                    sh '''
                        kubectl apply -f k8s/namespace.yaml
                        kubectl apply -f k8s/configmap.yaml -f k8s/service.yaml
                        # Sustituye la imagen en el manifiesto y lo aplica en una sola revision del Deployment.
                        sed "s|image: .*medisur-pilot.*|image: ${IMAGE_REPO}:${IMAGE_TAG}|" k8s/deployment.yaml | kubectl apply -f -
                        # change-cause deja la etiqueta en el historial de rollout (kubectl rollout history).
                        kubectl -n ${NAMESPACE} annotate deployment/${DEPLOYMENT} \
                            kubernetes.io/change-cause="${IMAGE_TAG}" --overwrite
                    '''
                }
            }
        }

        // Etapa 9: espera a que las dos replicas queden listas (RollingUpdate).
        // Si en 120 s no lo logran, la etapa falla y se activa la reversion.
        stage('Verificar rollout') {
            when { branch 'main' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig-k8s', variable: 'KUBECONFIG')]) {
                    sh 'kubectl -n ${NAMESPACE} rollout status deployment/${DEPLOYMENT} --timeout=120s'
                }
            }
        }

        // Etapa 10: prueba de humo desde fuera del cluster. curl -f falla ante cualquier HTTP >= 400,
        // y el grep confirma que /version reporta el SHA recien desplegado (no una version anterior).
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
        // Si algo falla despues de modificar el cluster en main, regresa a la revision estable
        // anterior sin intervencion manual.
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
        // Siempre limpia imagenes de mas de 24 h para no llenar el disco (alerta DiscoPorLlenarse).
        always {
            sh 'docker image prune -af --filter "until=24h" || true'
        }
    }
}
