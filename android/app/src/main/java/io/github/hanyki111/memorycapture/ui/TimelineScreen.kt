package io.github.hanyki111.memorycapture.ui

import android.app.Activity
import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.content.Intent
import android.speech.RecognizerIntent
import android.text.format.DateFormat
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import kotlinx.coroutines.launch
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
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import io.github.hanyki111.memorycapture.core.leadingTags
import androidx.compose.ui.text.style.TextOverflow
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
 * top and a field at the bottom that sends at once. The phone's unsent
 * entries sit just above that field, where what was just sent is seen.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TimelineScreen(model: TimelineModel, phoneEntries: List<Entry>, onSettings: () -> Unit) {
    val snackbar = remember { SnackbarHostState() }
    var editing by remember { mutableStateOf<TimelineEntry?>(null) }
    val list = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val hint = stringResource(R.string.edit_hint)
    val showHint: () -> Unit = {
        scope.launch {
            snackbar.currentSnackbarData?.dismiss()
            snackbar.showSnackbar(hint)
        }
    }

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

    // A new day on top (the first entry of today) is shown when the top was in view;
    // the list would otherwise keep the day that was first in place, below it.
    val newest = model.days.firstOrNull()?.date
    LaunchedEffect(newest) {
        if (list.firstVisibleItemIndex <= 1) list.scrollToItem(0)
    }

    Scaffold(
        topBar = { SearchBar(model, onSettings) },
        bottomBar = { BottomPanel(phoneEntries, model) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { inner ->
        PullToRefreshBox(
            isRefreshing = model.refreshing,
            onRefresh = { model.refresh() },
            modifier = Modifier.fillMaxSize().padding(inner),
        ) {
            LazyColumn(Modifier.fillMaxSize(), state = list) {
                if (model.results != null || model.searching || model.searchError != null) {
                    searchItems(model, showHint) { editing = it }
                } else {
                    timelineItems(model, showHint) { editing = it }
                }
            }
        }
    }

    editing?.let { entry -> EditSheet(model, entry, onClose = { editing = null }) }
}

@Composable
private fun SearchBar(model: TimelineModel, onSettings: () -> Unit) {
    val focus = LocalFocusManager.current
    Surface(color = MaterialTheme.colorScheme.background) {
        Row(
            Modifier.fillMaxWidth().statusBarsPadding().padding(start = 4.dp, end = 4.dp, top = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextField(
                value = model.query,
                onValueChange = { model.query = it },
                placeholder = { Text(stringResource(R.string.search_hint)) },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                colors = plainField(),
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
                Icon(Icons.Filled.Settings, contentDescription = stringResource(R.string.settings), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

/** The phone's unsent entries, then the field; padded for the navigation bar and the keyboard. */
@Composable
private fun BottomPanel(phoneEntries: List<Entry>, model: TimelineModel) {
    Surface(color = MaterialTheme.colorScheme.background) {
        Column(Modifier.fillMaxWidth().navigationBarsPadding().imePadding()) {
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            QueueStrip(phoneEntries)
            InputBar(model)
        }
    }
}

/** Write and send without opening anything; speech fills the field and offers recent tags. */
@Composable
private fun InputBar(model: TimelineModel) {
    val context = LocalContext.current
    var text by remember { mutableStateOf("") }
    var spoken by remember { mutableStateOf(false) }
    val voice = rememberVoiceInput { heard ->
        text = if (text.isBlank()) heard else "${text.trimEnd()} $heard"
        spoken = true
    }
    val tags = remember(spoken, model.days) {
        if (spoken) recentTags(context, model.days.flatMap { day -> Days.newestFirst(day).map { it.text } }) else emptyList()
    }

    fun send() {
        val entry = text.trim()
        if (entry.isEmpty()) return
        EntryStore.add(context, entry)
        Sender.schedule(context)
        text = ""
        spoken = false
    }

    if (voice.listening || (spoken && tags.isNotEmpty()) || voice.missed) {
        Column(Modifier.fillMaxWidth().padding(start = 20.dp, end = 12.dp, top = 6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            when {
                voice.listening -> Text(
                    voice.partial.ifEmpty { stringResource(R.string.voice_listening) },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                voice.missed && !spoken -> Text(stringResource(R.string.voice_missed), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                else -> TagChips(tags, text, { text = it })
            }
        }
    }

    run {
        Row(
            Modifier.fillMaxWidth().padding(start = 4.dp, end = 12.dp, top = 2.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextField(
                value = text,
                onValueChange = { text = it; if (it.isBlank()) spoken = false },
                placeholder = { Text(stringResource(R.string.input_hint)) },
                colors = plainField(),
                textStyle = MaterialTheme.typography.bodyLarge,
                maxLines = 4,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { send() }),
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = voice::start) {
                Icon(painterResource(R.drawable.ic_mic),
                    contentDescription = stringResource(if (voice.listening) R.string.voice_stop else R.string.capture_voice),
                    tint = if (voice.listening) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
            }
            FilledIconButton(
                onClick = ::send,
                enabled = text.isNotBlank(),
                shape = CircleShape,
                colors = IconButtonDefaults.filledIconButtonColors(
                    disabledContainerColor = MaterialTheme.colorScheme.surfaceContainerHighest,
                    disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
                ),
                modifier = Modifier.size(44.dp),
            ) {
                Icon(painterResource(R.drawable.ic_arrow_up), contentDescription = stringResource(R.string.capture_send))
            }
        }
    }
}

// ---- the list -------------------------------------------------------------

private fun LazyListScope.timelineItems(model: TimelineModel, onTap: () -> Unit, onEdit: (TimelineEntry) -> Unit) {
    for (day in model.days) {
        item(key = "day-${day.date}") { DayHeader(day.date) }
        val entries = Days.newestFirst(day)
        items(entries.size, key = { "e-${day.date}-$it" }) { i ->
            EntryRow(entries[i], first = i == 0, last = i == entries.lastIndex, onTap = onTap, onLongPress = { onEdit(entries[i]) })
        }
    }
    // No key: a keyed item here would stay in place while the first days load above it,
    // and the list would open scrolled to its end.
    item {
        Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
            when {
                model.loading -> CircularProgressIndicator(Modifier.size(28.dp), strokeWidth = 2.5.dp)
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

private fun LazyListScope.searchItems(model: TimelineModel, onTap: () -> Unit, onEdit: (TimelineEntry) -> Unit) {
    val results = model.results
    item(key = "search-head") {
        Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            when {
                model.searching -> CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.5.dp)
                model.searchError != null -> Text(model.searchError.orEmpty(), style = MaterialTheme.typography.bodyMedium)
                results != null -> Text(
                    if (results.isEmpty()) stringResource(R.string.search_none) else stringResource(R.string.search_results, results.size),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (model.searchError != null) TextButton(onClick = { model.search() }) { Text(stringResource(R.string.retry)) }
        }
    }
    if (results != null) {
        items(results.size, key = { "r-$it" }) { i ->
            ResultRow(results[i], onTap = onTap, onLongPress = { onEdit(results[i]) })
        }
    }
}

/** The date large, the weekday beside it: "11월 7일  토요일 · 오늘". */
@Composable
private fun DayHeader(date: String) {
    val day = runCatching { LocalDate.parse(date) }.getOrNull()
    Row(
        Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, top = 24.dp, bottom = 10.dp),
        verticalAlignment = Alignment.Bottom,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            if (day == null) date else formatDay(day, if (day.year == LocalDate.now().year) "MMMMd" else "yMMMMd"),
            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = (-0.3).sp),
        )
        if (day != null) {
            val weekday = formatDay(day, "EEEE")
            Text(
                if (day == LocalDate.now()) "$weekday · ${stringResource(R.string.today)}" else weekday,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 3.dp),
            )
        }
    }
}

private val TIME_WIDTH = 48.dp
private val RAIL_WIDTH = 22.dp

/**
 * One entry on the day's line: the time, a dot on the line, the text. The
 * newest of the day has the accent's dot; the line starts at the first dot
 * and ends at the last. Editing is rare, so it takes a long press; a tap says so.
 */
@Composable
private fun EntryRow(entry: TimelineEntry, first: Boolean, last: Boolean, onTap: () -> Unit, onLongPress: () -> Unit) {
    val haptic = LocalHapticFeedback.current
    val colors = MaterialTheme.colorScheme
    val density = LocalDensity.current
    var dotY by remember { mutableFloatStateOf(with(density) { 13.dp.toPx() }) }
    Row(
        Modifier.fillMaxWidth()
            .combinedClickable(onClick = onTap, onLongClick = {
                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                onLongPress()
            })
            .drawBehind {
                val x = 20.dp.toPx() + TIME_WIDTH.toPx() + 5.dp.toPx()
                val y = 6.dp.toPx() + dotY
                val stroke = 1.dp.toPx()
                drawLine(colors.outlineVariant, Offset(x, if (first) y else 0f), Offset(x, if (last) y else size.height), stroke)
                val r = 4.5.dp.toPx()
                if (first) {
                    drawCircle(colors.primary, r, Offset(x, y))
                } else {
                    drawCircle(colors.background, r, Offset(x, y))
                    drawCircle(colors.outline, r - 0.75.dp.toPx(), Offset(x, y), style = Stroke(1.5.dp.toPx()))
                }
            }
            .padding(start = 20.dp, end = 20.dp, top = 6.dp, bottom = 12.dp),
    ) {
        Text(
            normalTime(entry.time),
            style = MaterialTheme.typography.labelLarge.copy(fontFeatureSettings = "tnum"),
            color = colors.onSurfaceVariant,
            modifier = Modifier.width(TIME_WIDTH).padding(top = 3.dp),
        )
        Spacer(Modifier.width(RAIL_WIDTH))
        TaggedText(entry.text, Modifier.weight(1f), onFirstLine = { dotY = it })
    }
}

/** A search result: the day and time over the text, without the line. */
@Composable
private fun ResultRow(entry: TimelineEntry, onTap: () -> Unit, onLongPress: () -> Unit) {
    val haptic = LocalHapticFeedback.current
    Column(
        Modifier.fillMaxWidth()
            .combinedClickable(onClick = onTap, onLongClick = {
                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                onLongPress()
            })
            .padding(horizontal = 20.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Text(
            "${dayLabel(entry.date)}  ${normalTime(entry.time)}",
            style = MaterialTheme.typography.labelMedium.copy(fontFeatureSettings = "tnum"),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        TaggedText(entry.text, Modifier.fillMaxWidth())
    }
}

/**
 * The entry's text with its leading `[tags]` as tinted chips. The chips are
 * drawn behind the tag's letters, so they wrap with the text like words.
 *
 * @param onFirstLine the middle of the first line, in px from the top
 */
@Composable
private fun TaggedText(text: String, modifier: Modifier, onFirstLine: (Float) -> Unit = {}) {
    val colors = MaterialTheme.colorScheme
    val (tags, rest) = remember(text) { leadingTags(text) }
    val ranges = mutableListOf<IntRange>()
    val shown: AnnotatedString = remember(text) {
        buildAnnotatedString {
            tags.forEach { tag ->
                val from = length
                // No-break spaces pad the chip and keep it whole.
                withStyle(SpanStyle(fontSize = 0.8.em, fontWeight = FontWeight.Medium)) { append("\u00A0$tag\u00A0") }
                ranges += from until length
                append(" ")
            }
            append(rest)
        }
    }
    val tagRanges = remember(text) { ranges.toList() }
    val styled = remember(shown, colors.onPrimaryContainer) {
        AnnotatedString.Builder(shown).apply {
            tagRanges.forEach { addStyle(SpanStyle(color = colors.onPrimaryContainer), it.first, it.last + 1) }
        }.toAnnotatedString()
    }
    var layout by remember { mutableStateOf<TextLayoutResult?>(null) }
    Text(
        styled,
        style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 1.55.em),
        modifier = modifier.drawBehind {
            val l = layout ?: return@drawBehind
            tagRanges.forEach { r ->
                val line = l.getLineForOffset(r.first)
                if (l.getLineForOffset(r.last) != line) return@forEach
                val left = l.getHorizontalPosition(r.first, true)
                val right = l.getHorizontalPosition(r.last + 1, true)
                val middle = (l.getLineTop(line) + l.getLineBottom(line)) / 2
                val h = 20.sp.toPx().coerceAtMost(l.getLineBottom(line) - l.getLineTop(line))
                drawRoundRect(
                    colors.primaryContainer,
                    topLeft = Offset(minOf(left, right), middle - h / 2),
                    size = Size(kotlin.math.abs(right - left), h),
                    cornerRadius = CornerRadius(6.dp.toPx()),
                )
            }
        },
        onTextLayout = {
            layout = it
            if (it.lineCount > 0) onFirstLine((it.getLineTop(0) + it.getLineBottom(0)) / 2)
        },
    )
}

@Composable
private fun plainField() = TextFieldDefaults.colors(
    focusedContainerColor = Color.Transparent,
    unfocusedContainerColor = Color.Transparent,
    disabledContainerColor = Color.Transparent,
    focusedIndicatorColor = Color.Transparent,
    unfocusedIndicatorColor = Color.Transparent,
    disabledIndicatorColor = Color.Transparent,
    unfocusedPlaceholderColor = MaterialTheme.colorScheme.onSurfaceVariant,
    focusedPlaceholderColor = MaterialTheme.colorScheme.onSurfaceVariant,
    unfocusedLeadingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
    focusedLeadingIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
)

private fun formatDay(day: LocalDate, skeleton: String): String =
    day.format(DateTimeFormatter.ofPattern(DateFormat.getBestDateTimePattern(Locale.getDefault(), skeleton), Locale.getDefault()))

/** "11월 7일 (토)" in the phone's language; with the year when it is not this year. */
private fun dayLabel(date: String): String {
    val day = runCatching { LocalDate.parse(date) }.getOrNull() ?: return date
    val skeleton = if (day.year == LocalDate.now().year) "MMMMdEEE" else "yMMMMdEEE"
    val pattern = DateFormat.getBestDateTimePattern(Locale.getDefault(), skeleton)
    return day.format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))
}


// ---- the phone's own entries --------------------------------------------------

/**
 * Entries not yet on the PC, folded into one line above the field: the counts
 * and the latest entry. Opened, those to check first, then those waiting.
 */
@Composable
private fun QueueStrip(entries: List<Entry>) {
    val attention = entries.filter { it.state == State.ATTENTION }
    val pending = entries.filter { it.state == State.PENDING || it.state == State.CHECK }.sortedWith(compareBy({ it.date }, { it.time }))
    var open by rememberSaveable { mutableStateOf(false) }
    if (attention.isEmpty() && pending.isEmpty()) return

    val context = LocalContext.current
    Column(Modifier.fillMaxWidth().animateContentSize()) {
        Row(
            Modifier.fillMaxWidth().combinedClickable(onClick = { open = !open })
                .padding(start = 20.dp, end = 12.dp, top = 8.dp, bottom = 2.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Box(
                Modifier.size(7.dp).background(
                    if (attention.isNotEmpty()) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                    CircleShape,
                )
            )
            val counts = listOfNotNull(
                stringResource(R.string.main_attention, attention.size).takeIf { attention.isNotEmpty() },
                stringResource(R.string.main_pending, pending.size).takeIf { pending.isNotEmpty() },
            ).joinToString(" · ")
            Column(Modifier.weight(1f)) {
                Text(
                    counts,
                    style = MaterialTheme.typography.labelLarge,
                    color = if (attention.isNotEmpty()) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                )
                if (!open) {
                    val latest = pending.lastOrNull() ?: attention.last()
                    Text(
                        "${normalTime(latest.time)}  ${latest.text}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Icon(
                if (open) Icons.Filled.KeyboardArrowDown else Icons.Filled.KeyboardArrowUp,
                contentDescription = stringResource(if (open) R.string.queue_close else R.string.queue_open),
            )
        }
        if (open) Column(
            Modifier.fillMaxWidth().heightIn(max = 320.dp).verticalScroll(rememberScrollState())
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
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
