// Верхнеуровневый build-файл: только версии плагинов.
//
// AGP 9 сам компилирует Kotlin (built-in Kotlin), поэтому отдельный плагин
// org.jetbrains.kotlin.android больше не нужен — более того, он несовместим
// с AGP 9 и его применение ломает синхронизацию.
plugins {
    id("com.android.application") version "9.3.3" apply false
    id("com.chaquo.python") version "17.2.0" apply false
}
