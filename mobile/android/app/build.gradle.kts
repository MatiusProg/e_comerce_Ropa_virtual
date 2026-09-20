plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "bo.edu.uagrm.violetboutique"
    // Fijado a mano, no `flutter.compileSdkVersion` (que hoy resuelve a 36):
    // flutter_secure_storage 11 exige compilar contra la API 37 o el build
    // falla en CheckAarMetadata antes de compilar una sola clase.
    compileSdk = 37
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "bo.edu.uagrm.violetboutique"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")

            // SIN MINIFICACION, Y ES A PROPOSITO.
            //
            // Desde AGP 9 la minificacion viene ENCENDIDA por omision en
            // `release`. Nadie la activo aca, asi que tampoco nadie escribio
            // reglas de conservacion --- y el 20/09/2026 eso hizo que el APK
            // de produccion **no abriera**:
            //
            //   java.lang.RuntimeException: Unable to get provider
            //   androidx.startup.InitializationProvider: Failed to create an
            //   instance of androidx.work.impl.WorkDatabase
            //
            // La cadena es: `google_mlkit_pose_detection` (el vestidor de
            // CU-21) arrastra WorkManager, WorkManager usa Room, y Room carga
            // su clase generada `WorkDatabase_Impl` **por reflexion**. R8 la
            // renombra, Room no la encuentra y la aplicacion muere antes de
            // pintar el primer cuadro.
            //
            // Solo pasa en release: en debug no hay R8, y por eso el APK de
            // depuracion venia funcionando y este no.
            //
            // Se apaga en vez de escribir reglas de conservacion porque no hay
            // ninguna exigencia de tamano ni de rendimiento en el proyecto, y
            // las reglas habria que mantenerlas para Room, WorkManager y ML
            // Kit cada vez que uno de los tres cambie de version. El costo es
            // un APK mas grande; la alternativa es que deje de abrir por algo
            // que no avisa hasta que se instala.
            isMinifyEnabled = false
            isShrinkResources = false
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
