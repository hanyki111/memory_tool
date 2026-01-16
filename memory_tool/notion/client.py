from typing import List, Dict, Optional, Any
from notion_client import Client
from memory_tool.utils.config import Config
from memory_tool.notion.cache import NotionCache

class NotionError(Exception):
    """Base exception for Notion operations."""
    pass

class NotionClient:
    def __init__(self):
        self.config = Config()
        notion_config = self.config.get("notion", {})
        
        self.api_key = notion_config.get("api_key")
        self.default_page_id = notion_config.get("default_page_id")
        self.base_url = notion_config.get("base_url")
        
        self.cache = NotionCache()
        
        if not self.api_key:
            # Try getting from env var as fallback
            import os
            self.api_key = os.environ.get("NOTION_API_KEY")
            
        if not self.api_key:
            raise NotionError("Notion API key not found. Please configure 'notion.api_key' in config.yaml or set NOTION_API_KEY env var.")
            
        try:
            if self.base_url:
                self.client = Client(auth=self.api_key, base_url=self.base_url)
            else:
                self.client = Client(auth=self.api_key)
        except Exception as e:
            raise NotionError(f"Failed to initialize Notion client: {e}")

    def find_child_page(self, parent_id: str, title: str) -> Optional[str]:
        """Find a child page with specific title under parent_id."""
        try:
            # Note: blocks.children.list is paginated. For simplicity/speed, checking first 100.
            # A more robust solution would paginate, but for a month list it's usually fine.
            response = self.client.blocks.children.list(block_id=parent_id)
            
            for block in response.get("results", []):
                if block.get("type") == "child_page":
                    child_title = block.get("child_page", {}).get("title", "")
                    if child_title == title:
                        return block["id"]
            return None
        except Exception:
            return None

    def get_or_create_subpage(self, parent_id: str, title: str, cache_key: Optional[str] = None) -> str:
        """Get existing subpage or create new one."""
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
                new_page = self.create_page(title, parent_id)
                page_id = new_page["id"]
            except Exception as e:
                raise NotionError(f"Failed to create subpage '{title}': {e}")

        # 4. Update cache
        if cache_key and page_id:
            self.cache.set_page_id(cache_key, page_id)
            
        return page_id

    def get_or_create_daily_page(self, date_obj) -> str:
        """Get or create hierarchy: Root -> Month(YYYY-MM) -> Day(YYYY-MM-DD)."""
        root_id = self.default_page_id
        if not root_id:
            raise NotionError("Default page ID not configured.")

        # 1. Month Page (e.g., "2026-01")
        month_str = date_obj.strftime("%Y-%m")
        month_cache_key = f"month_{month_str}"
        
        month_page_id = self.get_or_create_subpage(root_id, month_str, month_cache_key)

        # 2. Day Page (e.g., "2026-01-16")
        day_str = date_obj.strftime("%Y-%m-%d")
        day_cache_key = f"day_{day_str}"
        
        day_page_id = self.get_or_create_subpage(month_page_id, day_str, day_cache_key)
        
        return day_page_id

    def append_timeline_entry(self, page_id: str, time_str: str, message: str):
        """Append a timeline entry: **HH:MM** | message."""
        try:
            self.client.blocks.children.append(
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
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": message,
                                        "link": None
                                    }
                                }
                            ]
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
                if block_type == "paragraph":
                    rich_text = block.get("paragraph", {}).get("rich_text", [])
                    text_parts = []
                    for rt in rich_text:
                        content = rt.get("text", {}).get("content", "")
                        # Simple markdown-like formatting for bold (time)
                        if rt.get("annotations", {}).get("bold"):
                            # If it looks like a time stamp (HH:MM | ), keep it clean
                            # Otherwise maybe add **
                            pass
                        text_parts.append(content)
                    
                    if text_parts:
                        lines.append("".join(text_parts))
            
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

    def create_page(self, title: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new page in Notion."""
        target_parent_id = parent_id or self.default_page_id
        
        if not target_parent_id:
            raise NotionError("No parent page ID provided and no default configured.")
            
        try:
            new_page = self.client.pages.create(
                parent={"page_id": target_parent_id},
                properties={
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
            )
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
