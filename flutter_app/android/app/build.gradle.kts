plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.pubentry.pub_entry_app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.pubentry.pub_entry_app"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")

            // Code + resource shrinking were both off, and there was no
            // per-ABI split — every release build bundled arm64,
            // armeabi-v7a AND x86_64 native libs (camera/mobile_scanner/
            // local_auth/sqflite each ship their own .so per ABI) into one
            // APK plus every unreferenced Java/Kotlin class and drawable
            // from all dependencies, several times over the size actually
            // needed to run on one real device.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    // Splits the release build into one small APK per CPU architecture
    // instead of a single APK carrying all three sets of native libraries.
    // `flutter build apk` (not --split-per-abi) still emits a universal
    // fallback APK alongside the per-ABI ones by default, which is what
    // the "Update" download in-app should keep pointing at unless staff
    // start distributing per-device architecture-specific builds instead.
    splits {
        abi {
            isEnable = true
            reset()
            include("armeabi-v7a", "arm64-v8a", "x86_64")
            isUniversalApk = true
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
