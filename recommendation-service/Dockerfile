# ---- Build stage: compile with Maven, cache dependency resolution ----
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app

# Copy only the POM first so `mvn dependency:go-offline` is cached as its
# own layer -- source changes won't force a full dependency re-download.
COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn clean package -DskipTests -B

# ---- Runtime stage: JRE only, no build tooling in the final image ----
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

RUN addgroup -S spring && adduser -S spring -G spring
COPY --from=build /app/target/*.jar app.jar
RUN chown spring:spring app.jar
USER spring

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
