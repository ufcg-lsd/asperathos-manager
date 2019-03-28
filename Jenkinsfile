pipeline {
  agent any
  stages {
    stage('Unit Python2.7') {
      agent any
      steps {
        sh 'tox -epy27'
      }
    }
    stage('Pep8') {
      agent any
      steps {
        sh 'tox -epep8'
      }
    }
    stage('Integration') {
      agent any
      steps {
        sh 'docker network create --attachable network-manager-$BUILD_ID'
        sh 'docker run -t -d --privileged --network=network-manager-$BUILD_ID -v /.kube:/.kube/ --name docker-manager-$BUILD_ID asperathos-docker'
        sh 'docker create --network=network-manager-$BUILD_ID --name integration-tests-manager-$BUILD_ID -e DOCKER_HOST=tcp://$(docker ps -aqf "name=docker-manager-$BUILD_ID"):2375 -e DOCKER_HOST_URL=$(docker ps -aqf "name=docker-manager-$BUILD_ID") integration-tests'
        sh 'docker cp . integration-tests-manager-$BUILD_ID:/integration-tests/test_env/manager/asperathos-manager/'
        sh 'docker start -i integration-tests-manager-$BUILD_ID'
      }
    }
  }
  post {
    cleanup {
      sh 'docker stop docker-manager-$BUILD_ID'
      sh 'docker rm -v docker-manager-$BUILD_ID'
      sh 'docker rm -v integration-tests-manager-$BUILD_ID'
      sh 'docker network rm network-manager-$BUILD_ID'
    }
  }
}
