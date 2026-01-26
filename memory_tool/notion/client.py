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
        except Exception as e:
            raise NotionError(f"Failed to append timeline entry: {e}")

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
