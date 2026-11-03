plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "com.textrpg.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.textrpg.app"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        ndk {
            // arm64-v8a — обычные современные телефоны,
            // x86_64 — эмулятор. Для очень старых устройств можно добавить "armeabi-v7a".
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

// Python-пакеты, вкомпилированные в APK.
// Важно: pydantic строго < 2 — на Android нет собранного pydantic-core,
// а FastAPI 0.115.6 официально поддерживает Pydantic v1.
chaquopy {
    defaultConfig {
        version = "3.11"
        // Chaquopy требует на машине сборки Python той же версии (3.11).
        // Обычно хватает `py -3.11`; при необходимости укажите путь явно:
        // buildPython("C:/Users/Вы/AppData/Local/Programs/Python/Python311/python.exe")
        pip {
            install("numpy")
            install("pydantic==1.10.18")
            install("fastapi==0.115.6")
            install("starlette==0.41.3")
            install("uvicorn==0.32.1")
            install("sqlalchemy==2.0.36")
            install("python-multipart==0.0.12")
            install("requests==2.32.3")
        }
    }
}

// Перед сборкой копируем Python-код игры и веб-интерфейс из корня проекта
// в src/main/python — Chaquopy упаковывает именно этот каталог.
val stagePython by tasks.registering(Sync::class) {
    from(rootProject.projectDir.parentFile) {
        include("main.py")
        include("app/**")
        include("static/**")
        include("index.html")
        exclude("**/__pycache__/**")
        exclude("**/*.pyc")
    }
    from(rootProject.file("python")) {
        include("bootstrap.py")
    }
    into(file("src/main/python"))
}

tasks.named("preBuild") {
    dependsOn(stagePython)
}
