package com.onixconnect.whitehattunnel

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
