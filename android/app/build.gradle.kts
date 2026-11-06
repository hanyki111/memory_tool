plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "io.github.hanyki111.memorycapture"
    compileSdk = 36

    defaultConfig {
        applicationId = "io.github.hanyki111.memorycapture"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }

    packaging {
        resources {
            // JSch and Bouncy Castle both carry these build metadata files.
            excludes += setOf("META-INF/versions/*/OSGI-INF/MANIFEST.MF", "META-INF/DEPENDENCIES")
        }
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2025.06.01")
    implementation(composeBom)
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.work:work-runtime-ktx:2.10.2")

    // SSH with Ed25519 keys; Bouncy Castle provides Ed25519 on every Android version.
    implementation("com.github.mwiede:jsch:2.27.2")
    implementation("org.bouncycastle:bcprov-jdk18on:1.81")

    testImplementation("junit:junit:4.13.2")
    // Android's org.json is a stub in JVM tests.
    testImplementation("org.json:json:20250517")
    // A real SSH server for the transport tests.
    testImplementation("org.apache.sshd:sshd-core:2.15.0")
}
