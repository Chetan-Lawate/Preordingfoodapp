## Goal Diagram
                       ┌── SonarQube ──→ Quality Gate ──-┐
                       │                                 │
Push → Tests ──────────┤                                 ├──→ Docker Build
                       │                                 │          ↓
                       └── Trivy Filesystem ─────────────┘    Trivy Image
                                                                    ↓
                                                              Docker Push


#Project Track
-
## Day1
      Using github pull the existing repository
      Changing the Database from SQL to Mongodb (Using Chatgpt)
      for container use the Docker build command  
      creating Docker-image 

## Day2
      Creating CI/CD pipeline
-      1st we create Ci-CD.yml file where we automate the push docker command using lastest tag fro image 
-      2nd docker-compose.yml--> for Monogodb to integrate with Docker file and github to keep track and find any leaks
      
## Day3
-      Using github tool codeQL for codescanning and find Malaware and Vulnerabnilities in code 
      
## Day4
      We Trying to Integrate the Sonarqube integration with github so we can use static analysis of code 

## Day5
-     USe Sonarqubecloud.io rather than Sonarqube community to get link Github driectly for  setup 
-     project and create Scretes SONAR_TOKEN and SONAR_HOST_URL with Sonar-project.properties where i store the projectkey

## Day6
     Trivy configuration for filesystem as we as trying to trivy image 

## Day7
     Trivy configuration successfully done using github co-pilot and utho 
     if system failed generate the .json file and aslo generate the scan summary

## Day 8 
     Using the render site for deployement 

## Day9
    automate the whole process start from run test to deployement 
    if any scans failed , sonar quality gates failed deployement will blocked and auto generate the report in the form .json

## Day10
    Now we start removing high vernabulity so we pass the quality gate 
    Their are some medium and low security checks points ar also 

## Day11
    Check the workflow of CI/CD pipeline sonar-qube trivy scan
    render the website test the apis deploy the site 

