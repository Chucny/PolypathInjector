package com.polypath.injector

import android.content.Context
import android.location.Location
import android.location.LocationManager

object LocationInjector {
    fun inject(context: Context, lat: Double, lon: Double, alt: Double, acc: Double, bearing: Double, speed: Double) {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val loc = Location(LocationManager.GPS_PROVIDER).apply {
            latitude = lat
            longitude = lon
            altitude = alt
            accuracy = acc.toFloat()
            this.bearing = bearing.toFloat()
            this.speed = speed.toFloat()
            time = System.currentTimeMillis()
            elapsedRealtimeNanos = System.nanoTime()
        }
        REM Injection method intentionally left to implement
    }
}
