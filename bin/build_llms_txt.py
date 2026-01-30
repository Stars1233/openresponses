#!/usr/bin/env python3
"""
Build script to automatically generate llms.txt from OpenResponses documentation.
Fetches content from all live website pages and creates a comprehensive,
well-structured llms.txt file for LLM consumption.
"""

import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# Page configuration with descriptions
PAGES = {
    "overview": {
        "url": "https://www.openresponses.org/",
        "title": "Overview",
        "description": "Introduction and getting started guide",
    },
    "specification": {
        "url": "https://www.openresponses.org/specification",
        "title": "Specification",
        "description": "Complete technical specification with core concepts",
    },
    "reference": {
        "url": "https://www.openresponses.org/reference",
        "title": "API Reference",
        "description": "Detailed API documentation with endpoints and schemas",
    },
    "compliance": {
        "url": "https://www.openresponses.org/compliance",
        "title": "Compliance",
        "description": "Acceptance tests and validation procedures",
    },
    "governance": {
        "url": "https://www.openresponses.org/governance",
        "title": "Governance",
        "description": "Technical charter and project governance",
    },
    "changelog": {
        "url": "https://www.openresponses.org/changelog",
        "title": "Changelog",
        "description": "Version history and specification updates",
    },
}


def fetch_web_content(url: str) -> str:
    """Fetch content from a URL with error handling"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"  [WARN] Error fetching {url}: {e}")
        return ""
    except Exception as e:
        print(f"  [WARN] Unexpected error fetching {url}: {e}")
        return ""


def extract_main_content(html: str) -> str:
    """Extract main content area from HTML, removing nav/footer/scripts"""
    # Remove script and style tags completely
    html = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<svg[^>]*>.*?</svg>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(
        r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Try to find main content area - common Astro/React patterns
    main_patterns = [
        r"<main[^>]*>(.*?)</main>",
        r"<article[^>]*>(.*?)</article>",
        r'<div[^>]*class="[^"]*(?:_content|_main|prose|markdown|docs)[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*id="[^"]*(?:content|main)[^"]*"[^>]*>(.*?)</div>',
        r'<section[^>]*class="[^"]*(?:content|main)[^"]*"[^>]*>(.*?)</section>',
    ]

    for pattern in main_patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            html = match.group(1)
            break

    return html


def clean_html_to_text(html: str) -> str:
    """Convert HTML to clean text"""
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", html)

    # Decode HTML entities
    entities = {
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quot;": '"',
        "&apos;": "'",
        "&#39;": "'",
        "&nbsp;": " ",
        "&ndash;": "–",
        "&mdash;": "—",
        "&hellip;": "…",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)

    # Clean up whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    lines = text.split("\n")
    cleaned = []
    prev_blank = False
    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned.append(stripped)
            prev_blank = False
        elif not prev_blank:
            cleaned.append("")
            prev_blank = True

    return "\n".join(cleaned).strip()


def extract_first_paragraph(text: str, max_chars: int = 300) -> str:
    """Extract the first meaningful paragraph from text, filtering out nav/header cruft"""
    # Remove common navigation/header text that appears in Astro sites
    nav_patterns = [
        r"Overview\s+Specification\s+Reference\s+Acceptance\s+Tests\s+Governance\s+Changelog",
        r"Skip\s+to\s+content",
        r"Menu\s+Close",
        r"^\s*Open\s+Responses\s*$",
        r"^\s*Overview\s*$",
        r"^\s*Specification\s*$",
        r"^\s*Reference\s*$",
        r"^\s*Acceptance\s+Tests\s*$",
        r"^\s*Governance\s*$",
        r"^\s*Changelog\s*$",
    ]
    for pattern in nav_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

    # Remove duplicate "Open Responses Open Responses" patterns
    text = re.sub(r"Open\s+Responses\s+Open\s+Responses", "Open Responses", text)

    paragraphs = text.split("\n\n")
    for para in paragraphs:
        para = para.strip()
        # Skip if too short or looks like a heading/code/navigation
        if len(para) < 40:
            continue
        if para.startswith("#") or para.startswith("```"):
            continue
        # Skip if it looks like navigation or metadata
        if re.match(
            r"^(Overview|Specification|Reference|Acceptance|Tests|Governance|Changelog|Menu|Close|Skip|Open Responses)\s*$",
            para,
            re.IGNORECASE,
        ):
            continue
        # Clean up excessive whitespace
        para = re.sub(r"\s+", " ", para)
        # Remove leading page titles (e.g., "Specification Open Responses is...")
        para = re.sub(
            r"^(Overview|Specification|Reference|Acceptance Tests|Governance|Changelog)\s+",
            "",
            para,
            flags=re.IGNORECASE,
        )
        # Return first substantial paragraph, truncated
        if len(para) > max_chars:
            para = para[:max_chars].rsplit(" ", 1)[0] + "..."
        return para
    return ""


def extract_section_content(
    text: str, section_patterns: List[str], max_chars: int = 500
) -> str:
    """Extract content from specific sections by heading patterns"""
    for pattern in section_patterns:
        # Look for heading followed by content
        match = re.search(
            pattern + r"[:\s]*\n+(.+?)(?:\n#|\n\n#|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            content = match.group(1).strip()
            # Clean up the content
            content = re.sub(r"\n+", " ", content)
            content = re.sub(r"\s+", " ", content)
            if len(content) > max_chars:
                content = content[:max_chars].rsplit(" ", 1)[0] + "..."
            return content
    return ""


def extract_key_concepts(text: str) -> List[str]:
    """Extract key concepts from specification text"""
    concepts = []

    # Define concept patterns with their descriptions
    concept_patterns = [
        (
            r"Items?\s+(?:are|is)\s+(?:the\s+)?(?:fundamental|core|basic|atomic)\s+(?:unit|building)\s+of[^.\n]{10,150}",
            "Items",
        ),
        (r"Agentic\s+[Ll]oop[^.\n]{0,20}(?:[^.\n]{0,200})", "Agentic Loop"),
        (
            r"Semantic\s+(?:streaming|events)[^.\n]{0,20}(?:[^.\n]{0,200})",
            "Semantic Streaming",
        ),
        (r"State\s+[Mm]achines?[^.\n]{0,20}(?:[^.\n]{0,200})", "State Machines"),
        (r"Multi[-\s]?provider[^.\n]{0,20}(?:[^.\n]{0,200})", "Multi-Provider"),
    ]

    seen = set()
    for pattern, name in concept_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches[:2]:  # Limit matches per pattern
            # Clean up the match
            clean = re.sub(r"\s+", " ", match.strip())
            if len(clean) > 30 and clean.lower() not in seen:
                # Capitalize first letter
                clean = clean[0].upper() + clean[1:] if clean else clean
                concepts.append(clean)
                seen.add(clean.lower())
                break

    # Fallback concepts if extraction failed
    if len(concepts) < 3:
        fallback = [
            "Items are the fundamental unit of context in Open Responses, representing atomic units of model output, tool invocation, or reasoning state",
            "Agentic Loop enables models to perceive input, reason, act through tools, and reflect on outcomes in a unified workflow",
            "Semantic Streaming models streaming as a series of meaningful events rather than raw text deltas",
            "State Machines define valid states and transitions for objects in the API such as in_progress, completed, or failed",
            "Multi-Provider support allows one schema to map cleanly to many model providers while maintaining semantic consistency",
        ]
        existing = {c.lower() for c in concepts}
        for concept in fallback:
            if concept.lower() not in existing:
                concepts.append(concept)
                if len(concepts) >= 5:
                    break

    return concepts[:5]


def extract_api_info(text: str) -> Tuple[List[str], List[str], List[str]]:
    """Extract endpoints, parameters, and streaming events from text"""
    endpoints = []
    parameters = []
    events = []

    # Extract HTTP endpoints
    endpoint_pattern = r"(POST|GET|PUT|DELETE|PATCH)\s+(/[\w\-/.:]+)"
    seen_endpoints = set()
    for method, path in re.findall(endpoint_pattern, text):
        endpoint = f"{method} {path}"
        if endpoint.lower() not in seen_endpoints:
            endpoints.append(endpoint)
            seen_endpoints.add(endpoint.lower())

    # Extract parameter-like patterns (backtick followed by type)
    param_pattern = r"`(\w+)`\s*[:\(]\s*(string|number|integer|boolean|array|object)"
    seen_params = set()
    for name, ptype in re.findall(param_pattern, text, re.IGNORECASE):
        if name.lower() not in seen_params and len(name) > 2:
            parameters.append(f"{name} ({ptype})")
            seen_params.add(name.lower())

    # Also look for common API parameter names
    common_params = [
        "model",
        "input",
        "tools",
        "tool_choice",
        "stream",
        "temperature",
        "top_p",
        "max_tokens",
        "truncation",
        "service_tier",
        "reasoning",
    ]
    for param in common_params:
        if param.lower() not in seen_params and re.search(
            rf"\b{param}\b", text, re.IGNORECASE
        ):
            parameters.append(param)
            seen_params.add(param.lower())

    # Extract streaming events
    event_pattern = r"`?(response\.[\w_\.]+)`?"
    seen_events = set()
    for event in re.findall(event_pattern, text):
        if event.lower() not in seen_events:
            events.append(event)
            seen_events.add(event.lower())

    return endpoints[:8], parameters[:15], events[:12]


def validate_llms_txt(file_path: str) -> Tuple[bool, Dict]:
    """Validate llms.txt against llmstxt.org specification"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    results = {
        "h1_found": any(line.startswith("# ") for line in lines),
        "blockquote_found": any(line.startswith("> ") for line in lines),
        "h2_count": sum(1 for line in lines if line.startswith("## ")),
        "links_found": any(re.search(r"\[.+\]\(.+\)", line) for line in lines),
        "file_size": len(content),
        "line_count": len(lines),
    }

    results["valid"] = (
        results["h1_found"] and results["blockquote_found"] and results["h2_count"] >= 1
    )

    return results["valid"], results


def generate_llms_txt(output_path: str) -> bool:
    """Generate comprehensive llms.txt from all website pages"""

    print("Fetching documentation from live website...\n")

    # Fetch all pages
    page_contents = {}
    for key, info in PAGES.items():
        print(f"  Fetching {info['title']}...")
        html = fetch_web_content(info["url"])
        if html:
            main_html = extract_main_content(html)
            text = clean_html_to_text(main_html)
            page_contents[key] = {
                "text": text,
                "info": info,
            }
            print(f"    [OK] Extracted {len(text)} characters")
        else:
            print(f"    [FAIL] Failed to fetch")
            page_contents[key] = None

    print("\nGenerating llms.txt content...")

    # Build llms.txt content
    content = []

    # Header
    content.append("# Open Responses")
    content.append("")
    content.append(
        "> Open Responses is an open, vendor-neutral specification for large language model APIs that defines a shared schema, consistent streaming/events, and extensible tooling to enable interoperable LLM workflows across different providers."
    )
    content.append("")

    # Core Concepts (from specification)
    spec_data = page_contents.get("specification")
    if spec_data and spec_data["text"]:
        concepts = extract_key_concepts(spec_data["text"])
        if concepts:
            content.append("## Core Concepts")
            content.append("")
            for concept in concepts:
                content.append(f"- {concept}")
            content.append("")

    # API Summary (from reference page)
    ref_data = page_contents.get("reference")
    if ref_data and ref_data["text"]:
        endpoints, params, events = extract_api_info(ref_data["text"])

        if endpoints or params or events:
            content.append("## API Summary")
            content.append("")

            if endpoints:
                content.append("### Endpoints")
                for ep in endpoints:
                    content.append(f"- `{ep}`")
                content.append("")

            if params:
                content.append("### Common Parameters")
                for param in params[:10]:
                    content.append(f"- `{param}`")
                content.append("")

            if events:
                content.append("### Streaming Events")
                for event in events[:8]:
                    content.append(f"- `{event}`")
                content.append("")

    # Documentation Pages with excerpts
    content.append("## Documentation")
    content.append("")

    for key in [
        "overview",
        "specification",
        "reference",
        "compliance",
        "governance",
        "changelog",
    ]:
        data = page_contents.get(key)
        if data and data["text"]:
            info = data["info"]
            excerpt = extract_first_paragraph(data["text"], max_chars=250)

            if excerpt:
                content.append(
                    f"- [{info['title']}]({info['url']}): {info['description']}. {excerpt}"
                )
            else:
                content.append(
                    f"- [{info['title']}]({info['url']}): {info['description']}"
                )

    content.append("")

    # Additional Resources
    content.append("## Additional Resources")
    content.append("")
    content.append(
        "- [cURL Snippets](https://www.openresponses.org/curl_snippets/curl_snippets.yaml): Practical examples for API calls"
    )
    content.append(
        "- [OpenAPI Spec](https://www.openresponses.org/openapi/openapi.json): Complete OpenAPI specification"
    )
    content.append("")

    # Write file
    output_text = "\n".join(content)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"\n[OK] Generated llms.txt ({len(output_text)} bytes, {len(content)} lines)")

    # Validate
    is_valid, results = validate_llms_txt(output_path)

    print("\n[RESULT] Validation Results:")
    print(f"  - H1 heading: {'[OK]' if results['h1_found'] else '[FAIL]'}")
    print(f"  - Blockquote: {'[OK]' if results['blockquote_found'] else '[FAIL]'}")
    print(
        f"  - H2 sections: {results['h2_count']} {'[OK]' if results['h2_count'] >= 1 else '[FAIL]'}"
    )
    print(f"  - Links found: {'[OK]' if results['links_found'] else '[FAIL]'}")
    print(f"  - Overall: {'[OK] VALID' if is_valid else '[FAIL] INVALID'}")

    if not is_valid:
        raise ValueError("Generated llms.txt does not meet llmstxt.org specification")

    return is_valid


def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent
    output_path = project_root / "public" / "llms.txt"

    # Ensure public directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("[GEN] OpenResponses llms.txt Generator")
    print("=" * 60)
    print()

    try:
        success = generate_llms_txt(str(output_path))
        if success:
            print(f"\n[SUCCESS] Success! File written to: {output_path}")
        else:
            print("\n[WARN]  Warning: Validation failed")
            return 1
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
