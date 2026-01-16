"""Markdown to Notion block conversion and vice versa."""

import re
from typing import Dict, List, Any, Optional, Tuple


class MarkdownNotionConverter:
    """Converts between Markdown and Notion blocks."""

    def markdown_to_blocks(self, md_content: str) -> List[Dict[str, Any]]:
        """Convert Markdown content to Notion block objects.

        Args:
            md_content: Markdown string

        Returns:
            List of Notion block objects
        """
        blocks = []
        lines = md_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines (will be added as spacing if needed)
            if not line.strip():
                i += 1
                continue

            # Code block (fenced)
            if line.strip().startswith("```"):
                block, consumed = self._parse_code_block(lines, i)
                blocks.append(block)
                i += consumed
                continue

            # Heading
            if line.startswith("#"):
                block = self._parse_heading(line)
                if block:
                    blocks.append(block)
                    i += 1
                    continue

            # Horizontal rule
            if line.strip() in ("---", "***", "___"):
                blocks.append({"type": "divider", "divider": {}})
                i += 1
                continue

            # Blockquote
            if line.startswith(">"):
                block = self._parse_blockquote(line)
                blocks.append(block)
                i += 1
                continue

            # Unordered list
            if re.match(r"^[\s]*[-*+]\s", line):
                block = self._parse_bulleted_list_item(line)
                blocks.append(block)
                i += 1
                continue

            # Ordered list
            if re.match(r"^[\s]*\d+\.\s", line):
                block = self._parse_numbered_list_item(line)
                blocks.append(block)
                i += 1
                continue

            # Checkbox / Todo
            if re.match(r"^[\s]*[-*+]\s\[([ xX])\]", line):
                block = self._parse_todo_item(line)
                blocks.append(block)
                i += 1
                continue

            # Default: paragraph
            block = self._create_paragraph(line)
            blocks.append(block)
            i += 1

        return blocks

    def blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert Notion blocks to Markdown string.

        Args:
            blocks: List of Notion block objects

        Returns:
            Markdown string
        """
        lines = []

        for block in blocks:
            block_type = block.get("type", "")

            if block_type == "paragraph":
                text = self._rich_text_to_markdown(
                    block.get("paragraph", {}).get("rich_text", [])
                )
                lines.append(text)

            elif block_type == "heading_1":
                text = self._rich_text_to_markdown(
                    block.get("heading_1", {}).get("rich_text", [])
                )
                lines.append(f"# {text}")

            elif block_type == "heading_2":
                text = self._rich_text_to_markdown(
                    block.get("heading_2", {}).get("rich_text", [])
                )
                lines.append(f"## {text}")

            elif block_type == "heading_3":
                text = self._rich_text_to_markdown(
                    block.get("heading_3", {}).get("rich_text", [])
                )
                lines.append(f"### {text}")

            elif block_type == "bulleted_list_item":
                text = self._rich_text_to_markdown(
                    block.get("bulleted_list_item", {}).get("rich_text", [])
                )
                lines.append(f"- {text}")

            elif block_type == "numbered_list_item":
                text = self._rich_text_to_markdown(
                    block.get("numbered_list_item", {}).get("rich_text", [])
                )
                lines.append(f"1. {text}")

            elif block_type == "to_do":
                todo_data = block.get("to_do", {})
                text = self._rich_text_to_markdown(todo_data.get("rich_text", []))
                checked = todo_data.get("checked", False)
                checkbox = "[x]" if checked else "[ ]"
                lines.append(f"- {checkbox} {text}")

            elif block_type == "quote":
                text = self._rich_text_to_markdown(
                    block.get("quote", {}).get("rich_text", [])
                )
                lines.append(f"> {text}")

            elif block_type == "code":
                code_data = block.get("code", {})
                text = self._rich_text_to_markdown(code_data.get("rich_text", []))
                language = code_data.get("language", "")
                lines.append(f"```{language}")
                lines.append(text)
                lines.append("```")

            elif block_type == "divider":
                lines.append("---")

            elif block_type == "child_page":
                # Skip child pages in markdown conversion
                pass

            else:
                # Unknown block type - try to get any text
                for key, value in block.items():
                    if isinstance(value, dict) and "rich_text" in value:
                        text = self._rich_text_to_markdown(value["rich_text"])
                        if text:
                            lines.append(text)
                        break

        return "\n".join(lines)

    def _parse_heading(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a heading line."""
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not match:
            return None

        level = len(match.group(1))
        text = match.group(2).strip()

        # Notion only supports h1, h2, h3
        if level == 1:
            return {
                "type": "heading_1",
                "heading_1": {"rich_text": self._parse_rich_text(text)}
            }
        elif level == 2:
            return {
                "type": "heading_2",
                "heading_2": {"rich_text": self._parse_rich_text(text)}
            }
        else:
            return {
                "type": "heading_3",
                "heading_3": {"rich_text": self._parse_rich_text(text)}
            }

    def _parse_blockquote(self, line: str) -> Dict[str, Any]:
        """Parse a blockquote line."""
        text = line.lstrip(">").strip()
        return {
            "type": "quote",
            "quote": {"rich_text": self._parse_rich_text(text)}
        }

    def _parse_bulleted_list_item(self, line: str) -> Dict[str, Any]:
        """Parse a bulleted list item."""
        text = re.sub(r"^[\s]*[-*+]\s+", "", line)
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": self._parse_rich_text(text)}
        }

    def _parse_numbered_list_item(self, line: str) -> Dict[str, Any]:
        """Parse a numbered list item."""
        text = re.sub(r"^[\s]*\d+\.\s+", "", line)
        return {
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": self._parse_rich_text(text)}
        }

    def _parse_todo_item(self, line: str) -> Dict[str, Any]:
        """Parse a todo/checkbox item."""
        match = re.match(r"^[\s]*[-*+]\s\[([ xX])\]\s*(.*)", line)
        if match:
            checked = match.group(1).lower() == "x"
            text = match.group(2)
        else:
            checked = False
            text = line

        return {
            "type": "to_do",
            "to_do": {
                "rich_text": self._parse_rich_text(text),
                "checked": checked
            }
        }

    def _parse_code_block(
        self,
        lines: List[str],
        start_idx: int
    ) -> Tuple[Dict[str, Any], int]:
        """Parse a fenced code block.

        Returns:
            Tuple of (block, lines_consumed)
        """
        first_line = lines[start_idx].strip()
        language = first_line[3:].strip()  # Extract language after ```

        code_lines = []
        i = start_idx + 1

        while i < len(lines):
            if lines[i].strip() == "```":
                i += 1
                break
            code_lines.append(lines[i])
            i += 1

        code_content = "\n".join(code_lines)

        return {
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": code_content}}],
                "language": language or "plain text"
            }
        }, i - start_idx

    def _create_paragraph(self, text: str) -> Dict[str, Any]:
        """Create a paragraph block."""
        return {
            "type": "paragraph",
            "paragraph": {"rich_text": self._parse_rich_text(text)}
        }

    def _parse_rich_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse inline formatting to Notion rich_text array.

        Handles: **bold**, *italic*, `code`, [link](url), ~~strikethrough~~
        """
        rich_text = []
        remaining = text

        # Pattern for inline elements
        patterns = [
            # Bold: **text** or __text__
            (r"\*\*(.+?)\*\*|__(.+?)__", "bold"),
            # Italic: *text* or _text_
            (r"\*(.+?)\*|_(.+?)_", "italic"),
            # Code: `text`
            (r"`([^`]+)`", "code"),
            # Strikethrough: ~~text~~
            (r"~~(.+?)~~", "strikethrough"),
            # Link: [text](url)
            (r"\[([^\]]+)\]\(([^)]+)\)", "link"),
        ]

        # For simplicity, we'll use a sequential approach
        # This handles nested formatting partially

        # First pass: find all formatted sections
        segments = []
        pos = 0

        while pos < len(remaining):
            earliest_match = None
            earliest_start = len(remaining)
            match_type = None

            for pattern, fmt_type in patterns:
                match = re.search(pattern, remaining[pos:])
                if match and pos + match.start() < earliest_start:
                    earliest_match = match
                    earliest_start = pos + match.start()
                    match_type = fmt_type

            if earliest_match:
                # Add plain text before match
                if earliest_start > pos:
                    plain_text = remaining[pos:earliest_start]
                    if plain_text:
                        segments.append(("plain", plain_text, {}))

                # Add formatted text
                if match_type == "link":
                    link_text = earliest_match.group(1)
                    link_url = earliest_match.group(2)
                    # Notion requires valid URLs starting with http:// or https://
                    if link_url.startswith(("http://", "https://")):
                        segments.append(("link", link_text, {"url": link_url}))
                    else:
                        # Invalid URL - render as plain text with brackets
                        segments.append(("plain", f"[{link_text}]({link_url})", {}))
                elif match_type == "bold":
                    fmt_text = earliest_match.group(1) or earliest_match.group(2)
                    segments.append(("bold", fmt_text, {}))
                elif match_type == "italic":
                    fmt_text = earliest_match.group(1) or earliest_match.group(2)
                    segments.append(("italic", fmt_text, {}))
                elif match_type == "code":
                    fmt_text = earliest_match.group(1)
                    segments.append(("code", fmt_text, {}))
                elif match_type == "strikethrough":
                    fmt_text = earliest_match.group(1)
                    segments.append(("strikethrough", fmt_text, {}))

                pos = earliest_start + earliest_match.end() - earliest_match.start()
            else:
                # No more matches, add remaining text
                if pos < len(remaining):
                    segments.append(("plain", remaining[pos:], {}))
                break

        # Convert segments to rich_text
        for seg_type, content, extra in segments:
            if not content:
                continue

            rt_item: Dict[str, Any] = {
                "type": "text",
                "text": {"content": content}
            }

            annotations = {
                "bold": False,
                "italic": False,
                "strikethrough": False,
                "underline": False,
                "code": False,
                "color": "default"
            }

            if seg_type == "bold":
                annotations["bold"] = True
            elif seg_type == "italic":
                annotations["italic"] = True
            elif seg_type == "code":
                annotations["code"] = True
            elif seg_type == "strikethrough":
                annotations["strikethrough"] = True
            elif seg_type == "link":
                rt_item["text"]["link"] = {"url": extra.get("url", "")}

            rt_item["annotations"] = annotations
            rich_text.append(rt_item)

        # If no segments, return plain text
        if not rich_text and text:
            rich_text.append({
                "type": "text",
                "text": {"content": text},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default"
                }
            })

        return rich_text

    def _rich_text_to_markdown(self, rich_text: List[Dict[str, Any]]) -> str:
        """Convert Notion rich_text array to Markdown string."""
        parts = []

        for rt in rich_text:
            if rt.get("type") != "text":
                continue

            text_data = rt.get("text", {})
            content = text_data.get("content", "")
            annotations = rt.get("annotations", {})
            link = text_data.get("link")

            # Apply formatting
            result = content

            if annotations.get("code"):
                result = f"`{result}`"
            if annotations.get("strikethrough"):
                result = f"~~{result}~~"
            if annotations.get("bold"):
                result = f"**{result}**"
            if annotations.get("italic"):
                result = f"*{result}*"
            if link:
                url = link.get("url", "")
                result = f"[{content}]({url})"

            parts.append(result)

        return "".join(parts)

    def create_module_page_content(
        self,
        module_name: str,
        files: Dict[str, str],
        file_links: Dict[str, str],
        submodule_links: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Create Notion blocks for a module page (integrated view).

        Args:
            module_name: Name of the module
            files: Dict of filename -> content
            file_links: Dict of filename -> Notion page URL
            submodule_links: Dict of submodule name -> Notion page URL

        Returns:
            List of Notion blocks
        """
        blocks = []

        # Title is handled by page title, not blocks
        # Quick links
        link_parts = []
        for filename, url in file_links.items():
            link_parts.append(f"[{filename}]({url})")

        if link_parts:
            quick_links_text = " | ".join(link_parts)
            blocks.append({
                "type": "quote",
                "quote": {
                    "rich_text": self._parse_rich_text(f"Quick Links: {quick_links_text}")
                }
            })
            blocks.append({"type": "divider", "divider": {}})

        # File contents
        for filename, content in files.items():
            # Section header
            icon = self._get_file_icon(filename)
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"{icon} {filename}"}}]
                }
            })

            # File content as blocks
            file_blocks = self.markdown_to_blocks(content)
            blocks.extend(file_blocks)

            blocks.append({"type": "divider", "divider": {}})

        # Sub-modules section
        if submodule_links:
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Sub-modules"}}]
                }
            })

            for submodule_name, url in submodule_links.items():
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self._parse_rich_text(f"[{submodule_name}]({url})")
                    }
                })

        return blocks

    def _get_file_icon(self, filename: str) -> str:
        """Get appropriate icon for file type."""
        icons = {
            "current.md": "",
            "module.md": "",
            "decisions.md": "",
            "interface.md": "",
            "dependencies.md": "",
        }
        return icons.get(filename, "")
