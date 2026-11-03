package com.textrpg.app

import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.provider.Settings
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.webkit.JavascriptInterface
import android.webkit.JsPromptResult
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.Toast
import androidx.core.content.FileProvider
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Единственный экран приложения.
 *
 * Запускает Python-сервер игры в фоновом потоке (Chaquopy) и показывает тот же
 * веб-интерфейс, что и на десктопе, внутри WebView на адресе 127.0.0.1.
 * В страницу встроен мост `Android`: выход, сохранение лога и установка
 * обновления — то, что из браузера сделать нельзя.
 */
class MainActivity : Activity() {

    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null

    private val prefs: SharedPreferences by lazy {
        getSharedPreferences("textrpg", MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            settings.allowContentAccess = true
            settings.useWideViewPort = true
            // Без этого WebView может «отзумить» страницу и уменьшить весь текст.
            settings.loadWithOverviewMode = false
            settings.mediaPlaybackRequiresUserGesture = false
            // Интерфейс лежит локально: кэш не нужен, а после обновления APK
            // он подсовывает старые index.html и CSS. Отключаем начисто.
            @Suppress("DEPRECATION")
            settings.cacheMode = WebSettings.LOAD_NO_CACHE

            // Мост в веб-страницу: выход, лог и установка обновления.
            addJavascriptInterface(Bridge(), "Android")

            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: WebView?,
                    request: WebResourceRequest?
                ): Boolean {
                    val url = request?.url?.toString() ?: return false
                    // Свои страницы (локальный сервер) остаются внутри WebView,
                    // внешние ссылки открываем в браузере телефона.
                    return if (url.startsWith("http://127.0.0.1") || url.startsWith("http://localhost")) {
                        false
                    } else {
                        openExternal(url)
                        true
                    }
                }
            }

            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(
                    webView: WebView?,
                    callback: ValueCallback<Array<Uri>>?,
                    params: FileChooserParams?
                ): Boolean {
                    filePathCallback?.onReceiveValue(null)
                    filePathCallback = callback
                    // ACTION_OPEN_DOCUMENT надёжнее GET_CONTENT: провайдер отдаёт
                    // стабильный URI, который мы сами прочитаем и скопируем.
                    val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "*/*"
                    }
                    return try {
                        startActivityForResult(
                            Intent.createChooser(intent, "Выберите файл книги (.txt)"),
                            REQUEST_FILE
                        )
                        true
                    } catch (e: Exception) {
                        filePathCallback = null
                        false
                    }
                }

                // window.prompt() в WebView по умолчанию не показывается вовсе —
                // без этого на телефоне нельзя было выбрать слот для предмета.
                override fun onJsPrompt(
                    view: WebView?,
                    url: String?,
                    message: String?,
                    defaultValue: String?,
                    result: JsPromptResult?
                ): Boolean {
                    if (result == null) return false
                    val input = EditText(this@MainActivity).apply {
                        setText(defaultValue ?: "")
                        setSingleLine(true)
                        selectAll()
                    }
                    android.app.AlertDialog.Builder(this@MainActivity)
                        .setTitle(message ?: "")
                        .setView(input)
                        .setCancelable(false)
                        .setPositiveButton("ОК") { _, _ -> result.confirm(input.text.toString()) }
                        .setNegativeButton("Отмена") { _, _ -> result.cancel() }
                        .show()
                    return true
                }
            }
        }

        setContentView(webView)
        applyImmersiveMode()
        showLoading()
        startServerAndLoad()
    }

    /**
     * Полноэкранный режим: прячем системные панели (строку состояния сверху и
     * панель навигации снизу). Они остаются доступны жестом от края экрана.
     */
    private fun applyImmersiveMode() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.let { controller ->
                controller.hide(WindowInsets.Type.systemBars())
                controller.systemBarsBehavior =
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    or View.SYSTEM_UI_FLAG_FULLSCREEN
                )
        }
    }

    override fun onResume() {
        super.onResume()
        applyImmersiveMode()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        // Прячем панели заново, если система показала их после свайпа.
        if (hasFocus) applyImmersiveMode()
    }

    /** Запускает сервер (однократно) и открывает игру. */
    private fun startServerAndLoad() {
        serverUrl?.let {
            loadGame(it)
            return
        }

        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        // Старый ключ из настроек Android, если пользователь вводил его раньше:
        // он остаётся запасным для провайдера proxyapi. Основные настройки
        // (провайдер, ключ, модель) теперь задаются в меню игры.
        val apiKey = prefs.getString(KEY_API, "") ?: ""
        Thread {
            val url = try {
                Python.getInstance()
                    .getModule("bootstrap")
                    .callAttr("start", filesDir.absolutePath, apiKey)
                    .toString()
            } catch (e: Exception) {
                null
            }
            runOnUiThread {
                if (url != null) {
                    serverUrl = url
                    loadGame(url)
                } else {
                    Toast.makeText(
                        this,
                        "Не удалось запустить сервер. Подробности — в Logcat (python.stderr).",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }.start()
    }

    /**
     * Открывает игру с гарантированно свежей вёрсткой: чистит кэш WebView и
     * добавляет версию ассетов в URL, чтобы не осталось старой страницы.
     */
    private fun loadGame(url: String) {
        webView.clearCache(true)
        val sep = if (url.contains('?')) '&' else '?'
        webView.loadUrl("$url${sep}v=$ASSET_VERSION")
    }

    private fun showLoading() {
        val html = """
            <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
              body{background:#2e3440;color:#d8dee9;font-family:sans-serif;margin:0;
                   display:flex;align-items:center;justify-content:center;height:100vh}
            </style></head>
            <body><p>Запускаю игру…</p></body></html>
        """.trimIndent()
        webView.loadDataWithBaseURL(null, html, "text/html", "utf-8", null)
    }

    /** Открывает внешнюю ссылку в браузере телефона. */
    private fun openExternal(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (e: Exception) {
            Toast.makeText(this, "Не удалось открыть ссылку", Toast.LENGTH_SHORT).show()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (this::webView.isInitialized && webView.canGoBack()) {
            webView.goBack()
        } else {
            @Suppress("DEPRECATION")
            super.onBackPressed()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == REQUEST_FILE) {
            val callback = filePathCallback
            filePathCallback = null
            if (callback == null) {
                super.onActivityResult(requestCode, resultCode, data)
                return
            }

            val uri = data?.data
            if (resultCode != RESULT_OK || uri == null) {
                callback.onReceiveValue(null)
                return
            }

            // Копируем выбранный файл в кэш приложения и отдаём WebView обычный
            // путь к файлу. Так загрузка не зависит от того, как ведёт себя
            // конкретный файловый провайдер телефона (на MIUI бывали зависания).
            Thread {
                val local = try {
                    copyToCache(uri)
                } catch (e: Exception) {
                    null
                }
                runOnUiThread {
                    if (local != null) {
                        callback.onReceiveValue(arrayOf(local))
                    } else {
                        // Резервный путь: пробуем отдать исходный URI как есть.
                        Toast.makeText(
                            this,
                            "Не удалось подготовить файл, пробую напрямую…",
                            Toast.LENGTH_SHORT
                        ).show()
                        callback.onReceiveValue(arrayOf(uri))
                    }
                }
            }.start()
            return
        }
        @Suppress("DEPRECATION")
        super.onActivityResult(requestCode, resultCode, data)
    }

    /** Читает выбранный документ и кладёт его копию в кэш приложения. */
    private fun copyToCache(uri: Uri): Uri? {
        val dir = File(cacheDir, "uploads")
        dir.mkdirs()
        // Прошлые книги не копим — телефону и так тесно.
        dir.listFiles()?.forEach { it.delete() }

        var name = "book.txt"
        try {
            contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (index >= 0 && cursor.moveToFirst()) {
                    val display = cursor.getString(index)
                    if (!display.isNullOrBlank()) name = display
                }
            }
        } catch (e: Exception) {
            // Не критично: имя можно и не узнать.
        }

        val safe = name.replace(Regex("[^A-Za-z0-9._-]"), "_")
        val fileName = if (safe.lowercase().endsWith(".txt")) safe else "book.txt"
        val target = File(dir, fileName)

        contentResolver.openInputStream(uri)?.use { input ->
            target.outputStream().use { output -> input.copyTo(output) }
        } ?: return null

        return if (target.exists() && target.length() > 0) Uri.fromFile(target) else null
    }

    override fun onDestroy() {
        filePathCallback?.onReceiveValue(null)
        filePathCallback = null
        super.onDestroy()
    }

    /**
     * Мост «страница → Android». Из браузера это недоступно, поэтому методы
     * вызываются только внутри приложения.
     */
    private inner class Bridge {

        /** Выход из игры. */
        @JavascriptInterface
        fun exitApp() {
            runOnUiThread { finishAffinity() }
        }

        /** Открывает ссылку во внешнем браузере (страницы провайдеров). */
        @JavascriptInterface
        fun openUrl(url: String) {
            runOnUiThread { openExternal(url) }
        }

        /** Версия приложения (versionName) — для проверки обновлений. */
        @JavascriptInterface
        fun appVersion(): String = try {
            packageManager.getPackageInfo(packageName, 0).versionName ?: ""
        } catch (e: Exception) {
            ""
        }

        /** Скачивает журнал игры с локального сервера в «Загрузки». */
        @JavascriptInterface
        fun saveLog(playerId: String) {
            val base = serverUrl
            if (base == null) {
                toast("Сервер ещё не запустился")
                return
            }
            Thread {
                try {
                    val text = httpGetText("${base}player/$playerId/log")
                    if (text == null) {
                        toast("Не удалось получить журнал")
                        return@Thread
                    }
                    val name = "textrpg-log-$playerId.txt"
                    val where = saveText(name, text)
                    toast(if (where != null) "Журнал сохранён: $where" else "Не удалось сохранить журнал")
                } catch (e: Exception) {
                    toast("Ошибка журнала: ${e.message}")
                }
            }.start()
        }

        /** Скачивает APK обновления и открывает системную установку. */
        @JavascriptInterface
        fun downloadAndInstall(url: String) {
            runOnUiThread {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                    !packageManager.canRequestPackageInstalls()
                ) {
                    Toast.makeText(
                        this@MainActivity,
                        "Разрешите установку приложений из этого источника",
                        Toast.LENGTH_LONG
                    ).show()
                    try {
                        startActivity(
                            Intent(
                                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                Uri.parse("package:$packageName")
                            )
                        )
                    } catch (e: Exception) {
                        // Настройки могут отсутствовать — пользователь сделает это вручную.
                    }
                    return@runOnUiThread
                }

                Toast.makeText(this@MainActivity, "Скачиваю обновление…", Toast.LENGTH_SHORT).show()
                Thread {
                    try {
                        val apk = File(cacheDir, "update.apk")
                        downloadFile(url, apk)
                        runOnUiThread { installApk(apk) }
                    } catch (e: Exception) {
                        toast("Не удалось скачать обновление: ${e.message}")
                    }
                }.start()
            }
        }
    }

    private fun installApk(file: File) {
        try {
            val uri = FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(intent)
        } catch (e: Exception) {
            toast("Не удалось открыть установщик: ${e.message}")
        }
    }

    /** Читает текст по HTTP (журнал игры с локального сервера). */
    private fun httpGetText(url: String): String? {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 15000
            readTimeout = 30000
        }
        return try {
            if (connection.responseCode != 200) return null
            connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }

    /** Скачивает файл, самостоятельно проходя перенаправления GitHub. */
    private fun downloadFile(url: String, target: File) {
        var current = url
        var hops = 0
        while (true) {
            val connection = (URL(current).openConnection() as HttpURLConnection).apply {
                instanceFollowRedirects = false
                connectTimeout = 20000
                readTimeout = 60000
                setRequestProperty("User-Agent", "TextRPG-Updater")
            }
            val code = connection.responseCode
            if (code in 300..399) {
                val location = connection.getHeaderField("Location")
                    ?: throw Exception("нет адреса перенаправления")
                current = if (location.startsWith("http")) {
                    location
                } else {
                    URL(URL(current), location).toString()
                }
                connection.disconnect()
                hops++
                if (hops > 6) throw Exception("слишком много перенаправлений")
                continue
            }
            if (code != 200) {
                connection.disconnect()
                throw Exception("HTTP $code")
            }
            connection.inputStream.use { input ->
                target.outputStream().use { output -> input.copyTo(output) }
            }
            connection.disconnect()
            return
        }
    }

    /** Сохраняет текст в «Загрузки» (на новых Android — без разрешений). */
    private fun saveText(name: String, content: String): String? {
        val bytes = content.toByteArray(Charsets.UTF_8)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, name)
                put(MediaStore.Downloads.MIME_TYPE, "text/plain")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val resolver = contentResolver
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: return null
            resolver.openOutputStream(uri)?.use { it.write(bytes) }
            values.clear()
            values.put(MediaStore.Downloads.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
            return "Загрузки/$name"
        }

        // Android 7–9: публичная папка требует разрешения, поэтому пишем в
        // собственную папку приложения — она видна через файловый менеджер.
        val dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS) ?: filesDir
        dir.mkdirs()
        val file = File(dir, name)
        file.writeBytes(bytes)
        return file.absolutePath
    }

    private fun toast(message: String) {
        runOnUiThread { Toast.makeText(this, message, Toast.LENGTH_LONG).show() }
    }

    companion object {
        private const val KEY_API = "proxy_api_key"
        private const val REQUEST_FILE = 1001

        // Версия веб-ассетов: меняйте при правках вёрстки/CSS, чтобы WebView
        // не использовал закэшированную страницу.
        private const val ASSET_VERSION = 6

        // Адрес сервера, чтобы не поднимать его повторно после пересоздания Activity.
        @Volatile
        private var serverUrl: String? = null
    }
}
