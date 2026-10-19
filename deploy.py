import os, subprocess, json, urllib.request

P = "com.onixconnect.whitehattunnel"
PD = "app/src/main/java/" + P.replace(".", "/")

F = {}
F["settings.gradle.kts"] = r'''
pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "WhiteHatTunnel"
include(":app")
'''
F["build.gradle.kts"] = r'''
plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}
'''
F["gradle.properties"] = "org.gradle.jvmargs=-Xmx2g\nandroid.useAndroidX=true\n"
F["app/build.gradle.kts"] = r'''
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.onixconnect.whitehattunnel"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.onixconnect.whitehattunnel"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
'''
F["app/src/main/AndroidManifest.xml"] = r'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:label="White Hat Tunnel" android:theme="@android:style/Theme.Material.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <service android:name=".WhiteHatVpnService"
            android:permission="android.permission.BIND_VPN_SERVICE"
            android:exported="false">
            <intent-filter>
                <action android:name="android.net.VpnService" />
            </intent-filter>
        </service>
    </application>
</manifest>
'''
F[PD + "/WhiteHatVpnService.kt"] = r'''package com.onixconnect.whitehattunnel

import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor

class WhiteHatVpnService : VpnService() {
    private var tun: ParcelFileDescriptor? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP") {
            stopTunnel()
            return START_NOT_STICKY
        }
        if (tun == null) {
            tun = Builder()
                .setSession("White Hat Tunnel")
                .addAddress("10.84.199.26", 32)
                .addRoute("10.84.199.0", 24)
                .addDnsServer("1.1.1.1")
                .establish()
        }
        return START_STICKY
    }

    private fun stopTunnel() {
        tun?.close()
        tun = null
        stopSelf()
    }

    override fun onDestroy() {
        stopTunnel()
        super.onDestroy()
    }
}
'''
F[PD + "/MainActivity.kt"] = r'''package com.onixconnect.whitehattunnel

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.net.TrafficStats
import android.net.VpnService
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.*
import java.io.File

class MainActivity : Activity() {
    private lateinit var down: TextView
    private lateinit var up: TextView
    private lateinit var status: TextView
    private lateinit var logv: TextView
    private lateinit var startBtn: Button
    private var running = false
    private var engine = "Profiles"
    private var lastRx = 0L
    private var lastTx = 0L
    private var peakD = 0L
    private var peakU = 0L
    private val h = Handler(Looper.getMainLooper())

    private val tick = object : Runnable {
        override fun run() {
            val rx = TrafficStats.getTotalRxBytes()
            val tx = TrafficStats.getTotalTxBytes()
            if (lastRx > 0) {
                val d = (rx - lastRx) * 8
                val u = (tx - lastTx) * 8
                peakD = maxOf(peakD, d)
                peakU = maxOf(peakU, u)
                down.text = "Download: $d bps  (peak $peakD)"
                up.text = "Upload: $u bps  (peak $peakU)"
            }
            lastRx = rx
            lastTx = tx
            h.postDelayed(this, 1000)
        }
    }

    private fun log(s: String) {
        logv.append(s + "\n")
    }

    private fun btn(t: String, a: () -> Unit): Button {
        val b = Button(this)
        b.text = t
        b.isAllCaps = false
        b.setOnClickListener { a() }
        return b
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this)
        root.orientation = LinearLayout.VERTICAL
        root.setBackgroundColor(Color.parseColor("#0f1218"))
        root.setPadding(32, 64, 32, 32)

        val title = TextView(this)
        title.text = "White Hat Tunnel"
        title.textSize = 26f
        title.setTextColor(Color.WHITE)
        root.addView(title)

        val by = TextView(this)
        by.text = "Cree par Onix Connect"
        by.setTextColor(Color.GRAY)
        root.addView(by)

        down = TextView(this)
        up = TextView(this)
        status = TextView(this)
        for (t in listOf(down, up, status)) {
            t.setTextColor(Color.WHITE)
            t.textSize = 16f
            t.setPadding(0, 16, 0, 0)
            root.addView(t)
        }
        down.text = "Download: 0 bps (peak 0)"
        up.text = "Upload: 0 bps (peak 0)"
        status.text = "Etat: Idle | IP: 10.84.199.26 | Moteur: $engine"

        val row1 = LinearLayout(this)
        val row2 = LinearLayout(this)
        val engines1 = listOf("Profiles", "SSH", "V2Ray")
        val engines2 = listOf("Psiphon", "OpenVPN", "UDP Custom")
        for (e in engines1) row1.addView(btn(e) { pick(e) })
        for (e in engines2) row2.addView(btn(e) { pick(e) })
        root.addView(row1)
        root.addView(row2)

        root.addView(btn("Importer un fichier (.ovpn, .json, .conf, .txt)") {
            val i = Intent(Intent.ACTION_OPEN_DOCUMENT)
            i.addCategory(Intent.CATEGORY_OPENABLE)
            i.type = "*/*"
            startActivityForResult(i, 2)
        })

        startBtn = btn("START") { toggle() }
        root.addView(startBtn)

        val sv = ScrollView(this)
        logv = TextView(this)
        logv.setTextColor(Color.parseColor("#9fe870"))
        logv.textSize = 12f
        sv.addView(logv)
        root.addView(sv, LinearLayout.LayoutParams(-1, 0, 1f))

        setContentView(root)
        log("White Hat Tunnel pret.")
        h.post(tick)
    }

    private fun pick(e: String) {
        engine = e
        status.text = "Etat: " + (if (running) "Connecte" else "Idle") + " | IP: 10.84.199.26 | Moteur: $e"
        log("Moteur selectionne: $e")
    }

    private fun toggle() {
        if (running) {
            val i = Intent(this, WhiteHatVpnService::class.java)
            i.action = "STOP"
            startService(i)
            running = false
            startBtn.text = "START"
            pick(engine)
            log("Tunnel arrete")
        } else {
            val p = VpnService.prepare(this)
            if (p != null) startActivityForResult(p, 1) else startVpn()
        }
    }

    private fun startVpn() {
        startService(Intent(this, WhiteHatVpnService::class.java))
        running = true
        startBtn.text = "STOP"
        pick(engine)
        log("Tunnel demarre avec $engine")
    }

    override fun onActivityResult(req: Int, res: Int, data: Intent?) {
        super.onActivityResult(req, res, data)
        if (req == 1 && res == RESULT_OK) startVpn()
        if (req == 2 && res == RESULT_OK && data?.data != null) {
            try {
                val txt = contentResolver.openInputStream(data.data!!)!!.bufferedReader().readText()
                val dir = File(filesDir, "profiles")
                dir.mkdirs()
                val name = "profile_" + System.currentTimeMillis() + ".cfg"
                File(dir, name).writeText(txt)
                log("Profil importe: $name (" + txt.length + " octets)")
            } catch (e: Exception) {
                log("Erreur import: " + e.message)
            }
        }
    }
}
'''
F[".github/workflows/build.yml"] = r'''
name: Build APK
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: 17
      - uses: gradle/actions/setup-gradle@v4
        with:
          gradle-version: 8.7
      - run: gradle assembleDebug --no-daemon
      - uses: actions/upload-artifact@v4
        with:
          name: WhiteHatTunnel
          path: app/build/outputs/apk/debug/app-debug.apk
      - name: Release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          cp app/build/outputs/apk/debug/app-debug.apk WhiteHatTunnel.apk
          gh release create "v${{ github.run_number }}" WhiteHatTunnel.apk --title "White Hat Tunnel v${{ github.run_number }}" --notes "Build auto - Onix Connect"
'''

for path, content in F.items():
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content.lstrip("\n"))

user = input("Pseudo GitHub : ").strip()
token = input("Token GitHub : ").strip()
repo = "WhiteHatTunnel"

req = urllib.request.Request(
    "https://api.github.com/user/repos",
    data=json.dumps({"name": repo, "private": False}).encode(),
    headers={"Authorization": "token " + token, "Accept": "application/vnd.github+json"},
)
try:
    urllib.request.urlopen(req)
    print("Depot cree.")
except Exception as e:
    print("Depot existe deja ou erreur:", e)

def sh(c):
    subprocess.run(c, shell=True, check=False)

sh("git init -q -b main")
sh('git config user.email "onix@connect.app" && git config user.name "Onix Connect"')
sh("git add -A && git commit -q -m 'White Hat Tunnel build'")
sh("git remote remove origin 2>/dev/null")
sh(f"git remote add origin https://{user}:{token}@github.com/{user}/{repo}.git")
sh("git push -u origin main --force")
print(f"\nFini ! Suis la compilation : https://github.com/{user}/{repo}/actions")
print(f"APK (apres ~5 min) : https://github.com/{user}/{repo}/releases")
