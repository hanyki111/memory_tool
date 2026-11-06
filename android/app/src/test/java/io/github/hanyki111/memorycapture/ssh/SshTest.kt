package io.github.hanyki111.memorycapture.ssh

import io.github.hanyki111.memorycapture.core.Outcome
import org.apache.sshd.common.config.keys.AuthorizedKeyEntry
import org.apache.sshd.common.config.keys.KeyUtils
import org.apache.sshd.common.config.keys.PublicKeyEntryResolver
import org.apache.sshd.server.SshServer
import org.apache.sshd.server.channel.ChannelSession
import org.apache.sshd.server.command.Command
import org.apache.sshd.server.keyprovider.SimpleGeneratorHostKeyProvider
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.net.ServerSocket
import java.nio.file.Files
import java.security.PublicKey

/** Runs the client against a real SSH server on this machine. */
class SshTest {

    private lateinit var server: SshServer
    private val received = mutableListOf<String>()
    private val phone = Ssh.generateKey("phone-test")
    private var trusted: PublicKey? = null

    @Before
    fun start() {
        trusted = AuthorizedKeyEntry.parseAuthorizedKeyEntry(phone.publicKeyLine)
            .resolvePublicKey(null, PublicKeyEntryResolver.FAILING)

        server = SshServer.setUpDefaultServer().apply {
            port = 0
            keyPairProvider = SimpleGeneratorHostKeyProvider(Files.createTempFile("host", ".key").also { Files.delete(it) })
            setPublickeyAuthenticator { _, key, _ -> KeyUtils.compareKeys(key, trusted) }
            setPasswordAuthenticator { _, _, _ -> false }
            setCommandFactory { _, command -> FakeShell(command, received) }
        }
        server.start()
    }

    @After
    fun stop() {
        server.stop(true)
    }

    private fun target() = Target("127.0.0.1", server.port, "tester")

    @Test
    fun thePublicKeyIsAnEd25519Line() {
        assertTrue(phone.publicKeyLine, phone.publicKeyLine.startsWith("ssh-ed25519 "))
        assertTrue(phone.publicKeyLine.endsWith(" phone-test"))
    }

    @Test
    fun learnsTheFingerprintThenRunsWithIt() {
        val fingerprint = Ssh.fingerprint(target()).getOrThrow()
        assertTrue(fingerprint, fingerprint.isNotEmpty())

        val outcome = Ssh.run(target(), phone, fingerprint, "echo 한글")

        assertEquals(Outcome.Ran("""{"ok": true, "got": "echo 한글"}""" + "\n", "", 0), outcome)
        assertEquals(listOf("echo 한글"), received)
    }

    /** The fingerprint must read like `ssh-keygen -l` on the PC, so a person can compare them. */
    @Test
    fun theFingerprintMatchesOpenSshsForm() {
        val hostKey = server.keyPairProvider.loadKeys(null).first().public
        val openSsh = KeyUtils.getFingerPrint(hostKey) // "SHA256:…" without padding

        val shown = Ssh.fingerprint(target()).getOrThrow()

        assertEquals(Fingerprints.normalize(openSsh), shown)
        assertTrue(openSsh, openSsh.startsWith("SHA256:"))
    }

    @Test
    fun aDifferentFingerprintIsRefusedBeforeSending() {
        val outcome = Ssh.run(target(), phone, "SHA256:AAAAnotTheRightOne", "echo x")

        assertTrue(outcome is Outcome.NotSent)
        assertEquals("The PC's fingerprint does not match the trusted one", (outcome as Outcome.NotSent).reason)
        assertTrue(outcome.needsPerson)
        assertTrue(received.isEmpty())
    }

    @Test
    fun anUnregisteredKeyIsRefusedBeforeSending() {
        val fingerprint = Ssh.fingerprint(target()).getOrThrow()
        val stranger = Ssh.generateKey("stranger")

        val outcome = Ssh.run(target(), stranger, fingerprint, "echo x")

        assertTrue(outcome.toString(), outcome is Outcome.NotSent && "registered" in outcome.reason)
        assertTrue((outcome as Outcome.NotSent).needsPerson)
        assertTrue(received.isEmpty())
    }

    @Test
    fun noServerIsNotSent() {
        val closedPort = ServerSocket(0).use { it.localPort }

        val outcome = Ssh.run(Target("127.0.0.1", closedPort, "tester"), phone, "SHA256:x", "echo x", timeoutMs = 3_000)

        assertTrue(outcome.toString(), outcome is Outcome.NotSent)
        assertTrue(!(outcome as Outcome.NotSent).needsPerson)
    }

    @Test
    fun aCommandThatEndsWithoutAnExitStatusIsUncertain() {
        val fingerprint = Ssh.fingerprint(target()).getOrThrow()

        val outcome = Ssh.run(target(), phone, fingerprint, "VANISH")

        assertTrue(outcome.toString(), outcome is Outcome.Uncertain)
        assertEquals(listOf("VANISH"), received)
    }

    @Test
    fun aNonZeroExitStatusStillRan() {
        val fingerprint = Ssh.fingerprint(target()).getOrThrow()

        val outcome = Ssh.run(target(), phone, fingerprint, "FAIL")

        assertEquals(Outcome.Ran("", "broken\n", 1), outcome)
    }
}

/** Answers like the PC: prints JSON, or misbehaves on request. */
private class FakeShell(private val command: String, private val received: MutableList<String>) : Command {
    private var out: java.io.OutputStream? = null
    private var err: java.io.OutputStream? = null
    private var exit: org.apache.sshd.server.ExitCallback? = null

    override fun setInputStream(input: java.io.InputStream?) {}
    override fun setOutputStream(output: java.io.OutputStream?) { out = output }
    override fun setErrorStream(error: java.io.OutputStream?) { err = error }
    override fun setExitCallback(callback: org.apache.sshd.server.ExitCallback?) { exit = callback }

    override fun start(channel: ChannelSession, env: org.apache.sshd.server.Environment?) {
        received.add(command)
        when (command) {
            "VANISH" -> channel.close(true)
            "FAIL" -> {
                err!!.write("broken\n".toByteArray()); err!!.flush()
                exit!!.onExit(1)
            }
            else -> {
                out!!.write("""{"ok": true, "got": "$command"}""".plus("\n").toByteArray(Charsets.UTF_8)); out!!.flush()
                exit!!.onExit(0)
            }
        }
    }

    override fun destroy(channel: ChannelSession?) {}
}
