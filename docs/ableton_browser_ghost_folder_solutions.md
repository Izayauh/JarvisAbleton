# Ableton Browser API "Ghost Folder" Issue - Research & Solutions

## The Problem Summary

You're encountering a known quirk in Ableton's Browser API where:
1. **"EQ & Filters"** reports `is_folder=False`
2. Yet it **contains child devices** (like EQ Eight)
3. When you iterate `children` or `iter_children`, they appear empty or inaccessible

This is a **category container** vs **folder** distinction that Ableton's API handles inconsistently.

---

## Understanding the Browser API Structure

### Key BrowserItem Properties
From the Live 11 API documentation:

```python
class BrowserItem:
    children        # Const access to descendants (BrowserItemVector)
    iter_children   # Const iterable access to descendants (BrowserItemIterator)
    is_device       # bool - indicates if item represents a device
    is_folder       # bool - BUT THIS LIES for category containers!
    is_loadable     # bool - True if item can be loaded via Browser.load_item()
    name            # str - canonical display name
    uri             # str - unique identifier
    source          # str - where item comes from (Live pack, user library, etc.)
```

### The Critical Insight
**Ableton's browser has TWO types of containers:**
1. **Folders** (`is_folder=True`) - Regular filesystem-like folders
2. **Category Containers** (`is_folder=False`) - Like "EQ & Filters", "Delays", "Reverbs"

The API reports `is_folder=False` for category containers, but they **DO have children**.

---

## Potential Solutions

### Solution 1: Check for Children Regardless of is_folder

Don't trust `is_folder`. Instead, always attempt to access children:

```python
def get_children_safe(browser_item):
    """
    Safely get children from a BrowserItem, regardless of is_folder flag.
    Returns a list of child items or empty list.
    """
    children = []
    try:
        # Method 1: Try iter_children (iterator)
        for child in browser_item.iter_children:
            children.append(child)
    except (AttributeError, TypeError, StopIteration):
        pass
    
    if not children:
        try:
            # Method 2: Try children property directly
            for child in browser_item.children:
                children.append(child)
        except (AttributeError, TypeError):
            pass
    
    return children


def has_children(browser_item):
    """Check if item has children without relying on is_folder."""
    try:
        # Try to get first child
        iterator = browser_item.iter_children
        next(iterator)
        return True
    except (StopIteration, AttributeError, TypeError):
        pass
    
    try:
        return len(list(browser_item.children)) > 0
    except:
        return False
```

### Solution 2: Force List Conversion Before Iteration

The iterator may be consumed or have context issues. Force it into a list immediately:

```python
def search_browser_item(item, target_name, depth=0, max_depth=10):
    """
    Recursively search for a device in browser hierarchy.
    Handles the 'ghost folder' issue by forcing list conversion.
    """
    if depth > max_depth:
        return None
    
    self.log(f"{'  ' * depth}Searching: {item.name} (is_folder={item.is_folder}, is_device={item.is_device})")
    
    # Check if this is the target
    if item.is_device and target_name.lower() in item.name.lower():
        if item.is_loadable:
            self.log(f"{'  ' * depth}FOUND: {item.name}")
            return item
    
    # CRITICAL: Force children into a list IMMEDIATELY
    # This prevents iterator context issues
    try:
        children_list = list(item.iter_children)
    except:
        try:
            children_list = list(item.children)
        except:
            children_list = []
    
    self.log(f"{'  ' * depth}Found {len(children_list)} children")
    
    # Now iterate the cached list
    for child in children_list:
        result = search_browser_item(child, target_name, depth + 1, max_depth)
        if result:
            return result
    
    return None
```

### Solution 3: Use URI-Based Direct Access (Bypass Browsing)

If you know the URI pattern for core devices, you might be able to construct it:

```python
def find_device_by_uri_pattern(browser, device_name):
    """
    Try to find device using URI pattern matching.
    Ableton core devices often have predictable URIs.
    """
    # Known URI patterns for core audio effects
    known_patterns = {
        "EQ Eight": "ableton:///Audio Effects/EQ Eight",
        "Compressor": "ableton:///Audio Effects/Compressor", 
        "Reverb": "ableton:///Audio Effects/Reverb",
        "Auto Filter": "ableton:///Audio Effects/Auto Filter",
        # etc.
    }
    
    if device_name in known_patterns:
        target_uri = known_patterns[device_name]
        # Search all items checking URI
        return find_by_uri(browser.audio_effects, target_uri)
    
    return None
```

### Solution 4: Explicit Category Mapping (Your "Brute Force" Approach)

Hard-code the known category structure:

```python
# Known Ableton Audio Effect categories and their contents
AUDIO_EFFECT_CATEGORIES = {
    "EQ & Filters": [
        "EQ Eight", "EQ Three", "Channel EQ", "Auto Filter", 
        "Multiband Dynamics"  # Sometimes here
    ],
    "Delays": [
        "Delay", "Echo", "Filter Delay", "Grain Delay", 
        "Ping Pong Delay", "Simple Delay"
    ],
    "Reverbs": [
        "Reverb", "Convolution Reverb", "Hybrid Reverb"
    ],
    "Dynamics": [
        "Compressor", "Glue Compressor", "Limiter", "Gate",
        "Multiband Dynamics"
    ],
    # ... etc
}

def find_device_with_category_fallback(browser, device_name):
    """
    Search for device, using category knowledge as fallback.
    """
    # First, try normal recursive search
    result = recursive_search(browser.audio_effects, device_name)
    if result:
        return result
    
    # If not found, use category knowledge
    target_category = None
    for category, devices in AUDIO_EFFECT_CATEGORIES.items():
        if device_name in devices:
            target_category = category
            break
    
    if target_category:
        self.log(f"Using category fallback: {device_name} should be in {target_category}")
        # Find the category item
        for item in browser.audio_effects.iter_children:
            if item.name == target_category:
                # Force-iterate this specific category
                return force_search_category(item, device_name)
    
    return None
```

### Solution 5: Scheduler/Deferred Access

The children might not be accessible in the same execution context. Try deferring:

```python
from _Framework.Task import Task

def search_with_defer(self, browser_item, target_name, callback):
    """
    Search with deferred execution to allow API state to settle.
    """
    def do_search():
        # Give the API a moment
        children = list(browser_item.iter_children)
        self.log(f"Deferred access got {len(children)} children")
        
        for child in children:
            if child.is_device and target_name.lower() in child.name.lower():
                callback(child)
                return
            
            # Recurse with another defer
            if has_children(child):
                self.schedule_message(1, lambda c=child: search_with_defer(self, c, target_name, callback))
    
    # Schedule for next tick
    self.schedule_message(1, do_search)
```

### Solution 6: Access via Application.browser Property Path

Sometimes accessing through a different path works:

```python
def get_browser_fresh():
    """Get a fresh browser reference."""
    import Live
    app = Live.Application.get_application()
    return app.browser

def search_audio_effects_fresh(device_name):
    """Get fresh browser reference and search."""
    browser = get_browser_fresh()
    audio_effects = browser.audio_effects
    
    # Log the entire structure first
    dump_structure(audio_effects, depth=0, max_depth=3)
    
    # Then search
    return recursive_search(audio_effects, device_name)

def dump_structure(item, depth=0, max_depth=3):
    """Debug helper to see actual structure."""
    indent = "  " * depth
    print(f"{indent}{item.name} [folder={item.is_folder}, device={item.is_device}, loadable={item.is_loadable}]")
    
    if depth < max_depth:
        try:
            children = list(item.iter_children)
            for child in children:
                dump_structure(child, depth + 1, max_depth)
        except Exception as e:
            print(f"{indent}  ERROR getting children: {e}")
```

---

## Debugging Recommendations

### 1. Comprehensive Logging
Add these log points to understand what's happening:

```python
def search_device(self, browser_item, target_name, depth=0):
    self.log(f"[{depth}] Item: '{browser_item.name}'")
    self.log(f"[{depth}]   is_folder: {browser_item.is_folder}")
    self.log(f"[{depth}]   is_device: {browser_item.is_device}")
    self.log(f"[{depth}]   is_loadable: {browser_item.is_loadable}")
    self.log(f"[{depth}]   uri: {browser_item.uri}")
    
    # Try to count children
    try:
        children_iter = browser_item.iter_children
        children_list = list(children_iter)
        self.log(f"[{depth}]   children count: {len(children_list)}")
        for i, child in enumerate(children_list[:5]):  # First 5
            self.log(f"[{depth}]     child[{i}]: {child.name}")
    except Exception as e:
        self.log(f"[{depth}]   ERROR getting children: {type(e).__name__}: {e}")
```

### 2. Check Log.txt
Ableton writes errors to:
- **Windows**: `%APPDATA%\Ableton\Live 11.x.x\Preferences\Log.txt`
- **macOS**: `~/Library/Preferences/Ableton/Live 11.x.x/Log.txt`

Look for `RemoteScriptError` entries.

### 3. Test in Isolation
Create a minimal script that ONLY tries to list audio effects:

```python
# test_browser.py
from _Framework.ControlSurface import ControlSurface

class TestBrowser(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._test_browser()
    
    def _test_browser(self):
        browser = self.application().browser
        self.log_message("=== BROWSER TEST ===")
        
        audio_effects = browser.audio_effects
        self.log_message(f"audio_effects: {audio_effects.name}")
        
        try:
            children = list(audio_effects.iter_children)
            self.log_message(f"Top-level items: {len(children)}")
            
            for item in children:
                self.log_message(f"  - {item.name} (folder={item.is_folder})")
                
                # Try to get grandchildren
                try:
                    grandchildren = list(item.iter_children)
                    self.log_message(f"      has {len(grandchildren)} children")
                    for gc in grandchildren[:3]:
                        self.log_message(f"        - {gc.name}")
                except Exception as e:
                    self.log_message(f"      ERROR: {e}")
                    
        except Exception as e:
            self.log_message(f"ERROR: {e}")
```

---

## Known Quirks Summary

| Issue | Description | Workaround |
|-------|-------------|------------|
| `is_folder=False` for categories | Categories like "EQ & Filters" report as non-folders | Always check for children regardless |
| Iterator consumed | `iter_children` can only be iterated once | Convert to list immediately |
| Context-sensitive access | Children may not be accessible in certain execution contexts | Use deferred/scheduled access |
| Empty children in recursion | Children accessible at one level but not when passed to function | Re-access item.iter_children fresh in each function |
| Live version differences | API behavior varies between 10/11/12 | Test on your specific version |

---

## Recommended Final Approach

Combine multiple strategies:

```python
def find_device_robust(self, device_name):
    """
    Robust device finder that handles all known API quirks.
    """
    browser = self.application().browser
    
    # Strategy 1: Direct name match at top level
    for item in list(browser.audio_effects.iter_children):
        if item.is_device and device_name.lower() in item.name.lower():
            if item.is_loadable:
                return item
    
    # Strategy 2: Deep search with forced list conversion
    def deep_search(parent, depth=0):
        if depth > 5:
            return None
        
        try:
            # CRITICAL: Fresh list every time
            children = list(parent.iter_children)
        except:
            return None
        
        for child in children:
            # Check this item
            if child.is_device and device_name.lower() in child.name.lower():
                if child.is_loadable:
                    return child
            
            # Always recurse, ignore is_folder
            result = deep_search(child, depth + 1)
            if result:
                return result
        
        return None
    
    result = deep_search(browser.audio_effects)
    if result:
        return result
    
    # Strategy 3: Known category fallback
    known_locations = {
        "EQ Eight": "EQ & Filters",
        "Compressor": "Dynamics",
        # ... add more
    }
    
    if device_name in known_locations:
        category_name = known_locations[device_name]
        for item in list(browser.audio_effects.iter_children):
            if item.name == category_name:
                self.log_message(f"Trying known category: {category_name}")
                for child in list(item.iter_children):
                    if device_name.lower() in child.name.lower():
                        return child
    
    self.log_message(f"Device not found: {device_name}")
    return None
```

---

## References

- [Live 11 Python API (XML)](https://structure-void.com/PythonLiveAPI_documentation/Live11.0.xml)
- [NSUSpray Live API Docs](https://nsuspray.github.io/Live_API_Doc/)
- [Decompiled Push Scripts](https://github.com/gluon/AbletonLive11_MIDIRemoteScripts)
- [AbletonOSC (working browser implementation)](https://github.com/ideoforms/AbletonOSC)

---

*Research compiled for JarvisAbleton debugging - January 2026*
