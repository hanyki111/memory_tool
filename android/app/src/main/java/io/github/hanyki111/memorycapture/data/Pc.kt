package io.github.hanyki111.memorycapture.data

import android.content.Context
import io.github.hanyki111.memorycapture.R
import io.github.hanyki111.memorycapture.core.CommandTemplate
import io.github.hanyki111.memorycapture.core.Outcome
import io.github.hanyki111.memorycapture.core.PcReply
import io.github.hanyki111.memorycapture.core.PowerShell
import io.github.hanyki111.memorycapture.ssh.Ssh

/** What came of asking the PC something. */
sealed class Call<out T> {
    data class Done<T>(val value: T) : Call<T>()

    /** memory_tool answered no, with its failure code. */
    data class Refused(val code: String, val message: String) : Call<Nothing>()

    /**
     * No usable answer. `mayHaveRun` is set when the command went out and the
     * connection broke, so a change may or may not have been made.
     */
    data class Failed(val reason: String, val mayHaveRun: Boolean = false) : Call<Nothing>()
}

/** Runs memory_tool on the PC through the saved command, for reading and changing the timeline. Blocking. */
object Pc {
    fun <T> call(context: Context, args: List<String>, read: (String, String) -> PcReply<T>): Call<T> {
        val settings = Settings(context)
        settings.missing()?.let { return Call.Failed(context.getString(R.string.pc_setup_needed, it)) }
        val template = CommandTemplate.parse(settings.template).getOrElse { return Call.Failed(it.message ?: "") }
        val command = PowerShell.forTransport(template.fill(args))
        return when (val outcome = Ssh.run(settings.target()!!, PhoneKey(context).get(), settings.fingerprint, command)) {
            is Outcome.NotSent -> Call.Failed(outcome.reason)
            is Outcome.Uncertain -> Call.Failed(outcome.reason, mayHaveRun = true)
            is Outcome.Ran -> when (val reply = read(outcome.stdout, outcome.stderr)) {
                is PcReply.Ok -> Call.Done(reply.value)
                is PcReply.Refused -> Call.Refused(reply.code, reply.message.ifEmpty { reply.code })
                is PcReply.Unreadable -> Call.Failed(reply.firstLine.ifEmpty { context.getString(R.string.notify_unreadable) })
            }
        }
    }
}
