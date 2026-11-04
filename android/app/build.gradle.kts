import java.util.Properties

plugins {
    id("com.android.application")
    // Kotlin компилирует сам AGP (built-in Kotlin) — отдельный плагин не нужен.
    id("com.chaquo.python")
}

// Пароли подписи лежат в android/keystore.properties (в git не попадает).
// Если файла нет (например, при клонировании репозитория), release собирается
// без подписи, а debug работает как обычно.
val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties().apply {
    if (keystorePropsFile.exists()) {
        keystorePropsFile.inputStream().use { load(it) }
    }
}

android {
    namespace = "com.textrpg.app"

    // AGP 9: compileSdk задаётся блоком (умеет и минорные версии).
    // release(37) — это обычный Android 17 / API 37.0.
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.textrpg.app"
        minSdk = 24
        // targetSdk в AGP 9 по умолчанию равен compileSdk — не задаём явно.
        versionCode = 12
        versionName = "1.2.5"

        ndk {
            // arm64-v8a — обычные современные телефоны,
            // x86_64 — эмулятор. Для очень старых устройств можно добавить "armeabi-v7a".
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    // Подпись release-сборки постоянным ключом: обновления встают поверх у всех,
    // кому передан APK. Файл ключа и пароли — в android/keystore* (не в git).
    signingConfigs {
        if (keystorePropsFile.exists()) {
            create("release") {
                storeFile = rootProject.file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            if (keystorePropsFile.exists()) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // jvmTarget для Kotlin наследуется от targetCompatibility (17),
    // поэтому устаревший блок kotlinOptions здесь не нужен.
}

dependencies {
    // FileProvider нужен, чтобы установщик Android принял скачанный APK.
    implementation("androidx.core:core-ktx:1.13.1")
}

// Python-пакеты, вкомпилированные в APK.
// Важно: pydantic строго < 2 — на Android нет собранного pydantic-core,
// а FastAPI 0.115.6 официально поддерживает Pydantic v1.
chaquopy {
    defaultConfig {
        version = "3.11"
        // Chaquopy собирает Python-часть тем же Python 3.11, что попадёт в APK.
        // На этой машине 3.11 доступен через лаунчер `py`. При необходимости
        // замените на полный путь:
        //   buildPython("C:/Users/Вы/AppData/Local/Programs/Python/Python311/python.exe")
        buildPython("py", "-3.11")
        pip {
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

// Gradle 9 строго следит за связями между задачами. Задачи Chaquopy читают
// каталог src/main/python, который наполняет stagePython, поэтому связываем их
// явно (иначе сборка падает с ошибкой «implicit dependency»).
tasks.configureEach {
    if (name.contains("Python") && name != "stagePython") {
        dependsOn(stagePython)
    }
}
