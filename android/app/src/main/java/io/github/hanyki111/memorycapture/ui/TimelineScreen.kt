package io.github.hanyki111.memorycapture.ui

import android.app.Activity
import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.content.Intent
import android.speech.RecognizerIntent
import android.text.format.DateFormat
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import io.github.hanyki111.memorycapture.R
import io.github.hanyki111.memorycapture.core.Days
import io.github.hanyki111.memorycapture.core.Entry
import io.github.hanyki111.memorycapture.core.State
import io.github.hanyki111.memorycapture.core.TimelineEntry
import io.github.hanyki111.memorycapture.core.Transitions
import io.github.hanyki111.memorycapture.core.normalTime
import io.github.hanyki111.memorycapture.data.EntryStore
import io.github.hanyki111.memorycapture.send.Sender
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * The first screen: the PC's timeline, newest first, with a search field on
 * top, the phone's unsent entries above the timeline, and a field at the
 * bottom that sends at once.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TimelineScreen(model: TimelineModel, phoneEntries: List<Entry>, onSettings: () -> Unit) {
    val snackbar = remember { SnackbarHostState() }
    var editing by remember { mutableStateOf<TimelineEntry?>(null) }
    val list = rememberLazyListState()

    LaunchedEffect(Unit) { model.start() }
    LaunchedEffect(model.message) {
        model.message?.let { snackbar.showSnackbar(it); model.message = null }
    }

    // A phone entry the PC just recorded shows up in its day.
    val lastSent = phoneEntries.filter { it.state == State.SENT }.maxByOrNull { it.changedAt }
    val shownAt = remember { System.currentTimeMillis() }
    LaunchedEffect(lastSent?.id, lastSent?.changedAt) {
        if (lastSent != null && lastSent.changedAt > shownAt) model.reload(listOf(lastSent.date))
    }

    // Reaching the end loads the week before, after a week that had entries.
    val atEnd by remember {
        derivedStateOf {
            val info = list.layoutInfo
            info.totalItemsCount > 0 && (info.visibleItemsInfo.lastOrNull()?.index ?: 0) >= info.totalItemsCount - 2
        }
    }
    LaunchedEffect(atEnd, model.autoLoad, model.results) {
        if (atEnd && model.autoLoad && model.results == null && model.error == null) model.loadOlder()
    }

    Scaffold(
        topBar = { SearchBar(model, onSettings) },
        bottomBar = { InputBar() },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { inner ->
        PullToRefreshBox(
            isRefreshing = model.refreshing,
            onRefresh = { model.refresh() },
            modifier = Modifier.fillMaxSize().padding(inner),
        ) {
            LazyColumn(Modifier.fillMaxSize(), state = list) {
                queueItems(phoneEntries)
                if (model.results != null || model.searching || model.searchError != null) {
                    searchItems(model) { editing = it }
                } else {
                    timelineItems(model) { editing = it }
                }
            }
        }
    }

    editing?.let { entry -> EditSheet(model, entry, onClose = { editing = null }) }
}

@Composable
private fun SearchBar(model: TimelineModel, onSettings: () -> Unit) {
    val focus = LocalFocusManager.current
    Surface(tonalElevation = 2.dp) {
        Row(
            Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 8.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = model.query,
                onValueChange = { model.query = it },
                placeholder = { Text(stringResource(R.string.search_hint)) },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                trailingIcon = {
                    if (model.query.isNotEmpty() || model.results != null) {
                        IconButton(onClick = { model.clearSearch(); focus.clearFocus() }) {
                            Icon(Icons.Filled.Clear, contentDescription = stringResource(R.string.search_clear))
                        }
                    }
                },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { model.search(); focus.clearFocus() }),
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = onSettings) {
                Icon(Icons.Filled.Settings, contentDescription = stringResource(R.string.settings))
            }
        }
    }
}

/** Write and send without opening anything; speech fills the field. */
@Composable
private fun InputBar() {
    val context = LocalContext.current
    var text by remember { mutableStateOf("") }
    val speech = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val heard = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
        if (result.resultCode == Activity.RESULT_OK && !heard.isNullOrBlank()) {
            text = if (text.isBlank()) heard else "${text.trimEnd()} $heard"
        }
    }

    fun send() {
        val entry = text.trim()
        if (entry.isEmpty()) return
        EntryStore.add(context, entry)
        Sender.schedule(context)
        text = ""
    }

    Surface(tonalElevation = 2.dp) {
        Row(
            Modifier.fillMaxWidth().navigationBarsPadding().imePadding().padding(horizontal = 8.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                placeholder = { Text(stringResource(R.string.capture_hint)) },
                maxLines = 4,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { send() }),
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = {
                val request = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                    .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    .putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
                runCatching { speech.launch(request) }
            }) {
                Icon(painterResource(R.drawable.ic_mic), contentDescription = stringResource(R.string.capture_voice))
            }
            IconButton(onClick = ::send, enabled = text.isNotBlank()) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = stringResource(R.string.capture_send))
            }
        }
    }
}

// ---- the list -------------------------------------------------------------

private fun LazyListScope.timelineItems(model: TimelineModel, onEdit: (TimelineEntry) -> Unit) {
    for (day in model.days) {
        item(key = "day-${day.date}") { DayHeader(day.date) }
        val entries = Days.newestFirst(day)
        items(entries.size, key = { "e-${day.date}-$it" }) { i ->
            EntryRow(entries[i], showDate = false, onClick = { onEdit(entries[i]) })
        }
    }
    item(key = "end") {
        Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
            when {
                model.loading -> CircularProgressIndicator()
                model.error != null -> Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(model.error.orEmpty(), style = MaterialTheme.typography.bodyMedium)
                    TextButton(onClick = { model.loadOlder() }) { Text(stringResource(R.string.retry)) }
                }
                else -> Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    model.oldest?.let {
                        Text(
                            stringResource(R.string.timeline_loaded_since, dayLabel(it.toString())),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    if (!model.autoLoad) {
                        TextButton(onClick = { model.loadOlder() }) { Text(stringResource(R.string.timeline_more)) }
                    }
                }
            }
        }
    }
}

private fun LazyListScope.searchItems(model: TimelineModel, onEdit: (TimelineEntry) -> Unit) {
    val results = model.results
    item(key = "search-head") {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            when {
                model.searching -> CircularProgressIndicator(Modifier.padding(end = 12.dp))
                model.searchError != null -> Text(model.searchError.orEmpty(), style = MaterialTheme.typography.bodyMedium)
                results != null -> Text(
                    if (results.isEmpty()) stringResource(R.string.search_none) else stringResource(R.string.search_results, results.size),
                    style = MaterialTheme.typography.titleSmall,
                )
            }
            if (model.searchError != null) TextButton(onClick = { model.search() }) { Text(stringResource(R.string.retry)) }
        }
    }
    if (results != null) {
        items(results.size, key = { "r-$it" }) { i ->
            EntryRow(results[i], showDate = true, onClick = { onEdit(results[i]) })
        }
    }
}

@Composable
private fun DayHeader(date: String) {
    Text(
        dayLabel(date),
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 4.dp),
    )
}

@Composable
private fun EntryRow(entry: TimelineEntry, showDate: Boolean, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            if (showDate) "${shortDay(entry.date)}\n${normalTime(entry.time)}" else normalTime(entry.time),
            style = MaterialTheme.typography.labelLarge.copy(fontFamily = FontFamily.Monospace),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(entry.text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
    }
}

/** "11월 7일 (토)" in the phone's language; with the year when it is not this year. */
private fun dayLabel(date: String): String {
    val day = runCatching { LocalDate.parse(date) }.getOrNull() ?: return date
    val skeleton = if (day.year == LocalDate.now().year) "MMMMdEEE" else "yMMMMdEEE"
    val pattern = DateFormat.getBestDateTimePattern(Locale.getDefault(), skeleton)
    return day.format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))
}

private fun shortDay(date: String): String {
    val day = runCatching { LocalDate.parse(date) }.getOrNull() ?: return date
    val skeleton = if (day.year == LocalDate.now().year) "Md" else "yyMd"
    return day.format(DateTimeFormatter.ofPattern(DateFormat.getBestDateTimePattern(Locale.getDefault(), skeleton), Locale.getDefault()))
}

// ---- the phone's own entries --------------------------------------------------

/** Entries not yet on the PC: those to check first, then those waiting. */
private fun LazyListScope.queueItems(entries: List<Entry>) {
    val attention = entries.filter { it.state == State.ATTENTION }
    val pending = entries.filter { it.state == State.PENDING || it.state == State.CHECK }.sortedWith(compareBy({ it.date }, { it.time }))
    if (attention.isEmpty() && pending.isEmpty()) return

    item(key = "queue") {
        val context = LocalContext.current
        Column(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (attention.isNotEmpty()) {
                Text(stringResource(R.string.main_attention, attention.size), style = MaterialTheme.typography.titleSmall)
                attention.forEach { entry ->
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text("${entry.date} ${entry.time}  ${entry.text}")
                            if (entry.maybeRecorded) Text(stringResource(R.string.main_maybe_recorded), style = MaterialTheme.typography.bodySmall)
                            if (entry.note.isNotEmpty()) {
                                Text(
                                    stringResource(R.string.main_reason, entry.note),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                TextButton(onClick = { EntryStore.put(context, Transitions.markSent(entry, System.currentTimeMillis())) }) {
                                    Text(stringResource(R.string.main_mark_sent))
                                }
                                TextButton(onClick = {
                                    EntryStore.put(context, Transitions.resend(entry, System.currentTimeMillis()))
                                    Sender.schedule(context)
                                }) { Text(stringResource(R.string.main_resend)) }
                                TextButton(onClick = { EntryStore.remove(context, entry.id) }) { Text(stringResource(R.string.delete)) }
                            }
                        }
                    }
                }
            }
            if (pending.isNotEmpty()) {
                Text(stringResource(R.string.main_pending, pending.size), style = MaterialTheme.typography.titleSmall)
                pending.forEach {
                    Column {
                        Text("${it.date} ${it.time}  ${it.text}", style = MaterialTheme.typography.bodyMedium)
                        Text(
                            when {
                                it.state == State.CHECK -> stringResource(R.string.main_checking, it.note)
                                it.attempts == 0 -> stringResource(R.string.main_not_tried)
                                else -> stringResource(R.string.main_last_try, whenTried(it.changedAt), it.note)
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                OutlinedButton(onClick = { Sender.schedule(context) }) { Text(stringResource(R.string.main_send_now)) }
            }
            HorizontalDivider()
        }
    }
}

/** HH:mm today, or MM-dd HH:mm on another day. */
private fun whenTried(millis: Long): String {
    val at = Instant.ofEpochMilli(millis).atZone(ZoneId.systemDefault())
    val pattern = if (at.toLocalDate() == LocalDate.now()) "HH:mm" else "MM-dd HH:mm"
    return at.format(DateTimeFormatter.ofPattern(pattern))
}

// ---- editing ----------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun EditSheet(model: TimelineModel, entry: TimelineEntry, onClose: () -> Unit) {
    val context = LocalContext.current
    val sheet = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var text by remember { mutableStateOf(entry.text) }
    var date by remember { mutableStateOf(entry.date) }
    var time by remember { mutableStateOf(normalTime(entry.time)) }
    var busy by remember { mutableStateOf(false) }
    var problem by remember { mutableStateOf<String?>(null) }
    var confirmDelete by remember { mutableStateOf(false) }

    val changed = text.trim() != entry.text || date != entry.date || time != normalTime(entry.time)
    val done: (String?) -> Unit = { reason ->
        busy = false
        if (reason == null) onClose() else problem = reason
    }

    ModalBottomSheet(onDismissRequest = { if (!busy) onClose() }, sheetState = sheet) {
        Column(
            Modifier.fillMaxWidth().imePadding().padding(horizontal = 16.dp).padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(stringResource(R.string.edit_title), style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = text,
                onValueChange = { text = it; problem = null },
                modifier = Modifier.fillMaxWidth(),
                minLines = 2,
                maxLines = 8,
                enabled = !busy,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(enabled = !busy, onClick = {
                    val d = LocalDate.parse(date)
                    DatePickerDialog(context, { _, y, m, dd ->
                        date = LocalDate.of(y, m + 1, dd).toString(); problem = null
                    }, d.year, d.monthValue - 1, d.dayOfMonth).show()
                }) { Text(dayLabel(date)) }
                OutlinedButton(enabled = !busy, onClick = {
                    val (h, m) = time.split(":").map { it.toInt() }
                    TimePickerDialog(context, { _, hh, mm ->
                        time = "%02d:%02d".format(hh, mm); problem = null
                    }, h, m, true).show()
                }) { Text(time, fontFamily = FontFamily.Monospace) }
            }
            problem?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium) }
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton(enabled = !busy, onClick = { confirmDelete = true }) {
                    Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
                }
                Spacer(Modifier.weight(1f))
                TextButton(enabled = !busy, onClick = onClose) { Text(stringResource(R.string.cancel)) }
                Spacer(Modifier.width(8.dp))
                Button(enabled = !busy && changed && text.isNotBlank(), onClick = {
                    busy = true
                    problem = null
                    model.save(entry, date, time, text, done)
                }) { Text(stringResource(R.string.save)) }
            }
        }
    }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            text = { Text(stringResource(R.string.edit_delete_confirm)) },
            confirmButton = {
                TextButton(onClick = {
                    confirmDelete = false
                    busy = true
                    model.delete(entry, done)
                }) { Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}
