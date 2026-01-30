#!/usr/bin/env python3
"""
Build script to automatically generate llms.txt from OpenResponses documentation
This script fetches content from the live OpenResponses website and creates a 
concise, sitemap-style llms.txt file similar to the Claude platform format.
"""

import os
import re
import requests
from pathlib import Path
import json
from typing import Dict, List, Optional
from bs4 import BeautifulSoup


def fetch_web_content(url: str) -> str:
    """Fetch content from a URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return ""


def extract_content_from_html(html_content: str) -> str:
    """Extract text content from HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text content
    text = soup.get_text()
    
    # Clean up text
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text


def extract_mdx_like_content_from_html(html_content: str) -> str:
    """Extract content that resembles MDX/markdown from HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Try to extract main content areas
    content_areas = soup.find_all(['main', 'article', 'div'], 
                                  attrs={'class': lambda x: x and ('content' in x or 'main' in x or 'doc' in x or 'page' in x)})
    
    if not content_areas:
        # If no specific content areas found, try to get the main content
        content_areas = [soup.body] if soup.body else [soup]
    
    extracted_content = ""
    for area in content_areas:
        extracted_content += area.get_text(separator='\n') + "\n"
    
    # Clean up text
    lines = (line.strip() for line in extracted_content.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text


def clean_markdown_content(content: str) -> str:
    """Clean markdown content for llms.txt format"""
    # Remove excessive blank lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

    # Clean up markdown artifacts while preserving structure
    # Remove markdown links, keep text: [text](url) -> text
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)

    # Remove image references
    content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'', content)

    # Remove HTML tags that might remain
    content = re.sub(r'<[^>]+>', '', content)

    return content.strip()


def extract_key_info_from_content(content: str) -> dict:
    """Extract key information from the content"""
    key_info = {
        'core_concepts': [],
        'endpoints': [],
        'parameters': [],
        'response_fields': [],
        'streaming_events': []
    }
    
    # Extract core concepts by looking for key phrases
    concepts_patterns = [
        r'(\*\*Items\*\*[^\.]*?)(?=\n\*\*|\n##|\Z)',
        r'(\*\*Agentic Loop\*\*[^\.]*?)(?=\n\*\*|\n##|\Z)',
        r'(\*\*Semantic Streaming\*\*[^\.]*?)(?=\n\*\*|\n##|\Z)',
        r'(\*\*State Machines\*\*[^\.]*?)(?=\n\*\*|\n##|\Z)',
        r'(\*\*Multi-provider\*\*[^\.]*?)(?=\n\*\*|\n##|\Z)',
        r'(\*\*Items → Items\*\*[^\.]*?)(?=\n\*\*|\n##|\Z)',
        r'Items.*?atomic.*?unit',
        r'Agentic.*?loop',
        r'Semantic.*?streaming',
        r'State.*?machines',
        r'Multi.*?provider'
    ]
    
    for pattern in concepts_patterns:
        try:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ''
                if match.strip():
                    # Clean up the match
                    clean_match = re.sub(r'\s+', ' ', match.strip())
                    if len(clean_match) > 10 and clean_match not in key_info['core_concepts']:  # Only add substantial matches
                        key_info['core_concepts'].append(clean_match)
        except re.error:
            # Skip problematic patterns
            continue
    
    # Extract endpoints
    try:
        endpoint_matches = re.findall(r'(POST|GET|PUT|DELETE)\s+(/[\w\/\-]+)', content)
        for method, path in endpoint_matches:
            endpoint = f"{method} {path}"
            if endpoint not in key_info['endpoints']:
                key_info['endpoints'].append(endpoint)
    except re.error:
        pass

    # Extract key parameters by looking for common parameter patterns
    param_patterns = [
        r'`(\w+)`\s+\([^)]*(?:string|number|boolean|integer)',
        r'`(\w+)`\s+.*?(?:parameter|field|argument)',
        r'`(\w+)`.*?(?:input|request|model|tool|stream|temperature|top_p|truncation|service_tier)',
        r'(\w+)\s+\(string\)|(\w+)\s+\(number\)|(\w+)\s+\(boolean\)|(\w+)\s+\(integer\)'
    ]
    
    for pattern in param_patterns:
        try:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match_group in matches:
                # Handle both single matches and groups
                if isinstance(match_group, tuple):
                    match = next((m for m in match_group if m), '')  # Get first non-empty match
                else:
                    match = match_group
                    
                if match and len(match) > 2 and match.lower() not in ['the', 'and', 'for', 'with', 'to', 'of', 'in', 'on', 'at', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'type', 'id', 'name', 'text', 'url', 'data', 'model', 'input', 'tools', 'tool', 'stream', 'temperature', 'top_p']:
                    if match not in key_info['parameters']:
                        key_info['parameters'].append(match)
        except re.error:
            # Skip problematic patterns
            continue

    # Extract response fields
    field_patterns = [
        r'`(\w+)`\s+.*?(?:response|output|status|model|usage|error)',
        r'`(\w+)`\s+.*?(?:field|property|attribute)',
        r'(\w+)\s+.*?(?:response|output|status|model|usage|error)'
    ]
    
    for pattern in field_patterns:
        try:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 2:
                    if match not in key_info['response_fields']:
                        key_info['response_fields'].append(match)
        except re.error:
            # Skip problematic patterns
            continue
    
    # Extract streaming events
    try:
        event_pattern = r'`(response\.[\w_]+)`'
        event_matches = re.findall(event_pattern, content)
        for event in event_matches:
            if event not in key_info['streaming_events']:
                key_info['streaming_events'].append(event)
    except re.error:
        pass

    # Deduplicate lists and limit to reasonable sizes
    key_info['core_concepts'] = key_info['core_concepts'][:5]  # Limit to 5 concepts
    key_info['endpoints'] = key_info['endpoints'][:10]  # Limit to 10 endpoints
    key_info['parameters'] = key_info['parameters'][:20]  # Limit to 20 parameters
    key_info['response_fields'] = key_info['response_fields'][:20]  # Limit to 20 fields
    key_info['streaming_events'] = key_info['streaming_events'][:15]  # Limit to 15 events
    
    return key_info


def validate_llms_txt(file_path: str) -> tuple:
    """Validate the generated llms.txt file against the llmstxt.org specification"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # Check for required elements per llmstxt.org specification
    h1_found = any(line.startswith('# ') for line in lines)
    blockquote_found = any(line.startswith('> ') for line in lines)
    h2_count = sum(1 for line in lines if line.startswith('## '))
    links_found = any('[' in line and ']' in line and '(' in line and ')' in line for line in lines)

    # Validation results
    validation_results = {
        'h1_found': h1_found,
        'blockquote_found': blockquote_found,
        'h2_count': h2_count,
        'links_found': links_found,
        'valid': h1_found and blockquote_found and h2_count >= 1
    }

    # Print validation results
    print("llmstxt.org Specification Validation:")
    print(f"- H1 heading found: {h1_found}")
    print(f"- Blockquote summary found: {blockquote_found}")
    print(f"- H2 sections found: {h2_count} (minimum 1 required)")
    print(f"- Links found: {links_found}")
    print(f"- Overall validity: {validation_results['valid']}")

    if not validation_results['valid']:
        print("\nValidation errors:")
        if not h1_found:
            print("  - Missing H1 heading (should start with '# ')")
        if not blockquote_found:
            print("  - Missing blockquote summary (should start with '> ')")
        if h2_count < 1:
            print("  - Need at least 1 H2 section (should start with '## ')")

    return validation_results['valid'], validation_results


def generate_llms_txt_from_docs(docs_dir: str, output_path: str):
    """Generate llms.txt from documentation files in Claude-like format"""
    
    # URLs to fetch content from
    urls = {
        'overview': 'https://www.openresponses.org/',
        'specification': 'https://www.openresponses.org/specification',
        'reference': 'https://www.openresponses.org/reference',
        'compliance': 'https://www.openresponses.org/compliance',
        'governance': 'https://www.openresponses.org/governance',
        'changelog': 'https://www.openresponses.org/changelog'
    }
    
    # Initialize content
    llms_content = []

    # Add main title
    llms_content.append("# Open Responses")
    llms_content.append("")
    llms_content.append("> Open Responses is an open, vendor-neutral specification for large language model APIs that defines a shared schema, consistent streaming/events, and extensible tooling to enable interoperable LLM workflows across different providers. It standardizes LLM interfaces while maintaining flexibility for provider-specific extensions and advanced agentic capabilities.")
    llms_content.append("")

    # Fetch content from specification page to extract key information
    spec_content = ""
    spec_html = fetch_web_content(urls['specification'])
    if spec_html:
        spec_content = extract_mdx_like_content_from_html(spec_html)
        spec_content = clean_markdown_content(spec_content)
        key_info = extract_key_info_from_content(spec_content)
        
        # Add Core Concepts section
        if key_info['core_concepts']:
            llms_content.append("## Core Concepts")
            llms_content.append("")
            for concept in key_info['core_concepts']:
                llms_content.append(f"- {concept}")
            llms_content.append("")
        
        # Add API section if we have endpoints or parameters
        if key_info['endpoints'] or key_info['parameters']:
            llms_content.append("## API")
            llms_content.append("")
            if key_info['endpoints']:
                llms_content.append("### Endpoints")
                for endpoint in key_info['endpoints']:
                    llms_content.append(f"- `{endpoint}`")
                llms_content.append("")
            
            if key_info['parameters']:
                llms_content.append("### Key Parameters")
                for param in key_info['parameters']:
                    llms_content.append(f"- `{param}`")
                llms_content.append("")
        
        # Add Streaming Events section
        if key_info['streaming_events']:
            llms_content.append("## Streaming Events")
            llms_content.append("")
            for event in key_info['streaming_events']:
                llms_content.append(f"- `{event}`")
            llms_content.append("")

    # Add Resources section (similar to Claude format)
    llms_content.append("## Resources")
    llms_content.append("")
    llms_content.append("- [API Reference](https://www.openresponses.org/reference): Detailed API documentation with all endpoints, parameters, and response structures")
    llms_content.append("- [Specification](https://www.openresponses.org/specification): Complete technical specification with detailed concepts and implementation guidelines")
    llms_content.append("- [Compliance](https://www.openresponses.org/compliance): Acceptance tests and validation procedures")
    llms_content.append("- [Governance](https://www.openresponses.org/governance): Technical charter and governance structure")
    llms_content.append("- [Changelog](https://www.openresponses.org/changelog): Version history and updates")
    llms_content.append("")

    # Add Documentation section
    llms_content.append("## Documentation")
    llms_content.append("")
    llms_content.append("- [Overview](https://www.openresponses.org/): Introduction to Open Responses")
    llms_content.append("- [Specification](https://www.openresponses.org/specification): Complete technical specification")
    llms_content.append("- [API Reference](https://www.openresponses.org/reference): Detailed API documentation")
    llms_content.append("- [Compliance](https://www.openresponses.org/compliance): Acceptance tests and validation")
    llms_content.append("- [Governance](https://www.openresponses.org/governance): Technical charter and governance structure")
    llms_content.append("- [Changelog](https://www.openresponses.org/changelog): Version history and updates")
    llms_content.append("")

    # Add Examples section
    llms_content.append("## Examples")
    llms_content.append("")
    llms_content.append("- [cURL Snippets](https://www.openresponses.org/curl_snippets/curl_snippets.yaml): YAML file with cURL examples for various API calls")
    llms_content.append("- [OpenAPI Specification](https://www.openresponses.org/openapi/openapi.json): Complete OpenAPI specification in JSON format")
    llms_content.append("")

    # Write to output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(llms_content))

    print(f"Generated llms.txt with {len(llms_content)} lines")

    # Validate the generated file
    is_valid, validation_results = validate_llms_txt(output_path)

    if is_valid:
        print(f"\nllms.txt file successfully validated against llmstxt.org specification!")
        print(f"File location: {output_path}")
        print(f"Structure: 1 H1 + blockquote + {validation_results['h2_count']} H2 sections + links")
    else:
        print(f"\nllms.txt file failed validation against llmstxt.org specification!")
        raise ValueError("Generated llms.txt file does not meet llmstxt.org specification requirements")

    return is_valid


def main():
    """Main function to run the generator"""
    # Define paths relative to the project root
    # When script is in bin/, need to go up one level to reach project root
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / "src" / "pages"
    output_path = project_root / "public" / "llms.txt"

    # Ensure public directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Generating llms.txt from live website documentation...")
    try:
        success = generate_llms_txt_from_docs(str(docs_dir), str(output_path))
        if success:
            print(f"\nllms.txt generation completed successfully!")
            print(f"Generated file location: {output_path}")
            print(f"File size: {output_path.stat().st_size} bytes")
        else:
            print("\nllms.txt generation failed validation!")
    except Exception as e:
        print(f"\nError during llms.txt generation: {str(e)}")
        raise


if __name__ == "__main__":
    main()