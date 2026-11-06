package io.github.hanyki111.memorycapture

import android.app.Application
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.send.Notifier
import io.github.hanyki111.memorycapture.send.Sender

class CaptureApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifier.channels(this)
        // The widget shows what is waiting, so it follows every change.
        EntryStore.listen { CaptureWidget.refresh(this) }
        // Anything left from before, such as entries written while offline.
        Sender.schedule(this)
    }
}
