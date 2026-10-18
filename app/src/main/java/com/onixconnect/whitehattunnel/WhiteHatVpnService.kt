package com.onixconnect.whitehattunnel

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
