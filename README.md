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
     Trivy configuration for filesystem as we as trivy image 



