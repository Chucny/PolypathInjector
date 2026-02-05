package com.polypath.injector

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class MockReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != "send.mock") return
        val svc = Intent(context, InjectorService::class.java).apply {
            putExtras(intent.extras ?: return)
        }
        context.startService(svc)
    }
}
