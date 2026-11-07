package io.github.hanyki111.memorycapture.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import io.github.hanyki111.memorycapture.core.Accent
import io.github.hanyki111.memorycapture.core.CommandTemplate
import io.github.hanyki111.memorycapture.core.KnowledgeBase
import io.github.hanyki111.memorycapture.core.Mode
import io.github.hanyki111.memorycapture.ssh.KeyMaterial
import io.github.hanyki111.memorycapture.ssh.Ssh
import io.github.hanyki111.memorycapture.ssh.Target
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** What the person sets: the PC, the knowledge base, the voice delay, the trusted fingerprint and the look. */
class Settings(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var host: String
        get() = prefs.getString("host", "").orEmpty()
        set(value) = prefs.edit().putString("host", value.trim()).apply()

    var port: Int
        get() = prefs.getInt("port", 22)
        set(value) = prefs.edit().putInt("port", value).apply()

    var user: String
        get() = prefs.getString("user", "").orEmpty()
        set(value) = prefs.edit().putString("user", value.trim()).apply()

    /**
     * The knowledge base folder on the PC. Up to 0.2 the person wrote the whole
     * command; its folder is taken from it until a folder is saved.
     */
    var basePath: String
        get() = prefs.getString("basePath", null) ?: KnowledgeBase.pathFrom(prefs.getString("template", null)).orEmpty()
        set(value) = prefs.edit().putString("basePath", value.trim()).remove("template").apply()

    /** How memory_tool is run, or null while the folder cannot be used */
    fun command(): CommandTemplate? = basePath.takeIf { KnowledgeBase.problem(it) == null }?.let { KnowledgeBase.command(it) }

    var mode: Mode
        get() = Mode.of(prefs.getString("mode", null))
        set(value) = prefs.edit().putString("mode", value.key).apply()

    var accent: Accent
        get() = Accent.of(prefs.getString("accent", null))
        set(value) = prefs.edit().putString("accent", value.key).apply()

    /** Seconds a voice entry is shown before it is sent */
    var voiceDelaySeconds: Int
        get() = prefs.getInt("voiceDelay", 3)
        set(value) = prefs.edit().putInt("voiceDelay", value.coerceIn(0, 30)).apply()

    /** The app's text size, in percent of the phone's own; [FONT_MIN] to [FONT_MAX] in steps of 10 */
    var fontPercent: Int
        get() = prefs.getInt("fontPercent", 100).coerceIn(FONT_MIN, FONT_MAX)
        set(value) = prefs.edit().putInt("fontPercent", (value.coerceIn(FONT_MIN, FONT_MAX) / 10) * 10).apply()

    /** The PC's host key fingerprint the person confirmed, or empty */
    var fingerprint: String
        get() = prefs.getString("fingerprint", "").orEmpty()
        set(value) = prefs.edit().putString("fingerprint", value).apply()

    fun target(): Target? =
        if (host.isEmpty() || user.isEmpty() || port !in 1..65535) null else Target(host, port, user)

    /** What is still missing before anything can be sent, or null when ready. */
    fun missing(): String? = when {
        target() == null -> "PC address, port and user"
        command() == null -> "the knowledge base folder"
        fingerprint.isEmpty() -> "the PC's fingerprint"
        else -> null
    }

    companion object {
        /** Android's own text size goes up to 200 percent as well */
        const val FONT_MIN = 70
        const val FONT_MAX = 200
    }
}

/**
 * The phone's SSH key. The private key is encrypted with a key that lives in
 * the Android Keystore and never leaves it, so the stored file is useless
 * anywhere else.
 */
class PhoneKey(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("phone_key", Context.MODE_PRIVATE)

    /** The key, made on first use. */
    @Synchronized
    fun get(): KeyMaterial {
        val publicLine = prefs.getString("public", null)
        val sealed = prefs.getString("private", null)
        val iv = prefs.getString("iv", null)
        if (publicLine != null && sealed != null && iv != null) {
            try {
                val cipher = Cipher.getInstance(TRANSFORMATION)
                cipher.init(Cipher.DECRYPT_MODE, wrappingKey(), GCMParameterSpec(128, decode(iv)))
                return KeyMaterial(cipher.doFinal(decode(sealed)), publicLine)
            } catch (e: Exception) {
                // The Keystore key is gone, as after data was copied from another
                // phone. The old key cannot be opened; make a new one, which the
                // person registers on the PC like any new phone.
                prefs.edit().clear().commit()
            }
        }

        val fresh = Ssh.generateKey("memory-capture@${android.os.Build.MODEL.replace(' ', '-')}")
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, wrappingKey())
        prefs.edit()
            .putString("public", fresh.publicKeyLine)
            .putString("private", encode(cipher.doFinal(fresh.privateKey)))
            .putString("iv", encode(cipher.iv))
            .apply()
        return fresh
    }

    fun publicKeyLine(): String = get().publicKeyLine

    private fun wrappingKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(ALIAS, null) as? SecretKey)?.let { return it }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }

    private fun encode(bytes: ByteArray) = Base64.encodeToString(bytes, Base64.NO_WRAP)
    private fun decode(text: String) = Base64.decode(text, Base64.NO_WRAP)

    private companion object {
        const val ALIAS = "memorycapture.ssh-key"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
