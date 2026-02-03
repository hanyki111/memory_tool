from typing import List, Dict, Optional, Any
from notion_client import Client
from memory_tool.utils.config import Config
from memory_tool.notion.cache import NotionCache
import httpx
import os

class NotionError(Exception):
    """Base exception for Notion operations."""
    pass

class NotionClient:
    """Notion API client with support for both default and PAT (proxy) modes.

    Modes:
        - "default": Standard Notion API (api.notion.com)
        - "pat": Corporate proxy mode with custom base_url and notion_version

    Config example:
        notion:
          mode: "default"  # or "pat"

          # Default mode settings
          api_key: "secret_xxx..."
          default_page_id: "abc123..."

          # PAT mode settings (used when mode: "pat")
          pat:
            api_key: "PAT_xxx..."
            base_url: "https://notion-proxy.company.com/v1"
            notion_version: "2025-09-03"
            default_page_id: "abc123..."
    """

    def __init__(self):
        self.config = Config()
        notion_config = self.config.get("notion", {})

        # Determine mode: "default" or "pat"
        self.mode = notion_config.get("mode", "default")

        if self.mode == "pat":
            # PAT mode: use settings from notion.pat section
            pat_config = notion_config.get("pat", {})
            self.api_key = pat_config.get("api_key")
            self.default_page_id = pat_config.get("default_page_id") or notion_config.get("default_page_id")
            self.base_url = pat_config.get("base_url")
            self.notion_version = pat_config.get("notion_version")

            # Fallback to env var
            if not self.api_key:
                self.api_key = os.environ.get("NOTION_PAT_KEY")

            if not self.api_key:
                raise NotionError(
                    "PAT mode: API key not found. "
                    "Configure 'notion.pat.api_key' in config.yaml or set NOTION_PAT_KEY env var."
                )

            if not self.base_url:
                raise NotionError(
                    "PAT mode: base_url is required. "
                    "Configure 'notion.pat.base_url' in config.yaml."
                )
        else:
            # Default mode: standard Notion API
            self.api_key = notion_config.get("api_key")
            self.default_page_id = notion_config.get("default_page_id")
            self.base_url = None
            self.notion_version = None

            # Fallback to env var
            if not self.api_key:
                self.api_key = os.environ.get("NOTION_API_KEY")

            if not self.api_key:
                raise NotionError(
                    "Notion API key not found. "
                    "Configure 'notion.api_key' in config.yaml or set NOTION_API_KEY env var."
                )

        self.cache = NotionCache()

        try:
            # Build client options
            client_kwargs = {"auth": self.api_key}

            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            # If custom notion_version is specified, use a custom httpx client
            # to override the default Notion-Version header
            if self.notion_version:
                custom_headers = {"Notion-Version": self.notion_version}
                http_client = httpx.Client(headers=custom_headers)
                client_kwargs["client"] = http_client

            self.client = Client(**client_kwargs)
        except Exception as e:
            raise NotionError(f"Failed to initialize Notion client: {e}")

    def find_child_page(self, parent_id: str, title: str, verbose: bool = False) -> Optional[str]:
        """Find a child page with specific title under parent_id.

        Supports pagination to handle parents with more than 100 children.
        """
        try:
            start_cursor = None
            found_titles = []
            while True:
                if start_cursor:
                    response = self.client.blocks.children.list(
                        block_id=parent_id, start_cursor=start_cursor
                    )
                else:
                    response = self.client.blocks.children.list(block_id=parent_id)

                for block in response.get("results", []):
                    # Skip archived blocks
                    if block.get("archived", False):
                        continue
                    if block.get("type") == "child_page":
                        child_title = block.get("child_page", {}).get("title", "")
                        found_titles.append(child_title)
                        if child_title == title:
                            return block["id"]

                # Check for more pages
                if not response.get("has_more"):
                    break
                start_cursor = response.get("next_cursor")

            if verbose and found_titles:
                print(f"    [debug] Looking for '{title}', found: {found_titles}")
            return None
        except Exception as e:
            if verbose:
                print(f"    [debug] find_child_page error: {e}")
            return None

    def get_or_create_subpage(self, parent_id: str, title: str, cache_key: Optional[str] = None, icon: Optional[str] = None) -> str:
        """Get existing subpage or create new one.

        Args:
            parent_id: Parent page ID
            title: Page title
            cache_key: Cache key for storing page ID
            icon: Emoji icon for the page (only used when creating new page)
        """
        # 1. Check cache
        if cache_key:
            cached_id = self.cache.get_page_id(cache_key)
            if cached_id:
                return cached_id

        # 2. Check Notion
        page_id = self.find_child_page(parent_id, title)

        # 3. Create if not found
        if not page_id:
            try:
                new_page = self.create_page(title, parent_id, icon=icon)
                page_id = new_page["id"]
            except Exception as e:
                raise NotionError(f"Failed to create subpage '{title}': {e}")

        # 4. Update cache
        if cache_key and page_id:
            self.cache.set_page_id(cache_key, page_id)

        return page_id

    def get_or_create_daily_page(self, date_obj, root_page_id: str = None) -> str:
        """Get or create hierarchy: Root -> Month(YYYY-MM) -> Day(YYYY-MM-DD).

        Args:
            date_obj: Date object for the daily page
            root_page_id: Optional root page ID. Falls back to default_page_id if not provided.
        """
        root_id = root_page_id or self.default_page_id
        if not root_id:
            raise NotionError("Timeline root page ID not configured. Set notion.sync.timeline.root_page_id in config.yaml")

        # 1. Month Page (e.g., "2026-01")
        month_str = date_obj.strftime("%Y-%m")
        month_cache_key = f"month_{month_str}"
        
        month_page_id = self.get_or_create_subpage(root_id, month_str, month_cache_key)

        # 2. Day Page (e.g., "2026-01-16")
        day_str = date_obj.strftime("%Y-%m-%d")
        day_cache_key = f"day_{day_str}"
        
        day_page_id = self.get_or_create_subpage(month_page_id, day_str, day_cache_key)
        
        return day_page_id

    def append_timeline_entry(self, page_id: str, time_str: str, message: str, date_obj=None):
        """Append a timeline entry with Notion date mention.

        Args:
            page_id: Target page ID
            time_str: Time string (HH:MM) - used for fallback
            message: Message content
            date_obj: Optional datetime object for Notion date mention
        """
        try:
            from datetime import datetime

            # Extra strict cleaning to prevent any extra blocks
            # Remove all newlines and carriage returns from the message
            clean_message = message.strip().replace("\r", "").replace("\n", " ")

            # Build rich_text array
            rich_text = []

            # Use Notion date mention if date_obj is provided
            if date_obj:
                # Format: 2026-01-16T17:37:00+09:00 (with timezone)
                # Get local timezone offset
                import time
                if time.daylight and time.localtime().tm_isdst > 0:
                    utc_offset_sec = -time.altzone
                else:
                    utc_offset_sec = -time.timezone
                utc_offset_hours = utc_offset_sec // 3600
                utc_offset_mins = abs(utc_offset_sec % 3600) // 60
                tz_str = f"{utc_offset_hours:+03d}:{utc_offset_mins:02d}"
                iso_datetime = date_obj.strftime(f"%Y-%m-%dT%H:%M:00{tz_str}")
                rich_text.append({
                    "type": "mention",
                    "mention": {
                        "type": "date",
                        "date": {
                            "start": iso_datetime,
                            "end": None
                        }
                    }
                })
                rich_text.append({
                    "type": "text",
                    "text": {"content": " "}
                })
            else:
                # Fallback to bold text format
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": f"{time_str} | ",
                        "link": None
                    },
                    "annotations": {
                        "bold": True,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default"
                    }
                })

            # Add message
            rich_text.append({
                "type": "text",
                "text": {
                    "content": clean_message,
                    "link": None
                }
            })

            # Find correct insertion position (sorted by time)
            after_block_id = self._find_insertion_position(page_id, time_str)

            append_kwargs = {
                "block_id": page_id,
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": rich_text
                        }
                    }
                ]
            }

            # Insert after specific block if position found
            if after_block_id:
                append_kwargs["after"] = after_block_id

            self.client.blocks.children.append(**append_kwargs)
        except Exception as e:
            raise NotionError(f"Failed to append timeline entry: {e}")

    def _parse_time_from_block(self, block: dict) -> tuple:
        """Extract time from a Notion block for sorting.

        Args:
            block: Notion block dict

        Returns:
            Tuple of (hour, minute) or (99, 99) if no time found
        """
        if block.get("type") != "paragraph":
            return (99, 99)

        rich_text = block.get("paragraph", {}).get("rich_text", [])
        if not rich_text:
            return (99, 99)

        for rt in rich_text:
            rt_type = rt.get("type")

            # Check for date mention
            if rt_type == "mention":
                mention = rt.get("mention", {})
                if mention.get("type") == "date":
                    date_info = mention.get("date", {})
                    start = date_info.get("start", "")
                    # Extract time from ISO format (2026-01-16T19:34:00+09:00)
                    if "T" in start:
                        time_part = start.split("T")[1][:5]  # HH:MM
                        try:
                            parts = time_part.split(":")
                            return (int(parts[0]), int(parts[1]))
                        except (ValueError, IndexError):
                            pass

            # Check for bold time format (legacy): "HH:MM | "
            elif rt_type == "text":
                content = rt.get("text", {}).get("content", "")
                annotations = rt.get("annotations", {})

                if annotations.get("bold") and "|" in content:
                    time_str = content.split("|")[0].strip()
                    try:
                        parts = time_str.split(":")
                        return (int(parts[0]), int(parts[1]))
                    except (ValueError, IndexError):
                        pass

        return (99, 99)

    def _find_insertion_position(self, page_id: str, time_str: str) -> str:
        """Find the block ID after which to insert a new entry.

        Args:
            page_id: Notion page ID
            time_str: Time string (HH:MM) of the entry to insert

        Returns:
            Block ID to insert after, or None to insert at beginning
        """
        try:
            # Parse the target time
            parts = time_str.split(":")
            target_time = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None  # Insert at beginning if time is invalid

        try:
            response = self.client.blocks.children.list(block_id=page_id)
            blocks = response.get("results", [])

            # Find the last block with time <= target_time
            insert_after = None

            for block in blocks:
                block_time = self._parse_time_from_block(block)

                # If this block's time is <= target time, it's a candidate
                if block_time <= target_time:
                    insert_after = block.get("id")
                else:
                    # We've passed the insertion point
                    break

            return insert_after

        except Exception:
            return None  # Insert at end if error

    def find_entry_block(self, page_id: str, time_str: str, message_key: str) -> Optional[str]:
        """Find a timeline entry block by time and message key.

        Args:
            page_id: Notion page ID
            time_str: Time string (HH:MM)
            message_key: Message without tags (for matching)

        Returns:
            Block ID if found, None otherwise
        """
        import re

        try:
            # Parse the target time
            parts = time_str.split(":")
            target_hour = int(parts[0])
            target_min = int(parts[1])
        except (ValueError, IndexError):
            return None

        try:
            response = self.client.blocks.children.list(block_id=page_id)
            blocks = response.get("results", [])

            for block in blocks:
                if block.get("type") != "paragraph":
                    continue

                rich_text = block.get("paragraph", {}).get("rich_text", [])
                if not rich_text:
                    continue

                # Extract time and message from block
                block_hour, block_min = self._parse_time_from_block(block)

                # Check if time matches
                if block_hour != target_hour or block_min != target_min:
                    continue

                # Extract full text content
                full_text = ""
                for rt in rich_text:
                    if rt.get("type") == "text":
                        full_text += rt.get("text", {}).get("content", "")
                    elif rt.get("type") == "mention":
                        # Skip date mentions
                        pass

                # Strip tags from block content for comparison
                stripped = re.sub(r'#[\w가-힣-]+', '', full_text)
                stripped = re.sub(r'\[[\w가-힣\s-]+\]', '', stripped)
                stripped = re.sub(r'\s+', ' ', stripped).strip()

                # Compare keys (normalized)
                if stripped.lower()[:50] == message_key.lower()[:50]:
                    return block.get("id")

            return None

        except Exception:
            return None

    def update_entry_block(self, block_id: str, time_str: str, message: str, date_obj=None):
        """Update an existing timeline entry block.

        Args:
            block_id: Block ID to update
            time_str: Time string (HH:MM)
            message: New message content
            date_obj: Optional datetime object for Notion date mention
        """
        try:
            from datetime import datetime
            import time

            clean_message = message.strip().replace("\r", "").replace("\n", " ")

            rich_text = []

            if date_obj:
                if time.daylight and time.localtime().tm_isdst > 0:
                    utc_offset_sec = -time.altzone
                else:
                    utc_offset_sec = -time.timezone
                utc_offset_hours = utc_offset_sec // 3600
                utc_offset_mins = abs(utc_offset_sec % 3600) // 60
                tz_str = f"{utc_offset_hours:+03d}:{utc_offset_mins:02d}"
                iso_datetime = date_obj.strftime(f"%Y-%m-%dT%H:%M:00{tz_str}")
                rich_text.append({
                    "type": "mention",
                    "mention": {
                        "type": "date",
                        "date": {
                            "start": iso_datetime,
                            "end": None
                        }
                    }
                })
                rich_text.append({
                    "type": "text",
                    "text": {"content": " "}
                })
            else:
                rich_text.append({
                    "type": "text",
                    "text": {"content": f"{time_str} | "},
                    "annotations": {"bold": True}
                })

            rich_text.append({
                "type": "text",
                "text": {"content": clean_message}
            })

            self.client.blocks.update(
                block_id=block_id,
                paragraph={"rich_text": rich_text}
            )

        except Exception as e:
            raise NotionError(f"Failed to update entry block: {e}")

    def delete_entry_block(self, block_id: str):
        """Delete a timeline entry block.

        Args:
            block_id: Block ID to delete
        """
        try:
            self.client.blocks.delete(block_id=block_id)
        except Exception as e:
            raise NotionError(f"Failed to delete entry block: {e}")

    def find_entry_block_by_time(self, page_id: str, time_str: str) -> Optional[tuple]:
        """Find a timeline entry block by time only.

        Args:
            page_id: Notion page ID
            time_str: Time string (HH:MM)

        Returns:
            Tuple of (block_id, full_text) if found, None otherwise
        """
        import re

        try:
            # Parse the target time
            parts = time_str.split(":")
            target_hour = int(parts[0])
            target_min = int(parts[1])
        except (ValueError, IndexError):
            return None

        try:
            response = self.client.blocks.children.list(block_id=page_id)
            blocks = response.get("results", [])

            for block in blocks:
                if block.get("type") != "paragraph":
                    continue

                rich_text = block.get("paragraph", {}).get("rich_text", [])
                if not rich_text:
                    continue

                # Extract time from block
                block_hour, block_min = self._parse_time_from_block(block)

                # Check if time matches
                if block_hour == target_hour and block_min == target_min:
                    # Extract full text content
                    full_text = ""
                    for rt in rich_text:
                        if rt.get("type") == "text":
                            full_text += rt.get("text", {}).get("content", "")
                    return (block.get("id"), full_text)

            return None

        except Exception:
            return None

    def reorder_timeline_page(self, page_id: str, verbose: bool = False) -> dict:
        """Reorder timeline entries in a Notion page by time.

        Args:
            page_id: Notion page ID
            verbose: Print progress

        Returns:
            Dict with reordered count and any errors
        """
        result = {"reordered": 0, "total": 0, "errors": []}

        try:
            # Get all blocks
            response = self.client.blocks.children.list(block_id=page_id)
            blocks = response.get("results", [])

            if not blocks:
                return result

            # Parse blocks with their times
            parsed_blocks = []
            for block in blocks:
                block_id = block.get("id")
                block_time = self._parse_time_from_block(block)

                # Only process paragraph blocks with valid times
                if block.get("type") == "paragraph" and block_time != (99, 99):
                    parsed_blocks.append({
                        "id": block_id,
                        "time": block_time,
                        "data": block
                    })

            result["total"] = len(parsed_blocks)

            if len(parsed_blocks) <= 1:
                return result  # Nothing to reorder

            # Check if already sorted
            times = [b["time"] for b in parsed_blocks]
            if times == sorted(times):
                if verbose:
                    print(f"  Page already sorted ({len(parsed_blocks)} entries)")
                return result

            # Sort by time
            sorted_blocks = sorted(parsed_blocks, key=lambda x: x["time"])

            # Delete all timeline blocks
            for block in parsed_blocks:
                try:
                    self.client.blocks.delete(block_id=block["id"])
                except Exception as e:
                    result["errors"].append(f"Delete failed: {e}")

            # Recreate blocks in sorted order
            for block in sorted_blocks:
                try:
                    # Extract rich_text from original block
                    rich_text = block["data"].get("paragraph", {}).get("rich_text", [])

                    self.client.blocks.children.append(
                        block_id=page_id,
                        children=[
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": rich_text
                                }
                            }
                        ]
                    )
                    result["reordered"] += 1
                except Exception as e:
                    result["errors"].append(f"Recreate failed: {e}")

            if verbose:
                print(f"  Reordered {result['reordered']}/{result['total']} entries")

        except Exception as e:
            result["errors"].append(f"Reorder failed: {e}")

        return result

    def check_child_pages_order(self, parent_page_id: str, verbose: bool = False) -> dict:
        """Check if child pages under a parent page are sorted by title.

        NOTE: Notion API does not support reordering child_page blocks safely.
        Deleting and recreating child_page blocks would lose all page content.
        This method only CHECKS the order and reports if sorting is needed.

        Args:
            parent_page_id: Parent page ID containing child pages
            verbose: Print progress

        Returns:
            Dict with sorted status and page list
        """
        result = {"is_sorted": True, "total": 0, "out_of_order": [], "errors": []}

        try:
            # Get all child blocks (with pagination)
            all_blocks = []
            start_cursor = None

            while True:
                if start_cursor:
                    response = self.client.blocks.children.list(
                        block_id=parent_page_id, start_cursor=start_cursor
                    )
                else:
                    response = self.client.blocks.children.list(block_id=parent_page_id)

                all_blocks.extend(response.get("results", []))

                if not response.get("has_more"):
                    break
                start_cursor = response.get("next_cursor")

            if not all_blocks:
                return result

            # Filter only child_page blocks
            child_pages = []
            for block in all_blocks:
                if block.get("type") == "child_page" and not block.get("archived", False):
                    title = block.get("child_page", {}).get("title", "")
                    child_pages.append({
                        "id": block.get("id"),
                        "title": title,
                    })

            result["total"] = len(child_pages)

            if len(child_pages) <= 1:
                return result  # Nothing to check

            # Check if already sorted by title (date string)
            titles = [p["title"] for p in child_pages]
            sorted_titles = sorted(titles)

            if titles == sorted_titles:
                if verbose:
                    print(f"  Child pages already sorted ({len(child_pages)} pages)")
                return result

            # Find out-of-order pages
            result["is_sorted"] = False
            for i, (current, expected) in enumerate(zip(titles, sorted_titles)):
                if current != expected:
                    result["out_of_order"].append({
                        "position": i + 1,
                        "current": current,
                        "expected": expected
                    })

            if verbose:
                print(f"  [yellow]Child pages NOT sorted ({len(result['out_of_order'])} out of order)[/yellow]")
                print(f"  [dim]Note: Notion API does not support safe reordering of child pages.[/dim]")
                print(f"  [dim]Please reorder manually in Notion by dragging pages.[/dim]")

        except Exception as e:
            result["errors"].append(f"Check child pages order failed: {e}")

        return result

    def get_page_content(self, page_id: str) -> str:
        """Get text content of a page."""
        try:
            response = self.client.blocks.children.list(block_id=page_id)
            lines = []
            
            for block in response.get("results", []):
                block_type = block.get("type")
                # Support both paragraph and bulleted_list_item (for backward compatibility)
                rich_text = []
                if block_type == "paragraph":
                    rich_text = block.get("paragraph", {}).get("rich_text", [])
                elif block_type == "bulleted_list_item":
                    rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
                
                if rich_text:
                    text_parts = []
                    for rt in rich_text:
                        content = rt.get("text", {}).get("content", "")
                        text_parts.append(content)
                    
                    if text_parts:
                        line = "".join(text_parts)
                        # No prefix for paragraph, only for list items if they still exist
                        if block_type == "bulleted_list_item":
                            line = f"- {line}"
                        lines.append(line)
            
            return "\n".join(lines)
        except Exception as e:
            raise NotionError(f"Failed to get page content: {e}")

    def search_content(self, query: str) -> List[Dict[str, Any]]:
        """Search content within pages (specifically filtering for Daily Pages)."""
        try:
            # Notion search API searches both titles and content by default
            response = self.client.search(query=query)
            results = []
            
            import re
            # Regex to match Daily Page titles (YYYY-MM-DD)
            date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

            for item in response.get("results", []):
                if item["object"] == "page":
                    # Extract Title
                    title = "Untitled"
                    props = item.get("properties", {})
                    for prop_val in props.values():
                        if prop_val.get("type") == "title":
                            title_obj = prop_val.get("title", [])
                            if title_obj:
                                title = title_obj[0].get("plain_text", "Untitled")
                            break
                    
                    # Filter: Only include pages that look like Daily Pages
                    if not date_pattern.match(title):
                        continue

                    # For content matches, Notion API unfortunately doesn't return *which* block matched in the search response directly for pages.
                    # It returns the Page object.
                    # However, if the match was a Block (paragraph), the object is 'page' or 'database'?
                    # Actually Notion search returns Pages or Databases.
                    # If we search for content, it returns the Page containing it.
                    # But it doesn't give us the snippet.
                    # So we have to fetch the page content and find the snippet ourselves, 
                    # OR we just link to the page.
                    # 
                    # Optimization: We'll fetch the content of the matched page and doing a quick local search
                    # to find the specific line. This is expensive (N API calls), but accurate.
                    # For a CLI 'search inside', user expects to see the line.
                    
                    # 1. Get full content (reuse get_page_content logic but keep list)
                    # We'll do a simplified fetch here to find the matching line
                    try:
                        page_content = self.get_page_content(item["id"])
                        matching_lines = []
                        for line in page_content.split('\n'):
                            if query.lower() in line.lower():
                                matching_lines.append(line)
                        
                        if matching_lines:
                            results.append({
                                "id": item["id"],
                                "title": title,
                                "matches": matching_lines,
                                "url": item.get("url"),
                                "date": title # Since title is YYYY-MM-DD
                            })
                    except Exception:
                        continue
            
            # Sort by date descending
            results.sort(key=lambda x: x["date"], reverse=True)
            return results
            
        except Exception as e:
            raise NotionError(f"Search content failed: {e}")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search Notion pages."""
        try:
            response = self.client.search(query=query)
            results = []
            
            for item in response.get("results", []):
                if item["object"] == "page":
                    title = "Untitled"
                    # Handle different title property types (title is usually in 'properties')
                    props = item.get("properties", {})
                    # Find the property that is of type 'title'
                    for prop_name, prop_val in props.items():
                        if prop_val.get("type") == "title":
                            title_obj = prop_val.get("title", [])
                            if title_obj:
                                title = title_obj[0].get("plain_text", "Untitled")
                            break
                            
                    results.append({
                        "id": item["id"],
                        "title": title,
                        "url": item.get("url"),
                        "last_edited": item.get("last_edited_time")
                    })
            
            return results
        except Exception as e:
            raise NotionError(f"Search failed: {e}")

    def create_page(self, title: str, parent_id: Optional[str] = None, icon: Optional[str] = None) -> Dict[str, Any]:
        """Create a new page in Notion.

        Args:
            title: Page title
            parent_id: Parent page ID (default: default_page_id)
            icon: Emoji icon for the page (e.g., "📁", "📄")
        """
        target_parent_id = parent_id or self.default_page_id

        if not target_parent_id:
            raise NotionError("No parent page ID provided and no default configured.")

        try:
            page_data = {
                "parent": {"page_id": target_parent_id},
                "properties": {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                }
            }

            # Add icon if specified
            if icon:
                page_data["icon"] = {"type": "emoji", "emoji": icon}

            new_page = self.client.pages.create(**page_data)
            return new_page
        except Exception as e:
            raise NotionError(f"Failed to create page: {e}")

    def archive_page(self, page_id: str) -> Dict[str, Any]:
        """Archive (soft delete) a Notion page.

        This moves the page to Notion's trash. It can be restored from trash
        within 30 days.

        Args:
            page_id: ID of the page to archive

        Returns:
            Updated page data from Notion API
        """
        try:
            # Notion API: set archived=true to move to trash
            response = self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            return response
        except Exception as e:
            raise NotionError(f"Failed to archive page: {e}")

    def move_page(self, page_id: str, new_parent_id: str) -> Dict[str, Any]:
        """Move a page to a new parent.

        Args:
            page_id: ID of the page to move
            new_parent_id: ID of the new parent page

        Returns:
            Updated page data from Notion API
        """
        try:
            response = self.client.pages.update(
                page_id=page_id,
                parent={"page_id": new_parent_id}
            )
            return response
        except Exception as e:
            raise NotionError(f"Failed to move page: {e}")

    def append_text(self, page_id: str, text: str) -> Dict[str, Any]:
        """Append text block to a page."""
        try:
            response = self.client.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": text
                                    }
                                }
                            ]
                        }
                    }
                ]
            )
            return response
        except Exception as e:
            raise NotionError(f"Failed to append text: {e}")
