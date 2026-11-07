package io.github.hanyki111.memorycapture

import android.app.Application
import android.content.res.Configuration
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.send.NetworkWatch
import io.github.hanyki111.memorycapture.send.Notifier
import io.github.hanyki111.memorycapture.send.Sender

class CaptureApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifier.channels(this)
        // The widget shows what is waiting, so it follows every change.
        // Waking on a returning network follows it too.
        EntryStore.listen {
            CaptureWidget.refresh(this)
            NetworkWatch.update(this)
        }
        // Anything left from before, such as entries written while offline.
        Sender.schedule(this)
        NetworkWatch.update(this)
    }

    /** The phone turned light or dark: the widget follows when the app is set to. */
    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        CaptureWidget.refresh(this)
    }
}
