pipeline {
  agent any
  stages {
    stage('Unit Python3.7') {
      agent any
      steps {
        sh 'tox -epy37 -r'
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
        labelledShell script: 'docker network create --attachable network-manager-$BUILD_ID', label: "Create test network"
        labelledShell script: 'docker run -t -d --privileged --network=network-manager-$BUILD_ID -v /.kube:/.kube/ -v d54-data-manager-$BUILD_ID:/demo-tests/d54 -v organon-data-manager-$BUILD_ID:/demo-tests/organon --name docker-manager-$BUILD_ID asperathos-docker', label: "Run Docker container"
        labelledShell script: """docker create --network=network-manager-$BUILD_ID -v d54-data-manager-$BUILD_ID:/demo-tests/d54 \
        -v organon-data-manager-$BUILD_ID:/demo-tests/organon --name integration-tests-manager-$BUILD_ID \
        -e DOCKER_HOST=tcp://docker-manager-$BUILD_ID:2375 \
        -e DOCKER_HOST_URL=docker-manager-$BUILD_ID \
        -e ASPERATHOS_URL=docker-manager-$BUILD_ID:1500/submissions \
        -e manager_URL=docker-manager-$BUILD_ID:5002/visualizing  integration-tests""" , label: "Create integration tests container"
        labelledShell script: 'docker cp . integration-tests-manager-$BUILD_ID:/integration-tests/test_env/manager/asperathos-manager/', label: "Copy manager code to container"
        labelledShell script: 'docker start -i integration-tests-manager-$BUILD_ID', label: "Run integration tests"
      }
    }
  }
  post {
    cleanup {
      labelledShell script: 'docker stop docker-manager-$BUILD_ID || true', label: "Stop Docker container"
      labelledShell script: 'docker rm -v docker-manager-$BUILD_ID || true', label: "Remove Docker container"
      labelledShell script: 'docker rm -v integration-tests-manager-$BUILD_ID || true', label: "Remove integration tests container"
      labelledShell script: 'docker network rm network-manager-$BUILD_ID || true', label: "Remove test network"
      labelledShell script: 'docker volume rm d54-data-manager-$BUILD_ID || true', label: "Remove D5.4 volume"
      labelledShell script: 'docker volume rm organon-data-manager-$BUILD_ID || true', label: "Remove Organon volume"
    }    
     failure {
      labelledShell script: 'docker exec docker-manager-$BUILD_ID docker logs testenv_manager_1', label: "Manager logs"
      labelledShell script: 'docker exec docker-manager-$BUILD_ID docker logs testenv_monitor_1', label: "Monitor logs"
      labelledShell script: 'docker exec docker-manager-$BUILD_ID docker logs testenv_visualizer_1', label: "Visualizer logs"
      labelledShell script: 'docker exec docker-manager-$BUILD_ID docker logs testenv_controller_1', label: "Controller logs"
    }
  }
}
