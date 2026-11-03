package com.textrpg.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.Toast
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/**
 * Единственный экран приложения.
 *
 * Запускает Python-сервер игры в фоновом потоке (Chaquopy) и показывает тот же
 * веб-интерфейс, что и на десктопе, внутри WebView на адресе 127.0.0.1.
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

            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(
                    webView: WebView?,
                    callback: ValueCallback<Array<Uri>>?,
                    params: FileChooserParams?
                ): Boolean {
                    filePathCallback?.onReceiveValue(null)
                    filePathCallback = callback
                    val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
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
            }
        }

        setContentView(webView)
        applyImmersiveMode()
        showLoading()

        if (prefs.getString(KEY_API, "").isNullOrBlank()) {
            promptForApiKey(firstRun = true)
        } else {
            startServerAndLoad()
        }
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

    private fun promptForApiKey(firstRun: Boolean) {
        val input = EditText(this).apply {
            hint = "PROXYAPI_KEY"
            setText(prefs.getString(KEY_API, "") ?: "")
            setSingleLine(true)
        }

        AlertDialog.Builder(this)
            .setTitle("Ключ proxyapi")
            .setMessage("Введите ключ PROXYAPI_KEY — он нужен для обращений к модели.")
            .setView(input)
            .setCancelable(!firstRun)
            .setPositiveButton("Сохранить") { _, _ ->
                prefs.edit().putString(KEY_API, input.text.toString().trim()).apply()
                if (firstRun) {
                    startServerAndLoad()
                } else {
                    Toast.makeText(
                        this,
                        "Ключ сохранён. Перезапустите приложение.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
            .setNegativeButton(if (firstRun) "Выйти" else "Отмена") { _, _ ->
                if (firstRun) finish()
            }
            .show()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(Menu.NONE, MENU_API_KEY, Menu.NONE, "Ключ API")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return if (item.itemId == MENU_API_KEY) {
            promptForApiKey(firstRun = false)
            true
        } else {
            super.onOptionsItemSelected(item)
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
            val result = if (resultCode == RESULT_OK && data?.data != null) {
                arrayOf(data.data!!)
            } else {
                null
            }
            filePathCallback?.onReceiveValue(result)
            filePathCallback = null
            return
        }
        @Suppress("DEPRECATION")
        super.onActivityResult(requestCode, resultCode, data)
    }

    override fun onDestroy() {
        filePathCallback?.onReceiveValue(null)
        filePathCallback = null
        super.onDestroy()
    }

    companion object {
        private const val KEY_API = "proxy_api_key"
        private const val REQUEST_FILE = 1001
        private const val MENU_API_KEY = 1

        // Версия веб-ассетов: меняйте при правках вёрстки/CSS, чтобы WebView
        // не использовал закэшированную страницу.
        private const val ASSET_VERSION = 3

        // Адрес сервера, чтобы не поднимать его повторно после пересоздания Activity.
        @Volatile
        private var serverUrl: String? = null
    }
}
