package com.polypath.injector

import android.app.Service
import android.content.Intent
import android.os.IBinder

class InjectorService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent ?: return START_NOT_STICKY
        LocationInjector.inject(
            this,
            intent.getDoubleExtra("lat", 0.0),
            intent.getDoubleExtra("lon", 0.0),
            intent.getDoubleExtra("altitude", 0.0),
            intent.getDoubleExtra("accuracy", 5.0),
            intent.getDoubleExtra("bearing", 0.0),
            intent.getDoubleExtra("speed", 0.0)
        )
        stopSelf()
        return START_NOT_STICKY
    }
    override fun onBind(intent: Intent?): IBinder? = null
}
