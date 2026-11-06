package io.github.hanyki111.memorycapture.ssh

import com.jcraft.jsch.ChannelExec
import com.jcraft.jsch.HostKey
import com.jcraft.jsch.HostKeyRepository
import com.jcraft.jsch.JSch
import com.jcraft.jsch.JSchException
import com.jcraft.jsch.KeyPair
import com.jcraft.jsch.Session
import com.jcraft.jsch.UserInfo
import io.github.hanyki111.memorycapture.core.Outcome
import java.io.ByteArrayOutputStream
import java.net.ConnectException
import java.net.NoRouteToHostException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

/** Where the PC is and who to log in as. */
data class Target(val host: String, val port: Int, val user: String)

/** The phone's key: an OpenSSH private key and the public key line for the PC. */
class KeyMaterial(val privateKey: ByteArray, val publicKeyLine: String)

object Ssh {
    init {
        // Android has no Ed25519 or X25519 in its Java crypto, so JSch must use
        // Bouncy Castle for them. Setting it everywhere keeps the JVM tests on
        // the same code as the phone.
        JSch.setConfig("ssh-ed25519", "com.jcraft.jsch.bc.SignatureEd25519")
        JSch.setConfig("ssh-ed448", "com.jcraft.jsch.bc.SignatureEd448")
        JSch.setConfig("keypairgen.eddsa", "com.jcraft.jsch.bc.KeyPairGenEdDSA")
        JSch.setConfig("keypairgen_fromprivate.eddsa", "com.jcraft.jsch.bc.KeyPairGenEdDSA")
        JSch.setConfig("xdh", "com.jcraft.jsch.bc.XDH")
        JSch.setConfig("FingerprintHash", "sha256")
    }

    /** Make the phone's own Ed25519 key. */
    fun generateKey(comment: String): KeyMaterial {
        val jsch = JSch()
        val pair = KeyPair.genKeyPair(jsch, KeyPair.ED25519)
        try {
            // The OpenSSH format is the one JSch can write for Ed25519; the key is
            // encrypted at rest by the app, not by a passphrase.
            val privateKey = ByteArrayOutputStream().also { pair.writeOpenSSHv1PrivateKey(it, null) }.toByteArray()
            val publicKey = ByteArrayOutputStream().also { pair.writePublicKey(it, comment) }.toString(Charsets.UTF_8.name()).trim()
            return KeyMaterial(privateKey, publicKey)
        } finally {
            pair.dispose()
        }
    }

    /**
     * Connect only far enough to learn the PC's host key fingerprint, for the
     * person to compare with the PC before it is trusted.
     */
    fun fingerprint(target: Target, timeoutMs: Int = 15_000): Result<String> {
        val repository = PinnedHostKeys(expected = null)
        val session = newSession(JSch(), target, repository, timeoutMs)
        return try {
            session.connect(timeoutMs)
            Result.failure(IllegalStateException("The PC was accepted without a fingerprint"))
        } catch (e: JSchException) {
            repository.seen?.let { Result.success(it) } ?: Result.failure(IllegalStateException(describe(e)))
        } finally {
            session.disconnect()
        }
    }

    /**
     * Run one command on the PC.
     *
     * Every failure before the command is sent is [Outcome.NotSent], so it is
     * safe to send again. A failure after that is [Outcome.Uncertain]: the
     * command may have run.
     */
    fun run(target: Target, key: KeyMaterial, fingerprint: String, command: String, timeoutMs: Int = 30_000): Outcome {
        val jsch = JSch()
        val session: Session
        try {
            jsch.addIdentity("phone", key.privateKey, null, null)
            session = newSession(jsch, target, PinnedHostKeys(expected = fingerprint), timeoutMs)
        } catch (e: JSchException) {
            return Outcome.NotSent("The phone's key could not be read: ${e.message}", needsPerson = true)
        }

        try {
            try {
                session.connect(timeoutMs)
            } catch (e: JSchException) {
                return Outcome.NotSent(describe(e), needsPerson = isSetupProblem(e))
            }

            val channel = session.openChannel("exec") as ChannelExec
            val stdout = ByteArrayOutputStream()
            val stderr = ByteArrayOutputStream()
            channel.setCommand(command)
            channel.outputStream = stdout
            channel.setErrStream(stderr)

            // From here on the command may have been sent.
            try {
                channel.connect(timeoutMs)
                val deadline = System.currentTimeMillis() + timeoutMs
                while (!channel.isClosed) {
                    if (!session.isConnected) return Outcome.Uncertain("The connection was lost while the PC was running the command")
                    if (System.currentTimeMillis() > deadline) return Outcome.Uncertain("The PC did not answer in time")
                    Thread.sleep(50)
                }
            } catch (e: JSchException) {
                return Outcome.Uncertain("The connection broke while sending the command: ${e.message}")
            } finally {
                channel.disconnect()
            }

            val status = channel.exitStatus
            if (status < 0) return Outcome.Uncertain("The PC closed the command without saying how it ended")
            return Outcome.Ran(stdout.toString(Charsets.UTF_8.name()), stderr.toString(Charsets.UTF_8.name()), status)
        } finally {
            session.disconnect()
        }
    }

    private fun newSession(jsch: JSch, target: Target, repository: HostKeyRepository, timeoutMs: Int): Session {
        jsch.hostKeyRepository = repository
        return jsch.getSession(target.user, target.host, target.port).apply {
            setConfig("StrictHostKeyChecking", "yes")
            // Key login only: never fall back to a password prompt.
            setConfig("PreferredAuthentications", "publickey")
            userInfo = NoPrompts
            timeout = timeoutMs
            serverAliveInterval = 15_000
        }
    }

    /** Failures that waiting for the network will not fix. */
    fun isSetupProblem(e: JSchException): Boolean {
        val message = e.message.orEmpty()
        return listOf("reject HostKey", "HostKey has been changed", "Auth fail", "Auth cancel")
            .any { message.contains(it, ignoreCase = true) }
    }

    /** A short reason for the person, from a failure before the command was sent. */
    fun describe(e: JSchException): String {
        val cause = e.cause
        val message = e.message.orEmpty()
        return when {
            message.contains("reject HostKey", ignoreCase = true) || message.contains("HostKey has been changed", ignoreCase = true) ->
                "The PC's fingerprint does not match the trusted one"
            message.contains("Auth fail", ignoreCase = true) || message.contains("Auth cancel", ignoreCase = true) ->
                "The PC did not accept the phone's key. Is its public key registered on the PC?"
            cause is UnknownHostException -> "The PC's address could not be found"
            cause is ConnectException || cause is NoRouteToHostException -> "The PC could not be reached"
            cause is SocketTimeoutException || message.contains("timeout", ignoreCase = true) -> "The PC did not answer in time"
            else -> message.ifEmpty { e.javaClass.simpleName }
        }
    }
}

/** Never asks anything: there is no one to answer while sending in the background. */
private object NoPrompts : UserInfo {
    override fun getPassphrase(): String? = null
    override fun getPassword(): String? = null
    override fun promptPassword(message: String?) = false
    override fun promptPassphrase(message: String?) = false
    override fun promptYesNo(message: String?) = false
    override fun showMessage(message: String?) {}
}

/**
 * Trusts exactly one host key fingerprint, and remembers the one it was shown.
 *
 * With no expected fingerprint it trusts nothing; that is how the fingerprint
 * is first learned.
 */
private class PinnedHostKeys(private val expected: String?) : HostKeyRepository {
    var seen: String? = null
        private set

    override fun check(host: String?, key: ByteArray?): Int {
        if (key == null) return HostKeyRepository.NOT_INCLUDED
        val shown = HostKey(host ?: "", key).getFingerPrint(JSch())
        seen = Fingerprints.normalize(shown)
        return when {
            expected == null -> HostKeyRepository.NOT_INCLUDED
            Fingerprints.normalize(expected) == seen -> HostKeyRepository.OK
            else -> HostKeyRepository.CHANGED
        }
    }

    override fun add(hostkey: HostKey?, ui: UserInfo?) {}
    override fun remove(host: String?, type: String?) {}
    override fun remove(host: String?, type: String?, key: ByteArray?) {}
    override fun getKnownHostsRepositoryID(): String = "pinned"
    override fun getHostKey(): Array<HostKey> = emptyArray()
    override fun getHostKey(host: String?, type: String?): Array<HostKey> = emptyArray()
}

object Fingerprints {
    /** "SHA256:abc=" and "abc" mean the same fingerprint. */
    fun normalize(fingerprint: String): String =
        fingerprint.trim().removePrefix("SHA256:").trimEnd('=')
}
